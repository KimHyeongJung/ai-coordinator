"""
날씨 기반 데일리룩 추천: Open-Meteo API + LLM 채팅.

날씨 API는 무료이며 인증 불필요 (Open-Meteo).
LLM은 ChatHuggingFace를 직접 호출(messages 리스트)해 대화 히스토리를 지원한다.
"""

from __future__ import annotations

import logging

import requests
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

import storage
from model_config import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    LLM_MODEL,
    WEATHER_API_BASE,
    get_token,
)

logger = logging.getLogger(__name__)

# WMO 날씨 코드 → 한국어 설명 매핑
WMO_CODE_MAP = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분 흐림",
    3: "흐림",
    45: "안개",
    48: "짙은 안개",
    51: "이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    61: "비",
    63: "비",
    65: "강한 비",
    71: "눈",
    73: "눈",
    75: "강한 눈",
    77: "싸락눈",
    80: "소나기",
    81: "소나기",
    82: "강한 소나기",
    85: "눈 소나기",
    86: "강한 눈 소나기",
    95: "뇌우",
    96: "뇌우(우박)",
    99: "뇌우(강한 우박)",
}

DAILY_SYSTEM_PROMPT = """
너는 AI 스타일리스트다. 사용자의 옷장과 날씨 정보를 바탕으로 코디를 추천한다.

현재 날씨: {weather_info}
사용자 옷장: {wardrobe_summary}

규칙:
- 반드시 옷장에 있는 의류만 조합해서 추천
- 날씨와 상황에 맞는 레이어링 팁 포함
- 한국어로 친근하게 답변
- 추천 코디는 구체적인 아이템명으로 설명
- 옷장이 비어있으면 일반적인 코디 조언 제공
"""

_daily_llm = None


def _llm_lazy():
    """ChatHuggingFace LLM lazy initialization."""
    global _daily_llm
    if _daily_llm is None:
        endpoint = HuggingFaceEndpoint(
            repo_id=LLM_MODEL,
            task="text-generation",
            max_new_tokens=600,
            temperature=0.7,
            huggingfacehub_api_token=get_token(),
        )
        _daily_llm = ChatHuggingFace(llm=endpoint)
    return _daily_llm


def get_weather(
    lat: float = DEFAULT_LATITUDE,
    lon: float = DEFAULT_LONGITUDE,
) -> dict:
    """Open-Meteo API로 내일 날씨 정보 조회. 실패 시 오류 메시지 반환."""
    try:
        url = (
            f"{WEATHER_API_BASE}"
            f"?latitude={lat}&longitude={lon}"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
            "&timezone=Asia/Seoul&forecast_days=2"
        )
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        daily = resp.json().get("daily", {})

        idx = 1  # index 0 = 오늘, index 1 = 내일
        code = int((daily.get("weathercode") or [0, 0])[idx])
        return {
            "temp_max": (daily.get("temperature_2m_max") or [None, None])[idx],
            "temp_min": (daily.get("temperature_2m_min") or [None, None])[idx],
            "precip": (daily.get("precipitation_sum") or [None, None])[idx],
            "weather_desc": WMO_CODE_MAP.get(code, "알 수 없음"),
            "date": "내일",
        }
    except Exception as e:
        logger.error("get_weather 실패: %s", e)
        return {
            "temp_max": None,
            "temp_min": None,
            "precip": None,
            "weather_desc": "날씨 정보 불러오기 실패",
            "date": "내일",
        }


def get_weather_display() -> str:
    """날씨 정보를 한 줄 문자열로 반환 (Gradio Textbox 출력용)."""
    w = get_weather()
    if w["temp_max"] is None:
        return f"⚠️ 날씨 정보를 불러올 수 없습니다. ({w['weather_desc']})"
    return (
        f"내일 날씨: {w['weather_desc']} | "
        f"최고 {w['temp_max']}°C / 최저 {w['temp_min']}°C | "
        f"강수량 {w['precip']}mm"
    )


def recommend_daily_look(
    user_message: str,
    chat_history: list,
) -> tuple[list, str]:
    """
    날씨 + 옷장 정보를 컨텍스트로 LLM 채팅 응답 생성.
    Gradio Chatbot(type="messages") 콜백용.
    반환: (업데이트된 chat_history, 입력창 초기화 문자열)
    """
    weather = get_weather()
    items = storage.load_wardrobe().get("items", [])

    weather_info = (
        f"{weather['date']} 날씨: {weather['weather_desc']}, "
        f"최고 {weather['temp_max']}°C / 최저 {weather['temp_min']}°C"
        if weather["temp_max"] is not None
        else "날씨 정보 조회 실패"
    )

    wardrobe_summary = (
        ", ".join(
            f"{item['name']}({item.get('category', '')})"
            for item in items[:20]  # 토큰 오버플로우 방지
        )
        if items
        else "등록된 의류 없음"
    )

    system_content = DAILY_SYSTEM_PROMPT.format(
        weather_info=weather_info,
        wardrobe_summary=wardrobe_summary,
    )

    # Gradio messages 포맷 → LangChain 메시지 포맷 변환
    messages = [SystemMessage(content=system_content)]
    for msg in chat_history:
        role = msg.get("role", "") if isinstance(msg, dict) else getattr(msg, "role", "")
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=user_message))

    try:
        llm = _llm_lazy()
        response = llm.invoke(messages)
        ai_text = response.content
    except Exception as e:
        logger.error("recommend_daily_look LLM 실패: %s", e)
        ai_text = f"죄송합니다, 응답 생성에 실패했습니다: {str(e)[:100]}"

    updated_history = chat_history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": ai_text},
    ]
    return updated_history, ""
