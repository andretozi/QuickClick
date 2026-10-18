"""
Infraestrutura · Banco · Alinhamento do banco antigo com a revisão inicial (0001_estado_atual)

O banco de produção nasceu do create_all de uma versão anterior dos modelos e ficou sem colunas
que o código usa. Este alinhamento roda uma vez, ANTES de marcar o banco na revisão inicial, e só:
    - acrescenta colunas que aceitam vazio (ADD COLUMN, sem NOT NULL);
    - deixa colunas aceitarem vazio (ALTER COLUMN ... DROP NOT NULL), nunca o contrário.
Cada operação é pulada se o banco já estiver como ela pede: rodar duas vezes não muda nada.

Uso: python -m scripts.migrar --alinhar-sql (mostra o SQL, sem aplicar) e --alinhar (aplica).
"""

import io
from dataclasses import dataclass

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

COLUNAS_A_ACRESCENTAR: tuple[tuple[str, sa.Column], ...] = (
    ("users", sa.Column("nome", sa.String(), nullable=True)),
    ("users", sa.Column("loja", sa.String(), nullable=True)),
    ("users", sa.Column("criado_em", sa.String(), nullable=True)),
    ("contas_vinculadas", sa.Column("conta_externa_id", sa.String(), nullable=True)),
    ("contas_vinculadas", sa.Column("apelido", sa.String(), nullable=True)),
)

COLUNAS_QUE_ACEITAM_VAZIO: tuple[tuple[str, str], ...] = (
    ("users", "email"),
    ("users", "password_hash"),
)


@dataclass(frozen=True)
class Operacao:
    tipo: str  # add_column | aceitar_vazio
    tabela: str
    coluna: str

    def __str__(self) -> str:
        acao = "acrescentar a coluna" if self.tipo == "add_column" else "deixar aceitar vazio"
        return f"{self.tabela}.{self.coluna}: {acao}"


def operacoes_pendentes(conexao) -> list[Operacao]:
    """O que ainda falta fazer no banco (lido do catálogo, sem escrever nada)."""
    insp = inspect(conexao)
    tabelas = set(insp.get_table_names())
    colunas = {t: {c["name"]: c for c in insp.get_columns(t)} for t in tabelas}
    pendentes = []
    for tabela, coluna in COLUNAS_A_ACRESCENTAR:
        if tabela in tabelas and coluna.name not in colunas[tabela]:
            pendentes.append(Operacao("add_column", tabela, coluna.name))
    for tabela, nome in COLUNAS_QUE_ACEITAM_VAZIO:
        atual = colunas.get(tabela, {}).get(nome)
        if atual is not None and not atual["nullable"]:
            pendentes.append(Operacao("aceitar_vazio", tabela, nome))
    return pendentes


def _executar(op: Operations, pendentes: list[Operacao]) -> None:
    novas = {(tabela, coluna.name): coluna for tabela, coluna in COLUNAS_A_ACRESCENTAR}
    for operacao in pendentes:
        if operacao.tipo == "add_column":
            coluna = novas[(operacao.tabela, operacao.coluna)]
            op.add_column(operacao.tabela, sa.Column(coluna.name, coluna.type, nullable=True))
        else:
            op.alter_column(operacao.tabela, operacao.coluna, existing_type=sa.String(), nullable=True)


def sql_do_alinhamento(pendentes: list[Operacao], dialeto: str = "postgresql") -> str:
    """O SQL que o alinhamento rodaria, sem conectar para aplicar."""
    saida = io.StringIO()
    contexto = MigrationContext.configure(dialect_name=dialeto, opts={"as_sql": True, "output_buffer": saida})
    _executar(Operations(contexto), pendentes)
    return saida.getvalue()


def aplicar_alinhamento(engine) -> list[Operacao]:
    """Aplica o que falta numa transação só (se uma operação falhar, nada fica pela metade)."""
    with engine.begin() as conexao:
        pendentes = operacoes_pendentes(conexao)
        _executar(Operations(MigrationContext.configure(conexao)), pendentes)
    return pendentes
