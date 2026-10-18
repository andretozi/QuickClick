"""Testes da API HTTP e da entrega do front, com a aplicação montada de verdade."""

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.bootstrap import criar_app
from backend.application.ia.escolha import ProvedoresDeIA
from backend.domain.marketplace import Marketplace, StatusMarketplace
from backend.infrastructure.banco import models
from backend.infrastructure.configuracao import Config
from backend.infrastructure.database import Base
from backend.infrastructure.seguranca.token_jwt import ServicoJWT
from backend.tests import leitor_de_teste

SEGREDO_JWT_TESTE = "segredo-jwt-so-dos-testes-com-mais-de-32-caracteres"
CHAVE_CRIPTO_TESTE = "nN1Yc8pK0wVQx3vT1o6m2f9W1u0Hq2c5e7Kx8Zl4bD0="

INDEX_HTML = "<!doctype html><title>Quick Click</title>"

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


class MockMeliClient:
    def __init__(self, *args, **kwargs):
        self.is_closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def close(self):
        self.is_closed = True

    def request(self, method, url, *args, **kwargs):
        if str(method).upper() == "POST":
            return self.post(url, *args, **kwargs)
        return self.get(url, *args, **kwargs)

    def post(self, url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.is_success = True
        url_str = str(url)
        if "/oauth/token" in url_str:
            resp.json.return_value = {
                "access_token": "token_ml_123",
                "refresh_token": "refresh_ml_123",
                "expires_in": 21600,
                "user_id": 123456,
            }
        elif "/items" in url_str:
            dados = kwargs.get("json", {})
            resp.json.return_value = {
                "id": "MLB999888",
                "title": dados.get("title", "Novo Anúncio"),
                "price": dados.get("price", 0.0),
                "status": "active",
            }
        else:
            resp.json.return_value = {}
        resp.raise_for_status = MagicMock()
        return resp

    def get(self, url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.is_success = True
        url_str = str(url)
        if "/users/me" in url_str:
            resp.json.return_value = {"id": 123456, "nickname": "LOJA_TESTE_ML", "email": "teste@exemplo.com"}
        elif "/items/search" in url_str:
            resp.json.return_value = {"results": ["MLB123"]}
        elif "/items" in url_str:
            resp.json.return_value = [
                {
                    "code": 200,
                    "body": {
                        "id": "MLB123",
                        "title": "Produto Teste",
                        "price": 99.90,
                        "status": "active",
                        "available_quantity": 5,
                        "sold_quantity": 1,
                        "permalink": "https://www.mercadolivre.com.br",
                    },
                }
            ]
        else:
            resp.json.return_value = {}
        resp.raise_for_status = MagicMock()
        return resp


class BaseApi(unittest.TestCase):
    def setUp(self):
        self.leitor = leitor_de_teste(
            MERCADO_LIVRE_CLIENT_ID="1234567890123456",
            MERCADO_LIVRE_CLIENT_SECRET="secret_teste",
            MERCADO_LIVRE_REDIRECT_URI="https://quickclick.azurewebsites.net/api/marketplaces/mercado-livre/callback",
            QUICKCLICK_JWT_SECRET=SEGREDO_JWT_TESTE,
            TOKENS_CHAVE_CRIPTO=CHAVE_CRIPTO_TESTE,
        )

        self._patch_meli = patch("backend.infrastructure.marketplaces.mercado_livre.httpx.Client", new=MockMeliClient)
        self._patch_meli.start()

        self._pasta = tempfile.TemporaryDirectory()
        raiz = Path(self._pasta.name)
        front = raiz / "frontend" / "dist"
        front.mkdir(parents=True)
        (front / "index.html").write_text(INDEX_HTML, encoding="utf-8")
        self.config = Config(raiz=raiz, pasta_front=front)
        self._engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self._engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        self.jwt = ServicoJWT(SEGREDO_JWT_TESTE)
        self.cliente = TestClient(criar_app(self.config, session_factory=self.Session, leitor=self.leitor,
                                            provedores=ProvedoresDeIA()))

        # Criação real da conta do vendedor via endpoint de cadastro (sem dados mockados/seeds)
        resp = self.cliente.post(
            "/api/auth/register",
            json={
                "nome": "Vendedor Teste",
                "email": "teste@quickclick.com.br",
                "loja": "Loja Teste",
                "senha": "senha_segura_123",
                "maior_de_idade": True,
            },
        )
        self.token = resp.json()["token"]
        self.cliente.headers["Authorization"] = f"Bearer {self.token}"

    def tearDown(self):
        self.cliente.close()
        self._pasta.cleanup()
        self._engine.dispose()
        self._patch_meli.stop()

    def conectar(self, slug, codigo="codigo_teste"):
        return self.cliente.post(
            f"/api/marketplaces/{slug}/connection",
            json={"codigo_autorizacao": codigo},
        )

    def conectados(self):
        return [m["slug"] for m in self.cliente.get("/api/marketplaces").json()["marketplaces"] if m["conectado"]]


class TestApiSistema(BaseApi):
    def test_health(self):
        resposta = self.cliente.get("/api/health")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"status": "ok"})

    def test_cabecalhos_de_seguranca_presentes(self):
        resposta = self.cliente.get("/api/health")
        self.assertIn("max-age=31536000", resposta.headers["strict-transport-security"])
        self.assertEqual(resposta.headers["x-content-type-options"], "nosniff")
        self.assertEqual(resposta.headers["x-frame-options"], "DENY")
        self.assertEqual(resposta.headers["referrer-policy"], "strict-origin-when-cross-origin")
        self.assertIn("camera=()", resposta.headers["permissions-policy"])
        self.assertIn("default-src 'self'", resposta.headers["content-security-policy"])
        self.assertIn("frame-ancestors 'none'", resposta.headers["content-security-policy"])

    def test_front_na_raiz(self):
        resposta = self.cliente.get("/")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("text/html", resposta.headers["content-type"])
        self.assertEqual(resposta.text, INDEX_HTML)

    def test_caminho_desconhecido_do_site_cai_no_index(self):
        resposta = self.cliente.get("/qualquer/pagina")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.text, INDEX_HTML)

    def test_caminho_desconhecido_da_api_e_404_em_json(self):
        for caminho in ("/api/nao-existe", "/api"):
            with self.subTest(caminho=caminho):
                resposta = self.cliente.get(caminho)
                self.assertEqual(resposta.status_code, 404)
                self.assertEqual(resposta.json()["erro"]["codigo"], "nao_encontrado")

    def test_documentacao_desligada_por_padrao_e_ligavel_por_configuracao(self):
        # Por padrão (/docs, /redoc e /openapi.json desligados): caem no index.html do front, sem expor Swagger/OpenAPI
        for caminho in ("/docs", "/redoc", "/openapi.json"):
            with self.subTest(caminho=caminho):
                resposta = self.cliente.get(caminho)
                self.assertEqual(resposta.text, INDEX_HTML)
                self.assertNotIn("swagger", resposta.text.lower())

        # Quando DOCUMENTACAO_API_ATIVA=true, expõe normalmente os esquemas para inspeção local
        leitor_doc = leitor_de_teste(
            QUICKCLICK_JWT_SECRET=SEGREDO_JWT_TESTE,
            TOKENS_CHAVE_CRIPTO=CHAVE_CRIPTO_TESTE,
            DOCUMENTACAO_API_ATIVA="true",
        )
        with TestClient(criar_app(self.config, session_factory=self.Session, leitor=leitor_doc,
                                  provedores=ProvedoresDeIA())) as cliente_doc:
            self.assertEqual(cliente_doc.get("/docs").status_code, 200)
            caminhos = cliente_doc.get("/openapi.json").json()["paths"]
            for caminho in (
                "/api/health",
                "/api/plans",
                "/api/auth/register",
                "/api/auth/login",
                "/api/auth/me",
                "/api/me",
                "/api/marketplaces",
                "/api/marketplaces/{slug}/connection",
                "/api/marketplaces/{slug}/authorize-url",
                "/api/marketplaces/{slug}/callback",
                "/api/marketplaces/{slug}/products",
            ):
                self.assertIn(caminho, caminhos)

    def test_quando_nao_ha_vendedor_no_banco_api_me_retorna_404(self):
        token_inexistente = self.jwt.gerar_token(user_id=999, email="nao_existe@quickclick.com.br")
        resposta = self.cliente.get("/api/me", headers={"Authorization": f"Bearer {token_inexistente}"})
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.json()["erro"]["codigo"], "vendedor_nao_encontrado")


class TestAutenticacaoJWT(BaseApi):
    def test_cadastro_com_sucesso_retorna_token_jwt_e_usuario(self):
        dados = {
            "nome": "Carlos Silva",
            "email": "carlos@exemplo.com",
            "loja": "Loja do Carlos",
            "senha": "senha_segura_123",
            "maior_de_idade": True,
        }
        resposta = self.cliente.post("/api/auth/register", json=dados)
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertIn("token", corpo)
        self.assertTrue(len(corpo["token"]) > 20)
        self.assertEqual(corpo["usuario"]["email"], "carlos@exemplo.com")
        self.assertEqual(corpo["usuario"]["nome"], "Carlos Silva")
        self.assertEqual(corpo["usuario"]["plano"], "gratis")

    def test_cadastro_sem_confirmar_maioridade_e_recusado(self):
        resposta = self.cliente.post("/api/auth/register", json={"nome": "Leo", "email": "leo@exemplo.com",
                                                                 "loja": "Loja", "senha": "senha_forte_789"})
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (400, "maioridade_obrigatoria"))

    def test_cadastro_grava_quando_confirmou_a_maioridade(self):
        self.cliente.post("/api/auth/register", json={"nome": "Lia", "email": "lia@exemplo.com", "loja": "Loja",
                                                      "senha": "senha_forte_789", "maior_de_idade": True})
        with self.Session() as session:
            user = session.query(models.User).filter_by(email="lia@exemplo.com").one()
            self.assertTrue(user.confirmou_maioridade_em)

    def test_cadastro_com_email_duplicado_retorna_409(self):
        dados = {
            "nome": "Maria",
            "email": "maria@exemplo.com",
            "loja": "Loja Maria",
            "senha": "senha_secreta_456",
            "maior_de_idade": True,
        }
        primeiro = self.cliente.post("/api/auth/register", json=dados)
        self.assertEqual(primeiro.status_code, 200)

        segundo = self.cliente.post("/api/auth/register", json=dados)
        self.assertEqual(segundo.status_code, 409)
        self.assertEqual(segundo.json()["erro"]["codigo"], "email_em_uso")

    def test_login_com_credenciais_corretas_retorna_token_jwt(self):
        dados = {
            "nome": "Ana",
            "email": "ana@exemplo.com",
            "loja": "Loja da Ana",
            "senha": "minha_senha_forte",
            "maior_de_idade": True,
        }
        self.cliente.post("/api/auth/register", json=dados)

        login_resp = self.cliente.post(
            "/api/auth/login",
            json={"email": "ana@exemplo.com", "senha": "minha_senha_forte"},
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("token", login_resp.json())
        self.assertEqual(login_resp.json()["usuario"]["email"], "ana@exemplo.com")

    def test_login_com_senha_incorreta_retorna_401(self):
        dados = {
            "nome": "Bia",
            "email": "bia@exemplo.com",
            "loja": "Loja da Bia",
            "senha": "senha_correta_123",
            "maior_de_idade": True,
        }
        self.cliente.post("/api/auth/register", json=dados)

        login_resp = self.cliente.post(
            "/api/auth/login",
            json={"email": "bia@exemplo.com", "senha": "senha_errada"},
        )
        self.assertEqual(login_resp.status_code, 401)
        self.assertEqual(login_resp.json()["erro"]["codigo"], "credenciais_invalidas")

    def test_login_com_email_inexistente_retorna_401(self):
        login_resp = self.cliente.post(
            "/api/auth/login",
            json={"email": "fantasma@exemplo.com", "senha": "qualquer_senha"},
        )
        self.assertEqual(login_resp.status_code, 401)
        self.assertEqual(login_resp.json()["erro"]["codigo"], "credenciais_invalidas")

    def test_bloqueio_contra_forca_bruta_no_login_retorna_429(self):
        for _ in range(8):
            resp = self.cliente.post(
                "/api/auth/login",
                json={"email": "teste@quickclick.com.br", "senha": "senha_incorreta"},
            )
            self.assertEqual(resp.status_code, 401)

        bloqueado = self.cliente.post(
            "/api/auth/login",
            json={"email": "teste@quickclick.com.br", "senha": "senha_segura_123"},
        )
        self.assertEqual((bloqueado.status_code, bloqueado.json()["erro"]["codigo"]), (429, "muitas_tentativas"))

    def test_obter_usuario_atual_via_token_jwt(self):
        dados = {
            "nome": "Carla Diaz",
            "email": "carla@exemplo.com",
            "loja": "Loja da Carla",
            "senha": "senha_segura_123",
            "maior_de_idade": True,
        }
        cad_resp = self.cliente.post("/api/auth/register", json=dados)
        self.assertEqual(cad_resp.status_code, 200)
        token = cad_resp.json()["token"]

        me_resp = self.cliente.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_resp.status_code, 200)
        usuario = me_resp.json()
        self.assertEqual(usuario["email"], "carla@exemplo.com")
        self.assertEqual(usuario["nome"], "Carla Diaz")
        self.assertEqual(usuario["loja"], "Loja da Carla")
        self.assertEqual(usuario["plano"], "gratis")

    def test_acesso_a_rota_protegida_sem_token_retorna_401(self):
        resposta = self.cliente.get("/api/me", headers={"Authorization": ""})
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["erro"]["codigo"], "nao_autenticado")

    def test_acesso_com_token_invalido_retorna_401(self):
        resposta = self.cliente.get("/api/me", headers={"Authorization": "Bearer token_falsificado_invalido"})
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["erro"]["codigo"], "token_invalido")

    def test_acesso_com_token_expirado_retorna_401(self):
        jwt_expirado = ServicoJWT(SEGREDO_JWT_TESTE, duracao=timedelta(seconds=-10))
        token_velho = jwt_expirado.gerar_token(user_id=1, email="teste@quickclick.com.br")

        resposta = self.cliente.get("/api/me", headers={"Authorization": f"Bearer {token_velho}"})
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["erro"]["codigo"], "token_invalido")


class TestApiConsultas(BaseApi):
    def test_plans(self):
        planos = self.cliente.get("/api/plans").json()["planos"]
        self.assertEqual([p["nome"] for p in planos], ["Grátis", "Essencial", "Pro", "Business"])
        self.assertEqual(planos[0]["preco_mensal_centavos"], 0)
        self.assertIsNone(planos[2]["preco_mensal_centavos"])
        self.assertEqual([p["limite_marketplaces"] for p in planos], [1, 1, None, None])

    def test_me_retorna_dados_do_vendedor_no_plano_gratis(self):
        eu = self.cliente.get("/api/me").json()
        self.assertEqual(eu["plano"]["slug"], "gratis")
        self.assertEqual(eu["marketplaces_conectados"], 0)
        self.assertTrue(eu["pode_conectar_mais"])
        self.assertEqual(eu["plano_para_mais_marketplaces"]["nome"], "Pro")

    def test_marketplaces_lista_o_catalogo_inteiro(self):
        marketplaces = self.cliente.get("/api/marketplaces").json()["marketplaces"]
        self.assertEqual(len(marketplaces), 9)
        self.assertEqual(
            [m["nome"] for m in marketplaces if m["status"] == "disponivel"], ["Mercado Livre"]
        )
        self.assertEqual(sum(m["status"] == "em_breve" for m in marketplaces), 8)
        self.assertFalse(any(m["conectado"] for m in marketplaces))


class TestApiConexoes(BaseApi):
    def test_conecta_e_desconecta(self):
        resposta = self.conectar("mercado-livre")
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()["conectado"])
        self.assertIsNotNone(resposta.json()["conectado_em"])
        self.assertEqual(self.conectados(), ["mercado-livre"])

        resposta = self.cliente.delete("/api/marketplaces/mercado-livre/connection")
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.json()["conectado"])
        self.assertEqual(self.conectados(), [])

    def test_obter_url_autorizacao_mercado_livre(self):
        resposta = self.cliente.get("/api/marketplaces/mercado-livre/authorize-url")
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertIn("url", dados)
        self.assertTrue(dados["url"].startswith("http"))
        self.assertIn("state=", dados["url"])

    def test_callback_oauth_mercado_livre(self):
        auth_url_resp = self.cliente.get("/api/marketplaces/mercado-livre/authorize-url")
        url = auth_url_resp.json()["url"]
        query = parse_qs(urlparse(url).query)
        estado = query["state"][0]

        # Simula o redirecionamento de retorno do Mercado Livre para a nossa API
        callback_resp = self.cliente.get(
            f"/api/marketplaces/mercado-livre/callback?code=codigo_teste_oauth&state={estado}",
            follow_redirects=False,
        )
        self.assertEqual(callback_resp.status_code, 302)
        self.assertIn("/#/marketplaces?conectado=mercado-livre", callback_resp.headers["location"])
        self.assertIn("mercado-livre", self.conectados())

    def test_callback_oauth_nao_vaza_excecao_interna_na_url(self):
        auth_url_resp = self.cliente.get("/api/marketplaces/mercado-livre/authorize-url")
        estado = parse_qs(urlparse(auth_url_resp.json()["url"]).query)["state"][0]
        with patch.object(MockMeliClient, "post", side_effect=RuntimeError("segredo_interno_do_banco")):
            callback_resp = self.cliente.get(
                f"/api/marketplaces/mercado-livre/callback?code=codigo_teste&state={estado}",
                follow_redirects=False,
            )
        self.assertEqual(callback_resp.status_code, 302)
        self.assertEqual(callback_resp.headers["location"], "/#/marketplaces?erro=falha_ao_conectar")
        self.assertNotIn("segredo_interno_do_banco", callback_resp.headers["location"])

    def test_listar_produtos_e_rota_antiga_de_publicar_desativada(self):
        self.conectar("mercado-livre")
        # Listar produtos para monitoramento
        produtos_resp = self.cliente.get("/api/marketplaces/mercado-livre/products")
        self.assertEqual(produtos_resp.status_code, 200)
        self.assertIsInstance(produtos_resp.json(), list)

        # A rota antiga que publicava um dict qualquer foi desativada (a publicação é montada no back)
        pub_resp = self.cliente.post("/api/marketplaces/mercado-livre/products", json={"title": "x", "price": 1})
        self.assertEqual(pub_resp.status_code, 405)

    @patch("backend.domain.marketplace.CATALOGO", CATALOGO_TESTE)
    def test_limite_do_plano_gratis_responde_403_dizendo_o_plano(self):
        self.conectar("mercado-livre")

        resposta = self.conectar("shopee")

        self.assertEqual(resposta.status_code, 403)
        erro = resposta.json()["erro"]
        self.assertEqual(erro["codigo"], "limite_do_plano")
        self.assertEqual(erro["plano_sugerido"], "pro")
        self.assertEqual(
            erro["mensagem"], "No plano Grátis você conecta 1 marketplace. Pra conectar mais, mude para o plano Pro."
        )
        eu = self.cliente.get("/api/me").json()
        self.assertEqual((eu["marketplaces_conectados"], eu["pode_conectar_mais"]), (1, False))

    def test_em_breve_responde_409(self):
        resposta = self.conectar("shein")
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(resposta.json()["erro"]["codigo"], "marketplace_em_breve")

    def test_inexistente_responde_404(self):
        for metodo in (self.cliente.post, self.cliente.delete):
            with self.subTest(metodo=metodo.__name__):
                resposta = metodo("/api/marketplaces/orkut/connection")
                self.assertEqual(resposta.status_code, 404)
                self.assertEqual(resposta.json()["erro"]["codigo"], "marketplace_nao_encontrado")

    def test_conectar_duas_vezes_nao_da_erro(self):
        self.assertEqual(self.conectar("mercado-livre").status_code, 200)
        self.assertEqual(self.conectar("mercado-livre").status_code, 200)
        self.assertEqual(self.conectados(), ["mercado-livre"])

    def test_desconectar_libera_a_vaga(self):
        self.conectar("mercado-livre")
        resposta = self.cliente.delete("/api/marketplaces/mercado-livre/connection")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.conectados(), [])

    def test_conexoes_ficam_salvas_no_banco(self):
        self.conectar("mercado-livre")
        with self.Session() as session:
            salvas = [
                c.marketplace
                for c in session.query(models.ContaVinculadaModel).filter_by(vendedor_id=1).all()
            ]
        self.assertEqual(salvas, ["mercado-livre"])


class TestApiPlanoPro(BaseApi):
    def setUp(self):
        super().setUp()
        with self.Session() as session:
            vendedor = session.query(models.VendedorModel).filter_by(id=1).first()
            if vendedor:
                vendedor.plano = "pro"
                session.commit()

    def test_pro_mostra_dados_do_plano(self):
        eu = self.cliente.get("/api/me").json()
        self.assertEqual(eu["plano"]["nome"], "Pro")
        self.assertEqual(eu["marketplaces_conectados"], 0)
        self.assertTrue(eu["pode_conectar_mais"])
        self.assertIsNone(eu["plano_para_mais_marketplaces"])


class TestApiTrocarPlano(BaseApi):
    def trocar(self, plano, **kwargs):
        return self.cliente.put("/api/me/plano", json={"plano": plano}, **kwargs)

    def test_gratis_pro_business_gratis_muda_selo_limite_e_cota(self):
        self.conectar("mercado-livre")
        esperado = {"pro": (True, 120), "business": (True, 400), "gratis": (False, 5)}
        for plano in ("pro", "business", "gratis"):
            resposta = self.trocar(plano)
            self.assertEqual((resposta.status_code, resposta.json()["plano"]), (200, plano))
            self.assertEqual(resposta.json()["email"], "teste@quickclick.com.br")
            self.assertEqual(self.cliente.get("/api/auth/me").json()["plano"], plano)
            eu = self.cliente.get("/api/me").json()
            cota = self.cliente.get("/api/ia/cota").json()
            self.assertEqual((eu["plano"]["slug"], eu["pode_conectar_mais"], cota["plano"], cota["analises_por_mes"]),
                             (plano, *esperado[plano][:1], plano, esperado[plano][1]))
        with self.Session() as session:
            self.assertEqual(session.query(models.VendedorModel).filter_by(id=1).one().plano, "gratis")

    def test_plano_que_nao_existe_e_400_sem_mudar_nada(self):
        resposta = self.trocar("ouro")
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (400, "plano_invalido"))
        self.assertEqual(self.cliente.get("/api/auth/me").json()["plano"], "gratis")

    def test_sem_token_e_401(self):
        resposta = self.trocar("pro", headers={"Authorization": ""})
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (401, "nao_autenticado"))

    def test_cada_um_troca_so_o_proprio_plano(self):
        outro = self.cliente.post("/api/auth/register", json={"nome": "Bia", "email": "bia@exemplo.com",
                                                              "loja": "Loja", "senha": "senha_forte_789",
                                                              "maior_de_idade": True}).json()["token"]
        self.trocar("business", headers={"Authorization": f"Bearer {outro}"})
        self.assertEqual(self.cliente.get("/api/auth/me").json()["plano"], "gratis")

    def test_plans_avisa_que_a_troca_e_livre(self):
        self.assertTrue(self.cliente.get("/api/plans").json()["troca_de_plano_livre"])


class TestApiTrocaDePlanoDesligada(BaseApi):
    def setUp(self):
        super().setUp()
        self.leitor = leitor_de_teste(QUICKCLICK_JWT_SECRET=SEGREDO_JWT_TESTE, TOKENS_CHAVE_CRIPTO=CHAVE_CRIPTO_TESTE,
                                      TROCA_DE_PLANO_LIVRE="false")
        self.cliente.close()
        self.cliente = TestClient(criar_app(self.config, session_factory=self.Session, leitor=self.leitor,
                                            provedores=ProvedoresDeIA()))
        self.cliente.headers["Authorization"] = f"Bearer {self.token}"

    def test_responde_402_e_o_plano_fica(self):
        resposta = self.cliente.put("/api/me/plano", json={"plano": "pro"})
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (402, "troca_de_plano_indisponivel"))
        self.assertEqual(self.cliente.get("/api/auth/me").json()["plano"], "gratis")
        self.assertFalse(self.cliente.get("/api/plans").json()["troca_de_plano_livre"])


if __name__ == "__main__":
    unittest.main()
