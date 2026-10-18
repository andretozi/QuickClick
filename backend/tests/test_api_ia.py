"""IA no criar anúncio, de ponta a ponta pela API, com provedores falsos (sem rede) e o executor na hora."""

import copy
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.bootstrap import configuracao_da_ia, criar_app
from backend.application.ia.escolha import ProvedoresDeIA
from backend.application.ia.etapas import DependenciasDaAnalise, ProcessoDaAnalise
from backend.application.ia.modelos import (
    ArquivoDeFoto,
    CategoriaSugerida,
    ConfiguracaoDaIA,
    FalhaDoProvedor,
    Fidelidade,
    PrecoObservado,
    RespostaDaIA,
)
from backend.domain.ia.atributos_ml import AtributoML
from backend.domain.ia.escrita import problemas_de_escrita
from backend.infrastructure.banco import models
from backend.infrastructure.configuracao import Config
from backend.infrastructure.database import Base
from backend.infrastructure.ia.preparador_pillow import PillowPreparador
from backend.infrastructure.ia.sem_tratamento import SemTratamento, SemVerificacaoDeFidelidade
from backend.tests import leitor_de_teste
from backend.tests.test_api import CHAVE_CRIPTO_TESTE, SEGREDO_JWT_TESTE
from backend.tests.test_provedores_ia import foto_com_detalhes, jpeg

LEITURA = {
    "reconhecido": True, "motivo_nao_reconhecido": "", "produto": "Tênis de corrida", "categoria": "calcados",
    "termos_busca": ["tenis corrida"],
    "atributos": [
        {"chave": "marca", "valor": "Nike", "origem": "foto", "evidencia": "logo", "confianca": "alta"},
        {"chave": "cor", "valor": "azul", "origem": "deducao", "evidencia": "cabedal", "confianca": "media"},
        {"chave": "tamanho", "valor": "", "origem": "desconhecido", "evidencia": "", "confianca": "baixa"},
    ],
    "condicao": {"valor": "usado", "sinais": ["sola gasta"], "confianca": "alta"},
    "defeitos_visiveis": ["risco no bico"], "texto_legivel": ["NIKE"], "etiqueta_ilegivel": [],
    "perguntas": [{"chave": "tamanho", "pergunta": "Qual é a numeração?", "sugerir_foto": "etiqueta"}],
}
ETIQUETA = {"texto_legivel": ["TAM 42"], "defeitos_visiveis": [], "atributos": [
    {"chave": "tamanho", "valor": "42", "origem": "etiqueta", "evidencia": "TAM 42", "confianca": "alta"}]}
TEXTO = {"titulo": "Tênis de corrida Nike azul usado", "descricao": "Tênis Nike de corrida, usado.\n\nMarca: Nike",
         "especificacoes": [{"rotulo": "Marca", "valor": "Nike"}]}


class Falso:
    def __init__(self, nome, respostas=None, falha=False):
        self.nome, self.respostas, self.falha, self.chamadas = nome, respostas or {}, falha, []

    def disponivel(self):
        return True

    def _responder(self, metodo, *args):
        self.chamadas.append(metodo)
        if self.falha:
            raise FalhaDoProvedor(self.nome, "fora do ar")
        return RespostaDaIA(copy.deepcopy(self.respostas[metodo]), "falso", self.nome)

    def ler(self, entrada, contexto):
        return self._responder("ler", entrada)

    def reler(self, entrada, contexto):
        return self._responder("reler", entrada)

    def pesquisar(self, entrada, contexto):
        return self._responder("pesquisar", entrada)

    def precificar(self, entrada, contexto):
        return self._responder("precificar", entrada)

    def buscar_precos(self, *args):
        return self._responder("buscar_precos")

    def escrever(self, entrada, contexto):
        return self._responder("escrever", entrada)

    def corrigir(self, texto, trechos, contexto):
        return self._responder("corrigir", texto)

    def ligar(self, sobras, da_categoria, contexto):
        return self._responder("ligar")


class ExecutorImediato:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


class FonteMLFalsa:
    def __init__(self, precos=None):
        self.precos = precos

    def descobrir_categoria(self, termos, token):
        return CategoriaSugerida("MLB23262", "Tênis", "Tênis")

    def atributos_da_categoria(self, categoria_id, token):
        return [AtributoML("BRAND", "Marca", True), AtributoML("SIZE", "Tamanho", True)]

    def buscar_parecidos(self, termos, categoria_id, condicao, token):
        return self.precos

    def tarifa(self, preco_centavos, categoria_id, token):
        return preco_centavos // 10


def leitores(leitura=LEITURA):
    return {"ler": leitura, "reler": ETIQUETA}


class BaseIA(unittest.TestCase):
    plano = "gratis"

    def montar(self, provedores, fonte_ml=None, **config):
        self._pasta = tempfile.TemporaryDirectory()
        raiz = Path(self._pasta.name)
        front = raiz / "frontend" / "dist"
        front.mkdir(parents=True)
        (front / "index.html").write_text("<!doctype html>", encoding="utf-8")
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                                    poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.agora = datetime(2026, 10, 17, 15, 0, tzinfo=UTC)
        leitor = leitor_de_teste(QUICKCLICK_JWT_SECRET=SEGREDO_JWT_TESTE, TOKENS_CHAVE_CRIPTO=CHAVE_CRIPTO_TESTE,
                                 **config)
        self.app = criar_app(Config(raiz=raiz, pasta_front=front), session_factory=self.Session, leitor=leitor,
                             provedores=provedores, fonte_ml=fonte_ml, executor=ExecutorImediato(),
                             relogio=lambda: self.agora)
        self.cliente = TestClient(self.app)
        self.token = self._cadastrar("vendedor@quickclick.com.br")
        self.cliente.headers["Authorization"] = f"Bearer {self.token}"
        self._trocar_plano(1, self.plano)

    def tearDown(self):
        self.cliente.close()
        self.engine.dispose()
        self._pasta.cleanup()

    def _cadastrar(self, email):
        resposta = self.cliente.post("/api/auth/register", json={"nome": "Loja", "email": email, "loja": "Loja",
                                                                 "senha": "senha_segura_123", "maior_de_idade": True})
        return resposta.json()["token"]

    def _trocar_plano(self, vendedor_id, plano):
        with self.Session() as sessao:
            sessao.query(models.VendedorModel).filter_by(id=vendedor_id).update({"plano": plano})
            sessao.commit()

    def fotos(self, quantas=2, campo="fotos"):
        return [(campo, (f"foto{i}.jpg", jpeg(foto_com_detalhes()), "image/jpeg")) for i in range(quantas)]

    def criar(self, quantas=2):
        return self.cliente.post("/api/ia/analises", files=self.fotos(quantas))

    def analise(self, analise_id):
        return self.cliente.get(f"/api/ia/analises/{analise_id}").json()

    def confirmar(self, analise_id, extra=None):
        corpo = {"produto": "Tênis de corrida", "categoria": "calcados", "condicao": "usado",
                 "atributos": [{"chave": "marca", "valor": "Nike"}, {"chave": "tamanho", "valor": "42"}],
                 "defeitos": ["risco no bico"], **(extra or {})}
        return self.cliente.post(f"/api/ia/analises/{analise_id}/confirmacao", json=corpo)


class TestPlanoGratis(BaseIA):
    def setUp(self):
        self.gemini = Falso("gemini", {**leitores(), "escrever": TEXTO})
        self.haiku = Falso("haiku", {**leitores(), "pesquisar": {"perfil_comprador": "Corredor amador.",
                                                                 "o_que_valoriza": ["leveza"], "objecoes": [],
                                                                 "termos_que_usam": ["tenis de corrida"]},
                                     "escrever": TEXTO, "corrigir": TEXTO})
        self.opus = Falso("opus", leitores())
        self.montar(ProvedoresDeIA(leitor_visao_pago=self.opus, leitor_gemini_gratis=self.gemini,
                                   leitor_rapido_gratis=self.haiku, pesquisador_gratis=self.haiku,
                                   redator_gemini_gratis=self.gemini, redator_rapido_gratis=self.haiku))

    def test_cota_do_gratis(self):
        cota = self.cliente.get("/api/ia/cota").json()
        self.assertEqual((cota["plano"], cota["nivel"], cota["restantes"], cota["disponivel"]), ("gratis", "gratis", 5, True))
        self.assertFalse(cota["tem"]["pesquisa_de_mercado"])
        self.assertTrue(cota["aviso_de_dados_no_gratis"])

    def test_fluxo_completo_no_gratis_usa_gemini_e_preco_so_por_regra(self):
        resposta = self.criar()
        self.assertEqual(resposta.status_code, 202)
        analise_id = resposta.json()["id"]
        analise = self.analise(analise_id)
        self.assertEqual(analise["status"], "aguardando_confirmacao")
        self.assertEqual(self.gemini.chamadas, ["ler"])
        self.assertEqual(self.opus.chamadas, [])
        self.assertEqual([a["cartao"] for a in analise["leitura"]["atributos"]], ["a_ia_viu", "confere", "pergunta"])
        self.assertEqual(analise["fotos"][0], {"indice": 0, "qualidade": "ok", "largura": 1200, "altura": 900})

        pronta = self.confirmar(analise_id).json()
        self.assertEqual(pronta["status"], "pronta")
        self.assertLessEqual(len(pronta["texto"]["titulo"]), 60)
        self.assertTrue(pronta["preco"]["sem_dados"])  # sem Mercado Livre e sem web no Grátis
        self.assertIn("mercado-livre", [c["slug"] for c in pronta["canais"]])
        self.assertIsNone(pronta["pesquisa"])  # o perfil aparece só no pago
        self.assertEqual(self.cliente.get("/api/ia/cota").json()["usadas_no_mes"], 1)

    def test_gemini_fora_do_ar_usa_o_haiku(self):
        self.gemini.falha = True
        analise_id = self.criar().json()["id"]
        self.assertEqual(self.analise(analise_id)["status"], "aguardando_confirmacao")
        self.assertEqual(self.haiku.chamadas[0], "ler")

    def test_foto_invalida_e_fotos_demais(self):
        ruim = self.cliente.post("/api/ia/analises", files=[("fotos", ("a.jpg", b"nao e foto", "image/jpeg"))])
        self.assertEqual((ruim.status_code, ruim.json()["erro"]["codigo"]), (400, "foto_invalida"))
        demais = self.criar(quantas=7)
        self.assertEqual(demais.json()["erro"]["codigo"], "foto_invalida")
        sem = self.cliente.post("/api/ia/analises")
        self.assertEqual(sem.status_code, 400)

    def test_cota_esgotada(self):
        with self.Session() as sessao:
            for i in range(5):
                sessao.add(models.AnaliseIAModel(id=f"p{i}", vendedor_id=1, plano_no_momento="gratis", nivel="gratis",
                                                 status="pronta", criado_em=self.agora, atualizado_em=self.agora,
                                                 concluida_em=self.agora - timedelta(hours=2)))
            sessao.commit()
        resposta = self.criar()
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (403, "cota_esgotada"))

    def test_uma_por_vez_e_dez_por_hora(self):
        with self.Session() as sessao:
            sessao.add(models.AnaliseIAModel(id="rodando", vendedor_id=1, plano_no_momento="gratis", nivel="gratis",
                                             status="lendo_produto", criado_em=self.agora, atualizado_em=self.agora))
            sessao.commit()
        self.assertEqual(self.criar().json()["erro"]["codigo"], "analise_em_andamento")
        with self.Session() as sessao:
            sessao.query(models.AnaliseIAModel).filter_by(id="rodando").update({"status": "falhou"})
            for i in range(9):
                sessao.add(models.AnaliseIAModel(id=f"h{i}", vendedor_id=1, plano_no_momento="gratis", nivel="gratis",
                                                 status="falhou", criado_em=self.agora - timedelta(minutes=5),
                                                 atualizado_em=self.agora))
            sessao.commit()
        resposta = self.criar()
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (429, "limite_por_hora"))

    def test_analise_de_outra_conta_nao_aparece(self):
        analise_id = self.criar().json()["id"]
        outro = self._cadastrar("outra@quickclick.com.br")
        resposta = self.cliente.get(f"/api/ia/analises/{analise_id}", headers={"Authorization": f"Bearer {outro}"})
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (404, "analise_nao_encontrada"))

    def test_sem_token_401(self):
        self.assertEqual(self.cliente.get("/api/ia/cota", headers={"Authorization": ""}).status_code, 401)

    def test_foto_extra_da_etiqueta_preenche_o_tamanho(self):
        analise_id = self.criar().json()["id"]
        resposta = self.cliente.post(f"/api/ia/analises/{analise_id}/fotos", data={"tipo": "etiqueta"},
                                     files=self.fotos(1, campo="foto"))
        self.assertEqual(resposta.status_code, 200)
        analise = self.analise(analise_id)
        tamanho = next(a for a in analise["leitura"]["atributos"] if a["chave"] == "tamanho")
        self.assertEqual((tamanho["valor"], tamanho["cartao"]), ("42", "a_ia_viu"))
        self.assertEqual(len(analise["fotos"]), 3)
        self.assertEqual(analise["status"], "aguardando_confirmacao")

    def test_confirmar_fora_de_hora(self):
        analise_id = self.criar().json()["id"]
        self.confirmar(analise_id)
        segunda = self.confirmar(analise_id)
        self.assertEqual((segunda.status_code, segunda.json()["erro"]["codigo"]), (409, "estado_da_analise_invalido"))

    def test_leitura_falha_e_retomada_pede_as_fotos(self):
        self.gemini.falha = self.haiku.falha = True
        analise_id = self.criar().json()["id"]
        analise = self.analise(analise_id)
        self.assertEqual((analise["status"], analise["erro"]["codigo"]), ("falhou", "ia_indisponivel"))
        self.assertTrue(analise["precisa_fotos_para_retomar"])
        self.assertEqual(self.cliente.get("/api/ia/cota").json()["usadas_no_mes"], 0)  # falha não conta
        sem_fotos = self.cliente.post(f"/api/ia/analises/{analise_id}/retomar")
        self.assertEqual(sem_fotos.json()["erro"]["codigo"], "fotos_necessarias")
        self.gemini.falha = False
        retomada = self.cliente.post(f"/api/ia/analises/{analise_id}/retomar", files=self.fotos(2))
        self.assertEqual(retomada.json()["status"], "aguardando_confirmacao")

    def test_produto_nao_reconhecido_avisa(self):
        self.gemini.respostas["ler"] = {**LEITURA, "reconhecido": False, "motivo_nao_reconhecido": "paisagem"}
        analise = self.analise(self.criar().json()["id"])
        self.assertEqual(analise["leitura"]["atributos"], [])
        self.assertIn("produto_nao_reconhecido", [a["codigo"] for a in analise["avisos"]])

    def test_texto_fora_da_regra_e_corrigido_e_por_fim_limpo_no_python(self):
        ruim = {"titulo": "Tênis Nike — azul / usado 😀", "descricao": "Ótimo tênis — confortável\n- leve",
                "especificacoes": [{"rotulo": "Cor", "valor": "azul/branco"}]}
        self.gemini.respostas["escrever"] = ruim
        self.haiku.respostas["corrigir"] = ruim  # a correção também falha
        analise_id = self.criar().json()["id"]
        texto = self.confirmar(analise_id).json()["texto"]
        self.assertEqual(self.haiku.chamadas.count("corrigir"), 1)
        self.assertTrue(texto["corrigido"])
        for parte in (texto["titulo"], texto["descricao"], texto["especificacoes"][0]["valor"]):
            self.assertEqual(problemas_de_escrita(parte), [], parte)

    def test_nada_da_foto_vai_para_o_banco(self):
        analise_id = self.criar().json()["id"]
        with self.Session() as sessao:
            linha = sessao.get(models.AnaliseIAModel, analise_id)
            self.assertEqual(set(linha.fotos_meta[0]), {"indice", "qualidade", "largura", "altura"})
            self.assertNotIn("base64", str(linha.leitura))


class TestPlanoPago(BaseIA):
    plano = "pro"

    def setUp(self):
        self.opus = Falso("opus", {**leitores({**LEITURA, "etiqueta_ilegivel": [{"foto": 0, "caixa": [100, 100, 400, 300]}]}),
                                   "precificar": {"preco_sugerido_centavos": 15990, "faixa": {"min": 14000, "max": 17000},
                                                  "estrategia": "equilibrado", "justificativa": "Perto da mediana.",
                                                  "alertas": [], "canais": [{"slug": "mercado-livre",
                                                                             "motivo": "Maior público de tênis."}]}})
        self.sonnet = Falso("sonnet", {"pesquisar": {"perfil_comprador": "Corredor amador.", "o_que_valoriza": ["leveza"],
                                                     "objecoes": ["tamanho"], "termos_que_usam": ["tenis corrida"],
                                                     "fontes": ["https://exemplo.com.br"]},
                                       "escrever": TEXTO,
                                       "buscar_precos": {"itens": [{"preco_centavos": p, "frete_gratis": True, "url": "x"}
                                                                   for p in (14000, 15000, 16000, 17000, 15500)]}})
        self.fonte = FonteMLFalsa()
        self.gemini = Falso("gemini", leitores())
        self.montar(ProvedoresDeIA(leitor_visao_pago=self.opus, pesquisador_pago=self.sonnet,
                                   precificador_pago=self.opus, precos_na_web_pago=self.sonnet, redator_pago=self.sonnet,
                                   leitor_gemini_gratis=self.gemini),
                    fonte_ml=self.fonte)

    def test_fluxo_pago_com_releitura_da_etiqueta_pesquisa_preco_pela_web_e_canais(self):
        analise_id = self.criar().json()["id"]
        analise = self.analise(analise_id)
        self.assertEqual(self.opus.chamadas[:2], ["ler", "reler"])
        tamanho = next(a for a in analise["leitura"]["atributos"] if a["chave"] == "tamanho")
        self.assertEqual(tamanho["valor"], "42")

        pronta = self.confirmar(analise_id).json()
        self.assertEqual(pronta["status"], "pronta")
        self.assertEqual(pronta["pesquisa"]["perfil_comprador"], "Corredor amador.")
        preco = pronta["preco"]
        self.assertEqual((preco["fonte"], preco["por_ia"], preco["sugerido_centavos"]), ("web", True, 15990))
        self.assertEqual(preco["mercado"]["quantidade"], 5)
        self.assertEqual(pronta["canais"][0]["motivo"], "Maior público de tênis.")

    def test_pesquisa_vem_do_cache_na_segunda_analise(self):
        for _ in range(2):
            analise_id = self.criar().json()["id"]
            self.confirmar(analise_id)
        self.assertEqual(self.sonnet.chamadas.count("pesquisar"), 1)

    def test_preco_da_ia_fora_dos_dados_reais_fica_o_da_regra(self):
        self.opus.respostas["precificar"]["preco_sugerido_centavos"] = 99_000_00
        analise_id = self.criar().json()["id"]
        preco = self.confirmar(analise_id).json()["preco"]
        self.assertFalse(preco["por_ia"])
        self.assertLess(preco["sugerido_centavos"], 20000)

    def test_orcamento_do_dia_estourado_cai_no_gratis_com_aviso(self):
        with self.Session() as sessao:
            sessao.add(models.UsoIAModel(etapa="leitura", provedor="anthropic", modelo="claude-opus-5-5",
                                         tokens_entrada=0, tokens_saida=0, cache_lido=0, cache_gravado=0, buscas_web=0,
                                         custo_estimado_usd=Decimal("0.50"), duracao_ms=1, criado_em=self.agora))
            sessao.commit()
        cota = self.cliente.get("/api/ia/cota").json()
        self.assertEqual((cota["orcamento_do_dia_estourado"], cota["nivel"], cota["nivel_agora"]), (True, "pago", "gratis"))
        analise = self.analise(self.criar().json()["id"])
        self.assertEqual(analise["nivel"], "gratis")
        self.assertIn("orcamento_do_dia", [a["codigo"] for a in analise["avisos"]])
        self.assertEqual((self.gemini.chamadas, self.opus.chamadas), (["ler"], []))

    def test_interrompida_na_partida_e_retomada_sem_fotos_depois_da_leitura(self):
        analise_id = self.criar().json()["id"]
        self.confirmar(analise_id)
        with self.Session() as sessao:
            sessao.query(models.AnaliseIAModel).filter_by(id=analise_id).update(
                {"status": "escrevendo", "etapa_atual": "escrevendo", "atualizado_em": self.agora - timedelta(minutes=30)})
            sessao.commit()
        from backend.infrastructure.banco.repositorio_ia import RepositorioDeAnalisesSQL

        self.assertEqual(RepositorioDeAnalisesSQL(self.Session).marcar_paradas_como_interrompidas(self.agora), 1)
        interrompida = self.analise(analise_id)
        self.assertEqual((interrompida["status"], interrompida["erro"]["codigo"]), ("interrompida", "interrompida"))
        self.assertFalse(interrompida["precisa_fotos_para_retomar"])
        retomada = self.cliente.post(f"/api/ia/analises/{analise_id}/retomar")
        self.assertEqual(retomada.json()["status"], "pronta")


class TestSemIA(BaseIA):
    def setUp(self):
        self.montar(ProvedoresDeIA())

    def test_sem_provedor_a_cota_avisa_e_criar_da_503(self):
        cota = self.cliente.get("/api/ia/cota").json()
        self.assertEqual((cota["disponivel"], cota["motivo_indisponivel"]), (False, "provedor_indisponivel"))
        resposta = self.criar()
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (503, "ia_indisponivel"))


class TestIADesligada(BaseIA):
    def setUp(self):
        self.montar(ProvedoresDeIA(leitor_gemini_gratis=Falso("gemini", leitores())), IA_ATIVA="false")

    def test_ia_ativa_false(self):
        self.assertEqual(self.cliente.get("/api/ia/cota").json()["motivo_indisponivel"], "ia_desligada")
        self.assertEqual(self.criar().json()["erro"]["codigo"], "ia_indisponivel")


if __name__ == "__main__":
    unittest.main()


class RepositorioDeAnalisesEmMemoria:
    """Guarda a análise e a ordem dos estados por onde ela passou."""

    def __init__(self, analise):
        self.analise = dict(analise)
        self.estados = []

    def obter(self, analise_id):
        return dict(self.analise)

    def atualizar(self, analise_id, campos):
        self.analise.update(campos)
        if "status" in campos:
            self.estados.append(campos["status"])


class TratadorQueAnota:
    def __init__(self, ordem):
        self.ordem = ordem

    def tratar(self, foto, contexto):
        self.ordem.append(("tratar", foto.indice))
        return replace(foto, leitura_jpeg=b"tratada")


class GuardiaoQueAnota:
    def __init__(self, ordem, resultado):
        self.ordem, self.resultado = ordem, resultado

    def verificar(self, original, tratada, contexto):
        self.ordem.append(("verificar", original.indice))
        return self.resultado


class LeitorQueAnota(Falso):
    def __init__(self, ordem):
        super().__init__("leitor", leitores())
        self.ordem = ordem
        self.fotos_lidas = []

    def ler(self, entrada, contexto):
        self.ordem.append(("ler", len(entrada.fotos)))
        self.fotos_lidas = [f.leitura_jpeg for f in entrada.fotos]
        return super().ler(entrada, contexto)


class TestEncaixeDaVersaoFinal(unittest.TestCase):
    """Parte 9: tratar, depois verificar, depois ler; no MVP (interruptor desligado) a foto passa igual."""

    def processar(self, ativo, ordem=None, tratador=None, guardiao=None):
        self.repo = RepositorioDeAnalisesEmMemoria({"id": "a1", "vendedor_id": 1, "nivel": "gratis", "avisos": []})
        self.leitor = LeitorQueAnota([] if ordem is None else ordem)
        fotos = PillowPreparador().preparar([ArquivoDeFoto(f"{i}.jpg", jpeg(foto_com_detalhes())) for i in range(2)])
        self.originais = [f.leitura_jpeg for f in fotos]
        dependencias = DependenciasDaAnalise(
            analises=self.repo, preparador=PillowPreparador(), tratador=tratador or SemTratamento(),
            guardiao=guardiao or SemVerificacaoDeFidelidade(),
            provedores=ProvedoresDeIA(leitor_gemini_gratis=self.leitor), fonte_ml=None, contas=None, pesquisas=None,
            config=ConfiguracaoDaIA(tratamento_foto_ativo=ativo), relogio=lambda: datetime(2026, 10, 18, tzinfo=UTC))
        ProcessoDaAnalise(dependencias).ler("a1", fotos)

    def test_mvp_sem_tratamento_le_a_foto_original_e_pula_os_estados_novos(self):
        self.processar(ativo=False)
        self.assertEqual(self.repo.estados, ["preparando_fotos", "lendo_produto", "aguardando_confirmacao"])
        self.assertEqual(self.leitor.fotos_lidas, self.originais)
        self.assertEqual(self.repo.analise["avisos"], [])

    def test_ligado_trata_verifica_e_so_depois_le_a_foto_tratada(self):
        ordem = []
        self.processar(ativo=True, ordem=ordem, tratador=TratadorQueAnota(ordem),
                       guardiao=GuardiaoQueAnota(ordem, Fidelidade.FIEL))
        self.assertEqual(ordem, [("tratar", 0), ("tratar", 1), ("verificar", 0), ("verificar", 1), ("ler", 2)])
        self.assertEqual(self.repo.estados, ["preparando_fotos", "tratando_fotos", "verificando_fotos", "lendo_produto",
                                             "aguardando_confirmacao"])
        self.assertEqual(self.leitor.fotos_lidas, [b"tratada", b"tratada"])

    def test_fidelidade_grave_le_a_original_e_avisa(self):
        self.processar(ativo=True, tratador=TratadorQueAnota([]), guardiao=GuardiaoQueAnota([], Fidelidade.GRAVE))
        self.assertEqual(self.leitor.fotos_lidas, self.originais)
        self.assertEqual([a["codigo"] for a in self.repo.analise["avisos"]], ["tratamento_descartado"])

    def test_interruptor_vem_desligado_e_liga_pela_configuracao(self):
        self.assertFalse(configuracao_da_ia(leitor_de_teste()).tratamento_foto_ativo)
        self.assertTrue(configuracao_da_ia(leitor_de_teste(TRATAMENTO_FOTO_ATIVO="true")).tratamento_foto_ativo)
