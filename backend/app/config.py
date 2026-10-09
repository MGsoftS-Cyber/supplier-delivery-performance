"""Environment configuration. Local development deliberately needs no cloud service."""

import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./supply.db")
ALLOWED_ORIGINS = {
    value.strip()
    for value in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5179,http://127.0.0.1:5179,http://localhost:8086,http://127.0.0.1:8086,http://localhost:8006,http://127.0.0.1:8006",
    ).split(",")
    if value.strip()
}
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
SESSION_SECONDS = 60 * 60 * 24 * 7
STATIC_DIR = Path(os.getenv("STATIC_DIR", "../frontend/dist"))
