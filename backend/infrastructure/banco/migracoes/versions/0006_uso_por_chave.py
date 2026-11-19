"""Uso da IA por chave: o orçamento do dia soma só a chave paga.

Revisão: 0006_uso_por_chave
Anterior: 0005_moderacao_e_auditoria

Só aditiva: uma coluna nova e nula em ia_uso. As linhas que já existem ficam como estão (sem chave).
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_uso_por_chave"
down_revision = "0005_moderacao_e_auditoria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ia_uso", sa.Column("chave", sa.String(length=10), nullable=True))


def downgrade() -> None:
    raise RuntimeError("Migrações da Quick Click não se desfazem pelo Alembic: peça ao André.")
