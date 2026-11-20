"""Original documents, stored by content hash (PRD §8.1 step 2).

Local disk for now. The key is the SHA-256 hex digest, so identical files are stored once and the key
doubles as the document hash. Swap this module for S3-compatible storage in production.
"""

import hashlib
import os
import re
from pathlib import Path

from app.core.config import settings

_KEY = re.compile(r"^[0-9a-f]{64}$")


def _path(key: str) -> Path:
    if not _KEY.match(key):
        raise ValueError("invalid storage key")
    return Path(settings.document_storage_dir) / key[:2] / f"{key}.pdf"


def save(content: bytes) -> str:
    key = hashlib.sha256(content).hexdigest()
    path = _path(key)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(content)
        os.replace(temporary, path)
    return key


def load(key: str) -> bytes:
    return _path(key).read_bytes()
