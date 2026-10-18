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
from backend.infrastructure.seguranca.cripto_tokens import CifradorDeTokens
from backend.tests.test_api import CHAVE_CRIPTO_TESTE

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
        self.contas = RepositorioContasVinculadasSQL(self.Session, CifradorDeTokens(CHAVE_CRIPTO_TESTE))
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

    def test_tokens_ficam_cifrados_no_banco(self):
        self.contas.salvar(conta("mercado-livre"))
        with self.Session() as session:
            linha = session.query(models.ContaVinculadaModel).filter_by(marketplace="mercado-livre").one()
            self.assertTrue(linha.access_token.startswith("enc:v1:"))
            self.assertTrue(linha.refresh_token.startswith("enc:v1:"))
            self.assertNotIn("tok_mercado-livre", linha.access_token)
        self.assertEqual(self.contas.buscar(1, "mercado-livre").credenciais.access_token, "tok_mercado-livre")

    def test_token_legado_em_texto_puro_e_lido_e_volta_cifrado_na_proxima_gravacao(self):
        with self.Session() as session:
            session.add(models.ContaVinculadaModel(
                vendedor_id=1, marketplace="mercado-livre", conectada_em=AGORA.isoformat(),
                access_token="legado_access", refresh_token="legado_refresh",
                token_expira_em=(AGORA + timedelta(hours=1)).isoformat(),
            ))
            session.commit()
        lida = self.contas.buscar(1, "mercado-livre")
        self.assertEqual(lida.credenciais.access_token, "legado_access")
        self.contas.salvar(lida)
        with self.Session() as session:
            linha = session.query(models.ContaVinculadaModel).filter_by(marketplace="mercado-livre").one()
            self.assertTrue(linha.access_token.startswith("enc:v1:"))

    def test_sem_chave_de_criptografia_nao_grava_token(self):
        from backend.domain.erros import ServicoIndisponivel

        sem_chave = RepositorioContasVinculadasSQL(self.Session, CifradorDeTokens(None, avisar=False))
        with self.assertRaises(ServicoIndisponivel):
            sem_chave.salvar(conta("amazon"))


if __name__ == "__main__":
    unittest.main()
