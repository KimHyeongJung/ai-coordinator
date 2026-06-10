"""
AI 코디 자동 생성: 옷장 아이템 목록 → LLM → 코디 JSON → Supabase 저장.

기존 LCEL 체인 패턴(prompt | ChatHuggingFace | JsonOutputParser)을 재사용한다.
"""

from __future__ import annotations

import json
import logging

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

import dashboard
import storage
from model_config import LLM_MODEL, get_token

logger = logging.getLogger(__name__)

OUTFIT_SYSTEM_PROMPT = """
너는 스타일리스트 AI다. 주어진 옷장 목록에서 어울리는 의류를 조합해 코디를 만들어라.
반드시 아래 JSON 형식만 출력하고, 다른 텍스트/마크다운/코드블록 금지.
{"name": str, "item_ids": [str], "tags": [str], "situation": str, "season": str, "reason": str}
- item_ids: 선택한 아이템의 id 배열 (2~4개)
- tags: 코디 태그 배열 (예: ["회사", "봄", "스마트캐주얼"])
- reason: 이 조합을 선택한 이유 (한국어 1~2문장)
"""

_outfit_chain = None


def _chain_lazy():
    """LCEL 체인: prompt | ChatHuggingFace | JsonOutputParser"""
    global _outfit_chain
    if _outfit_chain is None:
        endpoint = HuggingFaceEndpoint(
            repo_id=LLM_MODEL,
            task="text-generation",
            max_new_tokens=400,
            temperature=0.3,
            huggingfacehub_api_token=get_token(),
        )
        llm = ChatHuggingFace(llm=endpoint)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", OUTFIT_SYSTEM_PROMPT),
                ("human", "상황: {situation}\n계절: {season}\n\n옷장 목록:\n{wardrobe_json}"),
            ]
        )
        _outfit_chain = prompt | llm | JsonOutputParser()
    return _outfit_chain


def generate_outfit(situation: str, season: str) -> dict:
    """옷장 아이템을 조합해 코디 JSON을 생성한다."""
    wardrobe = storage.load_wardrobe()
    items = wardrobe.get("items", [])

    if not items:
        return {
            "name": "옷장 비어있음",
            "item_ids": [],
            "tags": [],
            "situation": situation,
            "season": season,
            "reason": "옷장에 등록된 의류가 없습니다. 먼저 옷장 탭에서 의류를 추가해 주세요.",
        }

    # LLM에게 필요한 필드만 전달 (토큰 절약)
    wardrobe_summary = [
        {
            "id": item["id"],
            "name": item.get("name", ""),
            "category": item.get("category", ""),
            "color": item.get("color", ""),
            "style": item.get("style", ""),
            "season": item.get("season", []),
        }
        for item in items
    ]

    chain = _chain_lazy()
    try:
        result = chain.invoke(
            {
                "situation": situation,
                "season": season,
                "wardrobe_json": json.dumps(wardrobe_summary, ensure_ascii=False),
            }
        )
        result.setdefault("situation", situation)
        result.setdefault("season", season)
        return result
    except Exception as e:
        logger.error("generate_outfit 실패: %s", e)
        return {
            "name": "코디 생성 실패",
            "item_ids": [],
            "tags": [],
            "situation": situation,
            "season": season,
            "reason": f"AI 오류: {str(e)[:100]}",
        }


def generate_outfit_ui(situation: str, season: str) -> tuple[str, list]:
    """
    Gradio 콜백용 래퍼.
    코디를 생성하고 DB에 저장한 뒤 (결과 메시지, 코디 테이블) 반환.
    """
    result = generate_outfit(situation, season)

    # 실제 아이템이 선택된 경우만 DB에 저장
    if result.get("item_ids"):
        storage.add_outfit(
            {
                "name": result.get("name", "코디"),
                "item_ids": result.get("item_ids", []),
                "tags": result.get("tags", []),
                "season": result.get("season", season),
                "situation": result.get("situation", situation),
                "ai_generated": True,
            }
        )
        tags_str = ", ".join(result.get("tags", []))
        msg = (
            f"✅ 코디 생성 완료!\n"
            f"코디명: {result.get('name', '')}\n"
            f"태그: {tags_str}\n\n"
            f"{result.get('reason', '')}"
        )
    else:
        msg = f"ℹ️ {result.get('reason', '코디를 생성할 수 없습니다.')}"

    return msg, dashboard.get_outfit_table()
