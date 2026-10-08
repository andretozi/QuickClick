"""Infraestrutura · Contas vinculadas no SQLite (implementa a porta RepositorioContasVinculadas)."""

import sqlite3
from datetime import datetime

from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.infrastructure.banco.sqlite import BancoSQLite

COLUNAS = "vendedor_id, marketplace, conectada_em, access_token, refresh_token, token_expira_em"


def _para_conta(linha: sqlite3.Row) -> ContaVinculada:
    return ContaVinculada(
        vendedor_id=linha["vendedor_id"],
        marketplace=linha["marketplace"],
        conectada_em=datetime.fromisoformat(linha["conectada_em"]),
        credenciais=CredenciaisOAuth(
            access_token=linha["access_token"],
            refresh_token=linha["refresh_token"],
            expira_em=datetime.fromisoformat(linha["token_expira_em"]),
        ),
    )


class RepositorioContasVinculadasSQLite:
    def __init__(self, banco: BancoSQLite):
        self._banco = banco

    def listar_do_vendedor(self, vendedor_id: int) -> list[ContaVinculada]:
        with self._banco.conectar() as conexao:
            linhas = conexao.execute(
                f"SELECT {COLUNAS} FROM contas_vinculadas WHERE vendedor_id = ? ORDER BY conectada_em",
                (vendedor_id,),
            ).fetchall()
        return [_para_conta(linha) for linha in linhas]

    def buscar(self, vendedor_id: int, marketplace: str) -> ContaVinculada | None:
        with self._banco.conectar() as conexao:
            linha = conexao.execute(
                f"SELECT {COLUNAS} FROM contas_vinculadas WHERE vendedor_id = ? AND marketplace = ?",
                (vendedor_id, marketplace),
            ).fetchone()
        return None if linha is None else _para_conta(linha)

    def salvar(self, conta: ContaVinculada) -> None:
        with self._banco.conectar() as conexao:
            conexao.execute(
                f"""
                INSERT INTO contas_vinculadas ({COLUNAS}) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (vendedor_id, marketplace) DO UPDATE SET
                    conectada_em = excluded.conectada_em,
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    token_expira_em = excluded.token_expira_em
                """,
                (
                    conta.vendedor_id,
                    conta.marketplace,
                    conta.conectada_em.isoformat(),
                    conta.credenciais.access_token,
                    conta.credenciais.refresh_token,
                    conta.credenciais.expira_em.isoformat(),
                ),
            )

    def remover(self, vendedor_id: int, marketplace: str) -> None:
        with self._banco.conectar() as conexao:
            conexao.execute(
                "DELETE FROM contas_vinculadas WHERE vendedor_id = ? AND marketplace = ?",
                (vendedor_id, marketplace),
            )
