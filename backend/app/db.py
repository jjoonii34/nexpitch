"""DB 접속 창구. 접속 주소는 backend/.env의 DATABASE_URL에서 읽는다."""

from sqlalchemy import Engine, create_engine, inspect

import app.models.analysis  # noqa: F401  — 분석 테이블을 Base에 등록하기 위해 (create_all이 알아야 한다)
from app.models.news import Base
from app.settings import require_env


def to_sqlalchemy_url(url: str) -> str:
    """Neon이 주는 주소(postgresql://…)를 psycopg 드라이버용 주소(postgresql+psycopg://…)로 바꾼다."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def get_engine() -> Engine:
    """DATABASE_URL로 접속 엔진을 만든다. 주소에 비밀번호가 들어 있으므로 주소는 어디에도 출력하지 않는다."""
    # pool_pre_ping: 호출 사이에 몇 초 쉬는 배치에서 Neon이 연결을 끊은 적이 있어, 쓰기 전에 연결이 살았는지 확인하고 아니면 다시 연다.
    # prepare_threshold=None: Neon의 -pooler 주소(PgBouncer)는 psycopg의 '준비된 문장(prepared statement)'을 지원하지 않아,
    # 같은 질의를 5번 넘게 보내면 "server closed the connection unexpectedly"로 끊겼다 (2026-11-16 수집 배치에서 두 번 겪음).
    return create_engine(to_sqlalchemy_url(require_env("DATABASE_URL")), pool_pre_ping=True, connect_args={"prepare_threshold": None})


def create_tables(engine: Engine) -> list[str]:
    """아직 없는 테이블을 만든다(있는 테이블은 건드리지 않는다). DB에 있는 테이블 이름을 돌려준다."""
    Base.metadata.create_all(engine)
    return sorted(inspect(engine).get_table_names())


if __name__ == "__main__":
    # 직접 실행하면 테이블을 만들고 이름을 보여준다: python -m app.db
    print("테이블:", ", ".join(create_tables(get_engine())))
