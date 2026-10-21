"""fase2 imagenes y registros_equipos

Revision ID: 20260725_0001
Revises:
Create Date: 2026-07-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260725_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "imagenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ruta_imagen", sa.Text(), nullable=False),
        sa.Column("ruta_thumb", sa.Text(), nullable=True),
        sa.Column("codigo_ocr", sa.String(length=50), nullable=True),
        sa.Column("tipo_deteccion", sa.String(length=20), nullable=True),
        sa.Column("confianza", sa.Float(), nullable=True),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("orientacion", sa.String(length=12), nullable=True),
        sa.Column("sin_deteccion", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "registros_equipos",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
        sa.Column("imagen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("tipo_deteccion", sa.String(length=20), nullable=False),
        sa.Column("codigo_ocr", sa.String(length=50), nullable=True),
        sa.Column("confianza", sa.Float(), nullable=True),
        sa.Column(
            "validado_manual", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("ruta_imagen", sa.Text(), nullable=False),
        sa.Column("orientacion", sa.String(length=12), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["imagen_id"], ["imagenes.id"]),
        sa.UniqueConstraint("imagen_id"),
    )
    op.create_index("ix_registros_equipos_codigo", "registros_equipos", ["codigo"])


def downgrade() -> None:
    op.drop_index("ix_registros_equipos_codigo", table_name="registros_equipos")
    op.drop_table("registros_equipos")
    op.drop_table("imagenes")
