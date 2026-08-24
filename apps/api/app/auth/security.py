import datetime as dt
import hashlib
import secrets
from typing import Optional

import jwt
import bcrypt as _bcrypt_native
from fastapi import Depends, HTTPException, Request, status

from app.core.settings import settings

_revoked_tokens: set = set()
_refresh_tokens: dict = {}


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

def hash_password(p: str) -> str:
    """Hash a password using native bcrypt (avoids passlib version conflicts)."""
    return _bcrypt_native.hashpw(p.encode(), _bcrypt_native.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    """Verify a password against a bcrypt hash (native bcrypt, bypasses passlib)."""
    try:
        return _bcrypt_native.checkpw(p.encode(), h.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Token creation / validation
# ---------------------------------------------------------------------------

def create_access_token(user_id: int, email: str) -> str:
    """Create a JWT access token with 24-hour expiry."""
    now = dt.datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + dt.timedelta(hours=24),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_token(user_id: int, email: str, hours: int = 8) -> str:
    """Legacy helper — kept for backward compat."""
    now = dt.datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + dt.timedelta(hours=hours),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> dict:
    """Decode and validate a JWT. Returns payload dict or raises."""
    if is_revoked(token):
        raise jwt.InvalidTokenError("token revoked")
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "iss", "sub"]},
    )


def decode_token(token: str) -> dict:
    """Alias for verify_token (backward compat)."""
    return verify_token(token)


# ---------------------------------------------------------------------------
# Refresh tokens (in-memory, for dev/testing)
# ---------------------------------------------------------------------------

def create_refresh_token(user_id: int, email: str) -> str:
    token = secrets.token_urlsafe(48)
    _refresh_tokens[token] = {"user_id": user_id, "email": email, "created": dt.datetime.utcnow().isoformat()}
    return token


def exchange_refresh_token(refresh_token: str) -> dict | None:
    data = _refresh_tokens.get(refresh_token)
    if not data:
        return None
    return {
        "token": create_access_token(data["user_id"], data["email"]),
        "refresh_token": refresh_token,
    }


def revoke_token(token: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    _revoked_tokens.add(token_hash)
    try:
        from app.core.cache import cache_set
        cache_set(f"revoked:{token_hash}", "1", ttl=86400 * 7)
    except Exception:
        pass


def is_revoked(token: str) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if token_hash in _revoked_tokens:
        return True
    try:
        from app.core.cache import cache_get
        if cache_get(f"revoked:{token_hash}"):
            _revoked_tokens.add(token_hash)
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def _extract_bearer(request: Request) -> Optional[str]:
    """Pull the raw token from the Authorization: Bearer <token> header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency — extracts and verifies the Bearer token.
    Returns a dict with user_id, email, and the full token payload.
    Raises 401 if missing or invalid.
    """
    token = _extract_bearer(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": int(payload["sub"]), "email": payload["email"], "payload": payload}


async def get_optional_user(request: Request) -> Optional[dict]:
    """
    FastAPI dependency — same as get_current_user but returns None
    instead of raising when no token is present (for public-with-optional-auth endpoints).
    """
    token = _extract_bearer(request)
    if not token:
        return None
    try:
        payload = verify_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    return {"user_id": int(payload["sub"]), "email": payload["email"], "payload": payload}
