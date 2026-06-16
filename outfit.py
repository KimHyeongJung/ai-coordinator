"""
AI 코디 자동 생성: 옷장 아이템 목록 → LLM → 코디 JSON → Supabase 저장.
"""

from __future__ import annotations

import json
import logging
import random

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

import dashboard
import storage
from model_config import LLM_MODEL, get_token

logger = logging.getLogger(__name__)

# ── 상황별 허용 스타일 ────────────────────────────────────────────────────────
_SITUATION_STYLES: dict[str, set[str]] = {
    "회사":   {"클래식", "포멀", "미니멀", "캐주얼"},
    "운동":   {"스포티"},
    "데이트": {"클래식", "포멀", "미니멀", "캐주얼"},
    "경조사": {"클래식", "포멀"},
    "기타":   {"클래식", "스포티", "포멀", "캐주얼", "미니멀"},
}

# 운동 상황에 스포티 아이템이 없을 때 허용할 폴백 스타일
_SPORTY_FALLBACK = {"캐주얼"}

# ── 상황별 색상 지침 (LLM 프롬프트 삽입용) ────────────────────────────────────
_SITUATION_COLOR_GUIDE: dict[str, str] = {
    "회사":   "차분한 색상 계열(네이비, 그레이, 베이지, 브라운, 블랙, 화이트 등) 우선 선택",
    "운동":   "차분한 색상 계열(블랙, 그레이, 네이비, 화이트 등) 우선 선택",
    "데이트": "모든 색상 허용 — 상황에 어울리는 색상 자유 선택",
    "경조사": "블랙 계열 필수. 상의(셔츠)는 화이트도 허용. 화려하거나 밝은 색상(빨강·노랑·형광 등) 절대 금지",
    "기타":   "상황에 어울리는 색상 자유 선택",
}

OUTFIT_SYSTEM_PROMPT = """
너는 스타일리스트 AI다. 주어진 카테고리별 옷장 목록에서 상황과 계절에 맞는 코디를 구성해라.
반드시 아래 JSON 형식만 출력하고, 다른 텍스트/마크다운/코드블록 금지.
{{"name": str, "item_ids": [str], "tags": [str], "reason": str}}

[필수 구성 규칙]
1. 상의: 반드시 1개만 선택, 복수 선택하면 안됨
2. 하의: 반드시 1개만 선택, 복수 선택하면 안됨
3. 신발: 반드시 1개만 선택, 복수 선택하면 안됨
4. 아우터: {outer_rule}
5. 악세서리·가방: 절대 선택 금지 — 코디 구성에서 완전 제외

[스타일 규칙]
허용 스타일: {allowed_styles}
위 스타일에 해당하는 의류만 선택할 것. 스타일 정보가 없는 아이템은 선택 가능.

[색상 규칙]
{color_rule}

- item_ids: 위 규칙에 따라 선택한 아이템 id 배열 (최소 3개)
- tags: 코디 태그 배열 (예: ["캐주얼", "봄", "데일리"])
- reason: 이 코디를 선택한 이유 (한국어 2~3문장)
- name: 코디명 — 반드시 "[계절] [상황] [스타일키워드]" 형식으로 작성. 예: "봄 회사 미니멀", "겨울 데이트 클래식", "여름 운동 스포티". 아래 기존 코디명과 절대 중복 금지: {existing_names}

언어 규칙: 모든 텍스트는 반드시 한국어로만 작성. 영어·한자(漢字·中文) 사용 절대 금지.
"""

_outfit_chain = None


def _chain_lazy():
    global _outfit_chain
    if _outfit_chain is None:
        endpoint = HuggingFaceEndpoint(
            repo_id=LLM_MODEL,
            task="text-generation",
            max_new_tokens=500,
            temperature=0.3,
            huggingfacehub_api_token=get_token(),
        )
        llm = ChatHuggingFace(llm=endpoint)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", OUTFIT_SYSTEM_PROMPT),
                ("human", "상황: {situation}\n계절: {season}\n\n카테고리별 옷장 목록:\n{wardrobe_json}"),
            ]
        )
        _outfit_chain = prompt | llm | JsonOutputParser()
    return _outfit_chain


def _build_outer_rule(season: str) -> str:
    """규칙5: 계절 기준으로만 아우터 필요 여부를 판단."""
    if season == "겨울":
        return "필수 포함 — 겨울에는 아우터 필수. 아우터 카테고리에서 반드시 1개 선택"
    if season == "가을":
        return "필수 포함 — 가을에는 아우터 필수. 아우터 카테고리에서 반드시 1개 선택"
    if season == "봄":
        return "선택 권장 — 봄에는 가벼운 아우터가 어울림. 아우터 카테고리에 있으면 1개 선택 권장"
    # 여름
    return "제외 — 여름에는 아우터 선택 금지"


def _group_by_category(items: list) -> dict:
    """아이템을 카테고리별로 그룹화."""
    groups: dict[str, list] = {}
    for item in items:
        cat = item.get("category", "기타")
        groups.setdefault(cat, []).append(item)
    return groups


def _filter_by_season(items: list, season: str) -> list:
    """선택한 계절에 맞는 의류만 반환."""
    matched = []
    for item in items:
        item_seasons = item.get("season") or []
        if isinstance(item_seasons, str):
            item_seasons = [s.strip() for s in item_seasons.split(",") if s.strip()]
        if not item_seasons or season in item_seasons or "사계절" in item_seasons:
            matched.append(item)
    return matched


def _filter_by_style(items: list, situation: str) -> list:
    """상황에 허용된 스타일의 의류만 반환. 스타일 정보 없는 아이템은 항상 포함."""
    allowed = _SITUATION_STYLES.get(situation, _SITUATION_STYLES["기타"])

    # 운동 상황: 스포티 아이템이 없으면 캐주얼 폴백 허용
    if situation == "운동":
        has_sporty = any(
            any(s in allowed for s in (it.get("style") or []))
            for it in items
        )
        if not has_sporty:
            allowed = allowed | _SPORTY_FALLBACK

    matched = []
    for item in items:
        item_styles = item.get("style") or []
        if isinstance(item_styles, str):
            try:
                parsed = json.loads(item_styles)
                item_styles = parsed if isinstance(parsed, list) else [parsed]
            except (json.JSONDecodeError, ValueError):
                item_styles = [s.strip() for s in item_styles.split(",") if s.strip()]
        if not item_styles or any(s in allowed for s in item_styles):
            matched.append(item)
    return matched


def _pick_fallback(groups: dict, category: str, used_ids: set) -> str | None:
    """해당 카테고리에서 아직 사용되지 않은 아이템 1개를 랜덤 선택."""
    candidates = [it for it in groups.get(category, []) if it["id"] not in used_ids]
    if not candidates:
        candidates = groups.get(category, [])
    if not candidates:
        return None
    return random.choice(candidates)["id"]


def _validate_and_fix(
    result: dict,
    groups: dict,
    season_groups: dict,
    situation: str,
    season: str,
) -> dict:
    """
    LLM 결과 검증 및 보정:
    - 악세서리·가방 제거 (규칙3·4)
    - 필수 카테고리(상의/하의/신발) 누락 시 자동 보완 (규칙2)
    - 아우터 계절 기준 보완 (규칙5)
    """
    all_items = {it["id"]: it for cats in groups.values() for it in cats}

    selected_ids: list[str] = result.get("item_ids") or []

    # 규칙3·4: 악세서리·가방 제거
    excluded_cats = {"악세서리", "가방"}
    selected_ids = [
        iid for iid in selected_ids
        if iid in all_items and all_items[iid].get("category") not in excluded_cats
    ]

    selected_cats = {all_items[iid]["category"] for iid in selected_ids if iid in all_items}
    used_ids = set(selected_ids)

    # 규칙2: 필수 카테고리 보완
    for cat in ["상의", "하의", "신발"]:
        if cat not in selected_cats and cat in groups:
            fid = _pick_fallback(groups, cat, used_ids)
            if fid:
                selected_ids.append(fid)
                used_ids.add(fid)
                selected_cats.add(cat)

    # 규칙5: 아우터 계절 기준 보완
    outer_required = season in {"가을", "겨울"}
    if outer_required and "아우터" not in selected_cats:
        # 계절 필터된 아우터 우선, 없으면 전체 아우터
        outer_pool = season_groups.get("아우터") or groups.get("아우터", [])
        candidates = [it for it in outer_pool if it["id"] not in used_ids]
        if candidates:
            fid = random.choice(candidates)["id"]
            selected_ids.append(fid)

    result["item_ids"] = selected_ids
    return result


def _make_unique_name(name: str, existing: set[str]) -> str:
    """이미 존재하는 코디명이면 숫자 접미사를 붙여 고유하게 만든다."""
    if name not in existing:
        return name
    i = 2
    while f"{name} {i}" in existing:
        i += 1
    return f"{name} {i}"


def generate_outfit(situation: str, season: str) -> dict:
    """옷장 아이템을 조합해 코디 JSON을 생성한다."""
    wardrobe = storage.load_wardrobe()
    items = wardrobe.get("items", [])

    if not items:
        return {
            "name": "옷장 비어있음",
            "item_ids": [],
            "tags": [],
            "reason": "옷장에 등록된 의류가 없습니다. 먼저 옷장 탭에서 의류를 추가해 주세요.",
        }

    all_groups = _group_by_category(items)

    # 1단계: 계절 필터링
    season_items = _filter_by_season(items, season)
    season_groups = _group_by_category(season_items)

    # 2단계: 스타일 필터링 (규칙1)
    style_items = _filter_by_style(season_items, situation)
    groups = _group_by_category(style_items)

    # 필수 카테고리가 비면 계절 필터 → 전체 순으로 폴백
    for cat in ["상의", "하의", "신발"]:
        if cat not in groups:
            groups[cat] = season_groups.get(cat) or all_groups.get(cat, [])

    # 악세서리·가방은 LLM에 아예 전달하지 않음 (규칙3·4)
    excluded_cats = {"악세서리", "가방"}

    wardrobe_summary: dict[str, list] = {}
    for cat, cat_items in groups.items():
        if cat in excluded_cats:
            continue
        wardrobe_summary[cat] = [
            {
                "id": it["id"],
                "name": it.get("name", ""),
                "color": it.get("color", ""),
                "style": it.get("style", []),
                "season": it.get("season", []),
            }
            for it in cat_items
        ]

    allowed_styles = "·".join(sorted(_SITUATION_STYLES.get(situation, _SITUATION_STYLES["기타"])))
    outer_rule = _build_outer_rule(season)
    color_rule = _SITUATION_COLOR_GUIDE.get(situation, _SITUATION_COLOR_GUIDE["기타"])

    existing_outfit_names: set[str] = {
        o.get("name", "") for o in storage.load_outfits().get("outfits", [])
    }
    existing_names_str = (
        "、".join(f'"{n}"' for n in existing_outfit_names if n) or "없음"
    )

    chain = _chain_lazy()
    try:
        result = chain.invoke(
            {
                "situation": situation,
                "season": season,
                "outer_rule": outer_rule,
                "allowed_styles": allowed_styles,
                "color_rule": color_rule,
                "existing_names": existing_names_str,
                "wardrobe_json": json.dumps(wardrobe_summary, ensure_ascii=False),
            }
        )
        result = _validate_and_fix(result, groups, season_groups, situation, season)

        # LLM이 중복 이름을 반환했을 경우 후처리로 고유 이름 보장
        raw_name = result.get("name") or f"{season} {situation} 코디"
        result["name"] = _make_unique_name(raw_name, existing_outfit_names)

        return result
    except Exception as e:
        logger.error("generate_outfit 실패: %s", e)
        return {
            "name": "코디 생성 실패",
            "item_ids": [],
            "tags": [],
            "reason": f"오류: {str(e)[:100]}",
        }


_VALID_SITUATIONS = {"회사", "데이트", "운동", "경조사", "기타"}
_VALID_SEASONS = {"봄", "여름", "가을", "겨울"}


def generate_outfit_ui(situation: str, season: str) -> tuple[str, list]:
    """
    Gradio 콜백용 래퍼.
    코디를 생성하고 DB에 저장한 뒤 (결과 메시지, 코디 테이블) 반환.
    """
    result = generate_outfit(situation, season)

    saved_situation = situation if situation in _VALID_SITUATIONS else "기타"
    saved_season = season if season in _VALID_SEASONS else "봄"

    if result.get("item_ids"):
        outfit_name = result.get("name") or f"{saved_situation} 코디"
        tags = result.get("tags") or []

        all_items = {it["id"]: it for it in storage.load_wardrobe().get("items", [])}
        cats_included = sorted({
            all_items[iid].get("category", "")
            for iid in result["item_ids"]
            if iid in all_items
        })

        storage.add_outfit(
            {
                "name": outfit_name,
                "item_ids": result["item_ids"],
                "tags": tags,
                "situation": saved_situation,
                "season": saved_season,
                "ai_generated": True,
            }
        )
        tags_str = ", ".join(tags) if tags else "-"
        msg = (
            f"✅ 코디 생성 완료!\n"
            f"코디명: {outfit_name}\n"
            f"상황: {saved_situation} | 계절: {saved_season}\n"
            f"구성: {', '.join(cats_included)}\n"
            f"태그: {tags_str}"
        )
    else:
        msg = f"ℹ️ {result.get('reason', '코디를 생성할 수 없습니다.')}"

    return msg, dashboard.get_outfit_table()
