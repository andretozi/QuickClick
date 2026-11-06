"""Controle de contas, moderação de vendedores e auditoria administrativa.

Revisão: 0005_moderacao_e_auditoria
Anterior: 0004_google_oauth

Só aditiva: novas colunas em users e a criação da tabela de auditoria com seus índices.
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_moderacao_e_auditoria"
down_revision = "0004_google_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("papel", sa.String(length=30), nullable=False, server_default="vendedor"))
    op.add_column("users", sa.Column("status_conta", sa.String(length=30), nullable=False, server_default="ativa"))
    op.add_column("users", sa.Column("motivo_moderacao", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("suspensa_ate", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("token_versao", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("ultimo_login_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("ultimo_acesso_em", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "registros_auditoria",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("admin_email", sa.String(length=254), nullable=False),
        sa.Column("alvo_id", sa.Integer(), nullable=True),
        sa.Column("alvo_identificador", sa.String(length=254), nullable=False),
        sa.Column("acao", sa.String(length=60), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("detalhes", sa.JSON(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_registros_auditoria_criado", "registros_auditoria", ["criado_em"])
    op.create_index("ix_registros_auditoria_acao", "registros_auditoria", ["acao"])
    op.create_index("ix_registros_auditoria_alvo", "registros_auditoria", ["alvo_id"])


def downgrade() -> None:
    raise RuntimeError("Migrações da Quick Click não se desfazem pelo Alembic: peça ao André.")
