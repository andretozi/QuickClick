"""Testes da API HTTP e da entrega do front, com a aplicação montada de verdade."""

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.bootstrap import criar_app
from backend.infrastructure.banco import models
from backend.infrastructure.config import Config
from backend.infrastructure.database import Base
from backend.infrastructure.seguranca.token_jwt import ServicoJWT

INDEX_HTML = "<!doctype html><title>Quick Click</title>"


class BaseApi(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        raiz = Path(self._pasta.name)
        front = raiz / "frontend" / "dist"
        front.mkdir(parents=True)
        (front / "index.html").write_text(INDEX_HTML, encoding="utf-8")
        self.config = Config(
            raiz=raiz,
            pasta_front=front,
            caminho_banco=raiz / "dados" / "teste.sqlite3",
        )
        self._engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self._engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        self.cliente = TestClient(criar_app(self.config, session_factory=self.Session))

        # Criação real da conta do vendedor via endpoint de cadastro (sem dados mockados/seeds)
        resp = self.cliente.post(
            "/api/auth/register",
            json={
                "nome": "Vendedor Teste",
                "email": "teste@quickclick.com.br",
                "loja": "Loja Teste",
                "senha": "senha_segura_123",
            },
        )
        self.token = resp.json()["token"]
        self.cliente.headers["Authorization"] = f"Bearer {self.token}"

    def tearDown(self):
        self.cliente.close()
        self._pasta.cleanup()
        self._engine.dispose()

    def conectar(self, slug):
        return self.cliente.post(f"/api/marketplaces/{slug}/connection")

    def conectados(self):
        return [m["slug"] for m in self.cliente.get("/api/marketplaces").json()["marketplaces"] if m["conectado"]]


class TestApiSistema(BaseApi):
    def test_health(self):
        resposta = self.cliente.get("/api/health")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"status": "ok"})

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

    def test_documentacao_automatica(self):
        self.assertEqual(self.cliente.get("/docs").status_code, 200)
        caminhos = self.cliente.get("/openapi.json").json()["paths"]
        for caminho in (
            "/api/health",
            "/api/plans",
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/me",
            "/api/me",
            "/api/marketplaces",
            "/api/marketplaces/{slug}/connection",
        ):
            self.assertIn(caminho, caminhos)

    def test_quando_nao_ha_vendedor_no_banco_api_me_retorna_404(self):
        token_inexistente = ServicoJWT().gerar_token(user_id=999, email="nao_existe@quickclick.com.br")
        cliente_sem_vendedor = TestClient(criar_app(self.config, session_factory=self.Session))
        cliente_sem_vendedor.headers["Authorization"] = f"Bearer {token_inexistente}"
        resposta = cliente_sem_vendedor.get("/api/me")
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.json()["erro"]["codigo"], "vendedor_nao_encontrado")
        cliente_sem_vendedor.close()


class TestAutenticacaoJWT(BaseApi):
    def test_cadastro_com_sucesso_retorna_token_jwt_e_usuario(self):
        dados = {
            "nome": "Carlos Silva",
            "email": "carlos@exemplo.com",
            "loja": "Loja do Carlos",
            "senha": "senha_segura_123",
        }
        resposta = self.cliente.post("/api/auth/register", json=dados)
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertIn("token", corpo)
        self.assertTrue(len(corpo["token"]) > 20)
        self.assertEqual(corpo["usuario"]["email"], "carlos@exemplo.com")
        self.assertEqual(corpo["usuario"]["nome"], "Carlos Silva")
        self.assertEqual(corpo["usuario"]["plano"], "gratis")

    def test_cadastro_com_email_duplicado_retorna_409(self):
        dados = {
            "nome": "Maria",
            "email": "maria@exemplo.com",
            "loja": "Loja Maria",
            "senha": "senha_secreta_456",
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

    def test_obter_usuario_atual_via_token_jwt(self):
        dados = {
            "nome": "Carla Diaz",
            "email": "carla@exemplo.com",
            "loja": "Loja da Carla",
            "senha": "senha_segura_123",
        }
        cad_resp = self.cliente.post("/api/auth/register", json=dados)
        self.assertEqual(cad_resp.status_code, 200)
        token = cad_resp.json()["token"]

        cliente_carla = TestClient(criar_app(self.config, session_factory=self.Session))
        cliente_carla.headers["Authorization"] = f"Bearer {token}"
        me_resp = cliente_carla.get("/api/auth/me")
        self.assertEqual(me_resp.status_code, 200)
        usuario = me_resp.json()
        self.assertEqual(usuario["email"], "carla@exemplo.com")
        self.assertEqual(usuario["nome"], "Carla Diaz")
        self.assertEqual(usuario["loja"], "Loja da Carla")
        self.assertEqual(usuario["plano"], "gratis")
        cliente_carla.close()

    def test_acesso_a_rota_protegida_sem_token_retorna_401(self):
        cliente_sem_auth = TestClient(criar_app(self.config, session_factory=self.Session))
        resposta = cliente_sem_auth.get("/api/me")
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["erro"]["codigo"], "nao_autenticado")
        cliente_sem_auth.close()

    def test_acesso_com_token_invalido_retorna_401(self):
        cliente_invalido = TestClient(criar_app(self.config, session_factory=self.Session))
        cliente_invalido.headers["Authorization"] = "Bearer token_falsificado_invalido"
        resposta = cliente_invalido.get("/api/me")
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["erro"]["codigo"], "token_invalido")
        cliente_invalido.close()

    def test_acesso_com_token_expirado_retorna_401(self):
        jwt_expirado = ServicoJWT(duracao=timedelta(seconds=-10))
        token_velho = jwt_expirado.gerar_token(user_id=1, email="teste@quickclick.com.br")

        cliente_expirado = TestClient(criar_app(self.config, session_factory=self.Session))
        cliente_expirado.headers["Authorization"] = f"Bearer {token_velho}"
        resposta = cliente_expirado.get("/api/me")
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["erro"]["codigo"], "token_invalido")
        cliente_expirado.close()


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
            [m["nome"] for m in marketplaces if m["status"] == "disponivel"], ["Mercado Livre", "Shopee", "Amazon"]
        )
        self.assertEqual(sum(m["status"] == "em_breve" for m in marketplaces), 6)
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
        self.assertEqual(self.conectar("amazon").status_code, 200)
        self.assertEqual(self.conectar("amazon").status_code, 200)
        self.assertEqual(self.conectados(), ["amazon"])

    def test_desconectar_libera_a_vaga(self):
        self.conectar("mercado-livre")
        self.cliente.delete("/api/marketplaces/mercado-livre/connection")
        self.assertEqual(self.conectar("shopee").status_code, 200)

    def test_conexoes_ficam_salvas_no_banco(self):
        self.conectar("amazon")
        outro_cliente = TestClient(criar_app(self.config, session_factory=self.Session))
        outro_cliente.headers["Authorization"] = f"Bearer {self.token}"
        self.addCleanup(outro_cliente.close)
        conectados = [m["slug"] for m in outro_cliente.get("/api/marketplaces").json()["marketplaces"] if m["conectado"]]
        self.assertEqual(conectados, ["amazon"])


class TestApiPlanoPro(BaseApi):
    def setUp(self):
        super().setUp()
        with self.Session() as session:
            vendedor = session.query(models.VendedorModel).filter_by(id=1).first()
            if vendedor:
                vendedor.plano = "pro"
                session.commit()

    def test_pro_conecta_os_tres_disponiveis(self):
        for slug in ("mercado-livre", "shopee", "amazon"):
            self.assertEqual(self.conectar(slug).status_code, 200)
        eu = self.cliente.get("/api/me").json()
        self.assertEqual(eu["plano"]["nome"], "Pro")
        self.assertEqual(eu["marketplaces_conectados"], 3)
        self.assertTrue(eu["pode_conectar_mais"])
        self.assertIsNone(eu["plano_para_mais_marketplaces"])


if __name__ == "__main__":
    unittest.main()
