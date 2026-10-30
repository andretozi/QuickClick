"""Anúncios no banco: produtos e publicações, por vendedor.

Revisão: 0003_produtos
Anterior: 0002_ia_anuncios

Só aditiva: duas tabelas novas e dois índices.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_produtos"
down_revision = "0002_ia_anuncios"
branch_labels = None
depends_on = None

Json = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "produtos",
        sa.Column("vendedor_id", sa.Integer(), sa.ForeignKey("vendedores.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("titulo", sa.String(300), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("categoria", sa.String(40), nullable=False),
        sa.Column("condicao", sa.String(10), nullable=False),
        sa.Column("preco_centavos", sa.Integer(), nullable=False),
        sa.Column("preco_sugerido_centavos", sa.Integer(), nullable=True),
        sa.Column("estoque", sa.Integer(), nullable=False),
        sa.Column("fotos", Json, nullable=False),
        sa.Column("capa", sa.Integer(), nullable=False),
        sa.Column("atributos", Json, nullable=False),
        sa.Column("analise_id", sa.String(36), sa.ForeignKey("ia_analises.id", ondelete="SET NULL"), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_produtos_vendedor_atualizado", "produtos", ["vendedor_id", "atualizado_em"])

    op.create_table(
        "publicacoes",
        sa.Column("vendedor_id", sa.Integer(), primary_key=True),
        sa.Column("produto_id", sa.String(40), primary_key=True),
        sa.Column("canal", sa.String(40), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("id_externo", sa.String(60), nullable=True),
        sa.Column("permalink", sa.String(500), nullable=True),
        sa.Column("categoria_id", sa.String(40), nullable=True),
        sa.Column("saude", sa.Float(), nullable=True),
        sa.Column("vendidos", sa.Integer(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vendedor_id", "produto_id"], ["produtos.vendedor_id", "produtos.id"],
                                ondelete="CASCADE"),
    )
    op.create_index("ux_publicacoes_externo", "publicacoes", ["vendedor_id", "canal", "id_externo"], unique=True)


def downgrade() -> None:
    raise RuntimeError("Migrações da Quick Click não se desfazem pelo Alembic: peça ao André.")
