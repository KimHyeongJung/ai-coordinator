"""
대시보드 데이터 집계: storage에서 데이터를 읽어 Gradio 컴포넌트용으로 가공.
"""

from __future__ import annotations

from collections import Counter

import storage


def get_stats() -> dict:
    """옷장/코디 통계 집계."""
    items = storage.load_wardrobe().get("items", [])
    outfit_list = storage.load_outfits().get("outfits", [])

    by_category = dict(Counter(item.get("category", "기타") for item in items))

    by_season: Counter = Counter()
    for item in items:
        for season in item.get("season") or []:
            by_season[season] += 1

    by_situation = dict(Counter(o.get("situation", "기타") for o in outfit_list))

    return {
        "total_items": len(items),
        "total_outfits": len(outfit_list),
        "by_category": by_category,
        "by_season": dict(by_season),
        "by_situation": by_situation,
    }


def get_wardrobe_table(items=None) -> list[list]:
    """옷장 아이템을 gr.Dataframe 출력용 2D 리스트로 변환.
    컬럼: 이름 / 카테고리 / 색상 / 스타일 / 계절 / 가격 / 구매시기 / 세탁방법
    """
    if items is None:
        items = storage.load_wardrobe().get("items", [])
    rows = []
    for item in items:
        season = ", ".join(item.get("season") or [])
        rows.append(
            [
                item.get("name", ""),
                item.get("category", ""),
                item.get("color", ""),
                item.get("style", ""),
                season,
                item.get("price") or "",
                item.get("purchase_date") or "",
                item.get("wash_instruction", ""),
            ]
        )
    return rows


def get_outfit_table(outfits=None, wardrobe_items=None) -> list[list]:
    """코디 목록을 gr.Dataframe 출력용 2D 리스트로 변환.
    컬럼: 코디명 / 상황 / 계절 / 태그 / 착용 의류 / AI생성 / 생성일
    """
    if outfits is None:
        outfits = storage.load_outfits().get("outfits", [])
    if wardrobe_items is None:
        wardrobe_items = storage.load_wardrobe().get("items", [])
    wardrobe_map = {
        item["id"]: item.get("name", item.get("id", ""))
        for item in wardrobe_items
    }
    rows = []
    for outfit in outfits:
        tags = ", ".join(outfit.get("tags") or [])
        date = (outfit.get("created_at") or "")[:10]
        item_names = ", ".join(
            wardrobe_map.get(iid, iid) for iid in (outfit.get("item_ids") or [])
        )
        rows.append(
            [
                outfit.get("name", ""),
                outfit.get("situation", ""),
                outfit.get("season", ""),
                tags,
                item_names,
                "✓" if outfit.get("ai_generated") else "✗",
                date,
            ]
        )
    return rows


def build_stats_cards(stats: dict) -> str:
    """카테고리별 통계를 플랫 카드 HTML로 변환."""
    by_category = stats.get("by_category", {})
    by_season = stats.get("by_season", {})
    by_situation = stats.get("by_situation", {})

    def section(title: str, icon: str, data: dict) -> str:
        if not data:
            return (
                f'<div class="sc-section">'
                f'<div class="sc-title">{icon} {title}</div>'
                f'<p style="font-size:12px;color:#9BAAC4;margin:0">데이터 없음</p>'
                f'</div>'
            )
        cards = "".join(
            f'<div class="sc-card">'
            f'<span class="sc-label">{k}</span>'
            f'<span class="sc-val">{v}</span>'
            f'</div>'
            for k, v in sorted(data.items(), key=lambda x: -x[1])
        )
        return (
            f'<div class="sc-section">'
            f'<div class="sc-title">{icon} {title}</div>'
            f'<div class="sc-grid">{cards}</div>'
            f'</div>'
        )

    html = (
        section("카테고리별", "👔", by_category)
        + section("계절별", "🌸", by_season)
        + section("상황별", "💼", by_situation)
    )
    return f'<div class="sc-wrap">{html}</div>'
