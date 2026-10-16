"""Casos de uso de conectar e desconectar marketplaces, com repositórios e gateways falsos em memória."""

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from backend.application.casos_de_uso import (
    ConectarMarketplace,
    DesconectarMarketplace,
    ListarMarketplaces,
    ObterVendedorAtual,
)
from backend.domain.conta_vinculada import CredenciaisOAuth
from backend.domain.erros import (
    LimiteDoPlanoAtingido,
    MarketplaceEmBreve,
    MarketplaceNaoEncontrado,
    VendedorNaoEncontrado,
)
from backend.domain.marketplace import Marketplace, StatusMarketplace
from backend.domain.plano import BUSINESS, ESSENCIAL, GRATIS, PRO
from backend.domain.vendedor import Vendedor

AGORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
VENDEDOR_ID = 1

CATALOGO_TESTE: tuple[Marketplace, ...] = (
    Marketplace("mercado-livre", "Mercado Livre", StatusMarketplace.DISPONIVEL),
    Marketplace("shopee", "Shopee", StatusMarketplace.DISPONIVEL),
    Marketplace("amazon", "Amazon", StatusMarketplace.DISPONIVEL),
    Marketplace("magalu", "Magalu", StatusMarketplace.EM_BREVE),
    Marketplace("americanas", "Americanas", StatusMarketplace.EM_BREVE),
    Marketplace("casas-bahia", "Casas Bahia", StatusMarketplace.EM_BREVE),
    Marketplace("shein", "Shein", StatusMarketplace.EM_BREVE),
    Marketplace("tiktok-shop", "TikTok Shop", StatusMarketplace.EM_BREVE),
    Marketplace("aliexpress", "AliExpress", StatusMarketplace.EM_BREVE),
)


class RepositorioVendedoresEmMemoria:
    def __init__(self, *vendedores: Vendedor):
        self._dados = {vendedor.id: vendedor for vendedor in vendedores}

    def obter(self, vendedor_id):
        return self._dados.get(vendedor_id)

    def salvar(self, vendedor):
        self._dados[vendedor.id] = vendedor


class RepositorioContasEmMemoria:
    def __init__(self):
        self._dados = {}

    def listar_do_vendedor(self, vendedor_id):
        return [conta for (dono, _), conta in self._dados.items() if dono == vendedor_id]

    def buscar(self, vendedor_id, marketplace):
        return self._dados.get((vendedor_id, marketplace))

    def salvar(self, conta):
        self._dados[(conta.vendedor_id, conta.marketplace)] = conta

    def remover(self, vendedor_id, marketplace):
        self._dados.pop((vendedor_id, marketplace), None)


class GatewayFalso:
    """Anota o que o caso de uso pediu, na ordem do OAuth 2.0."""

    def __init__(self):
        self.chamadas = []

    def gerar_url_autorizacao(self, estado):
        self.chamadas.append(("url", estado))
        return f"https://marketplace.exemplo/autorizar?state={estado}"

    def trocar_codigo_por_token(self, codigo):
        self.chamadas.append(("token", codigo))
        return CredenciaisOAuth("token_de_acesso", "token_de_renovacao", AGORA + timedelta(hours=6))

    def renovar_token(self, refresh_token):
        raise AssertionError("conectar não renova token")

    def obter_perfil_usuario(self, access_token):
        return {"id": "123", "nickname": "LOJA_TESTE"}

    def listar_anuncios(self, access_token, conta_externa_id=None):
        return []

    def publicar_anuncio(self, access_token, dados_produto):
        return {"id": "MLB123", "title": dados_produto.get("title", "")}


class BaseCasosDeUso(unittest.TestCase):
    def setUp(self):
        self._patcher = patch("backend.domain.marketplace.CATALOGO", CATALOGO_TESTE)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def montar(self, plano):
        self.contas = RepositorioContasEmMemoria()
        self.vendedores = RepositorioVendedoresEmMemoria(Vendedor(VENDEDOR_ID, "Loja de teste", plano))
        self.gateways = {slug: GatewayFalso() for slug in ("mercado-livre", "shopee", "amazon")}
        self.conectar = ConectarMarketplace(self.vendedores, self.contas, self.gateways, agora=lambda: AGORA)
        self.desconectar = DesconectarMarketplace(self.contas)

    def conectados(self):
        return sorted(conta.marketplace for conta in self.contas.listar_do_vendedor(VENDEDOR_ID))


class TestConectarMarketplace(BaseCasosDeUso):
    def test_conecta_um_marketplace_disponivel(self):
        self.montar(GRATIS)
        resultado = self.conectar.executar(VENDEDOR_ID, "mercado-livre", codigo_autorizacao="codigo_oauth")

        self.assertTrue(resultado.conectado)
        self.assertEqual(resultado.marketplace.nome, "Mercado Livre")
        self.assertEqual(resultado.conta.conectada_em, AGORA)
        self.assertEqual(self.conectados(), ["mercado-livre"])

    def test_troca_codigo_por_token(self):
        self.montar(GRATIS)
        self.conectar.executar(VENDEDOR_ID, "shopee", codigo_autorizacao="codigo_oauth")

        chamadas = self.gateways["shopee"].chamadas
        self.assertEqual([tipo for tipo, _ in chamadas], ["token"])
        self.assertEqual(chamadas[0][1], "codigo_oauth")

    def test_gratis_nao_conecta_o_segundo_marketplace(self):
        self.montar(GRATIS)
        self.conectar.executar(VENDEDOR_ID, "mercado-livre", codigo_autorizacao="codigo_oauth")

        with self.assertRaises(LimiteDoPlanoAtingido) as contexto:
            self.conectar.executar(VENDEDOR_ID, "shopee", codigo_autorizacao="codigo_oauth")

        self.assertEqual(contexto.exception.plano_sugerido, PRO)
        self.assertIn("plano Pro", contexto.exception.mensagem)
        self.assertEqual(self.conectados(), ["mercado-livre"])
        self.assertEqual(self.gateways["shopee"].chamadas, [], "não pode nem começar a autorização")

    def test_essencial_tambem_conecta_um_so(self):
        self.montar(ESSENCIAL)
        self.conectar.executar(VENDEDOR_ID, "amazon", codigo_autorizacao="codigo_oauth")
        with self.assertRaises(LimiteDoPlanoAtingido):
            self.conectar.executar(VENDEDOR_ID, "mercado-livre", codigo_autorizacao="codigo_oauth")

    def test_pro_e_business_conectam_os_tres(self):
        for plano in (PRO, BUSINESS):
            with self.subTest(plano=plano.nome):
                self.montar(plano)
                for slug in ("mercado-livre", "shopee", "amazon"):
                    self.conectar.executar(VENDEDOR_ID, slug, codigo_autorizacao="codigo_oauth")
                self.assertEqual(self.conectados(), ["amazon", "mercado-livre", "shopee"])

    def test_conectar_de_novo_nao_duplica_nem_ocupa_outra_vaga(self):
        self.montar(GRATIS)
        primeira = self.conectar.executar(VENDEDOR_ID, "mercado-livre", codigo_autorizacao="codigo_oauth")
        segunda = self.conectar.executar(VENDEDOR_ID, "mercado-livre", codigo_autorizacao="codigo_oauth")

        self.assertEqual(primeira.conta, segunda.conta)
        self.assertEqual(self.conectados(), ["mercado-livre"])
        self.assertEqual(len(self.gateways["mercado-livre"].chamadas), 1, "só a primeira vez troca o token")

    def test_marketplace_em_breve_nao_conecta(self):
        self.montar(BUSINESS)
        with self.assertRaises(MarketplaceEmBreve):
            self.conectar.executar(VENDEDOR_ID, "tiktok-shop", codigo_autorizacao="codigo_oauth")
        self.assertEqual(self.conectados(), [])

    def test_marketplace_inexistente(self):
        self.montar(BUSINESS)
        with self.assertRaises(MarketplaceNaoEncontrado):
            self.conectar.executar(VENDEDOR_ID, "orkut", codigo_autorizacao="codigo_oauth")

    def test_vendedor_inexistente(self):
        self.montar(GRATIS)
        with self.assertRaises(VendedorNaoEncontrado):
            self.conectar.executar(99, "shopee", codigo_autorizacao="codigo_oauth")


class TestDesconectarMarketplace(BaseCasosDeUso):
    def test_desconecta(self):
        self.montar(GRATIS)
        self.conectar.executar(VENDEDOR_ID, "mercado-livre", codigo_autorizacao="codigo_oauth")

        resultado = self.desconectar.executar(VENDEDOR_ID, "mercado-livre")

        self.assertFalse(resultado.conectado)
        self.assertEqual(self.conectados(), [])

    def test_desconectar_libera_a_vaga_do_plano(self):
        self.montar(GRATIS)
        self.conectar.executar(VENDEDOR_ID, "mercado-livre", codigo_autorizacao="codigo_oauth")
        self.desconectar.executar(VENDEDOR_ID, "mercado-livre")

        self.conectar.executar(VENDEDOR_ID, "shopee", codigo_autorizacao="codigo_oauth")
        self.assertEqual(self.conectados(), ["shopee"])

    def test_desconectar_o_que_nao_esta_conectado_nao_da_erro(self):
        self.montar(GRATIS)
        resultado = self.desconectar.executar(VENDEDOR_ID, "amazon")
        self.assertFalse(resultado.conectado)

    def test_desconectar_marketplace_inexistente(self):
        self.montar(GRATIS)
        with self.assertRaises(MarketplaceNaoEncontrado):
            self.desconectar.executar(VENDEDOR_ID, "orkut")


class TestConsultas(BaseCasosDeUso):
    def test_lista_o_catalogo_inteiro_marcando_o_que_esta_conectado(self):
        self.montar(GRATIS)
        self.conectar.executar(VENDEDOR_ID, "shopee", codigo_autorizacao="codigo_oauth")

        itens = ListarMarketplaces(self.contas).executar(VENDEDOR_ID)

        self.assertEqual(len(itens), 9)
        self.assertEqual([item.marketplace.slug for item in itens if item.conectado], ["shopee"])

    def test_resumo_do_vendedor_mostra_o_uso_do_plano(self):
        self.montar(GRATIS)
        obter = ObterVendedorAtual(self.vendedores, self.contas)

        antes = obter.executar(VENDEDOR_ID)
        self.conectar.executar(VENDEDOR_ID, "amazon", codigo_autorizacao="codigo_oauth")
        depois = obter.executar(VENDEDOR_ID)

        self.assertEqual((antes.marketplaces_conectados, antes.pode_conectar_mais), (0, True))
        self.assertEqual((depois.marketplaces_conectados, depois.pode_conectar_mais), (1, False))
        self.assertEqual(depois.plano_para_mais_marketplaces, PRO)


if __name__ == "__main__":
    unittest.main()
