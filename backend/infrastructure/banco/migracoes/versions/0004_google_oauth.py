"""Login e cadastro via Google OAuth: google_id único e store_name em users.

Revisão: 0004_google_oauth
Anterior: 0003_produtos

Só aditiva: duas colunas que aceitam vazio e um índice único.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_google_oauth"
down_revision = "0003_produtos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("store_name", sa.String(), nullable=True))
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)


def downgrade() -> None:
    raise RuntimeError("Migrações da Quick Click não se desfazem pelo Alembic: peça ao André.")
