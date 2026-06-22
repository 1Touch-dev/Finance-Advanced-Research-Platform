"""Shared HTTP helpers for U.S. connectors. Sample data only allowed in ENV=test."""
import os
import platform
import time
from typing import Any, Dict, Iterable, Optional, Tuple

import requests

TEST_ENV = os.getenv("ENV", "local") == "test"


def is_test_env() -> bool:
    return TEST_ENV


def http_get(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> requests.Response:
    resp = requests.get(url, headers=headers or {}, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp


def yield_samples(samples: list) -> Iterable[Tuple[str, Dict[str, Any]]]:
    if not is_test_env():
        return
    for it in samples:
        ext = it.get("external_id", str(it))
        yield ext, it
        time.sleep(0.02)


def env_or_creds(creds: Dict[str, Any], key: str, env_var: str) -> Optional[str]:
    val = creds.get(key) or os.getenv(env_var)
    return val if val else None


def ensure_playwright_platform() -> None:
    """
    Playwright may not recognise newer Ubuntu releases (e.g. 26.04) and refuses
    to download Chromium.  Ubuntu 24.04 binaries run fine on 26.04 once system
    deps are installed — override the detected platform when needed.
    """
    if os.getenv("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"):
        return
    release = platform.release()
    if release.startswith("7.") or "26.04" in platform.version():
        os.environ["PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"] = "ubuntu24.04-x64"
