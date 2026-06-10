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


def get_wardrobe_table() -> list[list]:
    """옷장 아이템을 gr.Dataframe 출력용 2D 리스트로 변환.
    컬럼: 이름 / 카테고리 / 색상 / 사진 / 계절 / 사이즈 / 등록일
    """
    items = storage.load_wardrobe().get("items", [])
    rows = []
    for item in items:
        season = ", ".join(item.get("season") or [])
        date = (item.get("created_at") or "")[:10]
        rows.append(
            [
                item.get("name", ""),
                item.get("category", ""),
                item.get("color", ""),
                "없음",  # image_path: 데모에서는 파일 경로 미저장
                season,
                item.get("size") or "",
                date,
            ]
        )
    return rows


def get_outfit_table() -> list[list]:
    """코디 목록을 gr.Dataframe 출력용 2D 리스트로 변환.
    컬럼: 코디명 / 상황 / 계절 / 태그 / AI생성 / 생성일
    """
    outfits = storage.load_outfits().get("outfits", [])
    rows = []
    for outfit in outfits:
        tags = ", ".join(outfit.get("tags") or [])
        date = (outfit.get("created_at") or "")[:10]
        rows.append(
            [
                outfit.get("name", ""),
                outfit.get("situation", ""),
                outfit.get("season", ""),
                tags,
                "✓" if outfit.get("ai_generated") else "✗",
                date,
            ]
        )
    return rows
