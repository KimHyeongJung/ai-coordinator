"""
의류 업로드 파이프라인: BLIP 캡셔닝 → LLM 정보 추출 → Supabase 저장.

기존 estimate_calories LCEL 체인 패턴을 그대로 재사용한다.
"""

from __future__ import annotations

import logging
import os
import tempfile

from huggingface_hub import InferenceClient
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from PIL import Image

import dashboard
import storage
from model_config import LLM_MODEL, VISION_MODEL, get_token

logger = logging.getLogger(__name__)

CLOTHING_SYSTEM_PROMPT = """
너는 패션 전문가 AI다. 영어로 된 의류 이미지 캡션을 분석해 의류 정보를 JSON으로 추출해라.
반드시 아래 JSON 형식만 출력하고, 다른 텍스트/마크다운/코드블록 금지.
{{"category": str, "name": str, "color": str, "material": str,
 "style": str, "season": [str], "wash_instruction": str, "note": str}}
- category: 상의/하의/아우터/신발/악세서리/스포츠/기타 중 하나
- name: 구체적인 한국어 의류명 (예: 화이트 오버사이즈 크롭 티셔츠)
- season: 적합한 계절 배열 (봄/여름/가을/겨울 중 복수 가능)
- material: 캡션에서 추정 불가 시 "추정 불가" 입력
- wash_instruction: 소재 기반 세탁 방법 한 줄로 작성
"""

_vision_client: InferenceClient | None = None
_clothing_chain = None


def _vision_lazy() -> InferenceClient:
    global _vision_client
    if _vision_client is None:
        _vision_client = InferenceClient(token=get_token())
    return _vision_client


def _chain_lazy():
    """LCEL 체인: prompt | ChatHuggingFace | JsonOutputParser"""
    global _clothing_chain
    if _clothing_chain is None:
        endpoint = HuggingFaceEndpoint(
            repo_id=LLM_MODEL,
            task="text-generation",
            max_new_tokens=400,
            temperature=0.2,
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
    """BLIP으로 의류 이미지 캡션 생성. 기존 tempfile 패턴 사용."""
    client = _vision_lazy()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        image.convert("RGB").save(tmp, format="JPEG")
        tmp_path = tmp.name
    try:
        result = client.image_to_text(tmp_path, model=VISION_MODEL)
        # huggingface_hub 버전에 따라 str 또는 ImageToTextOutput 반환
        return result.generated_text if hasattr(result, "generated_text") else str(result)
    except Exception as e:
        logger.error("caption_clothing 실패: %s", e)
        return "a clothing item on a hanger"
    finally:
        os.unlink(tmp_path)


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
            "material": "추정 불가",
            "style": "캐주얼",
            "season": ["봄", "가을"],
            "wash_instruction": "라벨 확인",
            "note": f"분석 실패: {str(e)[:100]}",
        }


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
    size: str,
    price: str,
    purchase_date: str,
) -> tuple[str, list]:
    """
    전체 파이프라인 함수 (Gradio 콜백으로 직접 연결).
    gr.Image(type="filepath")에서 파일 경로를 받아 직접 PIL로 열어
    Gradio의 한글 파일명 버그를 우회한다.
    1. PIL 로드 → 2. BLIP 캡셔닝 → 3. LLM 정보 추출 → 4. Supabase 저장
    반환: (결과 메시지, 현재 옷장 테이블 데이터)
    """
    if image_path is None:
        return "이미지를 먼저 업로드해 주세요.", dashboard.get_wardrobe_table()

    try:
        image = _load_image_from_path(image_path)
        caption = caption_clothing(image)
        info = extract_clothing_info(caption)

        item = {
            "category": info.get("category", "기타"),
            "name": info.get("name", "알 수 없는 의류"),
            "color": info.get("color", ""),
            "material": info.get("material", ""),
            "style": info.get("style", ""),
            "season": info.get("season", []),
            "wash_instruction": info.get("wash_instruction", ""),
            "size": size.strip() if size else None,
            "price": price.strip() if price else None,
            "purchase_date": purchase_date.strip() if purchase_date else None,
            "image_path": None,
        }

        saved = storage.add_item(item)

        if saved.get("id"):
            msg = (
                f"✅ 저장 완료!\n"
                f"이름: {item['name']}\n"
                f"카테고리: {item['category']}\n"
                f"색상: {item['color']}\n"
                f"계절: {', '.join(item['season'])}\n"
                f"AI 분석 캡션: {caption[:80]}..."
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
