"""Production pieces that local development does not exercise: Supabase Storage, the client IP behind proxies,
and the production settings check."""

import json

import httpx
import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.core import rate_limit
from app.core.config import Settings, settings
from app.modules.ingestion import storage

KEY = "ab" + "0" * 62


def supabase(handler, secret="sb_secret_abc"):
    calls = []

    def record(request: httpx.Request):
        calls.append(request)
        return handler(request)

    backend = storage.SupabaseStorage("https://proj.supabase.co/", secret, "documents",
                                      transport=httpx.MockTransport(record))
    return backend, calls


async def test_supabase_storage_puts_gets_and_removes_by_hash():
    stored = {}

    def handler(request: httpx.Request):
        path = request.url.path
        if request.method == "POST":
            stored[path.split("/documents/", 1)[1]] = request.content
            return httpx.Response(200, json={"Key": path})
        if request.method == "GET":
            name = path.split("/documents/", 1)[1]
            return httpx.Response(200, content=stored[name]) if name in stored else \
                httpx.Response(400, json={"error": "not_found", "message": "Object not found"})
        if request.method == "DELETE":
            for name in json.loads(request.content)["prefixes"]:
                stored.pop(name, None)
            return httpx.Response(200, json=[])
        return httpx.Response(405)

    backend, calls = supabase(handler)

    await backend.put(KEY, b"%PDF-1.4 x")
    assert await backend.get(KEY) == b"%PDF-1.4 x"
    await backend.remove(KEY)
    with pytest.raises(storage.DocumentNotFound):
        await backend.get(KEY)

    upload = calls[0]
    assert upload.url.path == f"/storage/v1/object/documents/ab/{KEY}.pdf"
    assert upload.headers["apikey"] == "sb_secret_abc" and "authorization" not in upload.headers
    assert upload.headers["content-type"] == "application/pdf"


async def test_legacy_service_role_keys_are_also_sent_as_a_bearer_token():
    backend, calls = supabase(lambda request: httpx.Response(200, json={}), secret="eyJhbGciOi.payload.sig")

    await backend.put(KEY, b"%PDF")

    assert calls[0].headers["authorization"] == "Bearer eyJhbGciOi.payload.sig"


async def test_storage_failures_become_storage_errors():
    backend, _ = supabase(lambda request: httpx.Response(500, json={"message": "boom"}))
    with pytest.raises(storage.StorageError):
        await backend.put(KEY, b"%PDF")

    def offline(request):
        raise httpx.ConnectError("down")

    backend, _ = supabase(offline)
    with pytest.raises(storage.StorageError):
        await backend.get(KEY)


def request_from(peer: str, forwarded: str | None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


@pytest.mark.parametrize("hops, forwarded, expected", [
    (0, "1.1.1.1", "10.0.0.9"),                     # local: headers are ignored
    (1, "203.0.113.7", "203.0.113.7"),             # one proxy
    (2, "203.0.113.7, 76.76.21.1", "203.0.113.7"),  # rewrite proxy + load balancer
    (2, "6.6.6.6, 203.0.113.7, 76.76.21.1", "203.0.113.7"),  # a forged entry on the left is skipped
    (2, None, "10.0.0.9"),                          # no header: the peer
])
def test_client_ip_counts_trusted_proxies_from_the_right(monkeypatch, hops, forwarded, expected):
    monkeypatch.setattr(settings, "trusted_proxy_hops", hops)

    assert rate_limit.client_ip(request_from("10.0.0.9", forwarded)) == expected


def test_production_refuses_unsafe_settings():
    with pytest.raises(ValidationError, match="AUTH_COOKIE_SECURE.*development password.*SUPABASE"):
        Settings(app_env="production", auth_secret_key="x" * 40, auth_cookie_secure=False, _env_file=None,
                 database_url="postgresql+asyncpg://taxora:taxora@localhost:5432/taxora")

    Settings(app_env="production", auth_secret_key="x" * 40, auth_cookie_secure=True, _env_file=None,
             database_url="postgresql+asyncpg://postgres.ref:s3cret@pooler.supabase.com:5432/postgres",
             supabase_url="https://ref.supabase.co", supabase_secret_key="sb_secret_x")
