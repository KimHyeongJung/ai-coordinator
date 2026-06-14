"""
Supabase 기반 영구 데이터 저장소.

HuggingFace Space는 컨테이너 재시작 시 로컬 파일이 초기화되므로
옷장 아이템과 코디 데이터를 외부 DB(Supabase)에 저장한다.

사전 준비 (개발자가 직접 수행):
  1. https://supabase.com 에서 무료 프로젝트 생성
  2. SQL Editor에서 wardrobe_items / outfits 테이블 생성 (README 참고)
  3. .env 및 HF Space Secrets에 SUPABASE_URL / SUPABASE_KEY 등록
"""

from __future__ import annotations

import logging
import mimetypes
import os

from supabase import Client, create_client

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client:
    """Supabase 클라이언트 lazy initialization."""
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_KEY 환경변수가 필요합니다.\n"
                "  .env 파일 또는 HF Space Secrets에 등록해 주세요."
            )
        _client = create_client(url, key)
    return _client


def load_wardrobe() -> dict:
    """옷장 아이템 전체 로드. 실패 시 빈 목록 반환."""
    try:
        res = (
            get_client()
            .table("wardrobe_items")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return {"items": res.data}
    except Exception as e:
        logger.error("load_wardrobe 실패: %s", e)
        return {"items": []}


def load_outfits() -> dict:
    """코디 목록 전체 로드. 실패 시 빈 목록 반환."""
    try:
        res = (
            get_client()
            .table("outfits")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return {"outfits": res.data}
    except Exception as e:
        logger.error("load_outfits 실패: %s", e)
        return {"outfits": []}


def add_item(item_dict: dict) -> dict:
    """
    옷장 아이템을 DB에 삽입하고 생성된 행을 반환한다.
    id / created_at은 DB 기본값을 사용하므로 입력 dict에서 제외한다.
    실패 시 입력 dict를 그대로 반환 (id 필드 없음).
    """
    try:
        data = {k: v for k, v in item_dict.items() if k not in ("id", "created_at")}
        res = get_client().table("wardrobe_items").insert(data).execute()
        return res.data[0] if res.data else item_dict
    except Exception as e:
        logger.error("add_item 실패: %s", e)
        return item_dict


def upload_image(src_path: str, filename: str) -> str | None:
    """
    이미지를 Supabase Storage 'wardrobe-images' 버킷에 업로드하고 공개 URL을 반환한다.
    버킷이 없거나 업로드 실패 시 None 반환.
    사전 준비: Supabase 대시보드 → Storage → 'wardrobe-images' 버킷 생성 (Public)
    """
    try:
        mime_type = mimetypes.guess_type(src_path)[0] or "image/jpeg"
        with open(src_path, "rb") as f:
            data = f.read()
        client = get_client()
        client.storage.from_("wardrobe-images").upload(
            path=filename,
            file=data,
            file_options={"content-type": mime_type, "upsert": "true"},
        )
        url = client.storage.from_("wardrobe-images").get_public_url(filename)
        return url
    except Exception as e:
        logger.error("upload_image 실패: %s", e)
        return None


def delete_item(item_id: str) -> None:
    """특정 아이템을 DB에서 삭제한다."""
    try:
        get_client().table("wardrobe_items").delete().eq("id", item_id).execute()
    except Exception as e:
        logger.error("delete_item 실패: %s", e)


def update_item(item_id: str, update_dict: dict) -> dict:
    """의류 아이템을 DB에서 업데이트하고 결과 행을 반환한다."""
    try:
        data = {k: v for k, v in update_dict.items() if k not in ("id", "created_at")}
        res = get_client().table("wardrobe_items").update(data).eq("id", item_id).execute()
        return res.data[0] if res.data else update_dict
    except Exception as e:
        logger.error("update_item 실패: %s", e)
        return update_dict


def delete_outfit(outfit_id: str) -> None:
    """특정 코디를 DB에서 삭제한다."""
    try:
        get_client().table("outfits").delete().eq("id", outfit_id).execute()
    except Exception as e:
        logger.error("delete_outfit 실패: %s", e)


def update_outfit(outfit_id: str, update_dict: dict) -> dict:
    """코디를 DB에서 업데이트하고 결과 행을 반환한다."""
    try:
        data = {k: v for k, v in update_dict.items() if k not in ("id", "created_at")}
        res = get_client().table("outfits").update(data).eq("id", outfit_id).execute()
        return res.data[0] if res.data else update_dict
    except Exception as e:
        logger.error("update_outfit 실패: %s", e)
        return update_dict


def add_outfit(outfit_dict: dict) -> dict:
    """
    코디를 DB에 삽입하고 생성된 행을 반환한다.
    id / created_at은 DB 기본값을 사용하므로 입력 dict에서 제외한다.
    실패 시 입력 dict를 그대로 반환.
    """
    try:
        data = {k: v for k, v in outfit_dict.items() if k not in ("id", "created_at")}
        res = get_client().table("outfits").insert(data).execute()
        return res.data[0] if res.data else outfit_dict
    except Exception as e:
        logger.error("add_outfit 실패: %s", e)
        return outfit_dict
