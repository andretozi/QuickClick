"""Shopee sem rede: assinatura, cliente assinado, fonte de esquema e publicador, com transporte HTTP falso."""

import json
import socket
import unittest
from datetime import UTC, datetime
from pathlib import Path

import httpx

from backend.application.ia.modelos import CategoriaSugerida
from backend.application.portas import FalhaNoMarketplace
from backend.domain.canais.esquema import CampoDoCanal, TipoDeCampo
from backend.domain.erros import CamposObrigatoriosFaltando, ServicoIndisponivel
from backend.domain.produto import Produto
from backend.infrastructure.configuracao import POR_NOME, LeitorDeConfiguracao
from backend.infrastructure.marketplaces.esquema_shopee import CAMPOS_FIXOS, FonteDeEsquemaShopee, esquema_da_shopee
from backend.infrastructure.marketplaces.publicador_shopee import PublicadorShopee
from backend.infrastructure.marketplaces.shopee import ClienteShopee, assinar, cliente_shopee_da_configuracao
from backend.tests.test_plano import FORA_DA_REGRA

PARTNER_ID, PARTNER_KEY, TOKEN, LOJA, TS = "2001887", "chave_de_teste_da_shopee", "token_de_teste", "600000", 1655714431
CAMINHO_LOJA = "/api/v2/product/add_item"
SIGN_LOJA = "ab9fbd6b6ca6b16397dc128c200a2541e7e043bf1b0f0af6caf8d5d8edca4604"


class RedeBloqueada(OSError):
    pass


def _sem_rede(*args, **kwargs):
    raise RedeBloqueada("teste da Shopee tentou sair para a rede")


_originais: dict = {}


def setUpModule():
    _originais.update(connect=vars(socket.socket).get("connect"), getaddrinfo=socket.getaddrinfo)
    socket.socket.connect = _sem_rede
    socket.getaddrinfo = _sem_rede


def tearDownModule():
    if _originais["connect"] is None:
        del socket.socket.connect
    else:
        socket.socket.connect = _originais["connect"]
    socket.getaddrinfo = _originais["getaddrinfo"]


class Transporte:
    """Responde em ordem: dict = 200 com JSON; (status, corpo); exceção = levanta. Guarda os pedidos."""

    def __init__(self, *respostas):
        self.respostas, self.pedidos = list(respostas) or [{"error": "", "response": {}}], []

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(pedido)
        resposta = self.respostas.pop(0) if len(self.respostas) > 1 else self.respostas[0]
        if isinstance(resposta, Exception):
            raise resposta
        status, corpo = resposta if isinstance(resposta, tuple) else (200, resposta)
        return httpx.Response(status, json=corpo) if isinstance(corpo, dict) else httpx.Response(status, text=corpo)


def http(transporte):
    return httpx.Client(transport=httpx.MockTransport(transporte))


def cliente(transporte, partner_id=PARTNER_ID, partner_key=PARTNER_KEY, relogio=lambda: TS):
    return ClienteShopee(partner_id, partner_key, host="https://shopee.teste", client=http(transporte), relogio=relogio)


ATRIBUTOS = [
    {"attribute_id": 100010, "name": "Cor", "is_mandatory": True,
     "attribute_value_list": [{"value_id": 1, "name": "Azul"}, {"value_id": 2, "name": "Verde"}],
     "attribute_info": {"input_validation_type": "STRING_TYPE"}},
    {"attribute_id": 100020, "name": "Capacidade", "is_mandatory": False, "attribute_value_list": [],
     "attribute_info": {"input_validation_type": "INT_TYPE", "attribute_unit_list": ["ml", "l"]}},
    {"attribute_id": 100017, "name": "Tipo de garantia", "is_mandatory": True,
     "attribute_info": {"input_validation_type": "STRING_TYPE"}},
    {"attribute_id": 100030, "name": "Material", "mandatory": False, "attribute_info": {}},
]
RESPOSTA_ATRIBUTOS = {"error": "", "response": {"list": [{"category_id": 100182, "attribute_tree": ATRIBUTOS}]}}
AGORA = datetime(2026, 10, 30, tzinfo=UTC)
PRODUTO = Produto(id="p1", titulo="Tênis de corrida azul", descricao="Leve e confortável.", categoria="calcados",
                  condicao="novo", preco_centavos=19990, preco_sugerido_centavos=None, estoque=3, fotos=[], capa=0,
                  atributos=[], analise_id=None, criado_em=AGORA, atualizado_em=AGORA)
RESPOSTAS = {"cor": "azul", "capacidade": "500 ml", "100017": "Garantia do fabricante", "marca": "Olympikus",
             "peso_g": "350", "comprimento_cm": "30,5", "largura_cm": "20", "altura_cm": "12"}


class TestTravaDeRede(unittest.TestCase):
    def test_a_trava_de_rede_esta_ativa(self):
        with self.assertRaises(RedeBloqueada):
            socket.getaddrinfo("partner.shopeemobile.com", 443)
        with socket.socket() as s, self.assertRaises(RedeBloqueada):
            s.connect(("127.0.0.1", 9))
        # Sem transporte falso, o cliente cai na trava (host .invalid: nem com a trava quebrada sairia)
        real = ClienteShopee(PARTNER_ID, PARTNER_KEY, host="https://shopee.invalid", relogio=lambda: TS)
        with self.assertRaises(FalhaNoMarketplace):
            real.get("/api/v2/shop/get_shop_info", access_token=TOKEN, shop_id=LOJA)


class TestAssinatura(unittest.TestCase):
    def test_vetor_da_chamada_publica(self):
        self.assertEqual(assinar(PARTNER_KEY, PARTNER_ID, "/api/v2/auth/token/get", TS),
                         "d90dcebee6a5b56f78b75bac879fbcb7a7bc8df7fc1c2b06121421d5d465c30d")

    def test_vetor_da_chamada_da_loja(self):
        self.assertEqual(assinar(PARTNER_KEY, PARTNER_ID, CAMINHO_LOJA, TS, TOKEN, LOJA), SIGN_LOJA)


class TestClienteShopee(unittest.TestCase):
    def test_chamada_da_loja_leva_parametros_assinados(self):
        transporte = Transporte()
        cliente(transporte).get(CAMINHO_LOJA, {"offset": 0}, access_token=TOKEN, shop_id=LOJA)
        pedido = transporte.pedidos[0]
        self.assertEqual((pedido.method, pedido.url.host, pedido.url.path), ("GET", "shopee.teste", CAMINHO_LOJA))
        self.assertEqual(dict(pedido.url.params), {"offset": "0", "partner_id": PARTNER_ID, "timestamp": str(TS),
                                                   "sign": SIGN_LOJA, "access_token": TOKEN, "shop_id": LOJA})

    def test_chamada_publica_vai_sem_token_e_sem_loja(self):
        transporte = Transporte()
        cliente(transporte).post("/api/v2/auth/token/get", json={"code": "abc"})
        pedido = transporte.pedidos[0]
        self.assertEqual(dict(pedido.url.params), {"partner_id": PARTNER_ID, "timestamp": str(TS),
                                                   "sign": assinar(PARTNER_KEY, PARTNER_ID, "/api/v2/auth/token/get", TS)})
        self.assertEqual(json.loads(pedido.content), {"code": "abc"})

    def test_post_multipart(self):
        transporte = Transporte()
        cliente(transporte).post("/api/v2/media_space/upload_image", files={"image": ("a.jpg", b"JPEGFALSO", "image/jpeg")})
        pedido = transporte.pedidos[0]
        self.assertTrue(pedido.headers["content-type"].startswith("multipart/form-data"))
        self.assertIn(b"JPEGFALSO", pedido.read())

    def test_sem_credencial_recusa_antes_de_montar_a_url_e_sem_rede(self):
        for partner_id, partner_key in (("", PARTNER_KEY), (PARTNER_ID, ""), (None, None), ("  ", " ")):
            with self.subTest(partner_id=partner_id, partner_key=partner_key):
                transporte, relogio = Transporte(), []
                sem = cliente(transporte, partner_id, partner_key, relogio=lambda: relogio.append(1) or TS)
                with self.assertRaises(ServicoIndisponivel):
                    sem.get(CAMINHO_LOJA, access_token=TOKEN, shop_id=LOJA)
                self.assertEqual((transporte.pedidos, relogio), ([], []))

    def test_fabrica_le_as_duas_chaves_pela_configuracao(self):
        leitor = LeitorDeConfiguracao(Path("."), {"SHOPEE_PARTNER_ID": PARTNER_ID, "SHOPEE_PARTNER_KEY": PARTNER_KEY},
                                      keyring=None, criar_cofre=None)
        transporte = Transporte()
        cliente_shopee_da_configuracao(leitor, client=http(transporte)).get(CAMINHO_LOJA, access_token=TOKEN, shop_id=LOJA)
        params = transporte.pedidos[0].url.params
        self.assertEqual(params["sign"], assinar(PARTNER_KEY, PARTNER_ID, CAMINHO_LOJA, int(params["timestamp"]), TOKEN, LOJA))
        vazio = LeitorDeConfiguracao(Path("."), {}, keyring=None, criar_cofre=None)
        with self.assertRaises(ServicoIndisponivel):
            cliente_shopee_da_configuracao(vazio, client=http(transporte)).get(CAMINHO_LOJA)
        self.assertEqual(len(transporte.pedidos), 1)

    def test_catalogo_tem_as_chaves_opcionais_e_sem_padrao(self):
        for nome in ("SHOPEE_PARTNER_ID", "SHOPEE_PARTNER_KEY"):
            item = POR_NOME[nome]
            self.assertEqual((item.segredo, item.padrao, item.obrigatoria_em_producao, item.usada_no_mvp),
                             (True, None, False, False))

    def test_erro_da_shopee_vira_falha_sem_segredo_na_excecao(self):
        eco = f"invalid access_token {TOKEN} sign {SIGN_LOJA} key {PARTNER_KEY}"
        casos = (
            ({"error": "error_auth", "message": eco}, 200),
            ((403, {"error": "error_auth", "message": eco}), 403),
            ((500, f"erro em https://shopee.teste{CAMINHO_LOJA}?sign={SIGN_LOJA}&access_token={TOKEN}"), 500),
            (httpx.ConnectError(f"falhou https://shopee.teste{CAMINHO_LOJA}?sign={SIGN_LOJA}&access_token={TOKEN}"), 0),
        )
        for resposta, status in casos:
            with self.subTest(status=status):
                com_erro = cliente(Transporte(resposta))
                with self.assertRaises(FalhaNoMarketplace) as contexto:
                    com_erro.get(CAMINHO_LOJA, access_token=TOKEN, shop_id=LOJA)
                erro = contexto.exception
                self.assertEqual(erro.status, status)
                self.assertIsNone(erro.__cause__)
                self.assertIsNone(erro.__context__)
                texto = " ".join((str(erro), repr(erro), repr(erro.args), repr(erro.corpo)))
                for segredo in (PARTNER_KEY, TOKEN, SIGN_LOJA, "sign=", "https://"):
                    self.assertNotIn(segredo, texto)
                self.assertNotIn(PARTNER_KEY, repr(com_erro))
                self.assertIsNone(FORA_DA_REGRA.search(str(erro)))

    def test_log_do_httpx_sai_sem_a_query_assinada(self):
        for resposta in ({"error": "", "response": {}}, (500, "fora do ar")):
            with self.subTest(resposta=resposta), self.assertLogs("httpx", "INFO") as logs:
                try:
                    cliente(Transporte(resposta)).get(CAMINHO_LOJA, access_token=TOKEN, shop_id=LOJA)
                except FalhaNoMarketplace:
                    pass
            texto = "\n".join(logs.output)
            self.assertIn(CAMINHO_LOJA, texto)
            for segredo in (PARTNER_KEY, TOKEN, SIGN_LOJA, "sign="):
                self.assertNotIn(segredo, texto)


class TestFonteDeEsquemaShopee(unittest.TestCase):
    def test_converte_os_atributos_e_acrescenta_os_campos_fixos(self):
        transporte = Transporte(RESPOSTA_ATRIBUTOS)
        esquema = FonteDeEsquemaShopee(cliente(transporte), LOJA).esquema("100182", TOKEN, "Tênis")
        self.assertEqual((esquema.canal, esquema.categoria_id, esquema.categoria_nome), ("shopee", "100182", "Tênis"))
        self.assertEqual(esquema.campos[:4], (
            CampoDoCanal("shopee", "100010", "Cor", True, TipoDeCampo.LISTA, (("1", "Azul"), ("2", "Verde")), "", "cor"),
            CampoDoCanal("shopee", "100020", "Capacidade", False, TipoDeCampo.NUMERO, (), "ml", "capacidade"),
            CampoDoCanal("shopee", "100017", "Tipo de garantia", True, TipoDeCampo.TEXTO, (), "", ""),
            CampoDoCanal("shopee", "100030", "Material", False, TipoDeCampo.TEXTO, (), "", "material"),
        ))
        self.assertEqual(esquema.campos[4:], CAMPOS_FIXOS)
        self.assertEqual({c: campos[-1].unidade for c, campos in esquema.por_chave().items() if c.endswith(("_g", "_cm"))},
                         {"peso_g": "g", "comprimento_cm": "cm", "largura_cm": "cm", "altura_cm": "cm"})
        params = transporte.pedidos[0].url.params
        self.assertEqual(transporte.pedidos[0].url.path, "/api/v2/product/get_attribute_tree")
        self.assertEqual((params["category_id_list"], params["language"], params["shop_id"], params["access_token"]),
                         ("100182", "pt-BR", LOJA, TOKEN))

    def test_categoria_sem_atributos_fica_so_com_os_campos_fixos(self):
        self.assertEqual(esquema_da_shopee("1", "", []).campos, CAMPOS_FIXOS)

    def test_falha_devolve_none(self):
        casos = ({"error": "error_param", "message": "x"}, (500, "fora"), httpx.ReadTimeout("lento"),
                 {"error": "", "response": {"list": [{"category_id": 999, "attribute_tree": ATRIBUTOS}]}})
        for resposta in casos:
            with self.subTest(resposta=resposta):
                self.assertIsNone(FonteDeEsquemaShopee(cliente(Transporte(resposta)), LOJA).esquema("100182", TOKEN))
        sem_credencial = Transporte(RESPOSTA_ATRIBUTOS)
        self.assertIsNone(FonteDeEsquemaShopee(cliente(sem_credencial, partner_key=""), LOJA).esquema("100182", TOKEN))
        self.assertEqual(sem_credencial.pedidos, [])

    def test_descobre_a_categoria_pelo_nome(self):
        transporte = Transporte({"error": "", "response": {"category_id": [100182, 100183]}})
        fonte = FonteDeEsquemaShopee(cliente(transporte), LOJA)
        self.assertEqual(fonte.descobrir_categoria(["Tênis", "corrida "], TOKEN), CategoriaSugerida("100182", ""))
        self.assertEqual(transporte.pedidos[0].url.path, "/api/v2/product/category_recommend")
        self.assertEqual(transporte.pedidos[0].url.params["item_name"], "Tênis corrida")
        self.assertIsNone(fonte.descobrir_categoria(["  "], TOKEN))
        self.assertEqual(len(transporte.pedidos), 1)
        falha = FonteDeEsquemaShopee(cliente(Transporte({"error": "error_auth"})), LOJA)
        self.assertIsNone(falha.descobrir_categoria(["Tênis"], TOKEN))


class TestPublicadorShopee(unittest.TestCase):
    esquema = esquema_da_shopee("100182", "Tênis", ATRIBUTOS)

    def test_corpo_do_add_item_com_as_conversoes(self):
        corpo = PublicadorShopee.corpo_add_item(PRODUTO, RESPOSTAS, self.esquema, ["img1"], [90001])
        self.assertEqual(corpo, {
            "item_name": "Tênis de corrida azul", "description": "Leve e confortável.", "category_id": 100182,
            "original_price": 199.9, "seller_stock": [{"stock": 3}], "condition": "NEW",
            "image": {"image_id_list": ["img1"]}, "logistic_info": [{"logistic_id": 90001, "enabled": True}],
            "attribute_list": [
                {"attribute_id": 100010, "attribute_value_list": [{"value_id": 1, "original_value_name": "Azul"}]},
                {"attribute_id": 100020, "attribute_value_list": [
                    {"value_id": 0, "original_value_name": "500", "value_unit": "ml"}]},
                {"attribute_id": 100017, "attribute_value_list": [
                    {"value_id": 0, "original_value_name": "Garantia do fabricante"}]},
            ],
            "brand": {"brand_id": 0, "original_brand_name": "Olympikus"},
            "weight": 0.35,
            "dimension": {"package_length": 31, "package_width": 20, "package_height": 12},
        })

    def test_medidas_incompletas_ficam_fora_e_usado_vira_used(self):
        usado = Produto(**{**PRODUTO.__dict__, "condicao": "usado"})
        respostas = {k: v for k, v in RESPOSTAS.items() if k != "altura_cm"}
        corpo = PublicadorShopee.corpo_add_item(usado, respostas, self.esquema, ["img1"], [90001])
        self.assertNotIn("dimension", corpo)
        self.assertEqual(corpo["condition"], "USED")

    def test_recusa_listando_tudo_o_que_falta(self):
        sem_preco = Produto(**{**PRODUTO.__dict__, "preco_centavos": 0})
        with self.assertRaises(CamposObrigatoriosFaltando) as contexto:
            PublicadorShopee.corpo_add_item(sem_preco, {"cor": "roxo", "marca": "X", "peso_g": "1 kg"},
                                            self.esquema, [], [90001])
        self.assertEqual(contexto.exception.faltando, ["Preço", "Fotos", "Cor", "Tipo de garantia", "Peso"])
        self.assertEqual(contexto.exception.codigo, "campos_obrigatorios_faltando")
        self.assertIsNone(FORA_DA_REGRA.search(contexto.exception.mensagem))

    def test_numero_sai_inteiro_sem_notacao_cientifica(self):
        for resposta, esperado in (("1500000 ml", "1500000"), ("1234,567", "1234.567")):
            corpo = PublicadorShopee.corpo_add_item(PRODUTO, {**RESPOSTAS, "capacidade": resposta}, self.esquema,
                                                    ["img1"], [90001])
            capacidade = next(a for a in corpo["attribute_list"] if a["attribute_id"] == 100020)
            self.assertEqual(capacidade["attribute_value_list"][0]["original_value_name"], esperado)

    def test_peso_absurdo_ou_quase_zero_conta_como_faltando(self):
        for peso in ("9" * 400, "2000000000", "0,3"):
            with self.assertRaises(CamposObrigatoriosFaltando) as contexto:
                PublicadorShopee.corpo_add_item(PRODUTO, {**RESPOSTAS, "peso_g": peso}, self.esquema, ["img1"], [90001])
            self.assertEqual(contexto.exception.faltando, ["Peso"])

    def test_corpo_do_upload_image(self):
        self.assertEqual(PublicadorShopee.corpo_upload_image(b"JPEG", "a.jpg"), {"image": ("a.jpg", b"JPEG", "image/jpeg")})

    def test_publicar_sobe_a_foto_sem_loja_e_cria_o_item_assinado(self):
        transporte = Transporte({"error": "", "response": {"image_info": {"image_id": "img1"}}},
                                {"error": "", "response": {"item_id": 123}})
        resposta = PublicadorShopee(cliente(transporte), LOJA).publicar(TOKEN, PRODUTO, RESPOSTAS, self.esquema,
                                                                       [b"JPEG"], [90001])
        self.assertEqual(resposta["response"], {"item_id": 123})
        foto, item = transporte.pedidos
        self.assertEqual(foto.url.path, "/api/v2/media_space/upload_image")
        self.assertNotIn("access_token", foto.url.params)
        self.assertEqual(item.url.path, CAMINHO_LOJA)
        self.assertEqual((item.url.params["sign"], item.url.params["shop_id"]), (SIGN_LOJA, LOJA))
        self.assertEqual(json.loads(item.content)["image"], {"image_id_list": ["img1"]})

    def test_publicar_recusa_antes_de_qualquer_chamada(self):
        transporte = Transporte()
        with self.assertRaises(CamposObrigatoriosFaltando):
            PublicadorShopee(cliente(transporte), LOJA).publicar(TOKEN, PRODUTO, {}, self.esquema, [b"JPEG"], [90001])
        self.assertEqual(transporte.pedidos, [])

    def test_foto_sem_image_id_e_falha(self):
        publicador = PublicadorShopee(cliente(Transporte({"error": "", "response": {}})), LOJA)
        with self.assertRaises(FalhaNoMarketplace):
            publicador.subir_foto(b"JPEG")


if __name__ == "__main__":
    unittest.main()
