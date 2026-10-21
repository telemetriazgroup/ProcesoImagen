"""observaciones y tiempo_proceso en imagenes/registros

Revision ID: 20260725_0002
Revises: 20260725_0001
Create Date: 2026-07-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260725_0002"
down_revision: Union[str, None] = "20260725_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("imagenes", sa.Column("fuente", sa.String(length=80), nullable=True))
    op.add_column("imagenes", sa.Column("observaciones", sa.Text(), nullable=True))
    op.add_column("imagenes", sa.Column("tiempo_proceso_s", sa.Float(), nullable=True))
    op.add_column(
        "registros_equipos", sa.Column("fuente", sa.String(length=80), nullable=True)
    )
    op.add_column("registros_equipos", sa.Column("observaciones", sa.Text(), nullable=True))
    op.add_column(
        "registros_equipos", sa.Column("tiempo_proceso_s", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("registros_equipos", "tiempo_proceso_s")
    op.drop_column("registros_equipos", "observaciones")
    op.drop_column("registros_equipos", "fuente")
    op.drop_column("imagenes", "tiempo_proceso_s")
    op.drop_column("imagenes", "observaciones")
    op.drop_column("imagenes", "fuente")
