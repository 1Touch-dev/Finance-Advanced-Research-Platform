import datetime as dt
import jwt
from passlib.hash import bcrypt
from app.core.settings import settings

def hash_password(p: str) -> str:
    return bcrypt.hash(p)

def verify_password(p: str, h: str) -> bool:
    return bcrypt.verify(p, h)

def create_token(user_id: int, email: str) -> str:
    now = dt.datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + dt.timedelta(hours=8),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], options={"require": ["exp","iat","iss"]})
