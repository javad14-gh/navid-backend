import os
from dataclasses import dataclass


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    coach_invite_code: str
    upload_dir: str
    timezone: str
    cors_origins: list
    token_hours: int = 24 * 14
    max_photo_bytes: int = 5 * 1024 * 1024


def load() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./navid.db"),
        jwt_secret=os.getenv("JWT_SECRET", "dev-only-secret-change-me"),
        coach_invite_code=os.getenv("COACH_INVITE_CODE", ""),
        upload_dir=os.getenv("UPLOAD_DIR", "./uploads"),
        timezone=os.getenv("TIMEZONE", "Asia/Tehran"),
        cors_origins=[o for o in os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",") if o],
    )


settings = load()
