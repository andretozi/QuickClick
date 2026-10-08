"""Infraestrutura · Vendedores no SQLite (implementa a porta RepositorioVendedores)."""

from backend.domain.plano import buscar_plano
from backend.domain.vendedor import Vendedor
from backend.infrastructure.banco.sqlite import BancoSQLite


class RepositorioVendedoresSQLite:
    def __init__(self, banco: BancoSQLite):
        self._banco = banco

    def obter(self, vendedor_id: int) -> Vendedor | None:
        with self._banco.conectar() as conexao:
            linha = conexao.execute(
                "SELECT id, nome, plano FROM vendedores WHERE id = ?", (vendedor_id,)
            ).fetchone()
        if linha is None:
            return None
        plano = buscar_plano(linha["plano"])
        if plano is None:
            raise ValueError(f"Plano desconhecido no banco para o vendedor {vendedor_id}: {linha['plano']!r}")
        return Vendedor(id=linha["id"], nome=linha["nome"], plano=plano)

    def salvar(self, vendedor: Vendedor) -> None:
        with self._banco.conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO vendedores (id, nome, plano) VALUES (?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET nome = excluded.nome, plano = excluded.plano
                """,
                (vendedor.id, vendedor.nome, vendedor.plano.slug),
            )
