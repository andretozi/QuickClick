"""Testes da API HTTP e da entrega do front, com a aplicação montada de verdade (SQLite temporário)."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.bootstrap import criar_app
from backend.infrastructure.config import Config

INDEX_HTML = "<!doctype html><title>Quick Click</title>"


class BaseApi(unittest.TestCase):
    plano_demo = "gratis"

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
            plano_demo=self.plano_demo,
        )
        self.cliente = TestClient(criar_app(self.config))

    def tearDown(self):
        self.cliente.close()
        self._pasta.cleanup()

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
        for caminho in ("/api/health", "/api/plans", "/api/me", "/api/marketplaces", "/api/marketplaces/{slug}/connection"):
            self.assertIn(caminho, caminhos)

    def test_plano_demo_invalido_para_o_boot_com_mensagem_clara(self):
        config = Config(self.config.raiz, self.config.pasta_front, self.config.caminho_banco, plano_demo="premium")
        with self.assertRaisesRegex(ValueError, "QUICKCLICK_PLANO_DEMO"):
            criar_app(config)


class TestApiConsultas(BaseApi):
    def test_plans(self):
        planos = self.cliente.get("/api/plans").json()["planos"]
        self.assertEqual([p["nome"] for p in planos], ["Grátis", "Essencial", "Pro", "Business"])
        self.assertEqual(planos[0]["preco_mensal_centavos"], 0)
        self.assertIsNone(planos[2]["preco_mensal_centavos"])
        self.assertEqual([p["limite_marketplaces"] for p in planos], [1, 1, None, None])

    def test_me_e_o_vendedor_de_demonstracao_no_plano_gratis(self):
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
        outro_cliente = TestClient(criar_app(self.config))  # simula reiniciar o servidor
        self.addCleanup(outro_cliente.close)
        conectados = [m["slug"] for m in outro_cliente.get("/api/marketplaces").json()["marketplaces"] if m["conectado"]]
        self.assertEqual(conectados, ["amazon"])


class TestApiPlanoPro(BaseApi):
    plano_demo = "pro"

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
