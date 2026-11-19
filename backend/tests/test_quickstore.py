"""Testes completos da integração com a QuickStore: OAuth 2.0, produtos, categorias e Webhooks de vendas."""

import hashlib
import hmac
import json
import unittest
from datetime import UTC, datetime, timedelta

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.bootstrap import criar_app
from backend.application.casos_de_uso import ConectarMarketplace, ProcessarWebhookQuickStore, PublicarNoMercadoLivre
from backend.application.ia.modelos import ArquivoDeFoto
from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.domain.erros import QuickStoreDesconectada
from backend.domain.plano import PRO
from backend.domain.produto import Produto, Publicacao
from backend.domain.vendedor import Vendedor
from backend.infrastructure.banco import models  # noqa: F401
from backend.infrastructure.banco.repositorio_contas import RepositorioContasVinculadasSQL
from backend.infrastructure.banco.repositorio_produtos import RepositorioDeProdutosSQL
from backend.infrastructure.banco.repositorio_vendedores import RepositorioVendedoresSQL
from backend.infrastructure.database import Base
from backend.infrastructure.ia.preparador_pillow import PillowPreparador
from backend.infrastructure.marketplaces.quickstore import GatewayQuickStore
from backend.infrastructure.seguranca.cripto_tokens import CifradorDeTokens
from backend.infrastructure.seguranca.token_jwt import ServicoJWT
from backend.tests import leitor_de_teste
from backend.tests.test_api_ia import FonteMLFalsa
from backend.tests.test_casos_de_uso import (
    AGORA,
    GatewayFalso,
    RepositorioContasEmMemoria,
    RepositorioVendedoresEmMemoria,
)
from backend.tests.test_plano import FORA_DA_REGRA
from backend.tests.test_publicacao_ml import ANUNCIO, AnalisesFalsas, PublicadorFalso, fotos

SEGREDO_QUICKSTORE = "segredo_super_secreto_quickstore_123"
SEGREDO_JWT_TESTE = "segredo_jwt_teste_integracao_quickstore_32_bytes"
CHAVE_CRIPTO_TESTE = "nN1Yc8pK0wVQx3vT1o6m2f9W1u0Hq2c5e7Kx8Zl4bD0="


def _criar_banco_em_memoria():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, session_factory


def _assinar_webhook(corpo_bytes: bytes, segredo: str = SEGREDO_QUICKSTORE) -> str:
    digest = hmac.new(segredo.encode("utf-8"), corpo_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class TestGatewayQuickStore(unittest.TestCase):
    def _gateway_com_transporte(self, handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        return GatewayQuickStore(
            base_url="https://quickstore.azurewebsites.net/",
            client_id="QuickClickApp",
            client_secret=SEGREDO_QUICKSTORE,
            redirect_uri="https://quickclick-cudkaseffgceaaaq.chilecentral-01.azurewebsites.net/api/quickstore/callback",
            agora=lambda: AGORA,
            client=client,
        )

    def test_gerar_url_autorizacao(self):
        gateway = GatewayQuickStore(
            base_url="https://quickstore.azurewebsites.net",
            client_id="QuickClickApp",
            client_secret=SEGREDO_QUICKSTORE,
            redirect_uri="https://quickclick-cudkaseffgceaaaq.chilecentral-01.azurewebsites.net/api/quickstore/callback",
        )
        url = gateway.gerar_url_autorizacao("estado_csrf_123")
        self.assertEqual(
            url,
            "https://quickstore.azurewebsites.net/authorization?response_type=code"
            "&client_id=QuickClickApp"
            "&redirect_uri=https%3A%2F%2Fquickclick-cudkaseffgceaaaq.chilecentral-01.azurewebsites.net%2Fapi%2Fquickstore%2Fcallback"
            "&state=estado_csrf_123",
        )

    def test_trocar_codigo_por_token_e_obter_perfil(self):
        chamadas = []

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas.append((request.method, str(request.url)))
            if request.url.path == "/oauth/token":
                corpo = json.loads(request.content.decode("utf-8"))
                self.assertEqual(corpo["grant_type"], "authorization_code")
                self.assertEqual(corpo["client_id"], "QuickClickApp")
                self.assertEqual(corpo["client_secret"], SEGREDO_QUICKSTORE)
                self.assertEqual(corpo["code"], "TG-QS-999")
                return httpx.Response(
                    200,
                    json={
                        "access_token": "APP_USR-QUICKSTORE-TOKEN",
                        "token_type": "Bearer",
                        "expires_in": 21600,
                        "scope": "offline_access read write",
                        "user_id": 1,
                        "refresh_token": "TG-QUICKSTORE-REFRESH",
                    },
                )
            if request.url.path == "/users/me":
                self.assertEqual(request.headers.get("Authorization"), "Bearer APP_USR-QUICKSTORE-TOKEN")
                return httpx.Response(
                    200,
                    json={
                        "id": 1,
                        "nickname": "LOJA_DO_VENDEDOR",
                        "email": "vendedor@email.com",
                        "first_name": "Nome do Vendedor",
                        "site_id": "MLB",
                    },
                )
            return httpx.Response(404)

        gateway = self._gateway_com_transporte(handler)
        credenciais = gateway.trocar_codigo_por_token("TG-QS-999")
        self.assertEqual(credenciais.access_token, "APP_USR-QUICKSTORE-TOKEN")
        self.assertEqual(credenciais.refresh_token, "TG-QUICKSTORE-REFRESH")
        self.assertEqual(credenciais.conta_externa_id, "1")
        self.assertEqual(credenciais.apelido, "LOJA_DO_VENDEDOR")
        self.assertEqual(credenciais.expira_em, AGORA + timedelta(seconds=21600))
        self.assertEqual(len(chamadas), 2)

    def test_renovar_token(self):
        def handler(request: httpx.Request) -> httpx.Response:
            corpo = json.loads(request.content.decode("utf-8"))
            self.assertEqual(corpo["grant_type"], "refresh_token")
            self.assertEqual(corpo["refresh_token"], "TG-REFRESH-1")
            return httpx.Response(
                200,
                json={
                    "access_token": "APP_USR-NOVO-TOKEN",
                    "token_type": "Bearer",
                    "expires_in": 21600,
                    "user_id": 1,
                    "refresh_token": "TG-REFRESH-2",
                },
            )

        gateway = self._gateway_com_transporte(handler)
        novas = gateway.renovar_token("TG-REFRESH-1")
        self.assertEqual(novas.access_token, "APP_USR-NOVO-TOKEN")
        self.assertEqual(novas.refresh_token, "TG-REFRESH-2")
        self.assertEqual(novas.conta_externa_id, "1")

    def test_ciclo_de_vida_anuncios_e_pedidos(self):
        requisicoes = []

        def handler(request: httpx.Request) -> httpx.Response:
            requisicoes.append((request.method, request.url.path))
            if request.method == "GET" and request.url.path == "/categories/MLB23332/attributes":
                return httpx.Response(
                    200,
                    json=[{"id": "BRAND", "name": "Marca", "value_type": "string", "tags": {"required": True}}],
                )
            if request.method == "POST" and request.url.path == "/items":
                corpo = json.loads(request.content.decode("utf-8"))
                return httpx.Response(
                    201,
                    json={
                        "id": "MLB1234567890",
                        "title": corpo["title"],
                        "category_id": corpo["category_id"],
                        "price": corpo["price"],
                        "currency_id": "BRL",
                        "available_quantity": corpo["available_quantity"],
                        "sold_quantity": 0,
                        "buying_mode": "buy_it_now",
                        "listing_type_id": "gold_special",
                        "condition": corpo["condition"],
                        "permalink": "https://quickstore.azurewebsites.net/produto.html?id=MLB1234567890",
                        "thumbnail": "https://seusite.com.br/imagens/tenis-frente.jpg",
                        "pictures": [{"id": "PIC1", "url": "https://seusite.com.br/imagens/tenis-frente.jpg"}],
                        "status": "active",
                        "seller_id": 1,
                    },
                )
            if request.method in ("POST", "PUT") and request.url.path == "/items/MLB1234567890/description":
                corpo = json.loads(request.content.decode("utf-8"))
                return httpx.Response(200, json={"plain_text": corpo["plain_text"]})
            if request.method == "PUT" and request.url.path == "/items/MLB1234567890":
                corpo = json.loads(request.content.decode("utf-8"))
                status = "paused" if corpo.get("available_quantity") == 0 else corpo.get("status", "active")
                return httpx.Response(200, json={"id": "MLB1234567890", "status": status, **corpo})
            if request.method == "DELETE" and request.url.path == "/items/MLB1234567890":
                return httpx.Response(200, json={"id": "MLB1234567890", "status": "closed"})
            if request.method == "GET" and request.url.path == "/users/1/items/search":
                return httpx.Response(
                    200,
                    json={
                        "seller_id": "1",
                        "results": [
                            {
                                "id": "MLB1234567890",
                                "title": "Tênis Esportivo Quick Runner",
                                "price": 199.9,
                                "status": "active",
                                "available_quantity": 15,
                                "sold_quantity": 2,
                                "category_id": "MLB23332",
                                "permalink": "https://quickstore.azurewebsites.net/produto.html?id=MLB1234567890",
                                "pictures": [{"url": "https://seusite.com.br/imagens/tenis-frente.jpg"}],
                                "seller_id": 1,
                            }
                        ],
                    },
                )
            if request.method == "GET" and request.url.path == "/items/MLB1234567890/description":
                return httpx.Response(200, json={"plain_text": "Tênis confortável para corrida."})
            if request.method == "GET" and request.url.path == "/orders/2000000001":
                return httpx.Response(
                    200,
                    json={
                        "id": 2000000001,
                        "status": "paid",
                        "total_amount": 399.80,
                        "currency_id": "BRL",
                        "order_items": [
                            {
                                "item": {
                                    "id": "MLB1234567890",
                                    "title": "Tênis Esportivo Quick Runner",
                                    "category_id": "MLB23332",
                                },
                                "quantity": 2,
                                "unit_price": 199.90,
                                "currency_id": "BRL",
                            }
                        ],
                        "seller": {"id": 1},
                    },
                )
            return httpx.Response(404)

        gateway = self._gateway_com_transporte(handler)
        token = "APP_USR-TOKEN"

        atributos = gateway.atributos_da_categoria("MLB23332", token)
        self.assertEqual(atributos[0]["id"], "BRAND")

        criado = gateway.publicar_anuncio(
            token,
            {
                "title": "Tênis Esportivo Quick Runner",
                "category_id": "MLB23332",
                "price": 199.90,
                "currency_id": "BRL",
                "available_quantity": 15,
                "buying_mode": "buy_it_now",
                "condition": "new",
                "listing_type_id": "gold_special",
            },
        )
        self.assertEqual(criado["id"], "MLB1234567890")

        desc = gateway.gravar_descricao(token, "MLB1234567890", "Tênis confortável para corrida.")
        self.assertEqual(desc["plain_text"], "Tênis confortável para corrida.")

        atualizado = gateway.atualizar_anuncio(token, "MLB1234567890", {"available_quantity": 0})
        self.assertEqual(atualizado["status"], "paused")

        lista = gateway.listar_anuncios(token, conta_externa_id="1")
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["id"], "MLB1234567890")
        self.assertEqual(lista[0]["description"], "Tênis confortável para corrida.")

        pedido = gateway.obter_pedido(token, "/orders/2000000001")
        self.assertEqual(pedido["id"], 2000000001)
        self.assertEqual(pedido["order_items"][0]["quantity"], 2)

        excluido = gateway.excluir_anuncio(token, "MLB1234567890")
        self.assertEqual(excluido["status"], "closed")

    def test_validacao_assinatura_hmac_webhook(self):
        gateway = GatewayQuickStore(
            base_url="https://quickstore.azurewebsites.net",
            client_id="QuickClickApp",
            client_secret=SEGREDO_QUICKSTORE,
        )
        corpo = b'{"_id":"notif_1","resource":"/orders/2000000001","user_id":1,"topic":"orders_v2"}'
        assinatura_valida = _assinar_webhook(corpo, SEGREDO_QUICKSTORE)

        self.assertTrue(gateway.validar_assinatura_webhook(corpo, assinatura_valida))
        self.assertFalse(gateway.validar_assinatura_webhook(corpo, "sha256=0000000000"))
        self.assertFalse(gateway.validar_assinatura_webhook(corpo, None))
        self.assertFalse(gateway.validar_assinatura_webhook(corpo + b" ", assinatura_valida))


class FonteSemCategoriaFalsa(FonteMLFalsa):
    def descobrir_categoria(self, termos, access_token):
        return None


class TestPublicarNaQuickStore(unittest.TestCase):
    def test_publica_na_quickstore_aceitando_fotos_externas_e_categoria_padrao(self):
        contas = RepositorioContasEmMemoria()
        contas.salvar(
            ContaVinculada(
                1,
                "quickstore",
                AGORA,
                CredenciaisOAuth("token_qs", "refresh_qs", AGORA + timedelta(hours=6), "1", "LOJA_QS"),
            )
        )
        vendedores = RepositorioVendedoresEmMemoria(Vendedor(1, "Ana", PRO))
        conectar = ConectarMarketplace(vendedores, contas, {"quickstore": GatewayFalso()}, agora=lambda: AGORA)
        publicador = PublicadorFalso(seller_id="1")
        fonte = FonteSemCategoriaFalsa()
        caso = PublicarNoMercadoLivre(
            conectar,
            publicador,
            fonte,
            AnalisesFalsas({}),
            PillowPreparador(),
            canal="quickstore",
        )

        anuncio_qs = {
            **ANUNCIO,
            "analise_id": None,
            "fotos_mantidas": ["https://seusite.com.br/imagens/tenis-frente.jpg"],
        }
        resposta = caso.executar(1, anuncio_qs, fotos(1))
        self.assertEqual(resposta["id"], "MLB123456")
        self.assertEqual(resposta["categoria_id"], "MLB23332")
        self.assertEqual(
            publicador.itens[0]["pictures"],
            [{"source": "https://seusite.com.br/imagens/tenis-frente.jpg"}, {"id": "IMG1"}],
        )

    def test_exige_quickstore_conectada(self):
        contas = RepositorioContasEmMemoria()
        vendedores = RepositorioVendedoresEmMemoria(Vendedor(1, "Ana", PRO))
        conectar = ConectarMarketplace(vendedores, contas, {"quickstore": GatewayFalso()}, agora=lambda: AGORA)
        caso = PublicarNoMercadoLivre(
            conectar,
            PublicadorFalso(),
            FonteMLFalsa(),
            AnalisesFalsas({}),
            PillowPreparador(),
            canal="quickstore",
        )
        with self.assertRaises(QuickStoreDesconectada) as ctx:
            caso.executar(1, ANUNCIO, fotos(1))
        self.assertIsNone(FORA_DA_REGRA.search(ctx.exception.mensagem))


class TestWebhookQuickStoreEIntegracaoHTTP(unittest.TestCase):
    def setUp(self):
        self.engine, self.session_factory = _criar_banco_em_memoria()
        self.leitor = leitor_de_teste(
             QUICKCLICK_JWT_SECRET=SEGREDO_JWT_TESTE,
            TOKENS_CHAVE_CRIPTO=CHAVE_CRIPTO_TESTE,
            QUICKSTORE_BASE_URL="https://quickstore.azurewebsites.net",
            QUICKSTORE_CLIENT_ID="QuickClickApp",
            QUICKSTORE_CLIENT_SECRET=SEGREDO_QUICKSTORE,
            QUICKSTORE_REDIRECT_URI="https://quickclick-cudkaseffgceaaaq.chilecentral-01.azurewebsites.net/api/quickstore/callback",
        )
        self.vendedores = RepositorioVendedoresSQL(self.session_factory)
        self.vendedores.salvar(Vendedor(id=1, nome="Loja Quick", plano=PRO))
        self.cifrador = CifradorDeTokens(CHAVE_CRIPTO_TESTE)
        self.contas = RepositorioContasVinculadasSQL(self.session_factory, self.cifrador)
        self.produtos = RepositorioDeProdutosSQL(self.session_factory)
        self.token_service = ServicoJWT(SEGREDO_JWT_TESTE)

    def tearDown(self):
        self.engine.dispose()

    def test_webhook_deduz_estoque_local_e_propaga_para_mercado_livre(self):
        # Vincula tanto QuickStore (user_id=1) quanto Mercado Livre para o vendedor 1
        self.contas.salvar(
            ContaVinculada(
                vendedor_id=1,
                marketplace="quickstore",
                conectada_em=AGORA,
                credenciais=CredenciaisOAuth(
                    access_token="token_qs_ativo",
                    refresh_token="refresh_qs",
                    expira_em=datetime.now(UTC) + timedelta(hours=5),
                    conta_externa_id="1",
                    apelido="LOJA_QS",
                ),
            )
        )
        self.contas.salvar(
            ContaVinculada(
                vendedor_id=1,
                marketplace="mercado-livre",
                conectada_em=AGORA,
                credenciais=CredenciaisOAuth(
                    access_token="token_ml_ativo",
                    refresh_token="refresh_ml",
                    expira_em=datetime.now(UTC) + timedelta(hours=5),
                    conta_externa_id="999",
                    apelido="LOJA_ML",
                ),
            )
        )

        # Cadastra um produto publicado nos dois canais com estoque 15
        produto_inicial = Produto(
            id="prod_tenis_1",
            titulo="Tênis Esportivo Quick Runner",
            descricao="Tênis confortável para corrida e caminhada.",
            categoria="calcados",
            condicao="novo",
            preco_centavos=19990,
            preco_sugerido_centavos=19990,
            estoque=15,
            fotos=["https://http2.mlstatic.com/D_1.jpg"],
            capa=0,
            atributos=[{"id": "BRAND", "nome": "Marca", "valor": "Quick"}],
            analise_id=None,
            criado_em=AGORA,
            atualizado_em=AGORA,
            publicacoes=[
                Publicacao(
                    canal="quickstore",
                    status="publicado",
                    id_externo="MLB1234567890",
                    permalink="https://quickstore.azurewebsites.net/produto.html?id=MLB1234567890",
                    categoria_id="MLB23332",
                    vendidos=0,
                ),
                Publicacao(
                    canal="mercado-livre",
                    status="publicado",
                    id_externo="MLB987654321",
                    permalink="https://produto.mercadolivre.com.br/MLB987654321",
                    categoria_id="MLB23332",
                    vendidos=1,
                ),
            ],
        )
        self.produtos.salvar(1, produto_inicial, AGORA)

        def handler_qs(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/orders/2000000001":
                self.assertEqual(request.headers.get("Authorization"), "Bearer token_qs_ativo")
                return httpx.Response(
                    200,
                    json={
                        "id": 2000000001,
                        "status": "paid",
                        "date_created": "2026-04-17T12:00:00Z",
                        "total_amount": 399.80,
                        "currency_id": "BRL",
                        "order_items": [
                            {
                                "item": {
                                    "id": "MLB1234567890",
                                    "title": "Tênis Esportivo Quick Runner",
                                    "category_id": "MLB23332",
                                },
                                "quantity": 2,
                                "unit_price": 199.90,
                                "currency_id": "BRL",
                            }
                        ],
                        "seller": {"id": 1},
                        "buyer": {"id": 500, "nickname": "COMPRADOR_EXEMPLO", "email": "comprador@email.com"},
                    },
                )
            return httpx.Response(404)

        gateway_qs = GatewayQuickStore(
            base_url="https://quickstore.azurewebsites.net",
            client_id="QuickClickApp",
            client_secret=SEGREDO_QUICKSTORE,
            client=httpx.Client(transport=httpx.MockTransport(handler_qs)),
        )
        publicador_ml = PublicadorFalso(seller_id="999")
        publicador_ml._armazenados["MLB987654321"] = {
            **publicador_ml._armazenados["MLB123456"],
            "id": "MLB987654321",
            "available_quantity": 15,
        }

        conectar = ConectarMarketplace(
            self.vendedores,
            self.contas,
            {"quickstore": gateway_qs, "mercado-livre": GatewayFalso()},
        )
        caso_webhook = ProcessarWebhookQuickStore(
            gateway_quickstore=gateway_qs,
            contas=self.contas,
            conectar=conectar,
            produtos=self.produtos,
            publicadores={"mercado-livre": publicador_ml, "quickstore": gateway_qs},
            relogio=lambda: AGORA + timedelta(minutes=5),
        )

        payload_notificacao = {
            "_id": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
            "resource": "/orders/2000000001",
            "user_id": 1,
            "topic": "orders_v2",
            "application_id": "QuickClickApp",
            "attempts": 1,
            "sent": "2026-04-17T12:00:00Z",
            "received": "2026-04-17T12:00:00Z",
        }
        corpo_bytes = json.dumps(payload_notificacao).encode("utf-8")
        assinatura = _assinar_webhook(corpo_bytes)

        caso_webhook.validar_assinatura(corpo_bytes, assinatura)
        resultado = caso_webhook.executar(payload_notificacao, topico_header="orders_v2")

        self.assertEqual(resultado["status"], "ok")
        self.assertEqual(len(resultado["itens_atualizados"]), 1)
        self.assertEqual(resultado["itens_atualizados"][0]["estoque_anterior"], 15)
        self.assertEqual(resultado["itens_atualizados"][0]["novo_estoque"], 13)
        self.assertEqual(resultado["itens_atualizados"][0]["canais_sincronizados"], ["mercado-livre"])

        # Verifica no banco de dados se o estoque caiu para 13 e vendidos subiu para 2
        salvo = self.produtos.obter(1, "prod_tenis_1")
        self.assertIsNotNone(salvo)
        self.assertEqual(salvo.estoque, 13)
        pubs = {p.canal: p for p in salvo.publicacoes}
        self.assertEqual(pubs["quickstore"].vendidos, 2)
        self.assertEqual(pubs["quickstore"].status, "publicado")

        # Verifica se o estoque 13 foi propagado para o Mercado Livre
        self.assertEqual(publicador_ml.atualizacoes, [("MLB987654321", {"available_quantity": 13})])

        # Idempotência: reenviar o mesmo pedido não abate o estoque duas vezes
        repetido = caso_webhook.executar(payload_notificacao, topico_header="orders_v2")
        self.assertEqual(repetido["itens_atualizados"], [])
        self.assertEqual(self.produtos.obter(1, "prod_tenis_1").estoque, 13)

    def test_rotas_http_callback_e_webhook_quickstore(self):
        app = criar_app(session_factory=self.session_factory, leitor=self.leitor, identificar_vendedor=lambda: 1)
        cliente = TestClient(app)

        # 1. Authorize URL da QuickStore
        resp_url = cliente.get("/api/marketplaces/quickstore/authorize-url")
        self.assertEqual(resp_url.status_code, 200)
        self.assertIn("https://quickstore.azurewebsites.net/authorization", resp_url.json()["url"])
        self.assertIn("client_id=QuickClickApp", resp_url.json()["url"])

        # 2. Callback /api/quickstore/callback com erro de acesso negado redireciona para o front
        resp_cb = cliente.get("/api/quickstore/callback?error=access_denied", follow_redirects=False)
        self.assertEqual(resp_cb.status_code, 302)
        self.assertEqual(resp_cb.headers["location"], "/#/marketplaces?erro=access_denied")

        # 3. Webhook /api/quickstore/webhook rejeita assinatura inválida com 401
        payload = {
            "_id": "notif_invalida",
            "resource": "/orders/2000000001",
            "user_id": 1,
            "topic": "orders_v2",
        }
        corpo = json.dumps(payload).encode("utf-8")
        resp_invalido = cliente.post(
            "/api/quickstore/webhook",
            content=corpo,
            headers={
                "Content-Type": "application/json",
                "X-QuickStore-Topic": "orders_v2",
                "X-QuickStore-Signature": "sha256=assinatura_falsa",
            },
        )
        self.assertEqual(resp_invalido.status_code, 401)

        # 4. Webhook /api/quickstore/webhook aceita assinatura HMAC-SHA256 válida com 200 OK
        resp_valido = cliente.post(
            "/api/quickstore/webhook",
            content=corpo,
            headers={
                "Content-Type": "application/json",
                "X-QuickStore-Topic": "orders_v2",
                "X-QuickStore-Signature": _assinar_webhook(corpo),
            },
        )
        self.assertEqual(resp_valido.status_code, 200)

        # 5. Bloqueia tentativa de Path Traversal no resource do webhook (mesmo com assinatura válida)
        payload_traversal = {
            "_id": "notif_traversal",
            "resource": "/orders/../../users/me",
            "user_id": 1,
            "topic": "orders_v2",
        }
        corpo_traversal = json.dumps(payload_traversal).encode("utf-8")
        resp_traversal = cliente.post(
            "/api/quickstore/webhook",
            content=corpo_traversal,
            headers={
                "Content-Type": "application/json",
                "X-QuickStore-Topic": "orders_v2",
                "X-QuickStore-Signature": _assinar_webhook(corpo_traversal),
            },
        )
        self.assertEqual(resp_traversal.status_code, 400)

        # 6. Bloqueia payload acima de 32 KB (anti-DoS)
        corpo_gigante = b'{"resource":"/orders/1","user_id":1,"lixo":"' + (b"A" * 40_000) + b'"}'
        resp_gigante = cliente.post(
            "/api/quickstore/webhook",
            content=corpo_gigante,
            headers={
                "Content-Type": "application/json",
                "X-QuickStore-Topic": "orders_v2",
                "X-QuickStore-Signature": _assinar_webhook(corpo_gigante),
            },
        )
        self.assertEqual(resp_gigante.status_code, 400)

    def test_webhook_fail_closed_sem_segredo_e_bloqueio_de_spoofing_e_ssrf(self):
        # 1. Fail-closed: quando QUICKSTORE_CLIENT_SECRET não está configurado, o webhook recusa com 401
        leitor_sem_segredo = leitor_de_teste(
            QUICKCLICK_JWT_SECRET=SEGREDO_JWT_TESTE,
            TOKENS_CHAVE_CRIPTO=CHAVE_CRIPTO_TESTE,
            QUICKSTORE_BASE_URL="https://quickstore.azurewebsites.net",
            QUICKSTORE_CLIENT_ID="QuickClickApp",
            QUICKSTORE_CLIENT_SECRET="",
        )
        app_sem_segredo = criar_app(
            session_factory=self.session_factory,
            leitor=leitor_sem_segredo,
            identificar_vendedor=lambda: 1,
        )
        cliente_sem_segredo = TestClient(app_sem_segredo)
        corpo = json.dumps({"resource": "/orders/2000000001", "user_id": 1, "topic": "orders_v2"}).encode("utf-8")
        resp_sem_segredo = cliente_sem_segredo.post(
            "/api/quickstore/webhook",
            content=corpo,
            headers={"Content-Type": "application/json", "X-QuickStore-Topic": "orders_v2"},
        )
        self.assertEqual(resp_sem_segredo.status_code, 401)

        # 2. Anti-SSRF em fotos_mantidas: URLs apontando para localhost, IPs privados ou IMDS da Azure são descartadas
        from backend.application.casos_de_uso.publicar_no_mercado_livre import anuncio_de_dict

        anuncio_com_ssrf = {
            **ANUNCIO,
            "fotos_mantidas": [
                "https://169.254.169.254/metadata/instance",
                "https://127.0.0.1/admin",
                "https://localhost/secret.jpg",
                "https://192.168.1.10/foto.jpg",
                "https://10.0.0.1/foto.jpg",
                "https://intranet.local/foto.jpg",
                "https://cdn.lojaexemplo.com.br/imagens/tenis.jpg",
            ],
        }
        convertido = anuncio_de_dict(anuncio_com_ssrf, exigir_mlstatic=False)
        self.assertEqual(convertido.fotos_mantidas, ("https://cdn.lojaexemplo.com.br/imagens/tenis.jpg",))

        # 3. Anti-Spoofing de seller.id: se o pedido na QuickStore pertencer a outro seller (ex: 999 != 1), ignora a baixa
        self.contas.salvar(
            ContaVinculada(
                vendedor_id=1,
                marketplace="quickstore",
                conectada_em=AGORA,
                credenciais=CredenciaisOAuth(
                    access_token="token_qs_1",
                    refresh_token="refresh_qs_1",
                    expira_em=datetime.now(UTC) + timedelta(hours=5),
                    conta_externa_id="1",
                    apelido="LOJA_QS_1",
                ),
            )
        )
        produto_alvo = Produto(
            id="prod_protegido",
            titulo="Produto Protegido",
            descricao="Descrição",
            categoria="eletronicos",
            condicao="novo",
            preco_centavos=10000,
            preco_sugerido_centavos=10000,
            estoque=10,
            fotos=["https://http2.mlstatic.com/D_1.jpg"],
            capa=0,
            atributos=[],
            analise_id=None,
            criado_em=AGORA,
            atualizado_em=AGORA,
            publicacoes=[Publicacao(canal="quickstore", status="publicado", id_externo="MLB111222")],
        )
        self.produtos.salvar(1, produto_alvo, AGORA)

        def handler_spoof(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "id": 2000000999,
                    "status": "paid",
                    "order_items": [{"item": {"id": "MLB111222", "title": "Produto Protegido"}, "quantity": 5}],
                    "seller": {"id": 999},  # pertence ao seller 999, não ao user_id=1 da notificação!
                },
            )

        gateway_spoof = GatewayQuickStore(
            base_url="https://quickstore.azurewebsites.net",
            client_id="QuickClickApp",
            client_secret=SEGREDO_QUICKSTORE,
            client=httpx.Client(transport=httpx.MockTransport(handler_spoof)),
        )
        conectar = ConectarMarketplace(self.vendedores, self.contas, {"quickstore": gateway_spoof})
        caso_webhook = ProcessarWebhookQuickStore(
            gateway_quickstore=gateway_spoof,
            contas=self.contas,
            conectar=conectar,
            produtos=self.produtos,
            relogio=lambda: AGORA + timedelta(minutes=10),
        )
        res_spoof = caso_webhook.executar(
            {"resource": "/orders/2000000999", "user_id": "1", "topic": "orders_v2"},
            topico_header="orders_v2",
        )
        self.assertEqual(res_spoof["itens_atualizados"], [])
        self.assertEqual(self.produtos.obter(1, "prod_protegido").estoque, 10)

    def test_upload_imagem_fallback_data_url_e_atualizacao_completa_na_quickstore(self):
        def handler_404_upload(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/pictures/items/upload":
                return httpx.Response(404)
            return httpx.Response(200, json={})

        gateway = GatewayQuickStore(
            base_url="https://quickstore.azurewebsites.net",
            client_id="QuickClickApp",
            client_secret=SEGREDO_QUICKSTORE,
            client=httpx.Client(transport=httpx.MockTransport(handler_404_upload)),
        )
        data_url = gateway.subir_imagem("token_qs", b"\xff\xd8\xff\xe0", "image/jpeg")
        self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))

        # Verifica que PublicarNoMercadoLivre(canal='quickstore') aceita data_url como source e atualiza todos os campos
        contas = RepositorioContasEmMemoria()
        contas.salvar(
            ContaVinculada(
                1,
                "quickstore",
                AGORA,
                CredenciaisOAuth("token_qs", "refresh_qs", AGORA + timedelta(hours=6), "1", "LOJA_QS"),
            )
        )
        vendedores = RepositorioVendedoresEmMemoria(Vendedor(1, "Ana", PRO))
        conectar = ConectarMarketplace(vendedores, contas, {"quickstore": GatewayFalso()}, agora=lambda: AGORA)
        publicador = PublicadorFalso(seller_id="1")
        publicador.subir_imagem = lambda token, conteudo, tipo: "data:image/jpeg;base64,ABCD"
        caso = PublicarNoMercadoLivre(
            conectar,
            publicador,
            FonteSemCategoriaFalsa(),
            AnalisesFalsas({}),
            PillowPreparador(),
            canal="quickstore",
        )
        criado = caso.executar(1, {**ANUNCIO, "analise_id": None}, fotos(1))
        self.assertEqual(publicador.itens[0]["pictures"], [{"source": "data:image/jpeg;base64,ABCD"}])

        # Ao atualizar um item já existente na QuickStore (mesmo com vendidos > 0), título, condição e fotos são atualizados
        publicador._armazenados[criado["id"]]["sold_quantity"] = 3
        atualizado = caso.atualizar(
            1,
            criado["id"],
            {
                **ANUNCIO,
                "titulo": "Título Alterado na QuickClick",
                "preco_centavos": 25990,
                "estoque": 7,
                "descricao": "Nova descrição sincronizada.",
            },
            fotos(1),
        )
        self.assertEqual(atualizado["status"], "active")
        ultimo_id, ultimo_corpo = publicador.atualizacoes[-1]
        self.assertEqual(ultimo_id, criado["id"])
        self.assertEqual(ultimo_corpo["title"], "Título Alterado na QuickClick")
        self.assertEqual(ultimo_corpo["price"], 259.9)
        self.assertEqual(ultimo_corpo["available_quantity"], 7)

    def test_webhook_items_sincroniza_alteracoes_da_quickstore_e_coloca_em_standby_quando_fechado(self):
        self.contas.salvar(
            ContaVinculada(
                vendedor_id=1,
                marketplace="quickstore",
                conectada_em=AGORA,
                credenciais=CredenciaisOAuth(
                    access_token="token_qs_ativo",
                    refresh_token="refresh_qs",
                    expira_em=datetime.now(UTC) + timedelta(hours=5),
                    conta_externa_id="1",
                    apelido="LOJA_QS",
                ),
            )
        )
        produto_inicial = Produto(
            id="prod_sync_qs",
            titulo="Fone Bluetooth Original",
            descricao="Descrição antiga",
            categoria="eletronicos",
            condicao="novo",
            preco_centavos=15000,
            preco_sugerido_centavos=15000,
            estoque=10,
            fotos=["https://http2.mlstatic.com/D_1.jpg"],
            capa=0,
            atributos=[{"id": "BRAND", "nome": "Marca", "valor": "Quick"}],
            analise_id=None,
            criado_em=AGORA,
            atualizado_em=AGORA,
            publicacoes=[
                Publicacao(
                    canal="quickstore",
                    status="publicado",
                    id_externo="MLB555666",
                    permalink="https://quickstore.azurewebsites.net/produto.html?id=MLB555666",
                    categoria_id="MLB23332",
                    vendidos=1,
                )
            ],
        )
        self.produtos.salvar(1, produto_inicial, AGORA)

        estado_remoto = {
            "id": "MLB555666",
            "title": "Fone Bluetooth Alterado na QuickStore",
            "price": 179.90,
            "available_quantity": 4,
            "sold_quantity": 3,
            "condition": "used",
            "status": "active",
            "category_id": "MLB23332",
            "permalink": "https://quickstore.azurewebsites.net/produto.html?id=MLB555666",
            "pictures": [{"url": "https://quickstore.azurewebsites.net/img/fone-novo.jpg"}],
            "attributes": [{"id": "BRAND", "value_name": "QuickAudio"}],
            "seller_id": 1,
        }

        def handler_qs(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/items/MLB555666":
                return httpx.Response(200, json=estado_remoto)
            if request.url.path == "/items/MLB555666/description":
                return httpx.Response(200, json={"plain_text": "Descrição alterada lá na QuickStore"})
            return httpx.Response(404)

        gateway_qs = GatewayQuickStore(
            base_url="https://quickstore.azurewebsites.net",
            client_id="QuickClickApp",
            client_secret=SEGREDO_QUICKSTORE,
            client=httpx.Client(transport=httpx.MockTransport(handler_qs)),
        )
        conectar = ConectarMarketplace(self.vendedores, self.contas, {"quickstore": gateway_qs})
        caso_webhook = ProcessarWebhookQuickStore(
            gateway_quickstore=gateway_qs,
            contas=self.contas,
            conectar=conectar,
            produtos=self.produtos,
            publicadores={"quickstore": gateway_qs},
            relogio=lambda: AGORA + timedelta(minutes=15),
        )

        # 1. Alteração na QuickStore reflete na QuickClick
        res_edicao = caso_webhook.executar(
            {"resource": "/items/MLB555666", "user_id": 1, "topic": "items"},
            topico_header="items",
        )
        self.assertEqual(res_edicao["status"], "ok")
        self.assertEqual(len(res_edicao["itens_atualizados"]), 1)

        atualizado = self.produtos.obter(1, "prod_sync_qs")
        self.assertEqual(atualizado.titulo, "Fone Bluetooth Alterado na QuickStore")
        self.assertEqual(atualizado.descricao, "Descrição alterada lá na QuickStore")
        self.assertEqual(atualizado.preco_centavos, 17990)
        self.assertEqual(atualizado.estoque, 4)
        self.assertEqual(atualizado.condicao, "usado")
        self.assertEqual(atualizado.fotos, ["https://quickstore.azurewebsites.net/img/fone-novo.jpg"])
        pub_qs = next(p for p in atualizado.publicacoes if p.canal == "quickstore")
        self.assertEqual(pub_qs.status, "publicado")
        self.assertEqual(pub_qs.vendidos, 3)

        # 2. Quando o item é fechado/excluído na QuickStore, o produto na QuickClick vai para standby (nao_publicado)
        estado_remoto["status"] = "closed"
        caso_webhook.executar(
            {"resource": "/items/MLB555666", "user_id": 1, "topic": "items"},
            topico_header="items",
        )
        em_standby = self.produtos.obter(1, "prod_sync_qs")
        pub_standby = next(p for p in em_standby.publicacoes if p.canal == "quickstore")
        self.assertEqual(pub_standby.status, "nao_publicado")
        self.assertIsNone(pub_standby.id_externo)

    def test_gerenciar_produtos_propaga_edicao_e_remocao_para_quickstore(self):
        from backend.application.casos_de_uso.produtos import GerenciarProdutos

        self.contas.salvar(
            ContaVinculada(
                vendedor_id=1,
                marketplace="quickstore",
                conectada_em=AGORA,
                credenciais=CredenciaisOAuth(
                    access_token="token_qs_ativo",
                    refresh_token="refresh_qs",
                    expira_em=datetime.now(UTC) + timedelta(hours=5),
                    conta_externa_id="1",
                    apelido="LOJA_QS",
                ),
            )
        )
        publicador_qs = PublicadorFalso(seller_id="1")
        publicador_qs._armazenados["MLB999999"] = {
            **publicador_qs._armazenados["MLB123456"],
            "id": "MLB999999",
            "status": "active",
        }
        conectar = ConectarMarketplace(self.vendedores, self.contas, {"quickstore": GatewayFalso()}, agora=lambda: AGORA)
        publicar_qs = PublicarNoMercadoLivre(
            conectar,
            publicador_qs,
            FonteSemCategoriaFalsa(),
            AnalisesFalsas({}),
            PillowPreparador(),
            canal="quickstore",
        )
        gerenciar = GerenciarProdutos(
            self.produtos,
            relogio=lambda: AGORA,
            publicar_na_quickstore=publicar_qs,
        )

        produto = Produto(
            id="prod_local_1",
            titulo="Cadeira Gamer Quick",
            descricao="Cadeira ergonômica",
            categoria="casa",
            condicao="novo",
            preco_centavos=89900,
            preco_sugerido_centavos=89900,
            estoque=5,
            fotos=["https://http2.mlstatic.com/D_1.jpg"],
            capa=0,
            atributos=[{"id": "BRAND", "nome": "Marca", "valor": "Quick"}],
            analise_id=None,
            criado_em=AGORA,
            atualizado_em=AGORA,
            publicacoes=[
                Publicacao(
                    canal="quickstore",
                    status="publicado",
                    id_externo="MLB999999",
                    permalink="https://quickstore.azurewebsites.net/produto.html?id=MLB999999",
                    categoria_id="MLB23332",
                    vendidos=0,
                )
            ],
        )
        salvo_inicial = gerenciar.salvar(1, produto)
        from dataclasses import replace

        editado = replace(salvo_inicial, titulo="Cadeira Gamer Quick Pro", preco_centavos=99900, estoque=3)
        gerenciar.salvar(1, editado)
        self.assertTrue(
            any(
                item_id == "MLB999999" and corpo.get("title") == "Cadeira Gamer Quick Pro" and corpo.get("price") == 999.0
                for item_id, corpo in publicador_qs.atualizacoes
            )
        )

        gerenciar.remover(1, "prod_local_1")
        self.assertIn("MLB999999", publicador_qs.excluidos)


if __name__ == "__main__":
    unittest.main()

