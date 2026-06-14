"""
AI Closet — 스마트 AI 옷장 관리 서비스
상단 네비게이션 바 + Tabs 전환 방식 (HF Spaces 호환)
"""

from __future__ import annotations

import json
import os

import gradio as gr
from gradio_client import utils as _gc_utils

# --- gradio_client JSON Schema walker 버그(#10178) 우회 ---
_orig_get_type = _gc_utils.get_type


def _safe_get_type(schema):
    if isinstance(schema, bool):
        return "Any"
    return _orig_get_type(schema)


_gc_utils.get_type = _safe_get_type

_orig_j2p = _gc_utils._json_schema_to_python_type


def _safe_j2p(schema, defs=None):
    if isinstance(schema, bool):
        return "Any"
    return _orig_j2p(schema, defs)


_gc_utils._json_schema_to_python_type = _safe_j2p
# ----------------------------------------------------------

from dotenv import load_dotenv  # noqa: E402

import daily_look  # noqa: E402
import dashboard   # noqa: E402
import outfit      # noqa: E402
import storage     # noqa: E402
import wardrobe    # noqa: E402

load_dotenv()

# ── CSS ──────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
/* ── Design tokens ── */
:root {
    --navy:         #1B3A6B;
    --navy-light:   #2A52A0;
    --navy-pale:    #EEF2FA;
    --navy-mid:     #4A6FA5;
    --white:        #FFFFFF;
    --surface:      #F7F9FC;
    --border:       #D8E2F0;
    --border-light: #EEF2FA;
    --text:         #1A2540;
    --text-muted:   #5A6A8A;
    --text-hint:    #9BAAC4;
    --radius:       10px;
    --radius-lg:    14px;
    --shadow-sm:    0 1px 3px rgba(27,58,107,0.07), 0 0 0 1px rgba(27,58,107,0.04);
    --shadow-card:  0 3px 12px rgba(27,58,107,0.09), 0 0 0 1px rgba(27,58,107,0.05);
}

/* ── Gradio 다크 테마 변수 강제 오버라이드 ── */
.gradio-container {
    --block-background-fill: #FFFFFF;
    --input-background-fill: #EEF2FA;
    --body-background-fill: #F7F9FC;
    --background-fill-primary: #FFFFFF;
    --background-fill-secondary: #F7F9FC;
    --panel-background-fill: #FFFFFF;
    --panel-border-color: #D8E2F0;
    --border-color-primary: #D8E2F0;
    --border-color-accent: #2A52A0;
    --chatbot-background: #FFFFFF;
    --button-primary-background-fill: #2A52A0;
    --button-primary-background-fill-hover: #1B3A6B;
    --button-primary-text-color: #FFFFFF;
    --button-secondary-background-fill: #FFFFFF;
    --button-secondary-background-fill-hover: #EEF2FA;
    --button-secondary-text-color: #1A2540;
    --button-secondary-border-color: #D8E2F0;
    --color-background-primary: #FFFFFF;
    --color-background-secondary: #F7F9FC;
}

/* ── Global ── */
html, body { background: var(--surface) !important; }
.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
    background: var(--surface) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif !important;
}
footer { display: none !important; }

/* ── 모든 블록 배경 강제 흰색 (다크 배경 제거) ── */
.block,
.block > div,
.form,
.panel,
.wrap,
.stretch {
    background: #FFFFFF !important;
}
.tabitem,
.tabitem > div,
.tabitem .block {
    background: #FFFFFF !important;
    border: none !important;
}
.tab-content {
    background: var(--surface) !important;
}
.tab-content > .block,
.tab-content .block {
    background: #FFFFFF !important;
}

/* ── 상단 네비게이션 바 ── */
#aic-topnav {
    position: sticky !important;
    top: 0 !important;
    z-index: 100 !important;
    background: #FFFFFF !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 0 !important;
    height: 58px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    box-shadow: 0 1px 0 rgba(27,58,107,0.06), 0 2px 8px rgba(27,58,107,0.04) !important;
    gap: 16px !important;
}
#aic-topnav .block,
#aic-topnav > .block {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

/* ── 탭 네비 완전히 숨기기 ── */
.tab-nav,
.tab-nav * {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
    pointer-events: none !important;
}

/* ── 탭 컨테이너 ── */
#content-tabs {
    background: transparent !important;
    border: none !important;
    gap: 0 !important;
    padding: 0 !important;
    box-shadow: none !important;
}
#content-tabs > div {
    padding: 0 !important;
    gap: 0 !important;
    background: transparent !important;
}
.tabitem {
    padding: 0 !important;
    border: none !important;
}

/* ── 탭 콘텐츠 영역 ── */
.tab-content {
    padding: 20px 0 32px !important;
    gap: 14px !important;
    border: none !important;
}
/* Gradio Soft 테마가 .block에 추가하는 좌우 패딩 제거 */
.tabitem > .block,
.tabitem > div > .block {
    padding-left: 0 !important;
    padding-right: 0 !important;
}

/* ── 섹션 헤더 ── */
.section-header {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    padding: 16px 0 10px !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    border-bottom: none !important;
    margin-bottom: 0 !important;
    background: transparent !important;
}
.section-header::before {
    content: '';
    display: inline-block;
    width: 3px;
    height: 13px;
    background: var(--navy);
    border-radius: 2px;
    flex-shrink: 0;
    opacity: 0.65;
}

/* ── 페이지 상단 topbar ── */
.topbar {
    background: var(--white) !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 0 !important;
    min-height: 54px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    box-shadow: 0 1px 0 rgba(27,58,107,0.06) !important;
}
.topbar-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.015em;
}
.topbar-meta { display: flex; align-items: center; gap: 8px; }
.topbar-badge {
    background: var(--navy-pale);
    color: var(--navy-mid);
    font-size: 11px;
    font-weight: 500;
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid var(--border);
    letter-spacing: 0.01em;
}
.topbar-pill {
    background: var(--navy);
    color: #fff;
    font-size: 11px;
    font-weight: 500;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 0.01em;
}

/* ── 버튼 (밝은 네이비 #2A52A0) ── */
button,
.btn button,
.block button {
    background: var(--white) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
}
.btn-primary button,
button.primary,
.block button.primary {
    background: var(--navy-light) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 9px 20px !important;
    letter-spacing: -0.01em !important;
    box-shadow: 0 1px 4px rgba(42,82,160,0.28) !important;
    transition: background 0.15s, transform 0.1s, box-shadow 0.15s !important;
}
.btn-primary button:hover,
button.primary:hover {
    background: var(--navy) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(27,58,107,0.28) !important;
}
.btn-primary button:active,
button.primary:active {
    transform: translateY(0) !important;
    box-shadow: 0 1px 3px rgba(27,58,107,0.18) !important;
}
.btn-secondary button,
button.secondary,
.block button.secondary {
    background: var(--white) !important;
    color: var(--navy-light) !important;
    border: 1.5px solid var(--navy-light) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
}
.btn-secondary button:hover,
button.secondary:hover {
    background: var(--navy-pale) !important;
    border-color: var(--navy) !important;
    color: var(--navy) !important;
}
.btn-danger button {
    background: #DC2626 !important;
    color: #FFFFFF !important;
    border-color: #B91C1C !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
.btn-danger button:hover {
    background: #B91C1C !important;
}

/* ── 계절 선택 버튼 색상 ── */
/* 미선택 공통: 흰색 */
#edit-w-season label {
    background: #FFFFFF !important;
    color: #9BAAC4 !important;
    border-color: #E2E8F0 !important;
}
/* 봄 - 선택 */
#edit-w-season label:nth-child(1):has(input:checked) {
    background: #EC4899 !important; color: #fff !important;
    border-color: #DB2777 !important;
}
/* 여름 - 선택 */
#edit-w-season label:nth-child(2):has(input:checked) {
    background: #0EA5E9 !important; color: #fff !important;
    border-color: #0284C7 !important;
}
/* 가을 - 선택 */
#edit-w-season label:nth-child(3):has(input:checked) {
    background: #F59E0B !important; color: #fff !important;
    border-color: #D97706 !important;
}
/* 겨울 - 선택 */
#edit-w-season label:nth-child(4):has(input:checked) {
    background: #6366F1 !important; color: #fff !important;
    border-color: #4F46E5 !important;
}

/* ── 코디 편집: 계절 색상 (의류와 동일) ── */
#edit-o-season label {
    background: #FFFFFF !important; color: #9BAAC4 !important;
    border-color: #E2E8F0 !important;
}
#edit-o-season label:nth-child(1):has(input:checked) {
    background: #EC4899 !important; color: #fff !important; border-color: #DB2777 !important;
}
#edit-o-season label:nth-child(2):has(input:checked) {
    background: #0EA5E9 !important; color: #fff !important; border-color: #0284C7 !important;
}
#edit-o-season label:nth-child(3):has(input:checked) {
    background: #F59E0B !important; color: #fff !important; border-color: #D97706 !important;
}
#edit-o-season label:nth-child(4):has(input:checked) {
    background: #6366F1 !important; color: #fff !important; border-color: #4F46E5 !important;
}
#edit-o-season label:nth-child(5):has(input:checked) {
    background: #14B8A6 !important; color: #fff !important; border-color: #0D9488 !important;
}

/* ── 코디 편집: 상황 색상 ── */
#edit-o-situation label {
    background: #FFFFFF !important; color: #9BAAC4 !important;
    border-color: #E2E8F0 !important;
}
#edit-o-situation label:nth-child(1):has(input:checked) {
    background: #2563EB !important; color: #fff !important; border-color: #1D4ED8 !important;
}
#edit-o-situation label:nth-child(2):has(input:checked) {
    background: #EC4899 !important; color: #fff !important; border-color: #DB2777 !important;
}
#edit-o-situation label:nth-child(3):has(input:checked) {
    background: #16A34A !important; color: #fff !important; border-color: #15803D !important;
}
#edit-o-situation label:nth-child(4):has(input:checked) {
    background: #7C3AED !important; color: #fff !important; border-color: #6D28D9 !important;
}
#edit-o-situation label:nth-child(5):has(input:checked) {
    background: #EA580C !important; color: #fff !important; border-color: #C2410C !important;
}
#edit-o-situation label:nth-child(6):has(input:checked) {
    background: #0D9488 !important; color: #fff !important; border-color: #0F766E !important;
}
#edit-o-situation label:nth-child(7):has(input:checked) {
    background: #6B7280 !important; color: #fff !important; border-color: #4B5563 !important;
}

/* ── 폼 라벨 배지 (span 텍스트만 타깃) ── */
.block label > span:first-child,
.block .label-wrap > span,
.block .label-wrap label > span:first-child,
.block [data-testid="block-label"],
[data-testid="block-label"] {
    background: #1B3A6B !important;
    color: #FFFFFF !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    padding: 3px 9px !important;
    border-radius: 5px !important;
    display: inline-block !important;
    margin-bottom: 4px !important;
    line-height: 1.4 !important;
}

/* ── 입력 필드 배경 #EEF2FA ── */
.block input[type="text"],
.block textarea,
.block select {
    border-color: var(--border) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    background: #EEF2FA !important;
    color: var(--text) !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.block input[type="number"] {
    border-color: var(--border) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    background: var(--white) !important;
    color: var(--text) !important;
}
.block input:focus, .block textarea:focus {
    border-color: var(--navy-mid) !important;
    box-shadow: 0 0 0 3px rgba(74,111,165,0.12) !important;
    background: #EEF2FA !important;
    outline: none !important;
}

/* ── 드롭다운 ── */
.block .wrap-inner {
    border-radius: 8px !important;
    border-color: var(--border) !important;
    background: #EEF2FA !important;
    color: var(--text) !important;
}
.block .wrap-inner *,
.block .wrap-inner .token span {
    color: var(--text) !important;
}
.block ul.options {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    z-index: 200 !important;
}
.block ul.options li,
.block ul.options .item {
    color: var(--text) !important;
    background: var(--white) !important;
    font-size: 13px !important;
}
.block ul.options li:hover,
.block ul.options .item:hover {
    background: var(--navy-pale) !important;
    color: var(--navy) !important;
}
.block ul.options li.selected,
.block ul.options .item.selected {
    background: var(--navy-pale) !important;
    color: var(--navy) !important;
    font-weight: 500 !important;
}

/* ── 이미지 업로드 박스 ── */
.image-box,
.image-box > .block {
    height: 100% !important;
    align-self: stretch !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}
/* 가장 바깥 점선만 */
.image-box .wrap {
    height: 100% !important;
    min-height: 280px !important;
    border: 1.5px dashed #BFD0E8 !important;
    border-radius: var(--radius-lg) !important;
    background: #FAFCFF !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    transition: border-color 0.2s, background 0.2s !important;
    box-sizing: border-box !important;
}
.image-box .wrap:hover { border-color: var(--navy-mid) !important; background: var(--navy-pale) !important; }
/* 내부 요소 점선 모두 제거 */
.image-box .upload-container,
.image-box .upload-container *,
.image-box .wrap > div,
.image-box .wrap > div > div,
.image-box .wrap > div > div > div {
    border: none !important;
    background: transparent !important;
}
/* 라벨 앞 아이콘(박스/SVG) 제거 */
.image-box label svg,
.image-box label > span:first-child svg,
.image-box label > span:first-child > *:first-child:not(svg + *) {
    display: none !important;
}
/* 이미지 라벨 배지: #1B3A6B, 11px, 흰 텍스트 */
.image-box label > span:first-child {
    background: #1B3A6B !important;
    color: #FFFFFF !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    padding: 3px 9px !important;
    border-radius: 5px !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 0 !important;
    margin-bottom: 4px !important;
}
/* 업로드 드롭존 텍스트 #6B7484 */
.image-box .wrap span,
.image-box .wrap p,
.image-box .wrap > div span,
.image-box .wrap > div p,
.image-box .upload-container span,
.image-box .upload-container p,
.image-box span,
.image-box p {
    color: #6B7484 !important;
}

.image-box .upload-text {
    color: #6B7484; /* 업로드 문구 색상 (주황색) */
}
.image-box .drag-text {
    color: #6B7484; /* 드래그 문구 색상 (파란색) */
}
.image-box .image-label {
    color: #6B7484; /* 레이블 텍스트 색상 (보라색) */
}

/* ── 결과 텍스트 박스 (자동 확장) ── */
.result-box textarea {
    background: #EEF2FA !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-size: 12.5px !important;
    line-height: 1.7 !important;
    color: var(--text) !important;
    min-height: 80px !important;
    height: auto !important;
    field-sizing: content !important;
    overflow-y: hidden !important;
    resize: none !important;
}

/* ── 통계 박스 (gr.Number) ── */
.stat-box {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: hidden !important;
    text-align: center !important;
}
.stat-box > .block { background: var(--white) !important; border: none !important; padding: 22px 16px 18px !important; }
.stat-box input[type="number"],
.stat-box input[type="number"]:focus,
.stat-box input[type="number"]:active {
    font-size: 36px !important; font-weight: 700 !important; color: #1A2540 !important;
    border: none !important; background: transparent !important;
    text-align: center !important; padding: 4px 0 !important; width: 100% !important;
    box-shadow: none !important; outline: none !important;
    -webkit-text-fill-color: #1A2540 !important;
}
.stat-box label > span:first-child {
    font-size: 16px !important; color: var(--white) !important; font-weight: 600 !important;
    text-align: center !important; display: block !important; text-transform: uppercase !important;
    letter-spacing: 0.07em !important; margin-bottom: 6px !important;
}

/* ── 통계 플랫 카드 ── */
.sc-wrap { display: flex; flex-direction: column; gap: 12px; padding: 4px 0; }
.sc-section { background: var(--white); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 14px 16px; box-shadow: var(--shadow-sm); }
.sc-title { font-size: 10.5px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 10px; }
.sc-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.sc-card { display: inline-flex; align-items: center; gap: 7px; background: var(--navy-pale); border: 1px solid var(--border); border-radius: 8px; padding: 7px 13px; }
.sc-label { font-size: 12px; color: var(--text-muted); font-weight: 500; }
.sc-val { font-size: 14px; font-weight: 700; color: var(--navy); }

/* ── 날씨 카드 ── */
.weather-card {
    background: linear-gradient(135deg, #1D3E72 0%, #2A52A0 100%);
    border-radius: 16px; padding: 20px 24px;
    display: flex; align-items: center; justify-content: space-between;
    color: #fff; box-shadow: 0 4px 20px rgba(27,58,107,0.25);
}
.weather-left { display: flex; align-items: center; gap: 16px; }
.weather-emoji { font-size: 46px; line-height: 1; }
.weather-temp { font-size: 34px; font-weight: 700; color: #fff; line-height: 1.1; letter-spacing: -0.03em; }
.weather-sub { font-size: 12px; color: rgba(255,255,255,0.65); margin-top: 4px; letter-spacing: 0.01em; }
.weather-right { text-align: right; display: flex; flex-direction: column; gap: 5px; align-items: flex-end; }
.weather-stat { font-size: 11.5px; color: rgba(255,255,255,0.68); }
.weather-source { font-size: 10px; color: rgba(255,255,255,0.35); margin-top: 2px; }

/* ── 챗봇 (강제 흰 배경) ── */
.chatbot-box,
.chatbot-box > *,
.chatbot-box .block,
.chatbot-box .wrap,
.chatbot-box [data-testid="chatbot"],
.chatbot-box [data-testid="chatbot"] > *,
[data-testid="chatbot"],
[data-testid="chatbot"] > div,
[data-testid="chatbot"] .wrap,
[data-testid="chatbot"] .message-wrap,
[data-testid="chatbot"] .bubble-wrap {
    background: #FFFFFF !important;
    border-color: var(--border) !important;
}
.chatbot-box > div,
.chatbot-box .wrap {
    border-radius: var(--radius-lg) !important;
    border: 1px solid var(--border) !important;
    background: var(--white) !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: hidden !important;
}
/* 유저 메시지 — 배경 없음 */
.chatbot-box [data-testid="user"] > div,
.chatbot-box .message.user .bubble {
    background: transparent !important;
    color: var(--text) !important;
    border: none !important;
    box-shadow: none !important;
}
/* 봇 메시지 — 배경 없음 */
.chatbot-box [data-testid="bot"] > div,
.chatbot-box .message.bot .bubble {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
.chatbot-box [data-testid="bot"] p,
.chatbot-box [data-testid="bot"] li,
.chatbot-box [data-testid="bot"] span,
.chatbot-box [data-testid="bot"] div { color: #5A6A8A !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif !important; }
.chatbot-box [data-testid="user"] p,
.chatbot-box [data-testid="user"] span,
.chatbot-box [data-testid="user"] div { color: #FFFFFF !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif !important; }
.chatbot-box [data-testid="bot"] strong,
.chatbot-box [data-testid="bot"] b { color: var(--navy-light) !important; font-weight: 600 !important; }

/* ── 채팅 입력 ── */
.chat-input-row { align-items: center !important; gap: 10px !important; }
.chat-input-row > .block,
.chat-input-row > div { margin: 0 !important; padding: 0 !important; background: transparent !important; }
#chat-input > .block,
#chat-input .block { background: transparent !important; border: none !important; padding: 0 !important; box-shadow: none !important; }
#chat-input textarea,
#chat-input input[type="text"] {
    border-radius: 50px !important; padding: 12px 22px !important;
    border: 1.5px solid var(--border) !important; background: #EEF2FA !important;
    color: var(--text) !important; font-size: 13px !important;
    resize: none !important; min-height: 46px !important; max-height: 46px !important;
    line-height: 1.5 !important; overflow-y: hidden !important; box-shadow: none !important;
}
#chat-input textarea:focus,
#chat-input input[type="text"]:focus {
    border-color: var(--navy-mid) !important;
    box-shadow: 0 0 0 3px rgba(74,111,165,0.12) !important;
    outline: none !important;
}

/* ── 전송 버튼 ── */
#chat-send-btn,
#chat-send-btn > .block,
#chat-send-btn > div {
    background: var(--navy-light) !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
    font-size: 28px !important;
    color: #FFFFFF !important;
    flex: 0 0 54px !important;
    max-width: 54px !important;
    min-width: 54px !important;
    display: flex !important;
    align-items: stretch !important;
}
#chat-send-btn button {
    background: var(--navy-light) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 50px !important;
    width: 54px !important;
    height: 46px !important;
    min-width: 54px !important;
    min-height: 46px !important;
    padding: 0 !important;
    font-size: 28px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 8px rgba(42,82,160,0.35) !important;
    transition: background 0.15s, transform 0.1s !important;
    cursor: pointer !important;
}
#chat-send-btn button:hover { background: var(--navy) !important; transform: translateY(-1px) !important; }
#chat-send-btn button:active { transform: translateY(0) !important; }

/* ── 데이터프레임 배경 ── */
.table-box { background: #EEF2FA !important; border: 1px solid var(--border) !important; border-radius: var(--radius-lg) !important; overflow: hidden !important; box-shadow: var(--shadow-sm) !important; }
.table-box > .block { border: none !important; padding: 0 !important; background: transparent !important; }
.table-box table { border-collapse: collapse !important; width: 100% !important; }
/* 헤더 행 */
.table-box table thead tr,
.table-box table thead,
[data-testid="dataframe"] thead tr,
[data-testid="dataframe"] table thead tr {
    background: #1B3A6B !important;
    background-color: #1B3A6B !important;
}
/* 헤더 셀 */
.table-box table thead th,
[data-testid="dataframe"] thead th,
[data-testid="dataframe"] table thead th {
    background: #1B3A6B !important;
    background-color: #1B3A6B !important;
    color: #FFFFFF !important;
    font-weight: 500 !important;
    font-size: 11.5px !important;
    padding: 11px 14px !important;
    border: none !important;
    letter-spacing: 0.03em !important;
    white-space: nowrap !important;
}
/* 헤더 셀 내부 래퍼 — 흰 띠/테두리 제거 + Bold */
.table-box table thead th *,
.table-box table thead th > *,
.table-box table thead th span,
.table-box table thead th div,
.table-box table thead th button,
[data-testid="dataframe"] thead th *,
[data-testid="dataframe"] thead th > *,
[data-testid="dataframe"] thead th span,
[data-testid="dataframe"] thead th div,
[data-testid="dataframe"] thead th button {
    background: #1B3A6B !important;
    background-color: #1B3A6B !important;
    color: #FFFFFF !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    font-weight: 700 !important;
    padding: 0 !important;
}
/* 헤더 셀 자체도 Bold */
.table-box table thead th,
[data-testid="dataframe"] thead th {
    font-weight: 700 !important;
}
.table-box table tbody tr td { font-size: 12.5px !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif !important; color: var(--text) !important; padding: 9px 14px !important; background: #EEF2FA !important; border-bottom: 1px solid var(--border-light) !important; border-right: none !important; border-left: none !important; border-top: none !important; word-break: break-word !important; white-space: normal !important; vertical-align: top !important; }
.table-box table { table-layout: auto !important; }
.table-box table tbody tr:last-child td { border-bottom: none !important; }
.table-box table tbody tr:hover td { background: #D8E2F0 !important; transition: background 0.12s !important; }

/* ── 스크롤바 ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #C4D4E8; border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--navy-mid); }

/* ── 2단 레이아웃 ── */
#main-layout {
    gap: 0 !important;
    align-items: stretch !important;
    min-height: 100vh !important;
}
#main-layout > .block { padding: 0 !important; border: none !important; background: transparent !important; }

/* 좌측 가이드 패널 */
#left-guide {
    background: linear-gradient(160deg, #1B3A6B 0%, #2A52A0 60%, #1E4D8C 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.1) !important;
    position: sticky !important;
    top: 0 !important;
    height: 100vh !important;
    overflow-y: auto !important;
    flex-shrink: 0 !important;
}
#left-guide > .block { background: transparent !important; border: none !important; padding: 0 !important; }
#left-guide .block { background: transparent !important; border: none !important; }

/* 우측 서비스 패널 */
#right-service {
    background: var(--surface) !important;
    min-height: 100vh !important;
    overflow-y: auto !important;
}
#right-service > .block { background: transparent !important; border: none !important; padding: 0 !important; }

/* 가이드 패널 내부 스타일 */
#usage-guide {
    padding: 28px 20px 24px;
    color: #1A2540;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
    min-height: 100vh;
    box-sizing: border-box;
}
.guide-logo {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 32px;
    padding-bottom: 20px;
    border-bottom: 1px solid #D8E2F0;
}
.guide-logo-icon { font-size: 36px; line-height: 1; }
.guide-title { font-size: 18px; font-weight: 700; letter-spacing: -0.02em; color: #1B3A6B; }
.guide-sub { font-size: 11px; color: #9BAAC4; margin-top: 2px; letter-spacing: 0.03em; }
.guide-step {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    padding-bottom: 20px;
    border-bottom: 1px solid #EEF2FA;
}
.guide-step:last-of-type { border-bottom: none; }
.guide-step-num {
    font-size: 11px;
    font-weight: 700;
    color: #9BAAC4;
    letter-spacing: 0.08em;
    flex-shrink: 0;
    padding-top: 2px;
    width: 20px;
}
.guide-step-title {
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 6px;
    color: #1A2540;
}
.guide-step-desc {
    font-size: 12px;
    color: #5A6A8A;
    line-height: 1.6;
}
.guide-step-desc b { color: #1B3A6B; font-weight: 600; }
.guide-step-desc em { color: #2A52A0; font-style: normal; font-weight: 500; }
.guide-tip {
    margin-top: 7px;
    font-size: 11px;
    color: #9BAAC4;
    background: #EEF2FA;
    border-radius: 6px;
    padding: 5px 8px;
}
.guide-footer {
    margin-top: 24px;
    font-size: 10px;
    color: #C4D4E8;
    text-align: center;
    letter-spacing: 0.04em;
}
"""

# ── 상단 네비게이션 HTML ──────────────────────────────────────────────────────
TOP_NAV_HTML = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.34.0/dist/tabler-icons.min.css">

<nav id="aic-topnav">
  <!-- 로고 -->
  <div style="display:flex;align-items:center;gap:11px;flex-shrink:0">
    <div style="
      width:36px;height:36px;
      background:linear-gradient(135deg,#1B3A6B,#2A52A0);
      border-radius:9px;
      display:flex;align-items:center;justify-content:center;
      flex-shrink:0;
      box-shadow:0 2px 8px rgba(27,58,107,0.3)
    ">
      <i class="ti ti-shirt" style="color:#fff;font-size:18px"></i>
    </div>
    <div>
      <div style="color:#1A2540;font-size:14px;font-weight:700;line-height:1.25;letter-spacing:-0.02em">AI Closet</div>
      <div style="color:#9BAAC4;font-size:10px;margin-top:1px;letter-spacing:0.01em">스마트 옷장 관리</div>
    </div>
  </div>

  <!-- 우측 배지 -->
  <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
    <span style="background:#EEF2FA;color:#4A6FA5;font-size:10.5px;font-weight:500;padding:3px 10px;border-radius:20px;border:1px solid #D8E2F0">Florence-2 · Qwen2.5</span>
  </div>
</nav>

<style>
#aic-topnav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #FFFFFF;
    border-bottom: 1px solid #D8E2F0;
    padding: 0 24px;
    height: 58px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 1px 0 rgba(27,58,107,0.06), 0 2px 8px rgba(27,58,107,0.04);
    gap: 16px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
}
.tn-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    border-radius: 8px;
    border: none;
    background: transparent;
    color: #5A6A8A;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
    white-space: nowrap;
    box-shadow: none !important;
    min-width: unset !important;
    height: auto !important;
    width: auto !important;
}
.tn-btn i { font-size: 16px; flex-shrink: 0; }
.tn-btn:hover {
    background: #EEF2FA;
    color: #1B3A6B;
}
.tn-btn.active {
    background: #EEF2FA;
    color: #2A52A0;
    font-weight: 600;
    box-shadow: inset 0 -2px 0 0 #2A52A0 !important;
}
</style>

<script>
/* ── 상단 네비 ↔ Gradio Tabs 연동 ── */
(function () {
    var _tabBtns = null;
    var NUM_TABS = 4;

    function findTabBtns() {
        if (_tabBtns && _tabBtns.length === NUM_TABS) return _tabBtns;
        var sel = [
            '#content-tabs [role="tab"]',
            '#content-tabs .tab-nav button',
            '[role="tab"]'
        ];
        for (var s = 0; s < sel.length; s++) {
            var found = document.querySelectorAll(sel[s]);
            if (found.length === NUM_TABS) { _tabBtns = found; return _tabBtns; }
        }
        return null;
    }

    function syncNav(idx) {
        for (var i = 0; i < NUM_TABS; i++) {
            var el = document.getElementById('tn-' + i);
            if (el) el.classList.toggle('active', i === idx);
        }
    }

    window.navGo = function navGo(idx, _retry) {
        _retry = _retry || 0;
        syncNav(idx);
        var tabs = findTabBtns();
        if (tabs) {
            tabs[idx].click();
        } else if (_retry < 20) {
            _tabBtns = null;
            setTimeout(function () { navGo(idx, _retry + 1); }, 150);
        }
    };

    document.addEventListener('click', function (e) {
        var btn = e.target && e.target.closest('[role="tab"]');
        if (!btn) return;
        var tabs = findTabBtns();
        if (!tabs) return;
        var idx = Array.from(tabs).indexOf(btn);
        if (idx >= 0) syncNav(idx);
    }, true);
})();

/* ── 이미지 업로드 텍스트 커스텀 ── */
function patchUploadText() {
    var box = document.querySelector('.image-box');
    if (!box) return false;
    var els = Array.from(box.getElementsByTagName('*'));
    for (var i = 0; i < els.length; i++) {
        var el = els[i];
        var t = (el.innerText || '').trim();
        // file input 직접 포함 여부만 체크 (type="file" 한정), children 제한 완화
        if ((t.includes('드롭') || t.includes('클릭') || t.includes('Drop') || t.includes('Click') || t.includes('업로드') || t.includes('Upload'))
            && !el.querySelector('input[type="file"]')
            && el.children.length <= 15) {
            el.style.cssText = 'display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;text-align:center!important;padding:30px 24px!important;min-height:180px!important;gap:0!important;';
            el.innerHTML =
                '<div style="width:48px;height:48px;background:#EEF2FA;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:12px">' +
                '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4A6FA5" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>' +
                '</div>' +
                '<p style="font-size:13px;font-weight:600;color:#6B7484;margin:0 0 5px 0;padding:0">의류 사진을 드래그하거나 클릭해서 업로드</p>' +
                '<span style="font-size:11.5px;color:#9BAAC4;margin:0;padding:0;display:block">AI가 카테고리 · 색상 · 재질을 자동 분류합니다</span>';
            return true;
        }
    }
    return false;
}
if (!patchUploadText()) {
    [300, 700, 1200, 2500].forEach(function(t) { setTimeout(patchUploadText, t); });
}

/* ── 결과 텍스트박스 자동 높이 조정 ── */
function autoResizeResultBoxes() {
    document.querySelectorAll('.result-box textarea').forEach(function(ta) {
        ta.style.height = 'auto';
        ta.style.height = (ta.scrollHeight + 2) + 'px';
    });
}
setInterval(autoResizeResultBoxes, 800);
</script>
"""

_gr_major = int(gr.__version__.split(".")[0])


def _make_outfit_gallery_html(item_ids: list, wardrobe_map: dict) -> str:
    """코디의 착용 의류 이미지 카드 HTML 생성 (데일리룩 탭용)."""
    if not item_ids:
        return '<div style="color:#9BAAC4;font-size:12px;padding:12px 0">착용 의류 없음</div>'
    cards = []
    for iid in item_ids:
        item = wardrobe_map.get(iid)
        if not item:
            continue
        name = item.get("name", iid)
        img_url = item.get("image_path")
        if img_url:
            img_part = (
                f'<img src="{img_url}" style="width:100%;height:120px;'
                f'object-fit:cover;border-radius:10px;display:block" />'
            )
        else:
            img_part = (
                '<div style="width:100%;height:120px;background:#EEF2FA;border-radius:10px;'
                'display:flex;align-items:center;justify-content:center;font-size:26px">👔</div>'
            )
        cards.append(
            f'<div style="flex:0 0 130px;min-width:130px;text-align:center">'
            f'{img_part}'
            f'<div style="font-size:11px;color:#5A6A8A;margin-top:6px;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{name}</div>'
            f'</div>'
        )
    if not cards:
        return '<div style="color:#9BAAC4;font-size:12px;padding:12px 0">착용 의류 정보 없음</div>'
    return (
        '<div style="display:flex;gap:12px;flex-wrap:nowrap;overflow-x:auto;'
        'padding:10px 0 14px;scrollbar-width:thin">'
        + "".join(cards)
        + "</div>"
    )


# ── Blocks 레이아웃 ───────────────────────────────────────────────────────────

USAGE_GUIDE_HTML = """
<div id="usage-guide">
  <div class="guide-logo">
    <span class="guide-logo-icon">👗</span>
    <div>
      <div class="guide-title">AI Closet</div>
      <div class="guide-sub">스마트 AI 옷장 관리 사용 가이드</div>
    </div>
  </div>

  <div class="guide-step">
    <div class="guide-step-num">01</div>
    <div class="guide-step-body">
      <div class="guide-step-title">📸 옷장에 옷 추가하기</div>
      <div class="guide-step-desc">
        <b>옷장</b> 탭 → 사진을 업로드하거나 직접 설명을 입력<br>
        AI(Florence-2)가 자동으로 카테고리·색상·계절을 분류해 저장합니다.
      </div>
      <div class="guide-tip">💡 사진 없이 <em>비고란</em>에 텍스트로도 추가 가능</div>
    </div>
  </div>

  <div class="guide-step">
    <div class="guide-step-num">02</div>
    <div class="guide-step-body">
      <div class="guide-step-title">✏️ 의류 수정 / 삭제</div>
      <div class="guide-step-desc">
        저장된 의류 목록 테이블의 행을 클릭하면<br>
        <b>선택 항목 수정 / 삭제</b> 패널이 열립니다.<br>
        이름·카테고리·색상·계절 등 모든 항목을 수정할 수 있습니다.
      </div>
    </div>
  </div>

  <div class="guide-step">
    <div class="guide-step-num">03</div>
    <div class="guide-step-body">
      <div class="guide-step-title">✨ AI 코디 생성</div>
      <div class="guide-step-desc">
        <b>코디</b> 탭 → 상황·계절 선택 후<br>
        <em>AI 코디 생성</em> 버튼 클릭<br>
        AI가 옷장 의류를 조합해 맞춤 코디를 추천·저장합니다.
      </div>
      <div class="guide-tip">💡 저장된 코디는 상황·계절·태그 수정 가능</div>
    </div>
  </div>

  <div class="guide-step">
    <div class="guide-step-num">04</div>
    <div class="guide-step-body">
      <div class="guide-step-title">🌤️ 데일리룩 추천</div>
      <div class="guide-step-desc">
        <b>데일리룩</b> 탭 → 채팅으로 오늘 코디 질문<br>
        AI가 <em>날씨 + 저장된 코디</em>를 바탕으로 추천하고<br>
        코디명 선택 시 착용 의류 사진도 확인할 수 있습니다.
      </div>
    </div>
  </div>

  <div class="guide-step">
    <div class="guide-step-num">05</div>
    <div class="guide-step-body">
      <div class="guide-step-title">📊 대시보드</div>
      <div class="guide-step-desc">
        옷장 통계(카테고리·계절·상황별) 현황을 한눈에 확인합니다.
      </div>
    </div>
  </div>

  <div class="guide-footer">
    Powered by Florence-2 &amp; Qwen2.5
  </div>
</div>
"""

with gr.Blocks(css=CUSTOM_CSS, title="AI Closet", theme=gr.themes.Soft()) as demo:

    with gr.Row(elem_id="main-layout"):
        with gr.Column(scale=1, min_width=280, elem_id="left-guide"):
            gr.HTML(USAGE_GUIDE_HTML)
        with gr.Column(scale=2, min_width=0, elem_id="right-service"):
            gr.HTML(TOP_NAV_HTML)

            with gr.Tabs(elem_id="content-tabs"):

                # ── 탭 0: 옷장 ────────────────────────────────────────────────────
                with gr.Tab("옷장"):
                    gr.HTML("""
                        <div class="topbar" style="position:sticky;top:58px;z-index:9">
                            <span class="topbar-title">내 옷장</span>
                            <div class="topbar-meta">
                                <span class="topbar-badge">Florence-2 Vision</span>
                            </div>
                        </div>
                    """)
                    with gr.Column(elem_classes=["tab-content"]):
                        gr.HTML('<div class="section-header">의류 추가</div>')
                        with gr.Row():
                            image_input = gr.Image(
                                type="filepath",
                                label=None,
                                placeholder="여기에 이미지를 드래그하거나 클릭하여 업로드하세요.",
                                show_label=False,
                                elem_classes=["image-box"],
                            )
                            with gr.Column():
                                description_input = gr.Textbox(
                                    label="비고",
                                    placeholder="예: 네이비 체크 반소매 오버사이즈 셔츠",
                                    lines=2,
                                )
                                size_input = gr.Textbox(
                                    label="사이즈", placeholder="S, M, L, 250 등"
                                )
                                price_input = gr.Textbox(
                                    label="구매 가격", placeholder="50000"
                                )
                                date_input = gr.Textbox(
                                    label="구매 시기", placeholder="2024-03"
                                )
                                upload_btn = gr.Button(
                                    "AI 분류 및 추가", elem_classes=["btn-primary"]
                                )

                        upload_result = gr.Textbox(
                            label="분류 결과", interactive=False,
                            elem_classes=["result-box"],
                            lines=3, max_lines=20,
                        )
                        gr.HTML('<div class="section-header">저장된 의류 목록</div>')
                        wardrobe_df = gr.Dataframe(
                            headers=["이름", "카테고리", "색상", "스타일", "계절", "가격", "구매시기", "세탁방법"],
                            label=None,
                            elem_classes=["table-box"],
                        )
                        wardrobe_items_state = gr.State([])
                        selected_wardrobe_idx = gr.State(-1)
                        refresh_wardrobe_btn = gr.Button(
                            "목록 새로고침", elem_classes=["btn-secondary"]
                        )
                        with gr.Accordion("✏️ 선택 항목 수정 / 삭제", open=False) as wardrobe_edit_acc:
                            gr.HTML('<p style="font-size:12px;color:#9BAAC4;margin:0 0 10px">테이블에서 행을 클릭하면 편집할 수 있습니다.</p>')
                            with gr.Row():
                                item_image_display = gr.HTML(
                                    value='<div style="width:100%;height:160px;background:#EEF2FA;border-radius:10px;display:flex;align-items:center;justify-content:center;color:#9BAAC4;font-size:12px">사진 없음</div>'
                                )
                                with gr.Column():
                                    edit_w_name = gr.Textbox(label="이름", interactive=True)
                                    edit_w_category = gr.Dropdown(
                                        choices=["상의", "하의", "아우터", "신발", "가방", "악세사리", "기타"],
                                        label="카테고리", interactive=True,
                                    )
                                    with gr.Row():
                                        edit_w_color = gr.Textbox(label="색상", interactive=True)
                                        edit_w_style = gr.Textbox(label="스타일", interactive=True)
                            edit_w_season = gr.CheckboxGroup(
                                choices=["봄", "여름", "가을", "겨울"],
                                label="계절", interactive=True,
                                elem_id="edit-w-season",
                            )
                            with gr.Row():
                                edit_w_price = gr.Textbox(label="가격", interactive=True)
                                edit_w_purchase_date = gr.Textbox(label="구매시기", interactive=True)
                            edit_w_wash = gr.Textbox(label="세탁방법", interactive=True)
                            edit_w_size = gr.Textbox(label="사이즈", interactive=True)
                            with gr.Row():
                                save_edit_w_btn = gr.Button("💾 수정 저장", elem_classes=["btn-primary"])
                                delete_w_btn = gr.Button("🗑️ 삭제", elem_classes=["btn-danger"])
                            edit_w_result = gr.Textbox(interactive=False, show_label=False, max_lines=1)

                # ── 탭 1: 코디 ────────────────────────────────────────────────────
                with gr.Tab("코디"):
                    gr.HTML("""
                        <div class="topbar" style="position:sticky;top:58px;z-index:9">
                            <span class="topbar-title">코디 목록</span>
                            <div class="topbar-meta">
                                <span class="topbar-pill">✨ AI 생성 지원</span>
                            </div>
                        </div>
                    """)
                    with gr.Column(elem_classes=["tab-content"]):
                        gr.HTML('<div class="section-header">AI 코디 생성</div>')
                        with gr.Row():
                            situation_input = gr.Dropdown(
                                choices=["회사", "데이트", "운동", "경조사", "캐주얼", "여행", "기타"],
                                label="상황", value="캐주얼",
                            )
                            season_input = gr.Dropdown(
                                choices=["봄", "여름", "가을", "겨울", "사계절"],
                                label="계절", value="봄",
                            )
                            gen_btn = gr.Button(
                                "✨ AI 코디 생성", elem_classes=["btn-primary"]
                            )

                        outfit_result = gr.Textbox(
                            label="생성 결과", interactive=False,
                            elem_classes=["result-box"],
                            lines=3, max_lines=20,
                        )
                        gr.HTML('<div class="section-header">저장된 코디 목록</div>')
                        outfit_df = gr.Dataframe(
                            headers=["코디명", "상황", "계절", "태그", "착용 의류", "AI생성", "생성일"],
                            label=None,
                            elem_classes=["table-box"],
                        )
                        outfit_items_state = gr.State([])
                        selected_outfit_idx = gr.State(-1)
                        with gr.Accordion("✏️ 선택 코디 수정 / 삭제", open=False) as outfit_edit_acc:
                            gr.HTML('<p style="font-size:12px;color:#9BAAC4;margin:0 0 10px">테이블에서 행을 클릭하면 편집할 수 있습니다.</p>')
                            gr.HTML('<div style="font-size:11px;font-weight:600;color:#5A6A8A;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px">착용 의류</div>')
                            outfit_items_gallery = gr.HTML(
                                value='<div style="color:#9BAAC4;font-size:12px;padding:8px 0">코디를 선택하면 착용 의류 사진이 표시됩니다.</div>'
                            )
                            edit_o_name = gr.Textbox(label="코디명", interactive=True)
                            edit_o_situation = gr.CheckboxGroup(
                                choices=["회사", "데이트", "운동", "경조사", "캐주얼", "여행", "기타"],
                                label="상황", interactive=True,
                                elem_id="edit-o-situation",
                            )
                            edit_o_season = gr.CheckboxGroup(
                                choices=["봄", "여름", "가을", "겨울", "사계절"],
                                label="계절", interactive=True,
                                elem_id="edit-o-season",
                            )
                            edit_o_tags = gr.Textbox(label="태그 (쉼표로 구분)", interactive=True)
                            with gr.Row():
                                save_edit_o_btn = gr.Button("💾 수정 저장", elem_classes=["btn-primary"])
                                delete_o_btn = gr.Button("🗑️ 삭제", elem_classes=["btn-danger"])
                            edit_o_result = gr.Textbox(interactive=False, show_label=False, max_lines=1)

                # ── 탭 2: 대시보드 ────────────────────────────────────────────────
                with gr.Tab("대시보드"):
                    gr.HTML("""
                        <div class="topbar" style="position:sticky;top:58px;z-index:9">
                            <span class="topbar-title">옷장 대시보드</span>
                            <div class="topbar-meta">
                                <span class="topbar-badge">실시간 통계</span>
                            </div>
                        </div>
                    """)
                    with gr.Column(elem_classes=["tab-content"]):
                        with gr.Row():
                            total_items_num = gr.Number(
                                label="총 의류 수", interactive=False,
                                elem_classes=["stat-box"],
                            )
                            total_outfits_num = gr.Number(
                                label="저장된 코디", interactive=False,
                                elem_classes=["stat-box"],
                            )
                        gr.HTML('<div class="section-header">카테고리별 통계</div>')
                        stats_html = gr.HTML(value="<div class='sc-wrap'></div>")
                        dash_refresh_btn = gr.Button(
                            "통계 새로고침", elem_classes=["btn-secondary"]
                        )

                # ── 탭 3: 데일리룩 ────────────────────────────────────────────────
                with gr.Tab("데일리룩"):
                    gr.HTML("""
                        <div class="topbar" style="position:sticky;top:58px;z-index:9">
                            <span class="topbar-title">AI 데일리룩 추천</span>
                            <div class="topbar-meta">
                                <span class="topbar-badge">Qwen2.5 Vision</span>
                            </div>
                        </div>
                    """)
                    with gr.Column(elem_classes=["tab-content"]):
                        weather_html = gr.HTML(value="<div class='weather-card'></div>")
                        chatbot = gr.Chatbot(
                            label=None,
                            show_label=False,
                            height=340,
                            type="messages",
                            elem_classes=["chatbot-box"],
                        )
                        with gr.Row(elem_classes=["chat-input-row"]):
                            chat_input = gr.Textbox(
                                label="", show_label=False,
                                placeholder="날씨 보고 내일 코디 추천해줘...",
                                scale=10,
                                lines=1,
                                max_lines=1,
                                elem_id="chat-input",
                            )
                            chat_btn = gr.Button(
                                "➤",
                                scale=1,
                                elem_id="chat-send-btn",
                            )
                        clear_btn = gr.Button(
                            "대화 초기화", elem_classes=["btn-secondary"]
                        )
                        gr.HTML('<div class="section-header">코디 상세 보기</div>')
                        daily_outfit_select = gr.Dropdown(
                            label="코디 선택 (AI가 추천한 코디명을 여기서 선택하면 이미지를 확인할 수 있습니다)",
                            choices=[],
                            interactive=True,
                            elem_classes=["daily-outfit-select"],
                        )
                        daily_outfit_gallery = gr.HTML(value="")

    # ── 이벤트 연결 ──────────────────────────────────────────────────────────

    # 옷장 — 업로드/추가
    def _analyze_and_save(image, desc, size, price, date):
        result_msg, table = wardrobe.analyze_and_save(image, desc, size, price, date)
        items = storage.load_wardrobe().get("items", [])
        return result_msg, table, items

    upload_btn.click(
        fn=_analyze_and_save,
        inputs=[image_input, description_input, size_input, price_input, date_input],
        outputs=[upload_result, wardrobe_df, wardrobe_items_state],
    )

    def _refresh_wardrobe():
        items = storage.load_wardrobe().get("items", [])
        return dashboard.get_wardrobe_table(items), items

    refresh_wardrobe_btn.click(
        fn=_refresh_wardrobe,
        outputs=[wardrobe_df, wardrobe_items_state],
    )

    # 옷장 — 행 선택 → 편집 폼 채우기
    def _make_image_html(url: str | None) -> str:
        if url:
            return (
                f'<img src="{url}" style="width:100%;max-height:360px;'
                f'object-fit:contain;border-radius:10px;display:block;background:#F7F9FC" />'
            )
        return (
            '<div style="width:100%;height:160px;background:#EEF2FA;border-radius:10px;'
            'display:flex;align-items:center;justify-content:center;'
            'color:#9BAAC4;font-size:12px">사진 없음</div>'
        )

    def _on_wardrobe_select(evt: gr.SelectData, items):
        row = evt.index[0]
        empty = (-1, _make_image_html(None), "", "기타", "", "", [], "", "", "", "", gr.update(open=True))
        if not items or row < 0 or row >= len(items):
            return empty
        item = items[row]
        season = item.get("season") or []
        if isinstance(season, str):
            season = [s.strip() for s in season.split(",") if s.strip()]
        return (
            row,
            _make_image_html(item.get("image_path")),
            item.get("name", ""),
            item.get("category", "기타"),
            item.get("color", ""),
            item.get("style", ""),
            season,
            item.get("price") or "",
            item.get("purchase_date") or "",
            item.get("wash_instruction", ""),
            item.get("size") or "",
            gr.update(open=True),
        )

    wardrobe_df.select(
        fn=_on_wardrobe_select,
        inputs=[wardrobe_items_state],
        outputs=[
            selected_wardrobe_idx, item_image_display,
            edit_w_name, edit_w_category, edit_w_color, edit_w_style,
            edit_w_season, edit_w_price, edit_w_purchase_date, edit_w_wash,
            edit_w_size, wardrobe_edit_acc,
        ],
    )

    # 옷장 — 수정 저장
    def _update_wardrobe(sel_idx, items, name, category, color, style, season, price, purchase_date, wash, size):
        if sel_idx < 0 or not items or sel_idx >= len(items):
            return "수정할 항목을 먼저 선택해주세요.", [], []
        item = items[sel_idx]
        storage.update_item(item["id"], {
            "name": name,
            "category": category,
            "color": color,
            "style": style,
            "season": season if isinstance(season, list) else [],
            "price": price or None,
            "purchase_date": purchase_date or None,
            "wash_instruction": wash,
            "size": size or None,
        })
        new_items = storage.load_wardrobe().get("items", [])
        return f"✅ '{name}' 수정 완료", dashboard.get_wardrobe_table(new_items), new_items

    save_edit_w_btn.click(
        fn=_update_wardrobe,
        inputs=[
            selected_wardrobe_idx, wardrobe_items_state,
            edit_w_name, edit_w_category, edit_w_color, edit_w_style,
            edit_w_season, edit_w_price, edit_w_purchase_date, edit_w_wash,
            edit_w_size,
        ],
        outputs=[edit_w_result, wardrobe_df, wardrobe_items_state],
    )

    # 옷장 — 삭제
    _EMPTY_IMAGE_HTML = (
        '<div style="width:100%;height:160px;background:#EEF2FA;border-radius:10px;'
        'display:flex;align-items:center;justify-content:center;'
        'color:#9BAAC4;font-size:12px">사진 없음</div>'
    )

    def _delete_wardrobe(sel_idx, items):
        if sel_idx < 0 or not items or sel_idx >= len(items):
            return ("삭제할 항목을 먼저 선택해주세요.",
                    gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(open=False))
        item = items[sel_idx]
        storage.delete_item(item["id"])
        new_items = storage.load_wardrobe().get("items", [])
        return (
            f"✅ '{item.get('name', '')}' 삭제 완료",
            dashboard.get_wardrobe_table(new_items),
            new_items,
            -1,
            _EMPTY_IMAGE_HTML,
            "", "기타", "", "", [], "", "", "", "",
            gr.update(open=False),
        )

    delete_w_btn.click(
        fn=_delete_wardrobe,
        inputs=[selected_wardrobe_idx, wardrobe_items_state],
        outputs=[
            edit_w_result, wardrobe_df, wardrobe_items_state,
            selected_wardrobe_idx, item_image_display,
            edit_w_name, edit_w_category, edit_w_color, edit_w_style,
            edit_w_season, edit_w_price, edit_w_purchase_date,
            edit_w_wash, edit_w_size,
            wardrobe_edit_acc,
        ],
    )

    # 코디 — 생성
    def _generate_outfit(situation, season):
        msg, table = outfit.generate_outfit_ui(situation, season)
        outfit_items = storage.load_outfits().get("outfits", [])
        return msg, table, outfit_items

    gen_btn.click(
        fn=_generate_outfit,
        inputs=[situation_input, season_input],
        outputs=[outfit_result, outfit_df, outfit_items_state],
    )

    # 코디 — 착용 의류 갤러리 HTML 생성 헬퍼
    def _make_outfit_items_html(item_ids: list, wardrobe_map: dict) -> str:
        if not item_ids:
            return '<div style="color:#9BAAC4;font-size:12px;padding:8px 0">착용 의류 없음</div>'
        cards = []
        for iid in item_ids:
            item = wardrobe_map.get(iid)
            if not item:
                continue
            name = item.get("name", iid)
            img_url = item.get("image_path")
            if img_url:
                img_part = (
                    f'<img src="{img_url}" style="width:100%;height:100px;'
                    f'object-fit:cover;border-radius:8px;display:block" />'
                )
            else:
                img_part = (
                    '<div style="width:100%;height:100px;background:#EEF2FA;border-radius:8px;'
                    'display:flex;align-items:center;justify-content:center;font-size:22px">👔</div>'
                )
            cards.append(
                f'<div style="flex:0 0 110px;min-width:110px;text-align:center">'
                f'{img_part}'
                f'<div style="font-size:11px;color:#5A6A8A;margin-top:4px;'
                f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{name}</div>'
                f'</div>'
            )
        if not cards:
            return '<div style="color:#9BAAC4;font-size:12px;padding:8px 0">착용 의류 정보 없음</div>'
        return (
            '<div style="display:flex;gap:10px;flex-wrap:nowrap;overflow-x:auto;padding:8px 0 12px">'
            + "".join(cards)
            + '</div>'
        )

    # 코디 — 행 선택 → 편집 폼 채우기
    def _on_outfit_select(evt: gr.SelectData, items, wardrobe_items):
        row = evt.index[0]
        empty_gallery = '<div style="color:#9BAAC4;font-size:12px;padding:8px 0">코디를 선택하면 착용 의류 사진이 표시됩니다.</div>'
        if not items or row < 0 or row >= len(items):
            return -1, empty_gallery, "", [], [], "", gr.update(open=True)
        item = items[row]
        tags_str = ", ".join(item.get("tags") or [])
        wardrobe_map = {w["id"]: w for w in (wardrobe_items or [])}
        gallery_html = _make_outfit_items_html(item.get("item_ids") or [], wardrobe_map)

        def _to_list(val):
            if not val:
                return []
            if isinstance(val, list):
                return val
            s = str(val).strip()
            if s.startswith("["):
                try:
                    return json.loads(s)
                except Exception:
                    pass
            return [v.strip() for v in s.split(",") if v.strip()]

        situation = _to_list(item.get("situation"))
        season = _to_list(item.get("season"))

        return (
            row,
            gallery_html,
            item.get("name", ""),
            situation,
            season,
            tags_str,
            gr.update(open=True),
        )

    outfit_df.select(
        fn=_on_outfit_select,
        inputs=[outfit_items_state, wardrobe_items_state],
        outputs=[selected_outfit_idx, outfit_items_gallery, edit_o_name, edit_o_situation, edit_o_season, edit_o_tags, outfit_edit_acc],
    )

    # 코디 — 수정 저장
    def _update_outfit(sel_idx, items, wardrobe_items, name, situation, season, tags_str):
        if sel_idx < 0 or not items or sel_idx >= len(items):
            return "수정할 항목을 먼저 선택해주세요.", [], [], ""
        item = items[sel_idx]
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        storage.update_outfit(item["id"], {
            "name": name,
            "situation": situation if isinstance(situation, list) else ([situation] if situation else []),
            "season": season if isinstance(season, list) else ([season] if season else []),
            "tags": tags,
        })
        new_items = storage.load_outfits().get("outfits", [])
        # 갤러리 재생성 (item_ids 불변, wardrobe 업데이트 반영)
        wardrobe_map = {w["id"]: w for w in (wardrobe_items or [])}
        gallery_html = _make_outfit_items_html(item.get("item_ids") or [], wardrobe_map)
        return f"✅ '{name}' 수정 완료", dashboard.get_outfit_table(new_items), new_items, gallery_html

    save_edit_o_btn.click(
        fn=_update_outfit,
        inputs=[selected_outfit_idx, outfit_items_state, wardrobe_items_state, edit_o_name, edit_o_situation, edit_o_season, edit_o_tags],
        outputs=[edit_o_result, outfit_df, outfit_items_state, outfit_items_gallery],
    )

    # 코디 — 삭제
    _EMPTY_GALLERY_HTML = (
        '<div style="color:#9BAAC4;font-size:12px;padding:8px 0">'
        '코디를 선택하면 착용 의류 사진이 표시됩니다.</div>'
    )

    def _delete_outfit(sel_idx, items):
        if sel_idx < 0 or not items or sel_idx >= len(items):
            return ("삭제할 항목을 먼저 선택해주세요.",
                    gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(open=False))
        item = items[sel_idx]
        storage.delete_outfit(item["id"])
        new_items = storage.load_outfits().get("outfits", [])
        return (
            f"✅ '{item.get('name', '')}' 삭제 완료",
            dashboard.get_outfit_table(new_items),
            new_items,
            -1,
            _EMPTY_GALLERY_HTML,
            "", [], [], "",
            gr.update(open=False),
        )

    delete_o_btn.click(
        fn=_delete_outfit,
        inputs=[selected_outfit_idx, outfit_items_state],
        outputs=[
            edit_o_result, outfit_df, outfit_items_state,
            selected_outfit_idx, outfit_items_gallery,
            edit_o_name, edit_o_situation, edit_o_season, edit_o_tags,
            outfit_edit_acc,
        ],
    )

    # 대시보드
    def _refresh_dashboard():
        stats = dashboard.get_stats()
        return stats["total_items"], stats["total_outfits"], dashboard.build_stats_cards(stats)

    dash_refresh_btn.click(
        fn=_refresh_dashboard,
        outputs=[total_items_num, total_outfits_num, stats_html],
    )

    # 데일리룩
    chat_btn.click(
        fn=daily_look.recommend_daily_look,
        inputs=[chat_input, chatbot],
        outputs=[chatbot, chat_input],
    )
    chat_input.submit(
        fn=daily_look.recommend_daily_look,
        inputs=[chat_input, chatbot],
        outputs=[chatbot, chat_input],
    )
    clear_btn.click(
        fn=lambda: ([], ""),
        outputs=[chatbot, chat_input],
    )

    # 데일리룩 — 코디 선택 시 이미지 갤러리 표시
    def _show_daily_outfit(outfit_name, wardrobe_items):
        if not outfit_name:
            return ""
        outfits = storage.load_outfits().get("outfits", [])
        target = next((o for o in outfits if o.get("name") == outfit_name), None)
        if not target:
            return ""
        wardrobe_map = {w["id"]: w for w in (wardrobe_items or [])}
        return _make_outfit_gallery_html(target.get("item_ids") or [], wardrobe_map)

    daily_outfit_select.change(
        fn=_show_daily_outfit,
        inputs=[daily_outfit_select, wardrobe_items_state],
        outputs=[daily_outfit_gallery],
    )

    # 앱 로드 시 초기 데이터
    def _initial_load():
        w_items = storage.load_wardrobe().get("items", [])
        o_items = storage.load_outfits().get("outfits", [])
        stats = dashboard.get_stats()
        outfit_names = [o.get("name", "") for o in o_items if o.get("name")]
        return (
            dashboard.get_wardrobe_table(w_items),
            w_items,
            dashboard.get_outfit_table(o_items, w_items),
            o_items,
            daily_look.get_weather_html(),
            daily_look.get_initial_chat(),
            stats["total_items"],
            stats["total_outfits"],
            dashboard.build_stats_cards(stats),
            gr.update(choices=outfit_names, value=None),
        )

    demo.load(
        fn=_initial_load,
        outputs=[
            wardrobe_df,
            wardrobe_items_state,
            outfit_df,
            outfit_items_state,
            weather_html,
            chatbot,
            total_items_num,
            total_outfits_num,
            stats_html,
            daily_outfit_select,
        ],
    )


if __name__ == "__main__":
    is_space = bool(os.getenv("SPACE_ID"))
    launch_kwargs: dict = {
        "server_name": "0.0.0.0" if is_space else "127.0.0.1",
        "server_port": int(os.getenv("PORT", 7860)),
        "show_api": False,
    }
    if _gr_major >= 5:
        launch_kwargs["ssr_mode"] = False

    demo.launch(**launch_kwargs)
