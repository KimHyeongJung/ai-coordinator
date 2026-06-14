"""
AI Closet — 스마트 AI 옷장 관리 서비스
HTML 사이드바 + JS 탭 전환 방식 (HF Spaces 호환)
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

# ── CSS ──────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
:root {
    --navy:       #1B3A6B;
    --navy-light: #2A52A0;
    --navy-pale:  #EEF2FA;
    --navy-mid:   #4A6FA5;
    --white:      #FFFFFF;
    --surface:    #E8EDF5;
    --border:     #D8E2F0;
    --text:       #1A2540;
    --text-muted: #5A6A8A;
    --text-hint:  #9BAAC4;
}

/* ── Global ── */
html, body { background: var(--surface) !important; }
.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
    background: var(--surface) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}
footer { display: none !important; }

/* ── Main row: 전체 화면 수평 배치 ── */
#main-row {
    gap: 0 !important;
    min-height: 100vh !important;
    align-items: stretch !important;
    flex-wrap: nowrap !important;
}

/* ── Sidebar col: 네이비, 패딩 제거 ── */
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
    min-height: 100vh !important;
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
    min-height: 100vh !important;
}

/* ── 상단 탭 네비 완전히 숨기기 ── */
.tab-nav {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
}
.tabitem {
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
}
#content-tabs,
#content-tabs > div {
    background: transparent !important;
    border: none !important;
    gap: 0 !important;
}

/* ── Topbar ── */
.topbar {
    background: var(--white) !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 14px 24px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
}
.topbar-title {
    font-size: 15px;
    font-weight: 500;
    color: var(--text);
}

/* ── Tab 내용 영역 ── */
.tab-content {
    padding: 20px 24px 28px !important;
    gap: 14px !important;
    background: var(--surface) !important;
    border: none !important;
}

/* ── 섹션 헤더 ── */
.section-header {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--text) !important;
    padding-bottom: 10px !important;
    border-bottom: 1px solid var(--border) !important;
    margin-bottom: 2px !important;
}

/* ── 버튼 ── */
.btn-primary button {
    background: var(--navy) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: background 0.15s !important;
}
.btn-primary button:hover { background: var(--navy-light) !important; }

.btn-secondary button {
    background: var(--white) !important;
    color: var(--text-muted) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}
.btn-secondary button:hover {
    border-color: var(--navy-mid) !important;
    color: var(--navy) !important;
}

/* ── 폼 라벨 ── */
.block label > span:first-child,
.block .label-wrap span {
    font-size: 12px !important;
    color: var(--text-muted) !important;
    font-weight: 500 !important;
}

/* ── 입력 필드 ── */
.block input[type="text"],
.block input[type="number"],
.block textarea,
.block select {
    border-color: var(--border) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    background: var(--navy-pale) !important;
    color: var(--text) !important;
}
.block input:focus, .block textarea:focus {
    border-color: var(--navy-light) !important;
    box-shadow: 0 0 0 2px rgba(42,82,160,0.1) !important;
    background: var(--white) !important;
}

/* ── 이미지 업로드: 흰 바탕 + 네이비 점선 테두리 ── */
.image-box .wrap,
.image-box .upload-container,
.image-box > div > div {
    border: 2px dashed #1B3A6B !important;
    border-radius: 12px !important;
    background: #ffffff !important;
}
.image-box,
.image-box .block,
.image-box > div {
    background: #ffffff !important;
    border: none !important;
    box-shadow: none !important;
}
/* 아이콘 색상 */
.image-box svg { color: #4A6FA5 !important; }
.image-box svg path, .image-box svg polyline, .image-box svg line {
    stroke: #4A6FA5 !important;
}
/* 기본 업로드 안내 텍스트 숨기기 (JS로 교체) */
.image-box .file-name,
.image-box .or-text {
    display: none !important;
}

/* ── 결과 텍스트 ── */
.result-box textarea {
    background: var(--navy-pale) !important;
    border-color: var(--border) !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    line-height: 1.65 !important;
    color: var(--text) !important;
}

/* ── 통계 박스 ── */
.stat-box {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}
.stat-box input[type="number"] {
    font-size: 30px !important;
    font-weight: 600 !important;
    color: var(--navy) !important;
    border: none !important;
    background: transparent !important;
}

/* ── 날씨 박스 ── */
.weather-box textarea {
    background: var(--navy) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    font-size: 13px !important;
    line-height: 1.65 !important;
}
.weather-box label > span:first-child { color: var(--text-muted) !important; }

/* ── 챗봇 ── */
.chatbot-box .wrap,
.chatbot-box > div {
    border-radius: 12px !important;
    border: 1px solid var(--border) !important;
    background: var(--white) !important;
}

/* ── 데이터프레임 ── */
.table-box table thead tr { background: var(--navy-pale) !important; }
.table-box table thead th {
    color: var(--navy) !important;
    font-weight: 500 !important;
    font-size: 12px !important;
    border-bottom: 1px solid var(--border) !important;
}
.table-box table td {
    font-size: 12.5px !important;
    color: var(--text) !important;
    border-bottom: 1px solid var(--border) !important;
}
.table-box table tbody tr:hover td { background: var(--navy-pale) !important; }

/* ── JSON 통계 ── */
.stats-json {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}
"""

# ── 사이드바 HTML ─────────────────────────────────────────────────────────────
SIDEBAR_HTML = """
<div id="aic-sidebar" style="
    background:#1B3A6B;min-height:100vh;
    display:flex;flex-direction:column;width:100%;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
">
  <!-- 로고 -->
  <div style="padding:20px 18px 16px;border-bottom:1px solid rgba(255,255,255,.1)">
    <div style="display:flex;align-items:center;gap:10px">
      <div style="width:34px;height:34px;background:rgba(255,255,255,.15);
                  border-radius:8px;display:flex;align-items:center;
                  justify-content:center;font-size:18px;flex-shrink:0">🧥</div>
      <div>
        <div style="color:#fff;font-size:14px;font-weight:500;line-height:1.2">AI Closet</div>
        <div style="color:rgba(255,255,255,.5);font-size:10px;margin-top:1px">스마트 옷장 관리</div>
      </div>
    </div>
  </div>

  <!-- 메뉴 -->
  <div style="padding:12px 10px;flex:1">
    <div class="sb-item active" id="sb-0" onclick="sbGo(0)">🧥 옷장</div>
    <div class="sb-item" id="sb-1" onclick="sbGo(1)">👗 코디</div>
    <div class="sb-item" id="sb-2" onclick="sbGo(2)">📊 대시보드</div>
    <div class="sb-item" id="sb-3" onclick="sbGo(3)">✨ 데일리룩</div>
  </div>

  <!-- 하단 -->
  <div style="padding:12px 10px;border-top:1px solid rgba(255,255,255,.1)">
    <div class="sb-item" style="color:rgba(255,255,255,.35);cursor:default">⚙️ 설정</div>
  </div>
</div>

<style>
.sb-item{
    display:flex;align-items:center;gap:8px;
    padding:9px 10px;border-radius:8px;cursor:pointer;
    color:rgba(255,255,255,.55);font-size:12.5px;
    transition:all .15s;margin-bottom:2px;user-select:none;
}
.sb-item:hover{background:rgba(255,255,255,.08);color:rgba(255,255,255,.85)}
.sb-item.active{background:rgba(255,255,255,.15);color:#fff;font-weight:500}
</style>

<script>
function sbGo(idx){
    // 사이드바 active 상태 업데이트
    [0,1,2,3].forEach(function(i){
        var el=document.getElementById('sb-'+i);
        if(el) el.classList.toggle('active', i===idx);
    });
    // Gradio 탭 버튼 클릭 (숨겨져 있어도 JS .click()은 동작함)
    setTimeout(function(){
        var btns = document.querySelectorAll('.tab-nav button, [role="tab"]');
        if(btns[idx]) btns[idx].click();
    }, 10);
}
// 탭 nav 숨기기
function hideTabNav(){
    document.querySelectorAll('.tab-nav').forEach(function(el){
        el.style.cssText='display:none!important;height:0!important;overflow:hidden!important';
    });
}
document.addEventListener('DOMContentLoaded', hideTabNav);
setTimeout(hideTabNav, 500);
setTimeout(hideTabNav, 1500);

// 업로드 안내 문구 교체
function patchUploadText(){
    var box = document.querySelector('.image-box');
    if(!box) return false;
    var els = Array.from(box.getElementsByTagName('*'));
    for(var i=0;i<els.length;i++){
        var el=els[i];
        var t=(el.innerText||'').trim();
        // 기본 Gradio 업로드 안내 문구를 포함한 컨테이너 탐색
        if((t.includes('드롭')||t.includes('클릭')||t.includes('Drop')||t.includes('Click')||t.includes('Upload'))
            && el.children.length<=5 && !el.querySelector('input')){
            el.innerHTML=
                '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#4A6FA5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:10px"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>'+
                '<strong style="display:block;font-size:14px;font-weight:700;color:#1A2540;margin-bottom:6px">의류 사진을 드래그해주세요</strong>'+
                '<span style="display:block;font-size:12px;color:#5A6A8A">AI가 카테고리, 색상, 재질을 자동 분류합니다</span>';
            return true;
        }
    }
    return false;
}
if(!patchUploadText()){
    [300,700,1500].forEach(function(t){ setTimeout(patchUploadText,t); });
}
</script>
"""

_gr_major = int(gr.__version__.split(".")[0])

# ── Blocks 레이아웃 ───────────────────────────────────────────────────────────
with gr.Blocks(css=CUSTOM_CSS, title="AI Closet", theme=gr.themes.Base()) as demo:

    with gr.Row(elem_id="main-row"):

        # ── 왼쪽: 사이드바 ────────────────────────────────────────────────────
        with gr.Column(scale=0, min_width=210, elem_id="sidebar-col"):
            gr.HTML(SIDEBAR_HTML)

        # ── 오른쪽: 컨텐츠 ───────────────────────────────────────────────────
        with gr.Column(scale=1, elem_id="content-col"):
            with gr.Tabs(elem_id="content-tabs"):

                # ── 탭 1: 옷장 ────────────────────────────────────────────
                with gr.Tab("옷장"):
                    gr.HTML('<div class="topbar"><span class="topbar-title">내 옷장</span></div>')
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

                # ── 탭 2: 코디 ────────────────────────────────────────────
                with gr.Tab("코디"):
                    gr.HTML('<div class="topbar"><span class="topbar-title">코디 목록</span></div>')
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
                        )
                        gr.HTML('<div class="section-header">저장된 코디 목록</div>')
                        outfit_df = gr.Dataframe(
                            headers=["코디명", "상황", "계절", "태그", "AI생성", "생성일"],
                            label=None,
                            elem_classes=["table-box"],
                        )

                # ── 탭 3: 대시보드 ────────────────────────────────────────
                with gr.Tab("대시보드"):
                    gr.HTML('<div class="topbar"><span class="topbar-title">옷장 대시보드</span></div>')
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
                        stats_json = gr.JSON(
                            label="카테고리별 통계", elem_classes=["stats-json"]
                        )
                        dash_refresh_btn = gr.Button(
                            "통계 새로고침", elem_classes=["btn-secondary"]
                        )

                # ── 탭 4: 데일리룩 ────────────────────────────────────────
                with gr.Tab("데일리룩"):
                    gr.HTML('<div class="topbar"><span class="topbar-title">AI 데일리룩 추천</span></div>')
                    with gr.Column(elem_classes=["tab-content"]):
                        weather_info_box = gr.Textbox(
                            label="내일 날씨", interactive=False,
                            elem_classes=["weather-box"],
                        )
                        chatbot = gr.Chatbot(
                            label="AI 스타일리스트",
                            height=380,
                            type="messages",
                            elem_classes=["chatbot-box"],
                        )
                        with gr.Row():
                            chat_input = gr.Textbox(
                                label="", show_label=False,
                                placeholder="예: 내일 회사에 입고 갈 옷 골라줘",
                                scale=4,
                            )
                            chat_btn = gr.Button(
                                "전송", scale=1, elem_classes=["btn-primary"]
                            )
                        clear_btn = gr.Button(
                            "대화 초기화", elem_classes=["btn-secondary"]
                        )

    # ── 이벤트 연결 (기존 그대로) ──────────────────────────────────────────────

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
        return stats["total_items"], stats["total_outfits"], stats

    dash_refresh_btn.click(
        fn=_refresh_dashboard,
        outputs=[total_items_num, total_outfits_num, stats_json],
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
