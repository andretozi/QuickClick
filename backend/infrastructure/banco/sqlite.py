"""
Infraestrutura · Banco SQLite

Um arquivo local, fora do Git (backend/data/ por padrão). Cada operação abre e fecha
a própria conexão: simples e seguro com as várias threads do servidor.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Os tokens ficam em texto puro porque nesta versão eles são simulados.
# Com integração real, guarde os tokens criptografados (chave no .env).
ESQUEMA = """
CREATE TABLE IF NOT EXISTS vendedores (
    id    INTEGER PRIMARY KEY,
    nome  TEXT    NOT NULL,
    plano TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS contas_vinculadas (
    vendedor_id     INTEGER NOT NULL REFERENCES vendedores (id) ON DELETE CASCADE,
    marketplace     TEXT    NOT NULL,
    conectada_em    TEXT    NOT NULL,
    access_token    TEXT    NOT NULL,
    refresh_token   TEXT    NOT NULL,
    token_expira_em TEXT    NOT NULL,
    PRIMARY KEY (vendedor_id, marketplace)
);
"""


class BancoSQLite:
    def __init__(self, caminho: Path):
        self.caminho = caminho

    def criar_tabelas(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        with self.conectar() as conexao:
            conexao.executescript(ESQUEMA)

    @contextmanager
    def conectar(self) -> Iterator[sqlite3.Connection]:
        """Abre uma conexão, confirma no fim (ou desfaz, se der erro) e sempre fecha."""
        conexao = sqlite3.connect(self.caminho)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        try:
            with conexao:
                yield conexao
        finally:
            conexao.close()
