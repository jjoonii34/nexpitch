"""DB 접속 창구. 접속 주소는 backend/.env의 DATABASE_URL에서 읽는다."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, inspect

from app.models.news import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]  # backend/


def to_sqlalchemy_url(url: str) -> str:
    """Neon이 주는 주소(postgresql://…)를 psycopg 드라이버용 주소(postgresql+psycopg://…)로 바꾼다."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def get_engine() -> Engine:
    """DATABASE_URL로 접속 엔진을 만든다. 주소에 비밀번호가 들어 있으므로 주소는 어디에도 출력하지 않는다."""
    load_dotenv(BACKEND_DIR / ".env")
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL이 없습니다. backend/.env를 확인하세요.")
    return create_engine(to_sqlalchemy_url(url))


def create_tables(engine: Engine) -> list[str]:
    """아직 없는 테이블을 만든다(있는 테이블은 건드리지 않는다). DB에 있는 테이블 이름을 돌려준다."""
    Base.metadata.create_all(engine)
    return sorted(inspect(engine).get_table_names())


if __name__ == "__main__":
    # 직접 실행하면 테이블을 만들고 이름을 보여준다: python -m app.db
    print("테이블:", ", ".join(create_tables(get_engine())))
