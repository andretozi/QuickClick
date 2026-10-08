"""Repositórios SQLite de verdade, num arquivo temporário."""

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.domain.plano import GRATIS, PRO
from backend.domain.vendedor import Vendedor
from backend.infrastructure.banco.repositorio_contas import RepositorioContasVinculadasSQLite
from backend.infrastructure.banco.repositorio_vendedores import RepositorioVendedoresSQLite
from backend.infrastructure.banco.sqlite import BancoSQLite

AGORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def conta(marketplace: str, minutos: int = 0) -> ContaVinculada:
    return ContaVinculada(
        vendedor_id=1,
        marketplace=marketplace,
        conectada_em=AGORA + timedelta(minutes=minutos),
        credenciais=CredenciaisOAuth("acesso", "renovacao", AGORA + timedelta(hours=6)),
    )


class TestRepositoriosSQLite(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        banco = BancoSQLite(Path(self._pasta.name) / "dados" / "teste.sqlite3")
        banco.criar_tabelas()
        banco.criar_tabelas()  # criar de novo não pode quebrar nada
        self.vendedores = RepositorioVendedoresSQLite(banco)
        self.contas = RepositorioContasVinculadasSQLite(banco)
        self.vendedores.salvar(Vendedor(1, "Loja de teste", GRATIS))

    def tearDown(self):
        self._pasta.cleanup()

    def test_vendedor_salvo_volta_igual_e_pode_mudar_de_plano(self):
        self.assertEqual(self.vendedores.obter(1), Vendedor(1, "Loja de teste", GRATIS))
        self.vendedores.salvar(Vendedor(1, "Loja de teste", PRO))
        self.assertEqual(self.vendedores.obter(1).plano, PRO)
        self.assertIsNone(self.vendedores.obter(2))

    def test_conta_salva_volta_igual(self):
        self.contas.salvar(conta("shopee"))
        self.assertEqual(self.contas.buscar(1, "shopee"), conta("shopee"))
        self.assertIsNone(self.contas.buscar(1, "amazon"))

    def test_lista_na_ordem_de_conexao_e_remove(self):
        self.contas.salvar(conta("amazon", minutos=5))
        self.contas.salvar(conta("mercado-livre", minutos=1))

        self.assertEqual([c.marketplace for c in self.contas.listar_do_vendedor(1)], ["mercado-livre", "amazon"])

        self.contas.remover(1, "mercado-livre")
        self.contas.remover(1, "mercado-livre")  # remover de novo não dá erro
        self.assertEqual([c.marketplace for c in self.contas.listar_do_vendedor(1)], ["amazon"])

    def test_salvar_de_novo_atualiza_em_vez_de_duplicar(self):
        self.contas.salvar(conta("shopee"))
        self.contas.salvar(conta("shopee", minutos=30))
        contas = self.contas.listar_do_vendedor(1)
        self.assertEqual(len(contas), 1)
        self.assertEqual(contas[0].conectada_em, AGORA + timedelta(minutes=30))


if __name__ == "__main__":
    unittest.main()
