"""기준선: 2026-11-18 시점의 테이블 14개 전체 (ADR 0011).

Neon에는 이미 create_all + 손 ALTER(predictions.hypothesis_json)로 같은 테이블이 있어, 거기서는 실행하지 않고 `alembic stamp 0001`로 "적용됨" 표시만 했다.
새 DB(테스트·새 환경)는 `alembic upgrade head`로 이 파일부터 만든다.

Revision ID: 0001
Revises: 
Create Date: 2026-11-18 11:31:48.566424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """빈 DB에 테이블 전체를 만든다 (외래 키 순서대로)."""
    # autogenerate 초안 (Text() → sa.Text()만 손봄)
    op.create_table('articles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('body_or_summary', sa.Text(), nullable=False),
    sa.Column('author', sa.String(length=200), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('url')
    )
    op.create_table('clubs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('guardian_tag', sa.String(length=100), nullable=False),
    sa.Column('in_premier_league', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('guardian_tag'),
    sa.UniqueConstraint('name')
    )
    op.create_table('players',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('raw_responses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=30), nullable=False),
    sa.Column('endpoint', sa.String(length=60), nullable=False),
    sa.Column('params', sa.String(length=200), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('payload', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('article_clubs',
    sa.Column('article_id', sa.Integer(), nullable=False),
    sa.Column('club_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
    sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ),
    sa.PrimaryKeyConstraint('article_id', 'club_id')
    )
    op.create_table('article_translations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('article_id', sa.Integer(), nullable=False),
    sa.Column('prompt_version', sa.String(length=20), nullable=False),
    sa.Column('model', sa.String(length=50), nullable=False),
    sa.Column('title_ko', sa.String(length=500), nullable=False),
    sa.Column('summary_ko', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('article_id', 'prompt_version')
    )
    op.create_table('teams',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('club_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('fixtures',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('season', sa.Integer(), nullable=False),
    sa.Column('kickoff', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('home_team_id', sa.Integer(), nullable=False),
    sa.Column('away_team_id', sa.Integer(), nullable=False),
    sa.Column('home_goals', sa.Integer(), nullable=True),
    sa.Column('away_goals', sa.Integer(), nullable=True),
    sa.Column('referee', sa.String(length=100), nullable=True),
    sa.Column('lineups_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('team_stats_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('player_stats_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['away_team_id'], ['teams.id'], ),
    sa.ForeignKeyConstraint(['home_team_id'], ['teams.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lineups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fixture_id', sa.Integer(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.Column('formation', sa.String(length=20), nullable=True),
    sa.Column('coach', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['fixture_id'], ['fixtures.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fixture_id', 'team_id')
    )
    op.create_table('player_match_stats',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fixture_id', sa.Integer(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.Column('player_id', sa.Integer(), nullable=False),
    sa.Column('minutes', sa.Integer(), nullable=True),
    sa.Column('is_starter', sa.Boolean(), nullable=True),
    sa.Column('position', sa.String(length=5), nullable=True),
    sa.Column('rating', sa.Float(), nullable=True),
    sa.Column('goals', sa.Integer(), nullable=True),
    sa.Column('assists', sa.Integer(), nullable=True),
    sa.Column('shots_total', sa.Integer(), nullable=True),
    sa.Column('passes_total', sa.Integer(), nullable=True),
    sa.Column('key_passes', sa.Integer(), nullable=True),
    sa.Column('tackles', sa.Integer(), nullable=True),
    sa.Column('duels_won', sa.Integer(), nullable=True),
    sa.Column('dribbles_success', sa.Integer(), nullable=True),
    sa.Column('yellow_cards', sa.Integer(), nullable=True),
    sa.Column('red_cards', sa.Integer(), nullable=True),
    sa.Column('stats_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.ForeignKeyConstraint(['fixture_id'], ['fixtures.id'], ),
    sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fixture_id', 'player_id')
    )
    op.create_table('predictions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fixture_id', sa.Integer(), nullable=False),
    sa.Column('model', sa.String(length=30), nullable=False),
    sa.Column('version', sa.String(length=20), nullable=False),
    sa.Column('p_home', sa.Float(), nullable=False),
    sa.Column('p_draw', sa.Float(), nullable=False),
    sa.Column('p_away', sa.Float(), nullable=False),
    sa.Column('rationale', sa.Text(), nullable=True),
    sa.Column('hypothesis', sa.Text(), nullable=True),
    sa.Column('hypothesis_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['fixture_id'], ['fixtures.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fixture_id', 'model', 'version')
    )
    op.create_table('team_match_stats',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fixture_id', sa.Integer(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.Column('shots_total', sa.Integer(), nullable=True),
    sa.Column('shots_on', sa.Integer(), nullable=True),
    sa.Column('possession', sa.Integer(), nullable=True),
    sa.Column('passes_total', sa.Integer(), nullable=True),
    sa.Column('passes_accurate', sa.Integer(), nullable=True),
    sa.Column('corners', sa.Integer(), nullable=True),
    sa.Column('fouls', sa.Integer(), nullable=True),
    sa.Column('yellow_cards', sa.Integer(), nullable=True),
    sa.Column('red_cards', sa.Integer(), nullable=True),
    sa.Column('xg', sa.Float(), nullable=True),
    sa.Column('stats_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.ForeignKeyConstraint(['fixture_id'], ['fixtures.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fixture_id', 'team_id')
    )
    op.create_table('hypothesis_checks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('prediction_id', sa.Integer(), nullable=False),
    sa.Column('feature', sa.String(length=30), nullable=False),
    sa.Column('op', sa.String(length=2), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('claim', sa.String(length=30), nullable=False),
    sa.Column('n_condition', sa.Integer(), nullable=False),
    sa.Column('n_other', sa.Integer(), nullable=False),
    sa.Column('rate_condition', sa.Float(), nullable=True),
    sa.Column('rate_other', sa.Float(), nullable=True),
    sa.Column('diff', sa.Float(), nullable=True),
    sa.Column('ci_low', sa.Float(), nullable=True),
    sa.Column('ci_high', sa.Float(), nullable=True),
    sa.Column('verdict', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['prediction_id'], ['predictions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lineup_players',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('lineup_id', sa.Integer(), nullable=False),
    sa.Column('player_id', sa.Integer(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=True),
    sa.Column('position', sa.String(length=5), nullable=True),
    sa.Column('grid', sa.String(length=10), nullable=True),
    sa.Column('is_starter', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['lineup_id'], ['lineups.id'], ),
    sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """전부 지운다 (만든 역순)."""
    # autogenerate 초안 (Text() → sa.Text()만 손봄)
    op.drop_table('lineup_players')
    op.drop_table('hypothesis_checks')
    op.drop_table('team_match_stats')
    op.drop_table('predictions')
    op.drop_table('player_match_stats')
    op.drop_table('lineups')
    op.drop_table('fixtures')
    op.drop_table('teams')
    op.drop_table('article_translations')
    op.drop_table('article_clubs')
    op.drop_table('raw_responses')
    op.drop_table('players')
    op.drop_table('clubs')
    op.drop_table('articles')
