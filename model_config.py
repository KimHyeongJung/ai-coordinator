"""
AI Closet 모델 설정
===================
- VISION_MODEL: 의류 이미지 캡셔닝 모델 (Florence-2, 로컬 추론)
- LLM_MODEL:    의류 정보 추출 / 코디 생성 / 대화형 추천 LLM
- 날씨 API: Open-Meteo (무료, 인증 불필요)

토큰은 .env 파일의 HF_TOKEN 또는 HUGGINGFACEHUB_API_TOKEN 환경변수에서 읽는다.
HF Space에 배포할 때는 Space의 Settings > Secrets 에서 HF_TOKEN 을 등록한다.
"""

from __future__ import annotations

import os

from huggingface_hub import InferenceClient

# -----------------------------------------------------------------------------
# 모델 선택
# -----------------------------------------------------------------------------
# 의류 이미지 캡셔닝 (Florence-2 — 로컬 transformers 추론)
VISION_MODEL = "microsoft/Florence-2-base"

# 의류 정보 추출 / 코디 생성 / 데일리룩 추천 LLM
LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"

# -----------------------------------------------------------------------------
# 날씨 API (Open-Meteo, API 키 불필요)
# -----------------------------------------------------------------------------
WEATHER_API_BASE = "https://api.open-meteo.com/v1/forecast"

# 기본 좌표: 서울 (사용자가 변경 가능)
DEFAULT_LATITUDE = 37.5665
DEFAULT_LONGITUDE = 126.9780


def get_token() -> str:
    """환경변수에서 HF 토큰을 읽는다 (이미지 캡셔닝 + LangChain LLM 공통)."""
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if not token:
        raise SystemExit(
            "HF_TOKEN(또는 HUGGINGFACEHUB_API_TOKEN) 환경변수가 비어 있습니다.\n"
            "  1) https://huggingface.co/settings/tokens 에서 Read 토큰 발급\n"
            "  2) 로컬: .env 에 HF_TOKEN=hf_xxx 추가\n"
            "  3) HF Space: Settings > Secrets 에 HF_TOKEN 등록"
        )
    return token


def get_client() -> InferenceClient:
    """InferenceClient 인스턴스 반환 (이미지 캡셔닝 등 직접 API 호출용)."""
    return InferenceClient(token=get_token())
