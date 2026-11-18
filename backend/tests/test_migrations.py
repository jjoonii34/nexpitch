"""마이그레이션 테스트 (ADR 0011). 빈 SQLite에 마이그레이션을 적용해 모델과 같은 DB가 되는지 본다."""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.db import Base
from app.settings import BACKEND_DIR


def alembic_config(connection) -> Config:
    """테스트용 설정: DATABASE_URL 대신 넘겨준 연결을 쓴다 (migrations/env.py가 이 값을 먼저 본다)."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


def test_upgrade_head_matches_models_and_downgrade_removes_all():
    with create_engine("sqlite://").connect() as conn:
        config = alembic_config(conn)
        command.upgrade(config, "head")
        assert set(inspect(conn).get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}

        # 모델을 고치고 마이그레이션을 안 만들면 여기서 실패한다 → `python -m alembic revision --autogenerate -m "설명"`
        command.check(config)

        command.downgrade(config, "base")
        assert set(inspect(conn).get_table_names()) == {"alembic_version"}
