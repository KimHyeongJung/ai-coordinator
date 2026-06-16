"""
날씨 기반 데일리룩 추천: Open-Meteo API + LLM 채팅.

날씨 API는 무료이며 인증 불필요 (Open-Meteo).
LLM은 ChatHuggingFace를 직접 호출(messages 리스트)해 대화 히스토리를 지원한다.
"""

from __future__ import annotations

import logging
import re

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

# CJK 한자 제거 패턴 (한글 AC00-D7AF 는 포함하지 않음)
_CJK_PATTERN = re.compile(
    "["
    "⺀-⻿"  # CJK 부수 보충
    "⼀-⿟"  # 강희자전 부수
    "㄀-ㄯ"  # 주음부호
    "㇀-㇯"  # CJK 획
    "㐀-䶿"  # CJK 통합한자 확장A
    "一-鿿"  # CJK 통합한자
    "豈-﫿"  # CJK 호환한자
    "︰-﹏"  # CJK 호환 형태
    "]"
)


def _strip_cjk(text: str) -> str:
    """한자(중국어) 문자를 제거하고 과도한 공백/개행을 정리한다."""
    cleaned = _CJK_PATTERN.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# WMO 날씨 코드 → 이모지 매핑
WMO_EMOJI: dict[int, str] = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️", 77: "🌨️",
    80: "⛈️", 81: "⛈️", 82: "⛈️",
    85: "🌨️", 86: "❄️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}

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
You are an AI stylist assistant. Respond ONLY in Korean (한국어).
NEVER use Chinese characters (漢字/中文/汉字). If you detect yourself writing Chinese, stop immediately and switch to Korean.

현재 날씨: {weather_info}
사용자 옷장 (의류): {wardrobe_summary}
저장된 코디 목록: {outfit_names}
악세서리·가방 목록: {acc_bag_summary}

[절대 규칙 — 코디 추천]
저장된 코디 목록이 비어 있지 않으면 아래 규칙을 반드시 따를 것. 예외 없음.
1. 코디를 추천할 때는 반드시 '저장된 코디 목록'에 있는 코디명 그대로 사용할 것.
2. 코디명은 반드시 **굵게** 표시. 예: **봄 데이트 클래식**
3. 목록에 없는 코디명을 임의로 만들어서 추천하는 것은 절대 금지.
4. 추천하는 모든 코디는 '저장된 코디 목록: {outfit_names}' 안에 존재해야 함.
5. 코디 목록이 없을 때만 옷장 의류를 조합해서 추천.

[기타 규칙]
- 날씨와 상황에 맞는 레이어링 팁 포함
- 오직 한국어와 영어만 사용. 한자(漢字·中文) 절대 금지.
- 추천 코디는 구체적인 아이템명으로 설명
- 옷장이 비어있으면 일반적인 코디 조언 제공

[악세서리·가방 추천 규칙]
- 악세서리·가방 목록에 아이템이 있으면 상황에 맞는 것을 1~2개 반드시 추천하고 **굵게** 표시
- 상황별 추천 기준:
  회사: 비즈니스백·토트백, 심플한 시계·벨트 등 포인트 악세서리
  데이트: 핸드백·크로스백, 귀걸이·목걸이 등 포인트 악세서리
  운동: 스포츠백·백팩, 머리띠·밴드 등 기능성 악세서리
  경조사: 클러치백·미니백, 심플한 귀걸이·목걸이 (화려한 것 금지)
  기타: 상황에 어울리는 자유 선택
- 악세서리·가방 목록이 없으면 상황에 맞는 아이템을 일반 조언으로 제안
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
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
            "weathercode,wind_speed_10m_max"
            "&hourly=relative_humidity_2m"
            "&timezone=Asia/Seoul&forecast_days=2"
        )
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        hourly = data.get("hourly", {})

        idx = 1  # index 0 = 오늘, index 1 = 내일
        code = int((daily.get("weathercode") or [0, 0])[idx])

        wind_kmh = (daily.get("wind_speed_10m_max") or [None, None])[idx]
        wind_ms = round(wind_kmh / 3.6, 1) if wind_kmh is not None else None

        # 내일 정오(noon) 습도: 오늘 0시부터 시작하는 hourly, 내일 12시 = index 36
        humidity_list = hourly.get("relative_humidity_2m") or []
        humidity = int(humidity_list[36]) if len(humidity_list) > 36 else None

        return {
            "temp_max": (daily.get("temperature_2m_max") or [None, None])[idx],
            "temp_min": (daily.get("temperature_2m_min") or [None, None])[idx],
            "precip": (daily.get("precipitation_sum") or [None, None])[idx],
            "weather_desc": WMO_CODE_MAP.get(code, "알 수 없음"),
            "code": code,
            "humidity": humidity,
            "wind_ms": wind_ms,
            "date": "내일",
        }
    except Exception as e:
        logger.error("get_weather 실패: %s", e)
        return {
            "temp_max": None,
            "temp_min": None,
            "precip": None,
            "weather_desc": "날씨 정보 불러오기 실패",
            "code": 0,
            "humidity": None,
            "wind_ms": None,
            "date": "내일",
        }


def _temp_tip(temp_min: float | None, temp_max: float | None) -> str:
    if temp_min is None:
        return ""
    if temp_min < 5:
        return "두꺼운 외투 필수"
    if temp_min < 10:
        return "아침 쌀쌀"
    if temp_min < 15:
        return "가벼운 겉옷 권장"
    if temp_max is not None and temp_max > 28:
        return "더위 대비 필요"
    return ""


def get_weather_html() -> str:
    """날씨 정보를 리치 HTML 카드로 반환 (gr.HTML 출력용)."""
    w = get_weather()
    if w["temp_max"] is None:
        return (
            '<div class="weather-card" style="justify-content:center">'
            '<span style="color:rgba(255,255,255,0.75);font-size:13px">'
            '⚠️ 날씨 정보를 불러올 수 없습니다</span></div>'
        )

    code = w.get("code", 0)
    emoji = WMO_EMOJI.get(code, "🌡️")
    temp_str = f"{w['temp_max']}°C"
    tip = _temp_tip(w["temp_min"], w["temp_max"])

    sub = f"서울 · 내일 {w['weather_desc']}"
    if tip:
        sub += f", {tip}"

    humidity = w.get("humidity")
    wind_ms = w.get("wind_ms")
    humidity_html = f'<div class="weather-stat">습도 {humidity}%</div>' if humidity is not None else ""
    wind_html = f'<div class="weather-stat">바람 {wind_ms}m/s</div>' if wind_ms is not None else ""

    return f"""<div class="weather-card">
  <div class="weather-left">
    <div class="weather-emoji">{emoji}</div>
    <div>
      <div class="weather-temp">{temp_str}</div>
      <div class="weather-sub">{sub}</div>
    </div>
  </div>
  <div class="weather-right">
    {humidity_html}
    {wind_html}
    <div class="weather-source">Open-Meteo</div>
  </div>
</div>"""


def get_initial_chat() -> list:
    """앱 로드 시 챗봇 초기 인사 메시지."""
    w = get_weather()
    temp = w["temp_max"]

    if temp is None:
        greeting = "안녕하세요! 날씨 정보를 불러오지 못했어요. 어떤 상황의 코디가 필요하세요?"
    else:
        if temp < 10:
            feel = "꽤 춥네요"
        elif temp < 18:
            feel = "선선하네요"
        elif temp < 24:
            feel = "따뜻하네요"
        else:
            feel = "더운 날이네요"
        greeting = (
            f"안녕하세요! 내일 날씨를 확인했어요. "
            f"{temp}°C로 {feel}. 어떤 상황의 코디가 필요하세요?"
        )

    return [{"role": "assistant", "content": greeting}]


def get_weather_display() -> str:
    """날씨 정보를 한 줄 문자열로 반환 (레거시 호환용)."""
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
) -> tuple[list, str, str | None]:
    """
    날씨 + 옷장 정보를 컨텍스트로 LLM 채팅 응답 생성.
    Gradio Chatbot(type="messages") 콜백용.
    반환: (업데이트된 chat_history, 입력창 초기화 문자열, 추천된 첫 번째 코디명 또는 None)
    """
    weather = get_weather()
    items = storage.load_wardrobe().get("items", [])
    outfits = storage.load_outfits().get("outfits", [])

    weather_info = (
        f"{weather['date']} 날씨: {weather['weather_desc']}, "
        f"최고 {weather['temp_max']}°C / 최저 {weather['temp_min']}°C"
        if weather["temp_max"] is not None
        else "날씨 정보 조회 실패"
    )

    _ACC_BAG_CATS = {"악세서리", "가방"}
    clothing_items = [it for it in items if it.get("category") not in _ACC_BAG_CATS]
    acc_bag_items  = [it for it in items if it.get("category") in _ACC_BAG_CATS]

    wardrobe_summary = (
        ", ".join(
            f"{it['name']}({it.get('category', '')})"
            for it in clothing_items[:20]
        )
        if clothing_items
        else "등록된 의류 없음"
    )

    acc_bag_summary = (
        ", ".join(
            f"{it['name']}({it.get('category', '')}, {it.get('color', '')})"
            for it in acc_bag_items[:15]
        )
        if acc_bag_items
        else "등록된 악세서리·가방 없음"
    )

    saved_outfit_names: list[str] = [o.get("name", "") for o in outfits if o.get("name")]
    outfit_names = (
        ", ".join(f'"{n}"' for n in saved_outfit_names[:20])
        if saved_outfit_names
        else "저장된 코디 없음"
    )

    system_content = DAILY_SYSTEM_PROMPT.format(
        weather_info=weather_info,
        wardrobe_summary=wardrobe_summary,
        acc_bag_summary=acc_bag_summary,
        outfit_names=outfit_names,
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
        ai_text = _strip_cjk(response.content)
        if not ai_text:
            ai_text = "죄송합니다, 다시 질문해 주세요."
    except Exception as e:
        logger.error("recommend_daily_look LLM 실패: %s", e)
        ai_text = f"죄송합니다, 응답 생성에 실패했습니다: {str(e)[:100]}"

    # 후처리: 저장된 코디가 있는데 응답에 코디명이 하나도 언급되지 않으면 보완
    first_recommended: str | None = None
    if saved_outfit_names:
        mentioned = [name for name in saved_outfit_names if name in ai_text]
        if not mentioned:
            names_bold = " / ".join(f"**{n}**" for n in saved_outfit_names[:10])
            ai_text += f"\n\n💡 저장된 코디 목록: {names_bold}"
            mentioned = saved_outfit_names[:10]
        first_recommended = mentioned[0] if mentioned else None

    updated_history = chat_history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": ai_text},
    ]
    return updated_history, "", first_recommended
