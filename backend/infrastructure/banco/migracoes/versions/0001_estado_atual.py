"""Estado do banco antes do Alembic (o que o create_all criava até a versão da Fase 0).

Revisão: 0001_estado_atual
Anterior: nenhuma

No banco real ela não roda: o banco já tem estas tabelas e é só marcado com "alembic stamp"
(python -m scripts.migrar --marcar, que antes confere se o banco bate com esta revisão).
Num banco vazio (testes, um ambiente novo) ela cria tudo.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_estado_atual"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(), nullable=True),  # como o banco de produção nasceu
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("nome", sa.String(), nullable=True),
        sa.Column("loja", sa.String(), nullable=True),
        sa.Column("criado_em", sa.String(), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "marketplace_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("access_token", sa.String(), nullable=True),
        sa.Column("refresh_token", sa.String(), nullable=True),
    )
    op.create_index("ix_marketplace_tokens_id", "marketplace_tokens", ["id"])

    op.create_table(
        "ai_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("credits_left", sa.Integer(), nullable=True),
    )
    op.create_index("ix_ai_usage_id", "ai_usage", ["id"])

    op.create_table(
        "vendedores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("plano", sa.String(), nullable=False),
    )

    op.create_table(
        "contas_vinculadas",
        sa.Column("vendedor_id", sa.Integer(), sa.ForeignKey("vendedores.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("marketplace", sa.String(), primary_key=True),
        sa.Column("conectada_em", sa.String(), nullable=False),
        sa.Column("access_token", sa.String(), nullable=False),
        sa.Column("refresh_token", sa.String(), nullable=False),
        sa.Column("token_expira_em", sa.String(), nullable=False),
        sa.Column("conta_externa_id", sa.String(), nullable=True),
        sa.Column("apelido", sa.String(), nullable=True),
    )


def downgrade() -> None:
    raise RuntimeError("A revisão inicial não se desfaz: ela representa o banco que já existia.")
