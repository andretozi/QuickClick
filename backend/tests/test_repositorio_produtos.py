"""Repositório de produtos em SQLite: publicações, versão (409), importação idempotente e isolamento por vendedor."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.domain.erros import AnuncioDesatualizado
from backend.domain.plano import GRATIS
from backend.domain.produto import Produto, Publicacao
from backend.domain.vendedor import Vendedor
from backend.infrastructure.banco import models
from backend.infrastructure.banco.repositorio_produtos import RepositorioDeProdutosSQL
from backend.infrastructure.banco.repositorio_vendedores import RepositorioVendedoresSQL
from backend.infrastructure.database import Base

AGORA = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def produto(id_: str = "a_1", minutos: int = 0, **campos) -> Produto:
    base = dict(
        id=id_, titulo="Tênis de corrida", descricao="Pouco uso.", categoria="calcados", condicao="usado",
        preco_centavos=15990, preco_sugerido_centavos=16990, estoque=1,
        fotos=["https://http2.mlstatic.com/D_1.jpg"], capa=0,
        atributos=[{"id": "BRAND", "nome": "Marca", "valor": "Corre"}], analise_id=None,
        criado_em=AGORA + timedelta(minutes=minutos), atualizado_em=AGORA + timedelta(minutes=minutos),
        publicacoes=[Publicacao("mercado-livre", "publicado", "MLB1", "https://produto.mercadolivre.com.br/MLB1",
                                "MLB1234", 87.5, 2)],
    )
    return Produto(**{**base, **campos})


class TestRepositorioDeProdutos(unittest.TestCase):
    def setUp(self):
        self._engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                                     poolclass=StaticPool)
        Base.metadata.create_all(bind=self._engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        vendedores = RepositorioVendedoresSQL(self.Session)
        vendedores.salvar(Vendedor(1, "Loja A", GRATIS))
        vendedores.salvar(Vendedor(2, "Loja B", GRATIS))
        self.repo = RepositorioDeProdutosSQL(self.Session)

    def tearDown(self):
        self._engine.dispose()

    def contar_publicacoes(self) -> int:
        with self.Session() as session:
            return session.query(models.PublicacaoModel).count()

    def test_salvar_e_ler_com_publicacoes_e_datas_em_utc(self):
        depois = AGORA + timedelta(hours=1)
        salvo = self.repo.salvar(1, produto(), depois)
        lido = self.repo.obter(1, "a_1")
        self.assertEqual(lido, salvo)
        self.assertEqual(lido.publicacoes[0].id_externo, "MLB1")
        self.assertEqual(lido.atualizado_em, depois)
        self.assertEqual(lido.criado_em, AGORA)
        self.assertIs(lido.atualizado_em.tzinfo, UTC)

    def test_put_substitui_campos_e_publicacoes_e_mantem_criado_em(self):
        primeiro = self.repo.salvar(1, produto(), AGORA + timedelta(hours=1))
        novo = replace(primeiro, titulo="Tênis novo", criado_em=AGORA + timedelta(days=9),
                       publicacoes=[Publicacao("shopee", "nao_publicado")])
        segundo = self.repo.salvar(1, novo, AGORA + timedelta(hours=2))
        self.assertEqual(segundo.titulo, "Tênis novo")
        self.assertEqual(segundo.criado_em, AGORA)
        self.assertEqual(segundo.atualizado_em, AGORA + timedelta(hours=2))
        self.assertEqual([p.canal for p in segundo.publicacoes], ["shopee"])
        self.assertEqual(self.contar_publicacoes(), 1)

    def test_versao_antiga_vira_conflito_e_nao_grava(self):
        self.repo.salvar(1, produto(), AGORA + timedelta(hours=1))
        velho = produto(titulo="Outra aba", atualizado_em=AGORA)
        with self.assertRaises(AnuncioDesatualizado):
            self.repo.salvar(1, velho, AGORA + timedelta(hours=2))
        self.assertEqual(self.repo.obter(1, "a_1").titulo, "Tênis de corrida")

    def test_duas_gravacoes_no_mesmo_instante_ainda_mudam_a_versao(self):
        primeiro = self.repo.salvar(1, produto(), AGORA)
        segundo = self.repo.salvar(1, primeiro, AGORA)
        self.assertEqual(segundo.atualizado_em, AGORA + timedelta(milliseconds=1))
        with self.assertRaises(AnuncioDesatualizado):
            self.repo.salvar(1, primeiro, AGORA)

    def test_item_do_canal_ja_usado_por_outro_produto_vira_conflito(self):
        self.repo.salvar(1, produto("a_1"), AGORA)
        with self.assertRaises(AnuncioDesatualizado):
            self.repo.salvar(1, produto("a_2"), AGORA)
        self.assertIsNone(self.repo.obter(1, "a_2"))

    def test_remover_apaga_as_publicacoes(self):
        self.repo.salvar(1, produto(), AGORA)
        self.assertTrue(self.repo.remover(1, "a_1"))
        self.assertIsNone(self.repo.obter(1, "a_1"))
        self.assertEqual(self.contar_publicacoes(), 0)
        self.assertFalse(self.repo.remover(1, "a_1"))

    def test_lista_do_mais_recente_ao_mais_antigo(self):
        self.repo.salvar(1, produto("a_1", publicacoes=[]), AGORA + timedelta(minutes=1))
        self.repo.salvar(1, produto("a_2", publicacoes=[]), AGORA + timedelta(minutes=3))
        self.repo.salvar(1, produto("a_3", publicacoes=[]), AGORA + timedelta(minutes=2))
        self.assertEqual([p.id for p in self.repo.listar(1)], ["a_2", "a_3", "a_1"])

    def test_importar_duas_vezes_grava_um_e_guarda_os_horarios_do_corpo(self):
        self.assertTrue(self.repo.importar(1, produto(minutos=-60)))
        self.assertFalse(self.repo.importar(1, produto(minutos=-60)))
        self.assertEqual(len(self.repo.listar(1)), 1)
        lido = self.repo.obter(1, "a_1")
        self.assertEqual((lido.criado_em, lido.atualizado_em), (AGORA - timedelta(hours=1),) * 2)

    def test_importar_nao_sobrescreve_existente(self):
        self.repo.salvar(1, produto(), AGORA)
        self.assertFalse(self.repo.importar(1, produto(titulo="Do navegador", publicacoes=[])))
        self.assertEqual(self.repo.obter(1, "a_1").titulo, "Tênis de corrida")

    def test_importar_com_item_do_canal_de_outro_produto_nao_duplica(self):
        self.repo.salvar(1, produto("a_1"), AGORA)
        self.assertFalse(self.repo.importar(1, produto("a_2")))
        self.assertIsNone(self.repo.obter(1, "a_2"))
        self.assertTrue(self.repo.importar(2, produto("a_2")))  # o mesmo item em outro vendedor não colide

    def test_outro_vendedor_nao_le_nao_altera_nem_apaga(self):
        self.repo.salvar(1, produto(), AGORA)
        self.assertIsNone(self.repo.obter(2, "a_1"))
        self.assertEqual(self.repo.listar(2), [])
        self.assertFalse(self.repo.remover(2, "a_1"))
        self.repo.salvar(2, produto(titulo="Do B"), AGORA - timedelta(days=1))
        self.assertEqual(self.repo.obter(1, "a_1").titulo, "Tênis de corrida")
        self.assertEqual(self.repo.obter(2, "a_1").titulo, "Do B")

    def test_analise_de_outro_vendedor_vira_nula(self):
        with self.Session() as session:
            session.add(models.AnaliseIAModel(id="an-a", vendedor_id=1, plano_no_momento="gratis", nivel="gratis",
                                              status="pronta", criado_em=AGORA, atualizado_em=AGORA))
            session.commit()
        self.assertEqual(self.repo.salvar(1, produto(analise_id="an-a"), AGORA).analise_id, "an-a")
        self.assertIsNone(self.repo.salvar(2, produto(analise_id="an-a"), AGORA).analise_id)
        self.assertIsNone(self.repo.salvar(1, produto("a_9", analise_id="nao-existe", publicacoes=[]), AGORA)
                          .analise_id)


if __name__ == "__main__":
    unittest.main()
