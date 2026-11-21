"""Tabela midia_fotos para servir fotos públicas de anúncios via https://."""

import sqlalchemy as sa
from alembic import context, op

revision = "0008_midia_fotos"
down_revision = "0007_preco_por_publicacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if context.is_offline_mode() or "midia_fotos" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "midia_fotos",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("vendedor_id", sa.Integer(), nullable=True),
            sa.Column("content_type", sa.String(length=40), nullable=False),
            sa.Column("conteudo", sa.LargeBinary(), nullable=False),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["vendedor_id"], ["vendedores.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_midia_fotos_criado", "midia_fotos", ["criado_em"], unique=False)


def downgrade() -> None:
    raise RuntimeError("As migrações da Quick Click são só para frente.")
