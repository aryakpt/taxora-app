"""Download regulation PDFs from allowed official sources only.

Guards against server-side request forgery: https only, host must be on the allowlist, every redirect
hop is re-checked (redirects are never followed blindly), and the body is capped while streaming.
"""

from pathlib import PurePosixPath

import httpx

from app.core.config import settings

MAX_REDIRECTS = 3


class SourceRejected(ValueError):
    """The URL or the response is not an acceptable regulation source. The message is safe to show admins."""


def check_url(url: str | httpx.URL) -> httpx.URL:
    try:
        parsed = httpx.URL(str(url))
    except (httpx.InvalidURL, TypeError) as exc:
        raise SourceRejected("URL tidak valid") from exc
    host = (parsed.host or "").lower().rstrip(".")
    if parsed.scheme != "https":
        raise SourceRejected("Hanya URL https yang diizinkan")
    if parsed.userinfo or parsed.port not in (None, 443):
        raise SourceRejected("URL tidak boleh memuat kredensial atau port khusus")
    allowed = [h.lower() for h in settings.ingestion_allowed_hosts]
    if not any(host == h or host.endswith("." + h) for h in allowed):
        raise SourceRejected(f"Domain {host or '-'} tidak ada dalam daftar sumber resmi yang diizinkan")
    return parsed


def filename_from(url: httpx.URL) -> str:
    name = PurePosixPath(url.path).name
    return (name or "document.pdf")[:300]


async def fetch_pdf(url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> tuple[bytes, str]:
    current = check_url(url)
    async with httpx.AsyncClient(
        timeout=settings.ingestion_fetch_timeout_seconds, follow_redirects=False, transport=transport
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            async with client.stream("GET", current) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise SourceRejected("Redirect tanpa tujuan")
                    current = check_url(current.join(location))
                    continue
                if response.status_code != 200:
                    raise SourceRejected(f"Sumber mengembalikan HTTP {response.status_code}")
                content = bytearray()
                async for block in response.aiter_bytes():
                    content.extend(block)
                    if len(content) > settings.max_upload_bytes:
                        raise SourceRejected("Dokumen melebihi batas ukuran")
                if not content.startswith(b"%PDF"):
                    raise SourceRejected(
                        "Sumber bukan file PDF. Gunakan tautan unduhan PDF langsung, bukan halaman detail peraturan."
                    )
                return bytes(content), filename_from(current)
    raise SourceRejected("Terlalu banyak redirect")
