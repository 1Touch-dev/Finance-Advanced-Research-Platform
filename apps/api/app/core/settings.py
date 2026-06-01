import os
from pydantic_settings import BaseSettings

# Dynamically resolve root .env path (four directories up from settings.py)
_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_env = os.path.abspath(os.path.join(_current_dir, "../../../../.env"))

class Settings(BaseSettings):
    database_url: str = "sqlite:///./local.db"
    jwt_secret: str = "dev-secret-change"
    jwt_issuer: str = "identity-api"
    env: str = "local"

    class Config:
        env_file = _root_env
        env_prefix = ""
        case_sensitive = False
        extra = "ignore"

settings = Settings()
