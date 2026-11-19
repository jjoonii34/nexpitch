"""predictions.input_text 추가: LLM에 실제로 보낸 입력을 예측과 함께 저장한다.

수집이 진행되면 특성 값(xG 등)이 바뀌어, 나중에 근거 문장의 숫자를 대조할 수 없었다 (2026-11-19 평가 하네스에서 발견). 기존 행은 NULL.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19 15:56:27.104543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """열 하나 추가 (비어 있어도 됨 → 기존 행에 영향 없음)."""
    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('input_text', sa.Text(), nullable=True))



def downgrade() -> None:
    """열을 지운다."""
    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.drop_column('input_text')

