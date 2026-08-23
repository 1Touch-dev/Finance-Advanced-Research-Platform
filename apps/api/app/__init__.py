"""
App package — ensures .env is loaded before anything else imports os.getenv().
"""
from dotenv import load_dotenv
from pathlib import Path

_env_path = Path(__file__).resolve().parents[2] / ".env"
if not _env_path.exists():
    _env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=False)
