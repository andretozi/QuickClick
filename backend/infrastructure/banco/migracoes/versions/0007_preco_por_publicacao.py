"""
0007 · Preço individual por publicação (canal de marketplace)

Revision ID: 0007_preco_por_publicacao
Revises: 0006_uso_por_chave
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_preco_por_publicacao"
down_revision = "0006_uso_por_chave"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("publicacoes", sa.Column("preco_centavos", sa.Integer(), nullable=True))


def downgrade() -> None:
    raise RuntimeError("As migrações da Quick Click são somente aditivas.")
