"""Rotas /api/produtos com a aplicação montada de verdade: token, isolamento entre vendedores, 409, limites e 413."""

import unittest
from datetime import UTC, datetime

from backend.infrastructure.banco import models
from backend.tests.test_api import BaseApi

CRIADO = "2026-10-30T12:00:00.000Z"


def corpo(id_: str = "a_k3j9x0q2mz", **campos) -> dict:
    return {
        "id": id_, "titulo": "Tênis de corrida", "descricao": "Pouco uso.", "categoria": "calcados",
        "condicao": "usado", "preco_centavos": 15990, "preco_sugerido_centavos": None, "estoque": 1,
        "fotos": ["https://http2.mlstatic.com/D_1.jpg"], "capa": 0,
        "atributos": [{"id": "BRAND", "nome": "Marca", "valor": "Corre"}, {"id": None, "nome": "Peso", "valor": 1.5}],
        "analise_id": None, "criado_em": CRIADO, "atualizado_em": CRIADO,
        "publicacoes": [{"canal": "mercado-livre", "status": "publicado", "id_externo": "MLB1",
                         "permalink": "https://produto.mercadolivre.com.br/MLB1", "categoria_id": "MLB1234",
                         "saude": 87.5, "vendidos": 2}],
        **campos,
    }


class TestApiProdutos(BaseApi):
    def setUp(self):
        super().setUp()
        self.id_a = int(self.jwt.validar_token(self.token)["sub"])
        resp = self.cliente.post("/api/auth/register", json={
            "nome": "Vendedor B", "email": "b@quickclick.com.br", "loja": "Loja B", "senha": "senha_segura_456",
            "maior_de_idade": True,
        })
        self.token_b = resp.json()["token"]
        self.b = {"Authorization": f"Bearer {self.token_b}"}

    def put(self, dados: dict, headers: dict | None = None):
        return self.cliente.put(f"/api/produtos/{dados['id']}", json=dados, headers=headers)

    def test_sem_token_401_nas_cinco_rotas(self):
        del self.cliente.headers["Authorization"]
        pedidos = [
            ("GET", "/api/produtos", None), ("GET", "/api/produtos/a_1", None),
            ("PUT", "/api/produtos/a_1", corpo("a_1")), ("POST", "/api/produtos/importar", corpo("a_1")),
            ("DELETE", "/api/produtos/a_1", None),
        ]
        for metodo, caminho, dados in pedidos:
            with self.subTest(metodo=metodo, caminho=caminho):
                resp = self.cliente.request(metodo, caminho, json=dados)
                self.assertEqual(resp.status_code, 401)
                self.assertEqual(resp.json()["erro"]["codigo"], "nao_autenticado")

    def test_cria_le_lista_e_apaga(self):
        resp = self.put(corpo())
        self.assertEqual(resp.status_code, 200)
        salvo = resp.json()
        self.assertEqual(salvo["publicacoes"][0]["id_externo"], "MLB1")
        self.assertEqual(salvo["atributos"][1]["valor"], 1.5)
        self.assertTrue(salvo["atualizado_em"].endswith("Z"))
        self.assertEqual(self.cliente.get("/api/produtos/a_k3j9x0q2mz").json(), salvo)
        self.assertEqual(self.cliente.get("/api/produtos").json(), {"produtos": [salvo]})
        self.assertEqual(self.cliente.delete("/api/produtos/a_k3j9x0q2mz").status_code, 204)
        resp = self.cliente.get("/api/produtos/a_k3j9x0q2mz")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["erro"]["codigo"], "anuncio_nao_encontrado")

    def test_vendedor_b_nao_le_nao_altera_e_nao_apaga_o_produto_de_a(self):
        de_a = self.put(corpo(titulo="Produto de A")).json()

        resp = self.cliente.get("/api/produtos/a_k3j9x0q2mz", headers=self.b)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["erro"]["codigo"], "anuncio_nao_encontrado")
        self.assertEqual(self.cliente.get("/api/produtos", headers=self.b).json(), {"produtos": []})

        resp = self.put(corpo(titulo="Produto de B", publicacoes=[]), headers=self.b)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.cliente.get("/api/produtos/a_k3j9x0q2mz").json(), de_a)

        resp = self.cliente.delete("/api/produtos/a_k3j9x0q2mz", headers=self.b)
        self.assertEqual(resp.status_code, 204)  # apagou o de B, que nasceu no PUT acima
        resp = self.cliente.delete("/api/produtos/a_k3j9x0q2mz", headers=self.b)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self.cliente.get("/api/produtos/a_k3j9x0q2mz").json(), de_a)
        self.assertEqual([p["titulo"] for p in self.cliente.get("/api/produtos").json()["produtos"]],
                         ["Produto de A"])

    def test_vendedor_id_no_corpo_e_ignorado(self):
        resp = self.put(corpo(vendedor_id=self.id_a), headers=self.b)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("vendedor_id", resp.json())
        self.assertEqual(self.cliente.get("/api/produtos").json(), {"produtos": []})

    def test_analise_de_outro_vendedor_vira_nula(self):
        with self.Session() as session:
            session.add(models.AnaliseIAModel(id="an-de-a", vendedor_id=self.id_a, plano_no_momento="gratis",
                                              nivel="gratis", status="pronta", criado_em=datetime.now(UTC),
                                              atualizado_em=datetime.now(UTC)))
            session.commit()
        self.assertIsNone(self.put(corpo(analise_id="an-de-a"), headers=self.b).json()["analise_id"])
        self.assertEqual(self.put(corpo(analise_id="an-de-a")).json()["analise_id"], "an-de-a")

    def test_409_com_versao_antiga_e_put_com_a_versao_devolvida_grava(self):
        primeiro = self.put(corpo()).json()
        segundo = self.put({**primeiro, "titulo": "Segunda gravação"})
        self.assertEqual(segundo.status_code, 200)
        resp = self.put({**primeiro, "titulo": "Aba velha"})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["erro"], {
            "codigo": "anuncio_desatualizado",
            "mensagem": "Este anúncio mudou em outra aba ou aparelho. Recarregue a página para ver a versão nova.",
        })
        self.assertEqual(self.cliente.get("/api/produtos/a_k3j9x0q2mz").json()["titulo"], "Segunda gravação")
        self.assertEqual(self.put({**segundo.json(), "titulo": "Terceira"}).status_code, 200)

    def test_put_vale_o_id_do_caminho(self):
        resp = self.cliente.put("/api/produtos/a_caminho", json=corpo("a_corpo"))
        self.assertEqual(resp.json()["id"], "a_caminho")
        self.assertEqual(self.cliente.get("/api/produtos/a_corpo").status_code, 404)

    def test_importar_uma_vez_so(self):
        resp = self.cliente.post("/api/produtos/importar", json=corpo())
        self.assertEqual(resp.json(), {"importado": True})
        self.assertEqual(self.cliente.post("/api/produtos/importar", json=corpo()).json(), {"importado": False})
        self.assertEqual(self.cliente.post("/api/produtos/importar", json=corpo("a_outro")).json(),
                         {"importado": False})  # o MLB1 já é do primeiro
        lido = self.cliente.get("/api/produtos/a_k3j9x0q2mz").json()
        self.assertEqual(lido["atualizado_em"], "2026-10-30T12:00:00Z")

    def test_validacao_recusa_fotos_ids_e_canais_fora_da_regra(self):
        casos = {
            "foto data:": corpo(fotos=["data:image/jpeg;base64,AAAA"]),
            "foto http": corpo(fotos=["http://exemplo.com/1.jpg"]),
            "url longa": corpo(fotos=["https://exemplo.com/" + "a" * 1000]),
            "13 fotos": corpo(fotos=[f"https://exemplo.com/{i}.jpg" for i in range(13)]),
            "permalink http": corpo(publicacoes=[{"canal": "mercado-livre", "status": "publicado",
                                                  "permalink": "http://exemplo.com"}]),
            "canal fora do catálogo": corpo(publicacoes=[{"canal": "ebay", "status": "publicado"}]),
            "canal repetido": corpo(publicacoes=[{"canal": "shopee", "status": "pausado"}] * 2),
            "condicao": corpo(condicao="seminovo"),
            "preco negativo": corpo(preco_centavos=-1),
            "id do corpo": corpo("a.b"),
        }
        for nome, dados in casos.items():
            with self.subTest(nome):
                resp = self.cliente.put("/api/produtos/a_1", json=dados)
                self.assertEqual(resp.status_code, 422)
        for caminho in ("/api/produtos/a%2Fb", "/api/produtos/a.b", "/api/produtos/..%2F..", "/api/produtos/a/b"):
            with self.subTest(caminho):
                self.assertIn(self.cliente.put(caminho, json=corpo()).status_code, (404, 405, 422))
        self.assertEqual(self.cliente.get("/api/produtos").json(), {"produtos": []})

    def test_422_nao_ecoa_o_corpo(self):
        resp = self.put(corpo(fotos=["data:image/jpeg;base64,SEGREDO_DO_CORPO"]))
        self.assertEqual(resp.status_code, 422)
        self.assertNotIn("SEGREDO_DO_CORPO", resp.text)
        self.assertEqual(resp.json()["erro"]["codigo"], "parametro_invalido")

    def test_corpo_acima_de_512_kb_413(self):
        grande = corpo(descricao="x" * (512 * 1024))
        resp = self.put(grande)
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(resp.json()["erro"]["codigo"], "pedido_grande_demais")

        def em_pedacos():  # sem Content-Length: conta os bytes lidos
            for _ in range(9):
                yield b"x" * (64 * 1024)

        resp = self.cliente.put("/api/produtos/a_1", content=em_pedacos(),
                                headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(self.cliente.get("/api/produtos").json(), {"produtos": []})

    def test_corpo_abaixo_do_limite_passa(self):
        self.assertEqual(self.put(corpo(descricao="x" * 50_000)).status_code, 200)


if __name__ == "__main__":
    unittest.main()
