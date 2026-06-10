"""
AI Closet — 스마트 AI 옷장 관리 서비스
========================================
탭 구성:
  1) 옷장  : 의류 사진 업로드 → BLIP 캡셔닝 → LLM 정보 추출 → Supabase 저장
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
# Label/JSON 컴포넌트가 생성하는 additionalProperties: true 스키마에서 발생.
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
.gradio-container { max-width: 1100px; margin: 0 auto; }
.tab-nav button {
    color: #5A6A8A; font-size: 13px; border-bottom: 2px solid transparent;
}
.tab-nav button.selected {
    color: #1B3A6B; border-bottom-color: #2A52A0; font-weight: 500;
}
.upload-btn {
    background: #1B3A6B !important; color: white !important; border: none !important;
}
.generate-btn {
    background: #2A52A0 !important; color: white !important;
}
"""

# Gradio 5에서 추가된 ssr_mode 파라미터 버전 분기
_gr_major = int(gr.__version__.split(".")[0])

with gr.Blocks(css=CUSTOM_CSS, title="AI Closet") as demo:
    gr.Markdown("# 👗 AI Closet\n스마트 AI 옷장 관리 서비스")

    with gr.Tabs():
        # ── 탭 1: 옷장 ──────────────────────────────────────────────────────
        with gr.Tab("👔 옷장"):
            with gr.Row():
                image_input = gr.Image(type="filepath", label="의류 사진 업로드")
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
                        "AI 분류 및 추가", elem_classes=["upload-btn"]
                    )

            upload_result = gr.Textbox(label="분류 결과", interactive=False)

            gr.Markdown("### 내 옷장")
            wardrobe_df = gr.Dataframe(
                headers=["이름", "카테고리", "색상", "사진", "계절", "사이즈", "등록일"],
                label="의류 목록",
            )
            refresh_wardrobe_btn = gr.Button("목록 새로고침")

        # ── 탭 2: 코디 ──────────────────────────────────────────────────────
        with gr.Tab("👗 코디"):
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
                    "AI 코디 생성", elem_classes=["generate-btn"]
                )

            outfit_result = gr.Textbox(label="생성된 코디", interactive=False)
            outfit_df = gr.Dataframe(
                headers=["코디명", "상황", "계절", "태그", "AI생성", "생성일"],
                label="코디 목록",
            )

        # ── 탭 3: 대시보드 ──────────────────────────────────────────────────
        with gr.Tab("📊 대시보드"):
            with gr.Row():
                total_items_num = gr.Number(label="총 의류 수", interactive=False)
                total_outfits_num = gr.Number(label="저장된 코디", interactive=False)

            stats_json = gr.JSON(label="카테고리별 통계")
            dash_refresh_btn = gr.Button("통계 새로고침")

        # ── 탭 4: 데일리룩 ──────────────────────────────────────────────────
        with gr.Tab("✨ 데일리룩 추천"):
            weather_info_box = gr.Textbox(label="내일 날씨", interactive=False)
            chatbot = gr.Chatbot(
                label="AI 스타일리스트",
                height=350,
                type="messages",  # Gradio 4.44+ / 5.x 공통
            )
            with gr.Row():
                chat_input = gr.Textbox(
                    label="메시지",
                    placeholder="예: 내일 회사에 입고 갈 옷 골라줘",
                    scale=4,
                )
                chat_btn = gr.Button("전송", scale=1)
            clear_btn = gr.Button("대화 초기화")

    # ── 이벤트 연결 ──────────────────────────────────────────────────────────

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

    # 데일리룩 탭 — 채팅 전송 (버튼 클릭 + Enter 키 모두 지원)
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

    # 앱 로드 시 초기 데이터 일괄 세팅 (날씨 + 테이블 + 통계)
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
