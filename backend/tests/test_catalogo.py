"""Catálogo de marketplaces: disponíveis, em breve e as mensagens de erro."""

import unittest

from backend.domain.erros import MarketplaceEmBreve, MarketplaceNaoEncontrado
from backend.domain.marketplace import CATALOGO, StatusMarketplace, obter_marketplace, obter_marketplace_disponivel
from backend.tests.test_plano import FORA_DA_REGRA


class TestCatalogo(unittest.TestCase):
    def test_disponiveis_sao_mercado_livre_shopee_e_amazon(self):
        disponiveis = [m.nome for m in CATALOGO if m.status is StatusMarketplace.DISPONIVEL]
        self.assertEqual(disponiveis, ["Mercado Livre", "Shopee", "Amazon"])

    def test_em_breve(self):
        em_breve = [m.nome for m in CATALOGO if m.status is StatusMarketplace.EM_BREVE]
        self.assertEqual(em_breve, ["Magalu", "Americanas", "Casas Bahia", "Shein", "TikTok Shop", "AliExpress"])

    def test_slugs_unicos(self):
        slugs = [m.slug for m in CATALOGO]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_obter_marketplace_disponivel(self):
        self.assertEqual(obter_marketplace_disponivel("shopee").nome, "Shopee")

    def test_em_breve_nao_conecta_e_explica(self):
        with self.assertRaises(MarketplaceEmBreve) as contexto:
            obter_marketplace_disponivel("shein")
        self.assertEqual(contexto.exception.codigo, "marketplace_em_breve")
        self.assertEqual(
            contexto.exception.mensagem,
            "A integração com Shein ainda está chegando. Por enquanto dá pra conectar Mercado Livre, Shopee e Amazon.",
        )

    def test_inexistente(self):
        for funcao in (obter_marketplace, obter_marketplace_disponivel):
            with self.subTest(funcao=funcao.__name__), self.assertRaises(MarketplaceNaoEncontrado):
                funcao("orkut")

    def test_mensagens_seguem_a_regra_de_escrita(self):
        mensagens = [MarketplaceNaoEncontrado("x").mensagem]
        for marketplace in CATALOGO:
            if not marketplace.disponivel:
                with self.assertRaises(MarketplaceEmBreve) as contexto:
                    obter_marketplace_disponivel(marketplace.slug)
                mensagens.append(contexto.exception.mensagem)
        for mensagem in mensagens:
            with self.subTest(mensagem=mensagem):
                self.assertIsNone(FORA_DA_REGRA.search(mensagem))


if __name__ == "__main__":
    unittest.main()
