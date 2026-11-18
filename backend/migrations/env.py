"""Alembic 실행 환경 (ADR 0011). `alembic upgrade head` 등을 실행하면 이 파일이 DB에 붙어 마이그레이션을 돌린다.

- 설정 파일 alembic.ini는 ASCII만 쓴다 — 윈도우에서 alembic이 시스템 인코딩(cp949)으로 읽어 한글 주석이 있으면 깨진다.
- 접속: 테스트가 연결을 넘겨주면(config.attributes["connection"]) 그것을, 아니면 app.db.get_engine()(DATABASE_URL)을 쓴다.
  접속 주소에는 비밀번호가 있으므로 alembic.ini에 적지 않는다.
- target_metadata: 모델(app/models)의 테이블 정의. autogenerate가 이것과 실제 DB를 비교해 마이그레이션 초안을 쓴다.
"""

from logging.config import fileConfig

from alembic import context

import app.models.analysis  # noqa: F401  — 분석 테이블을 Base에 등록하기 위해
from app.models.news import Base

target_metadata = Base.metadata


def run_migrations(connection) -> None:
    """주어진 연결로 마이그레이션을 실행한다. SQLite는 ALTER가 약해 '표 다시 만들기(batch)' 방식으로 바꾼다."""
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=connection.dialect.name == "sqlite")
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if connection is None and context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)  # 명령줄 실행 때만 진행 상황 출력
if connection is not None:
    run_migrations(connection)
else:
    from app.db import get_engine

    with get_engine().connect() as conn:
        run_migrations(conn)
