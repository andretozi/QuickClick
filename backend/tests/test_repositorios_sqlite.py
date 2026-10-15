"""Repositórios SQLAlchemy de verdade (compatíveis com Azure PostgreSQL)."""

import unittest
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.domain.plano import GRATIS, PRO
from backend.domain.vendedor import Vendedor
from backend.infrastructure.banco import models  # noqa: F401
from backend.infrastructure.banco.repositorio_contas import RepositorioContasVinculadasSQL
from backend.infrastructure.banco.repositorio_vendedores import RepositorioVendedoresSQL
from backend.infrastructure.database import Base

AGORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def conta(marketplace: str, minutos: int = 0) -> ContaVinculada:
    return ContaVinculada(
        vendedor_id=1,
        marketplace=marketplace,
        conectada_em=AGORA + timedelta(minutes=minutos),
        credenciais=CredenciaisOAuth(f"tok_{marketplace}", f"ref_{marketplace}", AGORA + timedelta(hours=1)),
    )


class TestRepositoriosSQL(unittest.TestCase):
    def setUp(self):
        self._engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self._engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        self.vendedores = RepositorioVendedoresSQL(self.Session)
        self.contas = RepositorioContasVinculadasSQL(self.Session)
        self.vendedores.salvar(Vendedor(1, "Loja de teste", GRATIS))

    def tearDown(self):
        self._engine.dispose()

    def test_vendedor_salvo_volta_igual_e_pode_mudar_de_plano(self):
        self.assertEqual(self.vendedores.obter(1), Vendedor(1, "Loja de teste", GRATIS))
        self.vendedores.salvar(Vendedor(1, "Loja de teste", PRO))
        self.assertEqual(self.vendedores.obter(1), Vendedor(1, "Loja de teste", PRO))

    def test_obter_vendedor_inexistente_devolve_none(self):
        self.assertIsNone(self.vendedores.obter(99))

    def test_contas_vinculadas_ordenadas_por_data_de_conexao(self):
        self.contas.salvar(conta("amazon", minutos=10))
        self.contas.salvar(conta("mercado-livre", minutos=0))
        salvas = self.contas.listar_do_vendedor(1)
        self.assertEqual([c.marketplace for c in salvas], ["mercado-livre", "amazon"])

    def test_salvar_duas_vezes_atualiza_a_mesma_conta(self):
        self.contas.salvar(conta("amazon"))
        nova = ContaVinculada(
            vendedor_id=1,
            marketplace="amazon",
            conectada_em=AGORA + timedelta(days=1),
            credenciais=CredenciaisOAuth("novo_tok", "novo_ref", AGORA + timedelta(days=2)),
        )
        self.contas.salvar(nova)
        self.assertEqual(self.contas.buscar(1, "amazon"), nova)
        self.assertEqual(len(self.contas.listar_do_vendedor(1)), 1)

    def test_remover_conta(self):
        self.contas.salvar(conta("amazon"))
        self.contas.remover(1, "amazon")
        self.assertIsNone(self.contas.buscar(1, "amazon"))
        self.assertEqual(self.contas.listar_do_vendedor(1), [])


if __name__ == "__main__":
    unittest.main()
