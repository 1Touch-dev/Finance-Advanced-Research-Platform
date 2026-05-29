from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://user:password@postgres:5432/mydb"
    jwt_secret: str = "dev-secret-change"
    jwt_issuer: str = "identity-api"
    env: str = "local"

    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False

settings = Settings()
