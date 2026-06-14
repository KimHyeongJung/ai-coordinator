"""
AI Closet — 스마트 AI 옷장 관리 서비스
상단 네비게이션 바 + Tabs 전환 방식 (HF Spaces 호환)
"""

from __future__ import annotations

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
    padding: 0 28px !important;
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
    padding: 0 24px !important;
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

/* ── 폼 라벨 배지 (span 텍스트만 타깃) ── */
.block label > span:first-child,
.block .label-wrap > span,
.block .label-wrap label > span:first-child {
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
.stat-box input[type="number"] {
    font-size: 36px !important; font-weight: 700 !important; color: var(--navy) !important;
    border: none !important; background: transparent !important;
    text-align: center !important; padding: 4px 0 !important; width: 100% !important; box-shadow: none !important;
}
.stat-box label > span:first-child {
    font-size: 10.5px !important; color: var(--text-hint) !important; font-weight: 600 !important;
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
/* 유저 메시지 */
.chatbot-box [data-testid="user"] > div,
.chatbot-box .message.user .bubble {
    background: var(--navy) !important;
    color: #fff !important;
    border-radius: 14px 14px 4px 14px !important;
    border: none !important;
}
/* 봇 메시지 - 회색 계열 텍스트 */
.chatbot-box [data-testid="bot"] > div,
.chatbot-box .message.bot .bubble {
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px 14px 14px 4px !important;
}
.chatbot-box [data-testid="bot"] p,
.chatbot-box [data-testid="bot"] li,
.chatbot-box [data-testid="bot"] span,
.chatbot-box [data-testid="bot"] div { color: #5A6A8A !important; }
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

/* ── 전송 버튼 (원형, 항상 보임) ── */
#chat-send-btn,
#chat-send-btn > .block,
#chat-send-btn > div {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
    flex: 0 0 54px !important;
    max-width: 54px !important;
    min-width: 46px !important;
}
#chat-send-btn button {
    background: var(--navy-light) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 50% !important;
    width: 46px !important;
    height: 46px !important;
    min-width: 46px !important;
    padding: 0 !important;
    font-size: 19px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 8px rgba(42,82,160,0.35) !important;
    transition: background 0.15s, transform 0.1s !important;
    cursor: pointer !important;
}
#chat-send-btn button:hover { background: var(--navy) !important; transform: scale(1.06) !important; }
#chat-send-btn button:active { transform: scale(0.97) !important; }

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
.table-box table tbody tr td { font-size: 12.5px !important; color: var(--text) !important; padding: 9px 14px !important; background: #EEF2FA !important; border-bottom: 1px solid var(--border-light) !important; border-right: none !important; border-left: none !important; border-top: none !important; }
.table-box table tbody tr:last-child td { border-bottom: none !important; }
.table-box table tbody tr:hover td { background: #D8E2F0 !important; transition: background 0.12s !important; }

/* ── 스크롤바 ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #C4D4E8; border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--navy-mid); }
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
        if ((t.includes('드롭') || t.includes('클릭') || t.includes('Drop') || t.includes('Click') || t.includes('Upload'))
            && el.children.length <= 5 && !el.querySelector('input')) {
            el.style.cssText = 'display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;text-align:center!important;padding:30px 24px!important;min-height:210px!important;gap:0!important;';
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
    [300, 700, 1500].forEach(function(t) { setTimeout(patchUploadText, t); });
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

# ── Blocks 레이아웃 ───────────────────────────────────────────────────────────
with gr.Blocks(css=CUSTOM_CSS, title="AI Closet", theme=gr.themes.Soft()) as demo:

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
                        label="의류 사진 업로드",
                        elem_classes=["image-box"],
                    )
                    with gr.Column():
                        description_input = gr.Textbox(
                            label="직접 설명 (선택 — AI 분석 실패 시)",
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
                gr.HTML('<div class="section-header">옷장 목록</div>')
                wardrobe_df = gr.Dataframe(
                    headers=["이름", "카테고리", "색상", "사진", "계절", "사이즈", "등록일"],
                    label=None,
                    elem_classes=["table-box"],
                )
                refresh_wardrobe_btn = gr.Button(
                    "목록 새로고침", elem_classes=["btn-secondary"]
                )

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
                    label="생성된 코디", interactive=False,
                    elem_classes=["result-box"],
                    lines=3, max_lines=20,
                )
                gr.HTML('<div class="section-header">저장된 코디 목록</div>')
                outfit_df = gr.Dataframe(
                    headers=["코디명", "상황", "계절", "태그", "착용 의류", "AI생성", "생성일"],
                    label=None,
                    elem_classes=["table-box"],
                )

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
                        <span class="topbar-badge">Open-Meteo 날씨</span>
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
                        "↑",
                        scale=1,
                        elem_id="chat-send-btn",
                    )
                clear_btn = gr.Button(
                    "대화 초기화", elem_classes=["btn-secondary"]
                )

    # ── 이벤트 연결 ──────────────────────────────────────────────────────────

    # 옷장
    upload_btn.click(
        fn=wardrobe.analyze_and_save,
        inputs=[image_input, description_input, size_input, price_input, date_input],
        outputs=[upload_result, wardrobe_df],
    )
    refresh_wardrobe_btn.click(
        fn=dashboard.get_wardrobe_table,
        outputs=wardrobe_df,
    )

    # 코디
    gen_btn.click(
        fn=outfit.generate_outfit_ui,
        inputs=[situation_input, season_input],
        outputs=[outfit_result, outfit_df],
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

    # 앱 로드 시 초기 데이터
    def _initial_load():
        wardrobe_table = dashboard.get_wardrobe_table()
        outfit_table = dashboard.get_outfit_table()
        stats = dashboard.get_stats()
        return (
            wardrobe_table,
            outfit_table,
            daily_look.get_weather_html(),
            daily_look.get_initial_chat(),
            stats["total_items"],
            stats["total_outfits"],
            dashboard.build_stats_cards(stats),
        )

    demo.load(
        fn=_initial_load,
        outputs=[
            wardrobe_df,
            outfit_df,
            weather_html,
            chatbot,
            total_items_num,
            total_outfits_num,
            stats_html,
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
