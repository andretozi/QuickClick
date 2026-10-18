"""IA no criar anúncio: análises, uso das IAs, caches e a confirmação de maioridade.

Revisão: 0002_ia_anuncios
Anterior: 0001_estado_atual

Só aditiva: quatro tabelas novas, uma coluna que aceita vazio e índices.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_ia_anuncios"
down_revision = "0001_estado_atual"
branch_labels = None
depends_on = None

Json = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("users", sa.Column("confirmou_maioridade_em", sa.String(), nullable=True))

    op.create_table(
        "ia_analises",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("vendedor_id", sa.Integer(), sa.ForeignKey("vendedores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plano_no_momento", sa.String(20), nullable=False),
        sa.Column("nivel", sa.String(10), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("etapa_atual", sa.String(30), nullable=True),
        sa.Column("fotos_meta", Json, nullable=True),
        sa.Column("leitura", Json, nullable=True),
        sa.Column("atributos_confirmados", Json, nullable=True),
        sa.Column("ml_categoria_id", sa.String(40), nullable=True),
        sa.Column("pesquisa_chave", sa.String(200), nullable=True),
        sa.Column("preco", Json, nullable=True),
        sa.Column("texto", Json, nullable=True),
        sa.Column("canais", Json, nullable=True),
        sa.Column("avisos", Json, nullable=True),
        sa.Column("erro_codigo", sa.String(60), nullable=True),
        sa.Column("erro_mensagem_usuario", sa.String(500), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ia_analises_vendedor_criado", "ia_analises", ["vendedor_id", "criado_em"])
    op.create_index("ix_ia_analises_status", "ia_analises", ["status"])

    op.create_table(
        "ia_uso",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("vendedor_id", sa.Integer(), sa.ForeignKey("vendedores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("analise_id", sa.String(36), sa.ForeignKey("ia_analises.id", ondelete="SET NULL"), nullable=True),
        sa.Column("etapa", sa.String(30), nullable=False),
        sa.Column("provedor", sa.String(20), nullable=False),
        sa.Column("modelo", sa.String(60), nullable=False),
        sa.Column("versao_prompt", sa.String(40), nullable=True),
        sa.Column("tokens_entrada", sa.Integer(), nullable=False),
        sa.Column("tokens_saida", sa.Integer(), nullable=False),
        sa.Column("cache_lido", sa.Integer(), nullable=False),
        sa.Column("cache_gravado", sa.Integer(), nullable=False),
        sa.Column("buscas_web", sa.Integer(), nullable=False),
        sa.Column("custo_estimado_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("duracao_ms", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ia_uso_criado", "ia_uso", ["criado_em"])
    op.create_index("ix_ia_uso_analise", "ia_uso", ["analise_id"])

    op.create_table(
        "pesquisas_mercado",
        sa.Column("chave", sa.String(200), primary_key=True),
        sa.Column("conteudo", Json, nullable=False),
        sa.Column("fontes", Json, nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "ml_categorias_cache",
        sa.Column("categoria_id", sa.String(40), primary_key=True),
        sa.Column("atributos", Json, nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    raise RuntimeError("Migrações da Quick Click não se desfazem pelo Alembic: peça ao André.")
