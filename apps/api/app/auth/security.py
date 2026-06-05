import datetime as dt
import hashlib
import secrets

import jwt
from passlib.hash import bcrypt

from app.core.settings import settings

_revoked_tokens: set = set()
_refresh_tokens: dict = {}


def hash_password(p: str) -> str:
    return bcrypt.hash(p)


def verify_password(p: str, h: str) -> bool:
    return bcrypt.verify(p, h)


def create_token(user_id: int, email: str, hours: int = 8) -> str:
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


def create_refresh_token(user_id: int, email: str) -> str:
    token = secrets.token_urlsafe(48)
    _refresh_tokens[token] = {"user_id": user_id, "email": email, "created": dt.datetime.utcnow().isoformat()}
    return token


def exchange_refresh_token(refresh_token: str) -> dict | None:
    data = _refresh_tokens.get(refresh_token)
    if not data:
        return None
    return {
        "token": create_token(data["user_id"], data["email"]),
        "refresh_token": refresh_token,
    }


def revoke_token(token: str) -> None:
    _revoked_tokens.add(hashlib.sha256(token.encode()).hexdigest())


def is_revoked(token: str) -> bool:
    return hashlib.sha256(token.encode()).hexdigest() in _revoked_tokens


def decode_token(token: str) -> dict:
    if is_revoked(token):
        raise jwt.InvalidTokenError("token revoked")
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], options={"require": ["exp", "iat", "iss"]})
