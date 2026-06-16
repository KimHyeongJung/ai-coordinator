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

# 아우터가 필요한 계절/상황
_OUTER_SEASONS = {"가을", "겨울"}
_OUTER_SITUATIONS = {"회사", "경조사"}

# 가방이 권장되는 상황
_BAG_PREFERRED = {"회사", "여행", "데이트", "경조사"}
# 악세서리가 권장되는 상황
_ACC_PREFERRED = {"경조사", "데이트", "회사"}

OUTFIT_SYSTEM_PROMPT = """
너는 스타일리스트 AI다. 주어진 카테고리별 옷장 목록에서 상황과 계절에 맞는 코디를 구성해라.
반드시 아래 JSON 형식만 출력하고, 다른 텍스트/마크다운/코드블록 금지.
{{"name": str, "item_ids": [str], "tags": [str], "reason": str}}

[필수 구성 규칙]
1. 상의(top): 반드시 1개 선택
2. 하의(bottom): 반드시 1개 선택
3. 신발(shoes): 반드시 1개 선택
4. 아우터(outer): {outer_rule}
5. 가방(bag): {bag_rule}
6. 악세서리(acc): {acc_rule}

[스타일·색상 지침]
{style_rule}

- item_ids: 위 규칙에 따라 선택한 아이템 id 배열 (최소 3개, 카테고리별로 규칙 준수)
- tags: 코디 태그 배열 (예: ["캐주얼", "봄", "데일리"])
- reason: 이 코디를 선택한 이유, 어떤 카테고리를 왜 포함했는지 설명 (한국어 2~3문장)
- name: 코디명 (상황+계절+스타일 반영, 예: "봄 오피스 스마트캐주얼")

언어 규칙: 모든 텍스트는 반드시 한국어로만 작성. 영어·한자(漢字·中文) 사용 절대 금지. name·tags·reason 모든 필드를 한국어로만 출력할 것.
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


def _build_outer_rule(situation: str, season: str) -> str:
    if season in _OUTER_SEASONS or situation in _OUTER_SITUATIONS:
        return "필수 포함 — 해당 계절/상황에 아우터가 필요함. outer 카테고리에서 반드시 1개 선택"
    return "선택 — 봄/여름이면 생략 가능. 필요하다고 판단되면 1개 선택"


def _build_bag_rule(situation: str) -> str:
    if situation in _BAG_PREFERRED:
        return f"권장 포함 — {situation} 상황에 가방이 어울림. bag 카테고리에서 1개 선택 권장"
    return "선택 — 상황에 맞으면 1개 선택"


def _build_acc_rule(situation: str) -> str:
    if situation in _ACC_PREFERRED:
        return f"권장 포함 — {situation} 상황에 악세서리가 어울림. acc 카테고리에서 1개 선택 권장"
    return "선택 — 상황에 맞으면 1개 선택"


def _build_style_rule(situation: str) -> str:
    if situation == "경조사":
        return (
            "경조사 전용 규칙: 블랙(검정) 계열 색상을 최우선으로 선택할 것. "
            "클래식 또는 포멀 스타일 아이템을 우선 선택하고, "
            "화려하거나 밝은 색상(빨강·노랑·형광 등)은 반드시 피할 것."
        )
    return "상황과 계절에 어울리는 색상과 스타일을 자유롭게 선택할 것."


def _group_by_category(items: list) -> dict:
    """아이템을 카테고리별로 그룹화."""
    groups: dict[str, list] = {}
    for item in items:
        cat = item.get("category", "기타")
        groups.setdefault(cat, []).append(item)
    return groups


def _filter_by_season(items: list, season: str) -> list:
    """선택한 계절에 맞는 의류만 반환. 사계절 아이템은 항상 포함."""
    if season == "사계절":
        return items
    matched = []
    for item in items:
        item_seasons = item.get("season") or []
        if isinstance(item_seasons, str):
            item_seasons = [s.strip() for s in item_seasons.split(",") if s.strip()]
        # 계절 정보 없거나 선택 계절 포함이거나 사계절이면 포함
        if not item_seasons or season in item_seasons or "사계절" in item_seasons:
            matched.append(item)
    return matched


def _pick_fallback(groups: dict, category: str, used_ids: set) -> str | None:
    """해당 카테고리에서 아직 사용되지 않은 아이템 1개를 랜덤 선택."""
    candidates = [
        it for it in groups.get(category, [])
        if it["id"] not in used_ids
    ]
    if not candidates:
        candidates = groups.get(category, [])
    if not candidates:
        return None
    return random.choice(candidates)["id"]


def _validate_and_fix(
    result: dict,
    groups: dict,
    situation: str,
    season: str,
) -> dict:
    """
    LLM 결과의 item_ids가 필수 카테고리를 포함하는지 검증.
    누락된 카테고리는 옷장에서 자동으로 채운다.
    """
    all_items = {it["id"]: it for cats in groups.values() for it in cats}
    selected_ids: list[str] = result.get("item_ids") or []
    selected_cats = {all_items[iid]["category"] for iid in selected_ids if iid in all_items}
    used_ids = set(selected_ids)

    required = ["상의", "하의", "신발"]
    for cat in required:
        if cat not in selected_cats and cat in groups:
            fid = _pick_fallback(groups, cat, used_ids)
            if fid:
                selected_ids.append(fid)
                used_ids.add(fid)
                selected_cats.add(cat)

    # 아우터 필수 상황인데 누락된 경우
    outer_required = season in _OUTER_SEASONS or situation in _OUTER_SITUATIONS
    if outer_required and "아우터" not in selected_cats and "아우터" in groups:
        fid = _pick_fallback(groups, "아우터", used_ids)
        if fid:
            selected_ids.append(fid)
            used_ids.add(fid)

    result["item_ids"] = selected_ids
    return result


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

    # 계절 필터링: 선택한 계절에 맞는 의류만 추출
    filtered_items = _filter_by_season(items, season)
    groups = _group_by_category(filtered_items)

    # 필터 후 필수 카테고리가 비어있으면 전체 옷장에서 보완 (최소 코디 보장)
    for cat in ["상의", "하의", "신발"]:
        if cat not in groups and cat in all_groups:
            groups[cat] = all_groups[cat]

    # 카테고리별로 정리된 요약 (LLM 토큰 절약 + 구조 명확화)
    wardrobe_summary: dict[str, list] = {}
    for cat, cat_items in groups.items():
        wardrobe_summary[cat] = [
            {
                "id": it["id"],
                "name": it.get("name", ""),
                "color": it.get("color", ""),
                "style": it.get("style", ""),
                "season": it.get("season", []),
            }
            for it in cat_items
        ]

    outer_rule = _build_outer_rule(situation, season)
    bag_rule = _build_bag_rule(situation)
    acc_rule = _build_acc_rule(situation)
    style_rule = _build_style_rule(situation)

    chain = _chain_lazy()
    try:
        result = chain.invoke(
            {
                "situation": situation,
                "season": season,
                "outer_rule": outer_rule,
                "bag_rule": bag_rule,
                "acc_rule": acc_rule,
                "style_rule": style_rule,
                "wardrobe_json": json.dumps(wardrobe_summary, ensure_ascii=False),
            }
        )
        result = _validate_and_fix(result, groups, situation, season)
        return result
    except Exception as e:
        logger.error("generate_outfit 실패: %s", e)
        return {
            "name": "코디 생성 실패",
            "item_ids": [],
            "tags": [],
            "reason": f"AI 오류: {str(e)[:100]}",
        }


_VALID_SITUATIONS = {"회사", "데이트", "운동", "경조사", "여행", "기타"}
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

        # 구성된 카테고리 요약 (결과 메시지용)
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
