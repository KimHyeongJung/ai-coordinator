"""
AI Closet — 스마트 AI 옷장 관리 서비스
========================================
탭 구성:
  1) 옷장  : 의류 사진 업로드 → Florence-2 캡셔닝 → LLM 정보 추출 → Supabase 저장
  2) 코디  : 상황/계절 입력 → LLM 코디 자동 생성 → Supabase 저장
  3) 대시보드: 옷장/코디 통계
  4) 데일리룩: 날씨(Open-Meteo) + 옷장 기반 AI 채팅 추천

HuggingFace Space(Gradio SDK)에 올리면 그대로 배포된다.
로컬 실행: python app.py
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
import dashboard  # noqa: E402
import outfit  # noqa: E402
import wardrobe  # noqa: E402

load_dotenv()

CUSTOM_CSS = """
/* ── Variables ──────────────────────────────────────────── */
:root {
    --navy:       #1B3A6B;
    --navy-light: #2A52A0;
    --navy-pale:  #EEF2FA;
    --navy-mid:   #4A6FA5;
    --white:      #FFFFFF;
    --surface:    #F7F9FC;
    --border:     #D8E2F0;
    --text:       #1A2540;
    --text-muted: #5A6A8A;
    --text-hint:  #9BAAC4;
}

/* ── Global ─────────────────────────────────────────────── */
.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
    background: var(--surface) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}
footer { display: none !important; }
.app-title { display: none !important; }

/* ── Sidebar: Tabs → vertical nav ───────────────────────── */
#main-tabs > div,
#main-tabs .tabs {
    display: flex !important;
    flex-direction: row !important;
    min-height: 100vh !important;
    border: none !important;
    gap: 0 !important;
    align-items: stretch !important;
}

#main-tabs .tab-nav {
    flex-direction: column !important;
    width: 210px !important;
    min-width: 210px !important;
    max-width: 210px !important;
    background: var(--navy) !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0 10px 20px !important;
    gap: 2px !important;
    align-items: stretch !important;
    position: sticky !important;
    top: 0 !important;
    height: 100vh !important;
    overflow: hidden !important;
    flex-shrink: 0 !important;
}

#main-tabs .tab-nav::before {
    content: "🧥  AI Closet";
    display: block;
    color: #ffffff;
    font-size: 15px;
    font-weight: 600;
    padding: 22px 10px 18px;
    border-bottom: 1px solid rgba(255,255,255,0.12);
    margin: 0 0 12px 0;
    letter-spacing: 0.01em;
    flex-shrink: 0;
}

#main-tabs .tab-nav button {
    display: flex !important;
    justify-content: flex-start !important;
    text-align: left !important;
    border-radius: 8px !important;
    padding: 9px 12px !important;
    color: rgba(255,255,255,0.55) !important;
    font-size: 12.5px !important;
    background: transparent !important;
    border: none !important;
    border-bottom: none !important;
    transition: all 0.15s !important;
    font-weight: 400 !important;
    width: 100% !important;
    letter-spacing: 0.01em !important;
}

#main-tabs .tab-nav button:hover {
    background: rgba(255,255,255,0.08) !important;
    color: rgba(255,255,255,0.85) !important;
}

#main-tabs .tab-nav button.selected {
    background: rgba(255,255,255,0.15) !important;
    color: #ffffff !important;
    font-weight: 500 !important;
    border-bottom: none !important;
}

#main-tabs .tabitem {
    flex: 1 !important;
    overflow: auto !important;
    border: none !important;
    background: var(--surface) !important;
    padding: 0 !important;
    min-width: 0 !important;
}

/* ── Topbar ──────────────────────────────────────────────── */
.topbar {
    background: var(--white) !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 14px 24px !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    color: var(--text) !important;
}

/* ── Tab content ─────────────────────────────────────────── */
.tab-content {
    padding: 20px 24px 28px !important;
    gap: 16px !important;
    background: var(--surface) !important;
    border: none !important;
}

/* ── Section headers ─────────────────────────────────────── */
.section-header {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--text) !important;
    padding-bottom: 10px !important;
    border-bottom: 1px solid var(--border) !important;
    margin-bottom: 2px !important;
}

/* ── Buttons ─────────────────────────────────────────────── */
.btn-primary button {
    background: var(--navy) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: background 0.15s !important;
}
.btn-primary button:hover {
    background: var(--navy-light) !important;
    border: none !important;
}

.btn-secondary button {
    background: var(--white) !important;
    color: var(--text-muted) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    transition: all 0.15s !important;
}
.btn-secondary button:hover {
    border-color: var(--navy-mid) !important;
    color: var(--navy) !important;
}

/* ── Form labels ─────────────────────────────────────────── */
.block label > span:first-child,
.block .label-wrap span {
    font-size: 12px !important;
    color: var(--text-muted) !important;
    font-weight: 500 !important;
}

/* ── Inputs ──────────────────────────────────────────────── */
.block input[type="text"],
.block input[type="number"],
.block textarea {
    border-color: var(--border) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    background: var(--white) !important;
    color: var(--text) !important;
}
.block input:focus,
.block textarea:focus {
    border-color: var(--navy-light) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(42,82,160,0.08) !important;
}

/* ── Result box ──────────────────────────────────────────── */
.result-box textarea {
    background: var(--navy-pale) !important;
    border-color: var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
}

/* ── Stat boxes ──────────────────────────────────────────── */
.stat-box {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}
.stat-box input[type="number"] {
    font-size: 32px !important;
    font-weight: 600 !important;
    color: var(--navy) !important;
    border: none !important;
    background: transparent !important;
    padding: 4px 0 !important;
}

/* ── Weather box ─────────────────────────────────────────── */
.weather-box textarea {
    background: var(--navy) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-size: 13px !important;
    padding: 14px 18px !important;
    line-height: 1.6 !important;
}
.weather-box label > span:first-child {
    color: var(--text-muted) !important;
}

/* ── Chatbot ─────────────────────────────────────────────── */
.chatbot-box .wrap,
.chatbot-box > div {
    border-radius: 12px !important;
    border: 1px solid var(--border) !important;
    background: var(--white) !important;
}

/* ── Dataframe ───────────────────────────────────────────── */
.table-box table thead tr {
    background: var(--navy-pale) !important;
}
.table-box table thead th {
    color: var(--navy) !important;
    font-weight: 500 !important;
    font-size: 12px !important;
    border-bottom: 1px solid var(--border) !important;
}
.table-box table tbody tr:hover td {
    background: var(--surface) !important;
}
.table-box table td {
    font-size: 12.5px !important;
    color: var(--text) !important;
    border-bottom: 1px solid var(--border) !important;
}

/* ── Image upload ────────────────────────────────────────── */
.image-box .wrap {
    border: 1.5px dashed var(--border) !important;
    border-radius: 12px !important;
    background: var(--white) !important;
}
.image-box .wrap:hover {
    border-color: var(--navy-mid) !important;
}

/* ── Chat input row ──────────────────────────────────────── */
.chat-send-btn button {
    background: var(--navy) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    height: 100% !important;
}

/* ── JSON stats ──────────────────────────────────────────── */
.stats-json {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}
"""

_gr_major = int(gr.__version__.split(".")[0])

with gr.Blocks(css=CUSTOM_CSS, title="AI Closet", theme=gr.themes.Base()) as demo:

    with gr.Tabs(elem_id="main-tabs"):

        # ── 탭 1: 옷장 ──────────────────────────────────────────────
        with gr.Tab("🧥  옷장"):
            gr.HTML('<div class="topbar">내 옷장</div>')
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
                            label="직접 설명 (선택 — AI 분석 실패 시 입력)",
                            placeholder="예: 네이비 체크 반소매 오버사이즈 셔츠",
                            lines=2,
                        )
                        size_input = gr.Textbox(
                            label="사이즈 (선택)", placeholder="S, M, L, 250 등"
                        )
                        price_input = gr.Textbox(
                            label="구매 가격 (선택)", placeholder="50000"
                        )
                        date_input = gr.Textbox(
                            label="구매 시기 (선택)", placeholder="2024-03"
                        )
                        upload_btn = gr.Button(
                            "AI 분류 및 추가", elem_classes=["btn-primary"]
                        )

                upload_result = gr.Textbox(
                    label="분류 결과", interactive=False, elem_classes=["result-box"]
                )

                gr.HTML('<div class="section-header">내 옷장 목록</div>')
                wardrobe_df = gr.Dataframe(
                    headers=["이름", "카테고리", "색상", "사진", "계절", "사이즈", "등록일"],
                    label=None,
                    elem_classes=["table-box"],
                )
                refresh_wardrobe_btn = gr.Button(
                    "목록 새로고침", elem_classes=["btn-secondary"]
                )

        # ── 탭 2: 코디 ──────────────────────────────────────────────
        with gr.Tab("👗  코디"):
            gr.HTML('<div class="topbar">코디 목록</div>')
            with gr.Column(elem_classes=["tab-content"]):
                gr.HTML('<div class="section-header">AI 코디 생성</div>')
                with gr.Row():
                    situation_input = gr.Dropdown(
                        choices=["회사", "데이트", "운동", "경조사", "캐주얼", "여행", "기타"],
                        label="상황",
                        value="캐주얼",
                    )
                    season_input = gr.Dropdown(
                        choices=["봄", "여름", "가을", "겨울", "사계절"],
                        label="계절",
                        value="봄",
                    )
                    gen_btn = gr.Button(
                        "✨ AI 코디 생성", elem_classes=["btn-primary"]
                    )

                outfit_result = gr.Textbox(
                    label="생성된 코디", interactive=False, elem_classes=["result-box"]
                )

                gr.HTML('<div class="section-header">저장된 코디 목록</div>')
                outfit_df = gr.Dataframe(
                    headers=["코디명", "상황", "계절", "태그", "AI생성", "생성일"],
                    label=None,
                    elem_classes=["table-box"],
                )

        # ── 탭 3: 대시보드 ──────────────────────────────────────────
        with gr.Tab("📊  대시보드"):
            gr.HTML('<div class="topbar">옷장 대시보드</div>')
            with gr.Column(elem_classes=["tab-content"]):
                with gr.Row():
                    total_items_num = gr.Number(
                        label="총 의류 수", interactive=False, elem_classes=["stat-box"]
                    )
                    total_outfits_num = gr.Number(
                        label="저장된 코디", interactive=False, elem_classes=["stat-box"]
                    )

                stats_json = gr.JSON(label="카테고리별 통계", elem_classes=["stats-json"])
                dash_refresh_btn = gr.Button(
                    "통계 새로고침", elem_classes=["btn-secondary"]
                )

        # ── 탭 4: 데일리룩 ──────────────────────────────────────────
        with gr.Tab("✨  데일리룩"):
            gr.HTML('<div class="topbar">AI 데일리룩 추천</div>')
            with gr.Column(elem_classes=["tab-content"]):
                weather_info_box = gr.Textbox(
                    label="내일 날씨", interactive=False, elem_classes=["weather-box"]
                )
                chatbot = gr.Chatbot(
                    label="AI 스타일리스트",
                    height=380,
                    type="messages",
                    elem_classes=["chatbot-box"],
                )
                with gr.Row():
                    chat_input = gr.Textbox(
                        label="",
                        placeholder="예: 내일 회사에 입고 갈 옷 골라줘",
                        show_label=False,
                        scale=4,
                    )
                    chat_btn = gr.Button("전송", scale=1, elem_classes=["chat-send-btn"])
                clear_btn = gr.Button("대화 초기화", elem_classes=["btn-secondary"])

    # ── 이벤트 연결 ──────────────────────────────────────────────────

    # 옷장 탭
    upload_btn.click(
        fn=wardrobe.analyze_and_save,
        inputs=[image_input, description_input, size_input, price_input, date_input],
        outputs=[upload_result, wardrobe_df],
    )
    refresh_wardrobe_btn.click(
        fn=dashboard.get_wardrobe_table,
        outputs=wardrobe_df,
    )

    # 코디 탭
    gen_btn.click(
        fn=outfit.generate_outfit_ui,
        inputs=[situation_input, season_input],
        outputs=[outfit_result, outfit_df],
    )

    # 대시보드 탭
    def _refresh_dashboard():
        stats = dashboard.get_stats()
        return stats["total_items"], stats["total_outfits"], stats

    dash_refresh_btn.click(
        fn=_refresh_dashboard,
        outputs=[total_items_num, total_outfits_num, stats_json],
    )

    # 데일리룩 탭
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

    # 앱 로드 시 초기 데이터 일괄 세팅
    def _initial_load():
        weather = daily_look.get_weather_display()
        wardrobe_table = dashboard.get_wardrobe_table()
        outfit_table = dashboard.get_outfit_table()
        stats = dashboard.get_stats()
        return (
            wardrobe_table,
            outfit_table,
            weather,
            stats["total_items"],
            stats["total_outfits"],
            stats,
        )

    demo.load(
        fn=_initial_load,
        outputs=[
            wardrobe_df,
            outfit_df,
            weather_info_box,
            total_items_num,
            total_outfits_num,
            stats_json,
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
