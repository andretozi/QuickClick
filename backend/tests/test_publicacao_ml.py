"""Publicação montada no back: o item do Mercado Livre, as fotos, a descrição, a gestão e os erros."""

import io
import json
import unittest
from datetime import timedelta

from PIL import Image

from backend.application.casos_de_uso import ConectarMarketplace
from backend.application.casos_de_uso.publicar_no_mercado_livre import PublicarNoMercadoLivre
from backend.application.ia.escolha import ProvedoresDeIA
from backend.application.ia.modelos import ArquivoDeFoto
from backend.application.portas import FalhaNoMarketplace
from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.domain.erros import (
    AnuncioNaoEncontrado,
    FotoInvalida,
    MercadoLivreDesconectado,
    PublicacaoRecusada,
)
from backend.domain.ia.atributos_ml import AtributoML, completar_para_publicacao, ligar_confirmados
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
    def __init__(self, erros_ao_publicar=(), erro_na_descricao=None, seller_id="1001", erros_ao_subir_imagem=()):
        self.imagens, self.itens, self.descricoes = [], [], []
        self.conteudos_imagens = []
        self.atualizacoes, self.excluidos = [], []
        self._erros = list(erros_ao_publicar)
        self._erros_imagem = list(erros_ao_subir_imagem)
        self._erro_na_descricao = erro_na_descricao
        self._armazenados = {
            "MLB123456": {
                "id": "MLB123456",
                "title": "Tênis de corrida Nike azul usado",
                "family_name": None,
                "description": "Tênis usado em bom estado.",
                "price": 159.9,
                "status": "active",
                "condition": "used",
                "available_quantity": 1,
                "sold_quantity": 0,
                "category_id": "MLB23262",
                "permalink": "https://produto.mercadolivre.com.br/MLB123456",
                "thumbnail": "https://http2.mlstatic.com/D_1.jpg",
                "pictures": ["https://http2.mlstatic.com/D_1.jpg"],
                "attributes": [{"id": "BRAND", "name": "Marca", "value": "Nike"}],
                "health": 0.85,
                "seller_id": seller_id,
                "tags": ["good_quality_thumbnail"],
                "last_updated": None,
            }
        }

    def subir_imagem(self, token, conteudo, nome="foto.jpg"):
        self.conteudos_imagens.append((nome, conteudo))
        if self._erros_imagem:
            erro = self._erros_imagem.pop(0)
            if erro is not None:
                raise erro
        self.imagens.append(nome)
        return f"IMG{len(self.imagens)}"

    def publicar_anuncio(self, token, dados):
        self.itens.append(dados)
        if self._erros:
            raise self._erros.pop(0)
        return {"id": "MLB123456", "permalink": "https://produto.mercadolivre.com.br/MLB123456", "status": "active"}

    def gravar_descricao(self, token, item_id, texto):
        if self._erro_na_descricao:
            raise self._erro_na_descricao
        self.descricoes.append((item_id, texto))

    def obter_anuncio(self, token, item_id):
        if item_id not in self._armazenados:
            raise FalhaNoMarketplace("404", 404, {"message": "not_found"})
        return dict(self._armazenados[item_id])

    def atualizar_anuncio(self, token, item_id, campos):
        self.atualizacoes.append((item_id, dict(campos)))
        atual = self._armazenados[item_id]
        atual.update(campos)
        return dict(atual)

    def atualizar_descricao(self, token, item_id, texto):
        if self._erro_na_descricao:
            raise self._erro_na_descricao
        self.descricoes.append((item_id, texto))
        self._armazenados[item_id]["description"] = texto

    def excluir_anuncio(self, token, item_id):
        self.excluidos.append(item_id)
        self._armazenados.pop(item_id, None)


class AnalisesFalsas:
    def __init__(self, analises):
        self._analises = analises

    def obter(self, analise_id):
        return self._analises.get(analise_id)


def caso(publicador=None, conectado=True, analises=None, conta_externa="1001"):
    contas = RepositorioContasEmMemoria()
    if conectado:
        contas.salvar(ContaVinculada(
            1, "mercado-livre", AGORA,
            CredenciaisOAuth("tok", "ref", AGORA + timedelta(days=3650), conta_externa_id=conta_externa),
        ))
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
        self.assertEqual(resultado["id"], "MLB123456")
        item = publicador.itens[0]
        self.assertEqual((item["category_id"], item["currency_id"], item["listing_type_id"], item["condition"]),
                         ("MLB23262", "BRL", "gold_special", "used"))
        self.assertEqual((item["price"], item["available_quantity"], item["buying_mode"]), (159.9, 1, "buy_it_now"))
        self.assertEqual(item["pictures"], [{"id": "IMG1"}, {"id": "IMG2"}])
        self.assertEqual({a["id"]: a["value_name"] for a in item["attributes"]}, {"BRAND": "Nike", "SIZE": "42"})
        self.assertEqual(publicador.descricoes, [("MLB123456", "Tênis usado em bom estado.")])

    def test_reenvia_foto_ampliada_quando_mercado_livre_recusa_por_bordas_brancas(self):
        erro_borda = FalhaNoMarketplace(
            "400",
            400,
            {
                "message": (
                    "Asegúrate de que la imagen tenga como mínimo 500 píxeles en uno de los lados. "
                    "La imagen subida, procesados los bordes blancos, tiene un tamaño de 447px x 447px"
                )
            },
        )
        publicador = PublicadorFalso(erros_ao_subir_imagem=[None, erro_borda, None])
        publicar, _ = caso(publicador)
        resultado = publicar.executar(1, ANUNCIO, fotos(2))
        self.assertEqual(resultado["id"], "MLB123456")
        self.assertEqual(publicador.imagens, ["foto1.jpg", "foto2.jpg"])
        self.assertEqual(len(publicador.conteudos_imagens), 3)
        with Image.open(io.BytesIO(publicador.conteudos_imagens[-1][1])) as reenviada:
            self.assertGreaterEqual(min(reenviada.size), 1200)
            self.assertGreaterEqual(max(reenviada.size), 1600)

    def test_analise_de_outro_vendedor_nao_empresta_a_categoria(self):
        publicar, publicador = caso(analises={"a1": {"vendedor_id": 2, "leitura": {"ml": {"categoria_id": "MLB999"}}}})
        publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual(publicador.itens[0]["category_id"], "MLB23262")  # veio da descoberta pelo título

    def test_sem_mercado_livre_conectado(self):
        publicar, _ = caso(conectado=False)
        with self.assertRaises(MercadoLivreDesconectado):
            publicar.executar(1, ANUNCIO, fotos(1))

    def test_categoria_do_modelo_novo_pede_family_name_sem_title(self):
        erro = FalhaNoMarketplace("400", 400, {"cause": [{"code": "item.family_name.missing"}]})
        publicar, publicador = caso(PublicadorFalso(erros_ao_publicar=[erro]))
        publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual(publicador.itens[1]["family_name"], ANUNCIO["titulo"])
        self.assertNotIn("title", publicador.itens[1])

    def test_completa_atributos_obrigatorios_de_qualidade_e_do_titulo_na_publicacao(self):
        da_categoria = [
            AtributoML("BRAND", "Marca", False),
            AtributoML("MANUFACTURER", "Fabricante", True),
            AtributoML("MODEL", "Modelo", True),
            AtributoML("MATERIAL", "Material", True, (("2282603", "Cerâmica"), ("2431731", "Vidro"))),
            AtributoML("COLOR", "Cor", False, (("52055", "Branco"), ("52049", "Preto"))),
            AtributoML("SALE_FORMAT", "Formato de venda", False, (("1359391", "Unidade"), ("1359392", "Kit"))),
            AtributoML("UNITS_PER_PACK", "Unidades por embalagem", False),
            AtributoML("IS_SET", "É kit", False, (("242084", "Não"), ("242085", "Sim"))),
            AtributoML("VOLUME_CAPACITY", "Capacidade em volume", False, (), "mL"),
            AtributoML("EMPTY_GTIN_REASON", "Motivo de GTIN vazio", False,
                       (("17055160", "O produto não tem código cadastrado"),)),
        ]
        ligados = completar_para_publicacao(
            ligar_confirmados([("quantidade", "1 unidade")], da_categoria, {}),
            da_categoria,
            "Caneca Branca de Cerâmica 250ml Acabamento Brilhante",
        )
        por_id = {l.id: l.para_api() for l in ligados}
        self.assertEqual(por_id["BRAND"], {"id": "BRAND", "value_name": "Genérica"})
        self.assertEqual(por_id["MANUFACTURER"], {"id": "MANUFACTURER", "value_name": "Genérica"})
        self.assertEqual(por_id["MODEL"], {"id": "MODEL", "value_name": "Caneca"})
        self.assertEqual(por_id["MATERIAL"], {"id": "MATERIAL", "value_id": "2282603"})
        self.assertEqual(por_id["COLOR"], {"id": "COLOR", "value_id": "52055"})
        self.assertEqual(por_id["SALE_FORMAT"], {"id": "SALE_FORMAT", "value_id": "1359391"})
        self.assertEqual(por_id["UNITS_PER_PACK"], {"id": "UNITS_PER_PACK", "value_name": "1"})
        self.assertEqual(por_id["IS_SET"], {"id": "IS_SET", "value_id": "242084"})
        self.assertEqual(por_id["VOLUME_CAPACITY"], {"id": "VOLUME_CAPACITY", "value_name": "250 mL"})
        self.assertEqual(por_id["EMPTY_GTIN_REASON"], {"id": "EMPTY_GTIN_REASON", "value_id": "17055160"})

        ligados_kit = completar_para_publicacao(
            ligar_confirmados([("quantidade", "2 unidades")], da_categoria, {}),
            da_categoria,
            "Caneca Branca de Cerâmica 250ml",
        )
        por_id_kit = {l.id: l.para_api() for l in ligados_kit}
        self.assertEqual(por_id_kit["SALE_FORMAT"], {"id": "SALE_FORMAT", "value_id": "1359392"})
        self.assertEqual(por_id_kit["UNITS_PER_PACK"], {"id": "UNITS_PER_PACK", "value_name": "2"})
        self.assertEqual(por_id_kit["IS_SET"], {"id": "IS_SET", "value_id": "242085"})

    def test_pausar_reativar_atualizar_e_excluir_anuncio(self):
        publicar, publicador = caso()
        pausado = publicar.alterar_status(1, "MLB123456", "pausado")
        self.assertEqual(pausado["status"], "paused")
        reativado = publicar.alterar_status(1, "MLB123456", "publicado")
        self.assertEqual(reativado["status"], "active")

        editado = publicar.atualizar(
            1,
            "MLB123456",
            {
                **ANUNCIO,
                "preco_centavos": 19990,
                "estoque": 4,
                "descricao": "Descrição atualizada.",
                "fotos_mantidas": ["https://http2.mlstatic.com/D_1.jpg", "http://malicioso.local/x.jpg"],
            },
            fotos(1),
        )
        self.assertEqual(editado["price"], 199.9)
        self.assertEqual(editado["available_quantity"], 4)
        self.assertEqual(editado["description"], "Descrição atualizada.")
        ultima_atualizacao = publicador.atualizacoes[-1][1]
        self.assertEqual(ultima_atualizacao["pictures"], [
            {"source": "https://http2.mlstatic.com/D_1.jpg"},
            {"id": "IMG1"},
        ])

        excluido = publicar.excluir(1, "MLB123456")
        self.assertTrue(excluido["excluido"])
        self.assertEqual(publicador.excluidos, ["MLB123456"])

    def test_impede_acesso_a_anuncio_de_outro_vendedor_ou_id_invalido(self):
        publicar, _ = caso(PublicadorFalso(seller_id="9999"), conta_externa="1001")
        with self.assertRaises(AnuncioNaoEncontrado):
            publicar.obter(1, "MLB123456")
        with self.assertRaises(AnuncioNaoEncontrado):
            publicar.excluir(1, "MLB123456")
        with self.assertRaises(ValueError):
            publicar.obter(1, "../../etc/passwd")

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
