"""Private document storage with a local development fallback."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import httpx

from .db import DATA

BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "patient-documents")


def configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def object_key(user_id: str, document_id: str, extension: str) -> str:
    return f"{user_id}/{document_id}{extension}"


def local_path(user_id: str, document_id: str, extension: str) -> Path:
    return DATA / "files" / user_id / (document_id + extension)


def _url(key: str) -> str:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    return f"{base}/storage/v1/object/{quote(BUCKET, safe='')}/{quote(key, safe='/')}"


def _headers(content_type: str | None = None) -> dict[str, str]:
    secret = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    result = {"Authorization": f"Bearer {secret}", "apikey": secret}
    if content_type:
        result["Content-Type"] = content_type
    return result


def put(user_id: str, document_id: str, extension: str, content: bytes, content_type: str) -> None:
    if not configured():
        path = local_path(user_id, document_id, extension)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return
    with httpx.Client(timeout=httpx.Timeout(60, connect=10), follow_redirects=False) as client:
        response = client.post(
            _url(object_key(user_id, document_id, extension)),
            headers={**_headers(content_type), "x-upsert": "false"},
            content=content,
        )
        if response.status_code not in {200, 201}:
            raise RuntimeError("原件存储暂不可用，请稍后重试。")


def get(user_id: str, document_id: str, extension: str) -> bytes:
    if not configured():
        path = local_path(user_id, document_id, extension)
        if not path.exists():
            raise FileNotFoundError
        return path.read_bytes()
    with httpx.Client(timeout=httpx.Timeout(60, connect=10), follow_redirects=False) as client:
        response = client.get(
            _url(object_key(user_id, document_id, extension)), headers=_headers()
        )
        if response.status_code == 404:
            raise FileNotFoundError
        if response.status_code != 200:
            raise RuntimeError("原件存储暂不可用，请稍后重试。")
        return response.content


def remove(user_id: str, document_id: str, extension: str) -> None:
    if not configured():
        local_path(user_id, document_id, extension).unlink(missing_ok=True)
        return
    with httpx.Client(timeout=httpx.Timeout(30, connect=10), follow_redirects=False) as client:
        response = client.delete(
            _url(object_key(user_id, document_id, extension)), headers=_headers()
        )
        if response.status_code not in {200, 204, 404}:
            raise RuntimeError("原件删除暂未完成，请稍后重试。")
