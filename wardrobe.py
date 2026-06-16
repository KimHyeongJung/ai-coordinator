"""
의류 업로드 파이프라인: Florence-2 캡셔닝 → LLM 정보 추출 → Supabase 저장.

Florence-2 모델을 transformers로 로컬에서 직접 로드한다.
HF Spaces Docker 환경에서는 외부 Inference API 네트워크가 차단되므로
requests 방식 대신 로컬 추론을 사용한다.
"""

from __future__ import annotations

import io
import logging
import os
import uuid

import torch
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

import dashboard
import storage
from model_config import LLM_MODEL, VISION_MODEL, get_token

logger = logging.getLogger(__name__)

_florence_model = None
_florence_processor = None


def _load_florence():
    """Florence-2 모델과 프로세서를 최초 1회만 로드한다 (lazy init)."""
    global _florence_model, _florence_processor
    if _florence_model is None:
        logger.info("Florence-2 모델 로딩 중: %s", VISION_MODEL)
        _florence_processor = AutoProcessor.from_pretrained(
            VISION_MODEL, trust_remote_code=True
        )
        _florence_model = AutoModelForCausalLM.from_pretrained(
            VISION_MODEL, trust_remote_code=True, torch_dtype=torch.float32
        )
        _florence_model.eval()
        logger.info("Florence-2 모델 로드 완료")
    return _florence_model, _florence_processor

CLOTHING_SYSTEM_PROMPT = """패션 AI. 캡션을 분석해 아래 JSON만 출력. 다른 텍스트·코드블록 금지.
{{"category":str,"name":str,"color":str,"style":[str],"season":[str],"wash_instruction":str}}
category: 상의/하의/아우터/신발/가방/악세서리/기타 중 하나 (가방→"가방", 스포츠→"상의"/"하의")
name: 한국어 의류명 (예: 네이비 슬림핏 치노 팬츠)
color: 한국어 색상명
style: 클래식/스포티/포멀/캐주얼/미니멀 중 해당하는 것 배열 (복수 가능)
season: 봄/여름/가을/겨울 중 해당하는 것 배열
wash_instruction: 한국어 세탁법 한 줄
모든 값 한국어만. 영어·한자 금지."""

_clothing_chain = None


def _chain_lazy():
    """LCEL 체인: prompt | ChatHuggingFace | JsonOutputParser"""
    global _clothing_chain
    if _clothing_chain is None:
        endpoint = HuggingFaceEndpoint(
            repo_id=LLM_MODEL,
            task="text-generation",
            max_new_tokens=200,
            temperature=0.1,
            huggingfacehub_api_token=get_token(),
        )
        llm = ChatHuggingFace(llm=endpoint)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CLOTHING_SYSTEM_PROMPT),
                ("human", "다음 캡션을 분석해줘: {caption}"),
            ]
        )
        _clothing_chain = prompt | llm | JsonOutputParser()
    return _clothing_chain


def caption_clothing(image: Image.Image) -> str:
    """
    Florence-2로 의류 이미지 캡션 생성 (로컬 추론).
    HF Spaces Docker 환경에서 외부 API 없이 직접 실행한다.
    실패 시 빈 문자열 반환 (analyze_and_save에서 저장 차단).
    """
    try:
        model, processor = _load_florence()
        rgb_image = image.convert("RGB")

        # 이미지 리사이즈: 비전 인코더 처리 속도 향상
        rgb_image.thumbnail((512, 512))

        task = "<DETAILED_CAPTION>"
        inputs = processor(text=task, images=rgb_image, return_tensors="pt")

        with torch.no_grad():
            generated_ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=128,
                num_beams=1,          # greedy: 빔서치 대비 ~3배 빠름
                do_sample=False,
            )

        raw = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed = processor.post_process_generation(
            raw, task=task, image_size=(rgb_image.width, rgb_image.height)
        )
        caption = parsed.get(task, "").strip()

        if not caption:
            raise ValueError(f"빈 캡션 반환: {repr(parsed)}")

        logger.info("caption_clothing 성공: %s", caption[:80])
        return caption

    except Exception as e:
        logger.error("caption_clothing 실패: [%s] %s", type(e).__name__, repr(e))
        return ""


def extract_clothing_info(caption: str) -> dict:
    """LCEL 체인으로 캡션 → 구조화된 의류 정보 JSON 추출."""
    chain = _chain_lazy()
    try:
        return chain.invoke({"caption": caption})
    except Exception as e:
        logger.error("extract_clothing_info 실패: %s", e)
        return {
            "category": "기타",
            "name": "알 수 없는 의류",
            "color": "",
            "style": ["캐주얼"],
            "season": ["봄", "가을"],
            "wash_instruction": "라벨 확인",
        }


_VALID_CATEGORIES = {"상의", "하의", "아우터", "신발", "가방", "악세서리", "기타"}

# LLM이 영어나 비표준 값을 반환할 때 매핑
_CATEGORY_NORMALIZE: dict[str, str] = {
    # 영어
    "top": "상의", "tops": "상의", "shirt": "상의", "t-shirt": "상의",
    "blouse": "상의", "sweater": "상의", "knit": "상의",
    "bottom": "하의", "bottoms": "하의", "pants": "하의", "jeans": "하의",
    "skirt": "하의", "shorts": "하의", "trousers": "하의",
    "outer": "아우터", "jacket": "아우터", "coat": "아우터", "outerwear": "아우터",
    "shoes": "신발", "shoe": "신발", "sneakers": "신발", "boots": "신발",
    "sandals": "신발", "loafers": "신발", "heels": "신발",
    "bag": "가방", "bags": "가방", "backpack": "가방", "purse": "가방",
    "handbag": "가방", "tote": "가방", "clutch": "가방",
    "accessory": "악세서리", "accessories": "악세서리",
    "hat": "악세서리", "belt": "악세서리", "scarf": "악세서리",
    "sports": "상의", "sportswear": "상의",
    # 한국어 비표준 표기
    "악세사리": "악세서리",
    "스포츠": "상의",
    "액세서리": "악세서리",
}


def _normalize_category(raw: str | None) -> str:
    """LLM 카테고리 출력을 드롭다운 허용값으로 정규화."""
    if not raw:
        return "기타"
    s = raw.strip()
    if s in _VALID_CATEGORIES:
        return s
    mapped = _CATEGORY_NORMALIZE.get(s) or _CATEGORY_NORMALIZE.get(s.lower())
    return mapped if mapped in _VALID_CATEGORIES else "기타"


_VALID_STYLES = {"클래식", "스포티", "포멀", "캐주얼", "미니멀"}

_STYLE_NORMALIZE: dict[str, str] = {
    "classic": "클래식", "formal": "포멀", "casual": "캐주얼",
    "sporty": "스포티", "sport": "스포티", "athletic": "스포티",
    "minimal": "미니멀", "minimalist": "미니멀", "minimalistic": "미니멀",
    "스트리트": "캐주얼", "street": "캐주얼", "비즈니스": "포멀",
    "모던": "미니멀", "modern": "미니멀", "엘레강스": "클래식",
    "엘레강트": "클래식", "elegant": "클래식",
}


def _normalize_style(raw) -> list[str]:
    """LLM 스타일 출력을 유효한 스타일 배열로 정규화."""
    if not raw:
        return ["캐주얼"]
    items = raw if isinstance(raw, list) else [raw]
    result = []
    for s in items:
        s = str(s).strip()
        if s in _VALID_STYLES:
            result.append(s)
        else:
            mapped = _STYLE_NORMALIZE.get(s) or _STYLE_NORMALIZE.get(s.lower())
            if mapped:
                result.append(mapped)
    return result if result else ["캐주얼"]


def _load_image_from_path(image_path: str) -> Image.Image:
    """
    filepath 모드에서 Gradio가 전달한 경로로 PIL Image 로드.
    한글 파일명 등으로 경로가 맞지 않을 때 디렉토리 검색으로 폴백.
    """
    if os.path.exists(image_path):
        return Image.open(image_path).convert("RGB")

    # 파일이 없으면 같은 디렉토리에서 임의 이미지 파일 탐색 (인코딩 불일치 대응)
    dir_path = os.path.dirname(image_path)
    if dir_path and os.path.isdir(dir_path):
        IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        candidates = [
            f for f in os.listdir(dir_path)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS
        ]
        if candidates:
            return Image.open(os.path.join(dir_path, candidates[0])).convert("RGB")

    raise FileNotFoundError(
        f"이미지 파일을 찾을 수 없습니다: {image_path}\n"
        "파일명을 영문으로 변경 후 다시 시도해 주세요."
    )


def analyze_and_save(
    image_path: str | None,
    manual_description: str,
    size: str,
    price: str,
    purchase_date: str,
) -> tuple[str, list]:
    """
    전체 파이프라인 함수 (Gradio 콜백으로 직접 연결).
    manual_description이 있으면 BLIP을 건너뛰고 해당 텍스트를 캡션으로 사용한다.
    image_path가 있으면: PIL 로드 → BLIP 캡셔닝 → LLM 정보 추출 → Supabase 저장
    반환: (결과 메시지, 현재 옷장 테이블 데이터)
    """
    manual = (manual_description or "").strip()

    if image_path is None and not manual:
        return "이미지를 업로드하거나 직접 설명을 입력해 주세요.", dashboard.get_wardrobe_table()

    try:
        # 캡션 결정: 직접 입력 우선 → BLIP 자동 분석
        if manual:
            caption = manual
            caption_source = "수동 입력"
        else:
            image = _load_image_from_path(image_path)
            caption = caption_clothing(image)
            caption_source = "AI(BLIP)"

            if not caption:
                return (
                    "❌ AI 이미지 분석 실패 — HF Inference API에 연결할 수 없습니다.\n\n"
                    "아래 두 가지 방법으로 해결하세요:\n"
                    "  1) 잠시 후(1~2분) 다시 시도 (BLIP 모델 콜드 스타트)\n"
                    "  2) '직접 설명' 필드에 의류 설명을 입력하고 다시 클릭\n"
                    "     예: 네이비 체크 반소매 오버사이즈 셔츠",
                    dashboard.get_wardrobe_table(),
                )

        info = extract_clothing_info(caption)

        # 이미지 Supabase Storage 업로드
        uploaded_image_url = None
        if image_path:
            try:
                ext = os.path.splitext(image_path)[1] or ".jpg"
                filename = f"{uuid.uuid4().hex}{ext}"
                uploaded_image_url = storage.upload_image(image_path, filename)
            except Exception as e:
                logger.warning("이미지 업로드 실패 (계속 진행): %s", e)

        item = {
            "category": _normalize_category(info.get("category")),
            "name": info.get("name", "알 수 없는 의류"),
            "color": info.get("color", ""),
            "material": info.get("material", ""),
            "style": _normalize_style(info.get("style")),
            "season": info.get("season", []),
            "wash_instruction": info.get("wash_instruction", ""),
            "size": size.strip() if size else None,
            "price": price.strip() if price else None,
            "purchase_date": purchase_date.strip() if purchase_date else None,
            "image_path": uploaded_image_url,
        }

        saved = storage.add_item(item)

        season_str = ", ".join(item["season"]) if isinstance(item["season"], list) else str(item["season"])
        if saved.get("id"):
            msg = (
                f"✅ 저장 완료! ({caption_source})\n"
                f"이름: {item['name']}\n"
                f"카테고리: {item['category']}\n"
                f"색상: {item['color']}\n"
                f"계절: {season_str}\n"
                f"분석 근거: {caption[:80]}"
            )
        else:
            msg = (
                f"⚠️ AI 분석 완료 (DB 저장 실패 — SUPABASE_URL/KEY 확인 필요)\n"
                f"이름: {item['name']} | 카테고리: {item['category']}"
            )

        return msg, dashboard.get_wardrobe_table()

    except Exception as e:
        logger.error("analyze_and_save 실패: %s", e)
        return f"❌ 처리 실패: {str(e)[:200]}", dashboard.get_wardrobe_table()
