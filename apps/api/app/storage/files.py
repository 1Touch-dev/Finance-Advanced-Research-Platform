import os
import hashlib
from pathlib import Path
from typing import Tuple

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

def store_file(fp, filename: str, sha256: str) -> str:
    target_dir = VAULT_DIR / sha256
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / filename
    if not dest.exists():
        with open(dest, 'wb') as out:
            while True:
                chunk = fp.read(8192)
                if not chunk:
                    break
                out.write(chunk)
        fp.seek(0)
    return str(dest)
