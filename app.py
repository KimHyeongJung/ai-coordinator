"""
AI Closet — 스마트 AI 옷장 관리 서비스
HTML 사이드바 + Tabs 전환 방식 (HF Spaces 호환)
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

/* ── Main row ── */
#main-row {
    gap: 0 !important;
    align-items: flex-start !important;
    flex-wrap: nowrap !important;
}

/* ── Sidebar ── */
#sidebar-col,
#sidebar-col > .block,
#sidebar-col .block {
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    background: var(--navy) !important;
    box-shadow: none !important;
    gap: 0 !important;
    border-radius: 0 !important;
}
#aic-sidebar {
    position: sticky !important;
    top: 0 !important;
    height: 100vh !important;
    overflow: hidden !important;
}

/* ── Content col ── */
#content-col,
#content-col > .block,
#content-col > .gap {
    padding: 0 !important;
    gap: 0 !important;
    border: none !important;
    background: var(--surface) !important;
    border-radius: 0 !important;
}

/* ── 탭 네비 완전히 숨기기 (CSS로 처리, JS 불필요) ── */
.tab-nav,
.tab-nav * {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
    pointer-events: none !important;
}

/* ── 탭 컨테이너 & 탭 아이템 ── */
#content-tabs {
    background: transparent !important;
    border: none !important;
    gap: 0 !important;
    padding: 0 !important;
}
#content-tabs > div {
    padding: 0 !important;
    gap: 0 !important;
}
.tabitem {
    padding: 0 !important;
    border: none !important;
    background: var(--surface) !important;
}

/* ── Topbar ── */
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
.topbar-meta {
    display: flex;
    align-items: center;
    gap: 8px;
}
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

/* ── 콘텐츠 영역 ── */
.tab-content {
    padding: 20px 24px 32px !important;
    gap: 14px !important;
    background: var(--surface) !important;
    border: none !important;
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

/* ── 버튼 ── */
.btn-primary button {
    background: var(--navy) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 9px 20px !important;
    letter-spacing: -0.01em !important;
    transition: background 0.15s, transform 0.1s, box-shadow 0.15s !important;
    box-shadow: 0 1px 4px rgba(27,58,107,0.22) !important;
}
.btn-primary button:hover {
    background: var(--navy-light) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(27,58,107,0.28) !important;
}
.btn-primary button:active {
    transform: translateY(0) !important;
    box-shadow: 0 1px 3px rgba(27,58,107,0.18) !important;
}
.btn-secondary button {
    background: var(--white) !important;
    color: var(--text-muted) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    transition: all 0.15s !important;
}
.btn-secondary button:hover {
    border-color: var(--navy-mid) !important;
    color: var(--navy) !important;
    background: var(--navy-pale) !important;
}

/* ── 폼 라벨 ── */
.block label > span:first-child,
.block .label-wrap span {
    font-size: 11.5px !important;
    color: var(--text-muted) !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em !important;
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
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.block input:focus, .block textarea:focus {
    border-color: var(--navy-mid) !important;
    box-shadow: 0 0 0 3px rgba(74,111,165,0.12) !important;
    background: #EEF2FA !important;
    outline: none !important;
}

/* ── 드롭다운 선택 영역 배경 #EEF2FA ── */
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
/* 드롭다운 열린 목록은 흰 배경 유지 (가독성) */
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
.image-box .wrap,
.image-box .upload-container,
.image-box > div > div {
    border: 1.5px dashed #BFD0E8 !important;
    border-radius: var(--radius-lg) !important;
    background: #FAFCFF !important;
    min-height: 210px !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    transition: border-color 0.2s, background 0.2s !important;
}
.image-box .wrap:hover,
.image-box .upload-container:hover {
    border-color: var(--navy-mid) !important;
    background: var(--navy-pale) !important;
}
.image-box,
.image-box .block,
.image-box > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* ── 결과 텍스트 박스 (자동 확장 + #EEF2FA) ── */
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
.stat-box > .block {
    background: var(--white) !important;
    border: none !important;
    padding: 22px 16px 18px !important;
}
.stat-box input[type="number"] {
    font-size: 36px !important;
    font-weight: 700 !important;
    color: var(--navy) !important;
    border: none !important;
    background: transparent !important;
    text-align: center !important;
    padding: 4px 0 !important;
    width: 100% !important;
    box-shadow: none !important;
}
.stat-box label > span:first-child {
    font-size: 10.5px !important;
    color: var(--text-hint) !important;
    font-weight: 600 !important;
    text-align: center !important;
    display: block !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    margin-bottom: 6px !important;
}

/* ── 통계 플랫 카드 ── */
.sc-wrap {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 4px 0;
}
.sc-section {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 14px 16px;
    box-shadow: var(--shadow-sm);
}
.sc-title {
    font-size: 10.5px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 10px;
}
.sc-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}
.sc-card {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: var(--navy-pale);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 7px 13px;
}
.sc-label {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
}
.sc-val {
    font-size: 14px;
    font-weight: 700;
    color: var(--navy);
}

/* ── 날씨 카드 (HTML) ── */
.weather-card {
    background: linear-gradient(135deg, #1D3E72 0%, #2A52A0 100%);
    border-radius: 16px;
    padding: 20px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #fff;
    box-shadow: 0 4px 20px rgba(27,58,107,0.25);
}
.weather-left {
    display: flex;
    align-items: center;
    gap: 16px;
}
.weather-emoji { font-size: 46px; line-height: 1; }
.weather-temp {
    font-size: 34px;
    font-weight: 700;
    color: #fff;
    line-height: 1.1;
    letter-spacing: -0.03em;
}
.weather-sub {
    font-size: 12px;
    color: rgba(255,255,255,0.65);
    margin-top: 4px;
    letter-spacing: 0.01em;
}
.weather-right {
    text-align: right;
    display: flex;
    flex-direction: column;
    gap: 5px;
    align-items: flex-end;
}
.weather-stat { font-size: 11.5px; color: rgba(255,255,255,0.68); }
.weather-source { font-size: 10px; color: rgba(255,255,255,0.35); margin-top: 2px; }

/* ── 챗봇 ── */
.chatbot-box > div,
.chatbot-box .wrap {
    border-radius: var(--radius-lg) !important;
    border: 1px solid var(--border) !important;
    background: var(--white) !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: hidden !important;
}
.chatbot-box [data-testid="user"] > div,
.chatbot-box .message.user .bubble {
    background: var(--navy) !important;
    color: #fff !important;
    border-radius: 14px 14px 4px 14px !important;
    border: none !important;
}
/* Bot 메시지: 흰 배경 + 회색 계열 텍스트 */
.chatbot-box [data-testid="bot"] > div,
.chatbot-box .message.bot .bubble {
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px 14px 14px 4px !important;
}
.chatbot-box [data-testid="bot"] p,
.chatbot-box [data-testid="bot"] li,
.chatbot-box [data-testid="bot"] span,
.chatbot-box [data-testid="bot"] div {
    color: #5A6A8A !important;
}
.chatbot-box [data-testid="bot"] strong,
.chatbot-box [data-testid="bot"] b {
    color: var(--navy-light) !important;
    font-weight: 600 !important;
}

/* ── 채팅 입력 (Pill 형태) ── */
.chat-input-row {
    align-items: center !important;
    gap: 10px !important;
}
.chat-input-row > .block,
.chat-input-row > div {
    margin: 0 !important;
    padding: 0 !important;
}
#chat-input > .block,
#chat-input .block {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}
#chat-input textarea,
#chat-input input[type="text"] {
    border-radius: 50px !important;
    padding: 12px 22px !important;
    border: 1.5px solid var(--border) !important;
    background: #EEF2FA !important;
    color: var(--text) !important;
    font-size: 13px !important;
    resize: none !important;
    min-height: 46px !important;
    max-height: 46px !important;
    line-height: 1.5 !important;
    overflow-y: hidden !important;
    box-shadow: none !important;
}
#chat-input textarea:focus,
#chat-input input[type="text"]:focus {
    border-color: var(--navy-mid) !important;
    box-shadow: 0 0 0 3px rgba(74,111,165,0.12) !important;
    outline: none !important;
}

/* ── 전송 버튼 (원형) ── */
#chat-send-btn,
#chat-send-btn > .block {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    flex-shrink: 0 !important;
    box-shadow: none !important;
}
#chat-send-btn button {
    background: var(--navy) !important;
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
    box-shadow: 0 2px 8px rgba(27,58,107,0.3) !important;
    transition: background 0.15s, transform 0.1s !important;
    cursor: pointer !important;
}
#chat-send-btn button:hover { background: var(--navy-light) !important; transform: scale(1.06) !important; }
#chat-send-btn button:active { transform: scale(0.97) !important; }

/* ── 데이터프레임 배경 #EEF2FA ── */
.table-box {
    background: #EEF2FA !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-sm) !important;
}
.table-box > .block {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}
.table-box table {
    border-collapse: collapse !important;
    width: 100% !important;
}
.table-box table thead tr { background: var(--navy) !important; }
.table-box table thead th {
    color: rgba(255,255,255,0.85) !important;
    font-weight: 500 !important;
    font-size: 11.5px !important;
    padding: 11px 14px !important;
    border: none !important;
    letter-spacing: 0.03em !important;
    white-space: nowrap !important;
}
.table-box table tbody tr td {
    font-size: 12.5px !important;
    color: var(--text) !important;
    padding: 9px 14px !important;
    background: #EEF2FA !important;
    border-bottom: 1px solid var(--border-light) !important;
    border-right: none !important;
    border-left: none !important;
    border-top: none !important;
}
.table-box table tbody tr:last-child td { border-bottom: none !important; }
.table-box table tbody tr:hover td {
    background: #D8E2F0 !important;
    transition: background 0.12s !important;
}

/* ── 스크롤바 ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #C4D4E8; border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--navy-mid); }
"""

# ── 사이드바 HTML ─────────────────────────────────────────────────────────────
SIDEBAR_HTML = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.34.0/dist/tabler-icons.min.css">
<div id="aic-sidebar" style="
    background: linear-gradient(180deg, #1D3E72 0%, #1B3A6B 100%);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    width: 100%;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
">
  <!-- 로고 -->
  <div style="padding:22px 18px 18px; border-bottom:1px solid rgba(255,255,255,.09)">
    <div style="display:flex; align-items:center; gap:11px">
      <div style="
        width:36px; height:36px;
        background:rgba(255,255,255,.15);
        border-radius:9px;
        display:flex; align-items:center; justify-content:center;
        flex-shrink:0;
        border:1px solid rgba(255,255,255,.1);
      ">
        <i class="ti ti-shirt" style="color:#fff; font-size:18px"></i>
      </div>
      <div>
        <div style="color:#fff; font-size:14px; font-weight:600; line-height:1.25; letter-spacing:-0.02em">AI Closet</div>
        <div style="color:rgba(255,255,255,.42); font-size:10px; margin-top:2px; letter-spacing:0.01em">스마트 옷장 관리</div>
      </div>
    </div>
  </div>

  <!-- 메뉴 -->
  <div style="padding:14px 10px; flex:1">
    <div style="
      font-size:9px; font-weight:700;
      color:rgba(255,255,255,.22);
      text-transform:uppercase; letter-spacing:.12em;
      padding:0 8px 10px;
    ">메뉴</div>

    <div class="sb-item active" id="sb-0" onclick="sbGo(0)">
      <i class="ti ti-hanger sb-icon" aria-hidden="true"></i>
      <span>옷장</span>
    </div>
    <div class="sb-item" id="sb-1" onclick="sbGo(1)">
      <i class="ti ti-layout-grid sb-icon" aria-hidden="true"></i>
      <span>코디</span>
    </div>
    <div class="sb-item" id="sb-2" onclick="sbGo(2)">
      <i class="ti ti-chart-pie sb-icon" aria-hidden="true"></i>
      <span>대시보드</span>
    </div>
    <div class="sb-item" id="sb-3" onclick="sbGo(3)">
      <i class="ti ti-wand sb-icon" aria-hidden="true"></i>
      <span>데일리룩</span>
    </div>
  </div>

  <!-- 하단 -->
  <div style="padding:10px 10px 20px; border-top:1px solid rgba(255,255,255,.08)">
    <div class="sb-item" style="opacity:.32; cursor:default; pointer-events:none">
      <i class="ti ti-settings sb-icon" aria-hidden="true"></i>
      <span>설정</span>
    </div>
    <div style="padding:10px 8px 0; font-size:9.5px; color:rgba(255,255,255,.18); line-height:1.55; letter-spacing:0.01em">
      Florence-2 · Qwen2.5-7B<br>Open-Meteo · Supabase
    </div>
  </div>
</div>

<style>
.sb-item {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 9px 10px;
    border-radius: 8px;
    cursor: pointer;
    color: rgba(255,255,255,.52);
    font-size: 13px;
    transition: all .15s;
    margin-bottom: 2px;
    user-select: none;
    position: relative;
}
.sb-item:hover { background: rgba(255,255,255,.08); color: rgba(255,255,255,.88); }
.sb-item.active { background: rgba(255,255,255,.13); color: #fff; font-weight: 500; }
.sb-item.active::before {
    content: '';
    position: absolute;
    left: 0; top: 50%;
    transform: translateY(-50%);
    width: 3px; height: 65%;
    background: rgba(255,255,255,.75);
    border-radius: 0 3px 3px 0;
}
.sb-icon { font-size: 16px; flex-shrink: 0; width: 18px; text-align: center; }
</style>

<script>
/* 사이드바 → 탭 전환
   gr.Tabs가 생성한 [role="tab"] 버튼을 찾아 클릭.
   Gradio는 display:none 탭 버튼도 click() 이벤트를 처리함. */
function sbGo(idx, attempt) {
    attempt = attempt || 0;

    /* 사이드바 active 상태 업데이트 */
    for (var i = 0; i < 4; i++) {
        var el = document.getElementById('sb-' + i);
        if (el) el.classList.toggle('active', i === idx);
    }

    /* Gradio Tabs 버튼 탐색 (여러 선택자 시도) */
    var btns = document.querySelectorAll('#content-tabs [role="tab"]');
    if (!btns || !btns.length) {
        btns = document.querySelectorAll('#content-tabs .tab-nav button');
    }
    if (!btns || !btns.length) {
        btns = document.querySelectorAll('[role="tab"]');
    }

    if (btns && btns.length > idx) {
        btns[idx].click();
    } else if (attempt < 10) {
        /* Gradio 렌더링 완료 전이면 재시도 */
        setTimeout(function() { sbGo(idx, attempt + 1); }, 150);
    }
}

/* 이미지 업로드 텍스트 커스텀 */
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
                '<p style="font-size:13px;font-weight:600;color:#1A2540;margin:0 0 5px 0;padding:0">의류 사진을 드래그하거나 클릭해서 업로드</p>' +
                '<span style="font-size:11.5px;color:#9BAAC4;margin:0;padding:0;display:block">AI가 카테고리 · 색상 · 재질을 자동 분류합니다</span>';
            return true;
        }
    }
    return false;
}
if (!patchUploadText()) {
    [300, 700, 1500].forEach(function(t) { setTimeout(patchUploadText, t); });
}

/* 결과 텍스트박스 자동 높이 조정 (field-sizing 미지원 브라우저 대응) */
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
with gr.Blocks(css=CUSTOM_CSS, title="AI Closet", theme=gr.themes.Base()) as demo:

    with gr.Row(elem_id="main-row"):

        # ── 왼쪽: 사이드바 ────────────────────────────────────────────────────
        with gr.Column(scale=0, min_width=210, elem_id="sidebar-col"):
            gr.HTML(SIDEBAR_HTML)

        # ── 오른쪽: 컨텐츠 (gr.Tabs로 페이지 전환) ───────────────────────────
        with gr.Column(scale=1, elem_id="content-col"):
            with gr.Tabs(elem_id="content-tabs"):

                # ── 탭 0: 옷장 ────────────────────────────────────────────
                with gr.Tab("옷장"):
                    gr.HTML("""
                        <div class="topbar" style="position:sticky;top:0;z-index:10">
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

                # ── 탭 1: 코디 ────────────────────────────────────────────
                with gr.Tab("코디"):
                    gr.HTML("""
                        <div class="topbar" style="position:sticky;top:0;z-index:10">
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

                # ── 탭 2: 대시보드 ────────────────────────────────────────
                with gr.Tab("대시보드"):
                    gr.HTML("""
                        <div class="topbar" style="position:sticky;top:0;z-index:10">
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

                # ── 탭 3: 데일리룩 ────────────────────────────────────────
                with gr.Tab("데일리룩"):
                    gr.HTML("""
                        <div class="topbar" style="position:sticky;top:0;z-index:10">
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
                                scale=4,
                                lines=1,
                                max_lines=1,
                                elem_id="chat-input",
                            )
                            chat_btn = gr.Button(
                                "↑", scale=0, min_width=46,
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
