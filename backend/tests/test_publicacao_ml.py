"""Publicação montada no back: o item do Mercado Livre, as fotos, a descrição e os erros."""

import json
import unittest
from datetime import timedelta

from backend.application.casos_de_uso import ConectarMarketplace
from backend.application.casos_de_uso.publicar_no_mercado_livre import PublicarNoMercadoLivre
from backend.application.ia.escolha import ProvedoresDeIA
from backend.application.ia.modelos import ArquivoDeFoto
from backend.application.portas import FalhaNoMarketplace
from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.domain.erros import FotoInvalida, MercadoLivreDesconectado, PublicacaoRecusada
from backend.domain.plano import GRATIS
from backend.domain.vendedor import Vendedor
from backend.infrastructure.ia.preparador_pillow import PillowPreparador
from backend.tests.test_api_ia import BaseIA, FonteMLFalsa
from backend.tests.test_casos_de_uso import AGORA, GatewayFalso, RepositorioContasEmMemoria, RepositorioVendedoresEmMemoria
from backend.tests.test_provedores_ia import foto_com_detalhes, jpeg

ANUNCIO = {"titulo": "Tênis de corrida Nike azul usado", "descricao": "Tênis usado em bom estado.",
           "preco_centavos": 15990, "estoque": 1, "condicao": "usado", "analise_id": "a1",
           "atributos": [{"chave": "marca", "valor": "Nike"}, {"chave": "numero", "valor": "42"}]}


class PublicadorFalso:
    def __init__(self, erros_ao_publicar=(), erro_na_descricao=None):
        self.imagens, self.itens, self.descricoes = [], [], []
        self._erros = list(erros_ao_publicar)
        self._erro_na_descricao = erro_na_descricao

    def subir_imagem(self, token, conteudo, nome="foto.jpg"):
        self.imagens.append(nome)
        return f"IMG{len(self.imagens)}"

    def publicar_anuncio(self, token, dados):
        self.itens.append(dados)
        if self._erros:
            raise self._erros.pop(0)
        return {"id": "MLB123", "permalink": "https://produto.mercadolivre.com.br/MLB123", "status": "active"}

    def gravar_descricao(self, token, item_id, texto):
        if self._erro_na_descricao:
            raise self._erro_na_descricao
        self.descricoes.append((item_id, texto))


class AnalisesFalsas:
    def __init__(self, analises):
        self._analises = analises

    def obter(self, analise_id):
        return self._analises.get(analise_id)


def caso(publicador=None, conectado=True, analises=None):
    contas = RepositorioContasEmMemoria()
    if conectado:
        contas.salvar(ContaVinculada(1, "mercado-livre", AGORA, CredenciaisOAuth("tok", "ref", AGORA + timedelta(days=3650))))
    conectar = ConectarMarketplace(RepositorioVendedoresEmMemoria(Vendedor(1, "Loja", GRATIS)), contas,
                                   {"mercado-livre": GatewayFalso()})
    analises = analises if analises is not None else {"a1": {"vendedor_id": 1, "leitura": {"ml": {
        "categoria_id": "MLB23262", "mapa": {"numero": "SIZE"}, "obrigatorios": ["SIZE"]}}}}
    publicador = publicador or PublicadorFalso()
    return PublicarNoMercadoLivre(conectar, publicador, FonteMLFalsa(), AnalisesFalsas(analises), PillowPreparador()), publicador


def fotos(quantas=2):
    return [ArquivoDeFoto(f"f{i}.jpg", jpeg(foto_com_detalhes())) for i in range(quantas)]


class TestPublicarNoMercadoLivre(unittest.TestCase):
    def test_monta_o_item_sobe_as_fotos_e_grava_a_descricao(self):
        publicar, publicador = caso()
        resultado = publicar.executar(1, ANUNCIO, fotos())
        self.assertEqual(resultado["id"], "MLB123")
        item = publicador.itens[0]
        self.assertEqual((item["category_id"], item["currency_id"], item["listing_type_id"], item["condition"]),
                         ("MLB23262", "BRL", "gold_special", "used"))
        self.assertEqual((item["price"], item["available_quantity"], item["buying_mode"]), (159.9, 1, "buy_it_now"))
        self.assertEqual(item["pictures"], [{"id": "IMG1"}, {"id": "IMG2"}])
        self.assertEqual({a["id"]: a["value_name"] for a in item["attributes"]}, {"BRAND": "Nike", "SIZE": "42"})
        self.assertEqual(publicador.descricoes, [("MLB123", "Tênis usado em bom estado.")])

    def test_analise_de_outro_vendedor_nao_empresta_a_categoria(self):
        publicar, publicador = caso(analises={"a1": {"vendedor_id": 2, "leitura": {"ml": {"categoria_id": "MLB999"}}}})
        publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual(publicador.itens[0]["category_id"], "MLB23262")  # veio da descoberta pelo título

    def test_sem_mercado_livre_conectado(self):
        publicar, _ = caso(conectado=False)
        with self.assertRaises(MercadoLivreDesconectado):
            publicar.executar(1, ANUNCIO, fotos(1))

    def test_categoria_do_modelo_novo_pede_family_name(self):
        erro = FalhaNoMarketplace("400", 400, {"cause": [{"code": "item.family_name.missing"}]})
        publicar, publicador = caso(PublicadorFalso(erros_ao_publicar=[erro]))
        publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual(publicador.itens[1]["family_name"], ANUNCIO["titulo"])

    def test_recusa_do_mercado_livre_traz_as_causas(self):
        erro = FalhaNoMarketplace("400", 400, {"message": "validation", "cause": [{"message": "Price too low"}]})
        publicar, _ = caso(PublicadorFalso(erros_ao_publicar=[erro]))
        with self.assertRaises(PublicacaoRecusada) as recusa:
            publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual(recusa.exception.detalhes, ["Price too low"])

    def test_descricao_que_nao_entrou_vira_aviso(self):
        publicar, _ = caso(PublicadorFalso(erro_na_descricao=FalhaNoMarketplace("500", 500)))
        resultado = publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual([a["codigo"] for a in resultado["avisos"]], ["descricao_nao_gravada"])

    def test_validacoes(self):
        publicar, _ = caso()
        with self.assertRaises(FotoInvalida):
            publicar.executar(1, ANUNCIO, [])
        with self.assertRaises(ValueError):
            publicar.executar(1, {**ANUNCIO, "preco_centavos": 50}, fotos(1))
        with self.assertRaises(ValueError):
            publicar.executar(1, {**ANUNCIO, "titulo": " "}, fotos(1))


class TestRotaDePublicacao(BaseIA):
    def setUp(self):
        self.montar(ProvedoresDeIA())

    def test_sem_mercado_livre_conectado_responde_409(self):
        resposta = self.cliente.post("/api/anuncios/publicar/mercado-livre", data={"anuncio": json.dumps(ANUNCIO)},
                                     files=self.fotos(1))
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (409, "mercado_livre_desconectado"))

    def test_anuncio_que_nao_e_json(self):
        resposta = self.cliente.post("/api/anuncios/publicar/mercado-livre", data={"anuncio": "{"}, files=self.fotos(1))
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (400, "parametro_invalido"))


if __name__ == "__main__":
    unittest.main()
