"""Original documents, stored by content hash (PRD §8.1 step 2).

The key is the SHA-256 hex digest, so identical files are stored once and the key doubles as the document hash.
Two backends:

- local disk (development): `DOCUMENT_STORAGE_DIR`;
- Supabase Storage (production, where the server's disk is wiped on every restart): used when `SUPABASE_URL`
  and `SUPABASE_SECRET_KEY` are set; files go to the private bucket `SUPABASE_STORAGE_BUCKET`.
"""

import hashlib
import os
import re
from pathlib import Path
from typing import Protocol

import httpx

from app.core.config import settings

_KEY = re.compile(r"^[0-9a-f]{64}$")


class DocumentNotFound(FileNotFoundError):
    pass


class StorageError(Exception):
    """The storage service failed. The message is safe to show admins."""


def _object_name(key: str) -> str:
    if not _KEY.match(key):
        raise ValueError("invalid storage key")
    return f"{key[:2]}/{key}.pdf"


class Backend(Protocol):
    async def put(self, key: str, content: bytes) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def remove(self, key: str) -> None: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / _object_name(key)

    async def put(self, key: str, content: bytes) -> None:
        path = self._path(key)
        if path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(content)
        os.replace(temporary, path)

    async def get(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError as exc:
            raise DocumentNotFound(key) from exc

    async def remove(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class SupabaseStorage:
    """Supabase Storage over its REST API, with the project's secret key (server side only)."""

    def __init__(self, url: str, secret_key: str, bucket: str, *, transport: httpx.AsyncBaseTransport | None = None):
        self.base = f"{url.rstrip('/')}/storage/v1"
        self.bucket = bucket
        headers = {"apikey": secret_key}
        if secret_key.startswith("eyJ"):  # legacy service_role JWT; the newer sb_secret_ keys go in apikey only
            headers["Authorization"] = f"Bearer {secret_key}"
        self._client_options = {"headers": headers, "timeout": 60, "transport": transport}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(**self._client_options)

    async def _send(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            async with self._client() as client:
                return await client.request(method, f"{self.base}{path}", **kwargs)
        except httpx.HTTPError as exc:
            raise StorageError(f"Penyimpanan dokumen tidak dapat dihubungi ({type(exc).__name__}).") from exc

    async def put(self, key: str, content: bytes) -> None:
        response = await self._send("POST", f"/object/{self.bucket}/{_object_name(key)}", content=content,
                                    headers={"Content-Type": "application/pdf", "x-upsert": "true"})
        if response.status_code not in (200, 201):
            raise StorageError(f"Dokumen tidak dapat disimpan ({response.status_code}).")

    async def get(self, key: str) -> bytes:
        response = await self._send("GET", f"/object/authenticated/{self.bucket}/{_object_name(key)}")
        if response.status_code == 200:
            return response.content
        if response.status_code in (400, 404):  # Supabase answers 400 "Object not found" for a missing file
            raise DocumentNotFound(key)
        raise StorageError(f"Dokumen tidak dapat dibaca ({response.status_code}).")

    async def remove(self, key: str) -> None:
        response = await self._send("DELETE", f"/object/{self.bucket}", json={"prefixes": [_object_name(key)]})
        if response.status_code not in (200, 404):
            raise StorageError(f"Dokumen tidak dapat dihapus ({response.status_code}).")


def configured() -> Backend:
    if settings.supabase_url and settings.supabase_secret_key:
        return SupabaseStorage(settings.supabase_url, settings.supabase_secret_key, settings.supabase_storage_bucket)
    return LocalStorage(settings.document_storage_dir)


def key_for(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def save(content: bytes) -> str:
    key = key_for(content)
    await configured().put(key, content)
    return key


async def load(key: str) -> bytes:
    return await configured().get(key)


async def delete(key: str) -> None:
    """Remove a stored original. Callers check first that no job or version still refers to it."""
    await configured().remove(key)
