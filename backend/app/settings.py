"""경로와 환경변수를 한 곳에서 다룬다. 다른 모듈은 Path(__file__)나 load_dotenv를 직접 쓰지 않는다."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]  # backend/
REPO_ROOT = BACKEND_DIR.parent  # nexpitch/
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # 외부 API 원본 응답 (git 제외)
CLUBS_CSV = DATA_DIR / "clubs.csv"  # 구단 목록의 원본


def load_env() -> None:
    """backend/.env를 읽는다. 이미 있는 환경변수(예: GitHub Actions의 Secrets)는 덮어쓰지 않고, 파일이 없으면 아무것도 안 한다."""
    load_dotenv(BACKEND_DIR / ".env")


def require_env(name: str) -> str:
    """환경변수 값을 돌려준다. 없으면 어디에 넣어야 하는지 알려 주는 오류를 낸다 (값 자체는 절대 출력하지 않는다)."""
    load_env()
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name}이(가) 없습니다. backend/.env 또는 GitHub Secrets를 확인하세요.")
    return value
