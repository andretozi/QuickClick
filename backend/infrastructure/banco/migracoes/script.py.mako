"""${message}

Revisão: ${up_revision}
Anterior: ${down_revision | comma,n}
Criada em: ${create_date}

Só aditiva: criar tabela, criar coluna que aceita vazio, criar índice. O migrador recusa o resto.
"""

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
