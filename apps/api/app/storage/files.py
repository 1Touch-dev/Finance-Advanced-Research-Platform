import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from app.storage.s3_vault import s3_configured, store_s3

VAULT_DIR = Path(os.getenv("EVIDENCE_VAULT_DIR", "vault"))


def ensure_vault():
    VAULT_DIR.mkdir(parents=True, exist_ok=True)


def compute_sha256(fp) -> Tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    while True:
        chunk = fp.read(8192)
        if not chunk:
            break
        h.update(chunk)
        size += len(chunk)
    fp.seek(0)
    return h.hexdigest(), size


def _immutable_local_path(sha256: str, filename: str, source: str = "evidence") -> Path:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return VAULT_DIR / source / date / sha256 / filename


def store_file(fp, filename: str, sha256: str, source: str = "evidence") -> str:
    if s3_configured():
        content = fp.read()
        fp.seek(0)
        path, _ = store_s3(content, sha256, filename, source=source)
        return path

    dest = _immutable_local_path(sha256, filename, source)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        with open(dest, "wb") as out:
            while True:
                chunk = fp.read(8192)
                if not chunk:
                    break
                out.write(chunk)
        fp.seek(0)
    return str(dest)
