import os
import secrets
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_env = os.path.abspath(os.path.join(_current_dir, "../../../../.env"))
if not os.path.exists(_root_env):
    _root_env = os.path.abspath(os.path.join(_current_dir, "../../../.env"))


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=_root_env,
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "sqlite:///./local.db"
    jwt_secret: str = ""
    jwt_issuer: str = "identity-api"
    env: str = "local"


settings = Settings()

if not settings.jwt_secret or len(settings.jwt_secret) < 32:
    if settings.env == "production":
        raise RuntimeError("JWT_SECRET must be at least 32 characters in production. Set it in .env or environment.")
    settings.jwt_secret = os.getenv("JWT_SECRET") or secrets.token_hex(32)
elif len(settings.jwt_secret) < 32:
    # Pad short secrets in dev/test to silence InsecureKeyLengthWarning
    settings.jwt_secret = settings.jwt_secret.ljust(32, "0")
