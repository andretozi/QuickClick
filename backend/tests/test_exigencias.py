"""Fase 2 do multicanal: união das exigências dos canais, faltantes, GTIN e embalagem na leitura, releitura
dirigida no processo da análise e campos próprios na confirmação."""

import copy
import unittest
from datetime import UTC, datetime
from decimal import Decimal

from backend.application.ia.escolha import ProvedoresDeIA
from backend.application.ia.etapas import DependenciasDaAnalise, ProcessoDaAnalise, _fatos, _sugestao
from backend.application.ia.modelos import CategoriaSugerida, ConfiguracaoDaIA, FalhaDoProvedor, FotoPreparada
from backend.domain.canais.esquema import CampoDoCanal, EsquemaDoCanal, TipoDeCampo
from backend.domain.canais.exigencias import faltantes, unir_exigencias
from backend.domain.canais.ficha import montar_ficha
from backend.domain.ia.atributos_ml import AtributoML, esquema_do_ml, perguntas_dos_obrigatorios
from backend.domain.ia.leitura import (
    CampoProprioConfirmado,
    Confianca,
    OrigemAtributo,
    normalizar_confirmacao,
    normalizar_leitura,
)
from backend.infrastructure.ia.sem_tratamento import SemTratamento, SemVerificacaoDeFidelidade
from backend.presentation.http.esquemas import RequisicaoConfirmacaoIA
from backend.tests.test_api_ia import Falso, RepositorioDeAnalisesEmMemoria

ML, SHOPEE = "mercado-livre", "shopee"
T, N, L, B = TipoDeCampo.TEXTO, TipoDeCampo.NUMERO, TipoDeCampo.LISTA, TipoDeCampo.BOOLEANO


def campo(canal, id_, chave, tipo=T, obrigatorio=True, valores=(), unidade="", nome=None):
    return CampoDoCanal(canal, id_, nome or id_, obrigatorio, tipo, tuple((n, n) for n in valores), unidade, chave)


def esquema(canal, *campos):
    return EsquemaDoCanal(canal, "CAT", "", tuple(campos))


class TestUnirExigencias(unittest.TestCase):
    def test_chave_comum_entre_ml_e_shopee_vira_uma_so(self):
        uniao = unir_exigencias([esquema(ML, campo(ML, "BRAND", "marca", nome="Marca", obrigatorio=False)),
                                 esquema(SHOPEE, campo(SHOPEE, "10", "marca", nome="Brand"))])
        self.assertEqual([(e.chave, e.nome, e.canais, e.obrigatoria, e.tipo) for e in uniao],
                         [("marca", "Marca", (ML, SHOPEE), True, T)])
        self.assertEqual([c.id for c in uniao[0].campos], ["BRAND", "10"])

    def test_listas_ficam_com_os_nomes_em_comum_na_grafia_do_primeiro(self):
        uniao = unir_exigencias([esquema(ML, campo(ML, "COLOR", "cor", L, valores=("Azul", "Preto", "Branco"))),
                                 esquema(SHOPEE, campo(SHOPEE, "2", "cor", L, valores=("BRANCO ", "azúl", "Verde")))])
        self.assertEqual([(e.chave, e.tipo, e.valores) for e in uniao], [("cor", L, ("Azul", "Branco"))])

    def test_listas_sem_nome_em_comum_viram_campo_proprio_por_canal_na_posicao_da_chave(self):
        uniao = unir_exigencias([
            esquema(ML, campo(ML, "BRAND", "marca"), campo(ML, "COLOR", "cor", L, valores=("Preto",)),
                    campo(ML, "SIZE", "tamanho")),
            esquema(SHOPEE, campo(SHOPEE, "2", "cor", L, valores=("Verde",))),
        ])
        self.assertEqual([(e.chave, e.canais, e.valores) for e in uniao],
                         [("marca", (ML,), ()), ("", (ML,), ("Preto",)), ("", (SHOPEE,), ("Verde",)),
                          ("tamanho", (ML,), ())])
        self.assertEqual([c.chave for c in uniao[1].campos + uniao[2].campos], ["cor", "cor"])

    def test_lista_num_canal_e_texto_no_outro_vale_a_lista(self):
        uniao = unir_exigencias([esquema(ML, campo(ML, "GENDER", "genero")),
                                 esquema(SHOPEE, campo(SHOPEE, "7", "genero", L, valores=("Masculino", "Feminino")))])
        self.assertEqual([(e.tipo, e.valores, e.canais) for e in uniao], [(L, ("Masculino", "Feminino"), (ML, SHOPEE))])

    def test_numero_com_unidades_diferentes_fica_com_a_do_primeiro_canal_numerico(self):
        uniao = unir_exigencias([esquema(ML, campo(ML, "W", "peso_g", T), campo(ML, "LED", "tem_led", T)),
                                 esquema(SHOPEE, campo(SHOPEE, "3", "peso_g", N, unidade="kg"),
                                         campo(SHOPEE, "4", "tem_led", B, valores=("Sim", "Não"))),
                                 esquema("amazon", campo("amazon", "w", "peso_g", N, unidade="g"))])
        self.assertEqual([(e.chave, e.tipo, e.unidade, e.valores) for e in uniao],
                         [("peso_g", N, "kg", ()), ("tem_led", B, "", ("Sim", "Não"))])
        self.assertEqual(uniao[0].canais, (ML, SHOPEE, "amazon"))

    def test_campo_sem_chave_e_exigencia_propria_e_a_ordem_segue_o_primeiro_esquema(self):
        uniao = unir_exigencias([esquema(ML, campo(ML, "BRAND", "marca")),
                                 esquema(SHOPEE, campo(SHOPEE, "100017", "", nome="Tipo de garantia"),
                                         campo(SHOPEE, "100018", "", obrigatorio=False), campo(SHOPEE, "1", "marca"))])
        self.assertEqual([(e.chave, e.canais, [c.id for c in e.campos]) for e in uniao],
                         [("marca", (ML, SHOPEE), ["BRAND", "1"]), ("", (SHOPEE,), ["100017"]),
                          ("", (SHOPEE,), ["100018"])])
        self.assertEqual(uniao[1].nome, "Tipo de garantia")


class TestFaltantes(unittest.TestCase):
    def test_so_confirmado_conta_e_campo_proprio_obrigatorio_sempre_falta(self):
        uniao = unir_exigencias([esquema(SHOPEE, campo(SHOPEE, "1", "marca"), campo(SHOPEE, "2", "cor"),
                                         campo(SHOPEE, "3", "estampa", obrigatorio=False),
                                         campo(SHOPEE, "9", ""))])
        leitura = normalizar_leitura({"reconhecido": True, "atributos": [
            {"chave": "marca", "valor": "Nike", "origem": "foto", "evidencia": "logo", "confianca": "alta"},
            {"chave": "cor", "valor": "Azul", "origem": "foto", "evidencia": "x", "confianca": "alta"}]}, 1)
        self.assertEqual([e.chave for e in faltantes(uniao, montar_ficha(leitura))], ["marca", "cor", ""])
        confirmacao = normalizar_confirmacao({"atributos": [{"chave": "cor", "valor": "Azul"}]}, leitura)
        self.assertEqual([e.chave for e in faltantes(uniao, montar_ficha(leitura, confirmacao))], ["marca", ""])


class TestLeituraComGtinEEmbalagem(unittest.TestCase):
    def ler(self, *atributos, perguntas=()):
        return normalizar_leitura({"reconhecido": True, "atributos": [
            {"chave": c, "valor": v, "origem": o, "evidencia": "x", "confianca": k} for c, v, o, k in atributos],
            "perguntas": list(perguntas)}, 1)

    def test_gtin_so_da_etiqueta_e_valido_guarda_normalizado(self):
        leitura = self.ler(("gtin", "400-6381 333931", "etiqueta", "alta"))
        self.assertEqual((leitura.atributo("gtin").valor, leitura.atributo("gtin").origem),
                         ("4006381333931", OrigemAtributo.ETIQUETA))

    def test_gtin_sem_etiqueta_ou_invalido_some_sem_virar_pergunta(self):
        for origem, valor in (("foto", "4006381333931"), ("deducao", "4006381333931"), ("etiqueta", "4006381333932"),
                              ("etiqueta", "")):
            with self.subTest(origem=origem, valor=valor):
                leitura = self.ler(("gtin", valor, origem, "alta"),
                                   perguntas=[{"chave": "gtin", "pergunta": "Qual o código?", "sugerir_foto": "verso"}])
                self.assertIsNone(leitura.atributo("gtin"))
                self.assertEqual(leitura.perguntas, ())

    def test_embalagem_sempre_deducao_no_maximo_media_e_numero_positivo(self):
        leitura = self.ler(("peso_g", "350 g", "foto", "alta"), ("comprimento_cm", "20,5", "etiqueta", "media"),
                           ("largura_cm", "0", "deducao", "media"), ("altura_cm", "1 m", "deducao", "media"),
                           ("dimensoes", "20 x 10 cm", "etiqueta", "alta"))
        peso, comprimento = leitura.atributo("peso_g"), leitura.atributo("comprimento_cm")
        self.assertEqual((peso.valor, peso.origem, peso.confianca), ("350 g", OrigemAtributo.DEDUCAO, Confianca.MEDIA))
        self.assertEqual((comprimento.origem, comprimento.confianca), (OrigemAtributo.DEDUCAO, Confianca.MEDIA))
        self.assertIsNone(leitura.atributo("largura_cm"))
        self.assertIsNone(leitura.atributo("altura_cm"))
        self.assertEqual(leitura.atributo("dimensoes").origem, OrigemAtributo.ETIQUETA)  # a do produto não muda


class TestConfirmacaoComCamposProprios(unittest.TestCase):
    def test_le_campos_proprios_sem_repetir_canal_e_id(self):
        confirmacao = normalizar_confirmacao({"campos_proprios": [
            {"canal": "shopee", "id": "100017", "valor": " Garantia  do vendedor "},
            {"canal": "shopee", "id": "100017", "valor": "outra"}, {"canal": "shopee", "id": "", "valor": "x"},
            {"canal": "shopee", "id": "9", "valor": ""}, "lixo"]}, None)
        self.assertEqual(confirmacao.campos_proprios, (CampoProprioConfirmado("shopee", "100017", "Garantia do vendedor"),))
        self.assertEqual(list(confirmacao.para_dict()["campos_proprios"]),
                         [{"canal": "shopee", "id": "100017", "valor": "Garantia do vendedor"}])
        self.assertEqual(normalizar_confirmacao({}, None).campos_proprios, ())

    def test_corpo_http_aceita_campos_proprios_opcionais(self):
        self.assertEqual(RequisicaoConfirmacaoIA().model_dump()["campos_proprios"], [])
        corpo = RequisicaoConfirmacaoIA(campos_proprios=[{"canal": "shopee", "id": "1", "valor": "Sim"}]).model_dump()
        self.assertEqual(corpo["campos_proprios"], [{"canal": "shopee", "id": "1", "valor": "Sim"}])


# ----------------------------------------------------------------------------------------------------------
# processo da análise com fontes de esquema falsas
# ----------------------------------------------------------------------------------------------------------

AGORA = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
LEITURA = {
    "reconhecido": True, "produto": "Tênis de corrida", "categoria": "calcados", "termos_busca": ["tenis corrida"],
    "atributos": [
        {"chave": "marca", "valor": "Nike", "origem": "foto", "evidencia": "logo", "confianca": "alta"},
        {"chave": "cor", "valor": "azul", "origem": "foto", "evidencia": "cabedal", "confianca": "media"},
        {"chave": "acabamento", "valor": "Fosco", "origem": "foto", "evidencia": "cabedal", "confianca": "media"},
        {"chave": "tamanho", "valor": "", "origem": "desconhecido", "evidencia": "", "confianca": "baixa"},
        {"chave": "peso_g", "valor": "350", "origem": "deducao", "evidencia": "tamanho", "confianca": "media"},
    ],
    "condicao": {"valor": "novo", "sinais": [], "confianca": "media"},
}
RELIDA = {"texto_legivel": ["TAM 42"], "defeitos_visiveis": [], "atributos": [
    {"chave": "tamanho", "valor": "42", "origem": "etiqueta", "evidencia": "TAM 42", "confianca": "alta"}]}
ATRIBUTOS_ML = [
    AtributoML("BRAND", "Marca", True, tipo_valor="string"),
    AtributoML("COLOR", "Cor", True, (("1", "Azul"), ("2", "Preto")), tipo_valor="list"),
    AtributoML("SIZE", "Tamanho", True, tipo_valor="string"),
    AtributoML("FOOTWEAR_TYPE", "Tipo de calçado", True),
    AtributoML("FINISH", "Acabamento externo", True),
    AtributoML("MATERIAL", "Material", False),
]


class FonteMLFalsa:
    def __init__(self, falha=False):
        self.falha = falha

    def descobrir_categoria(self, termos, token):
        return CategoriaSugerida("MLB23262", "Tênis")

    def atributos_da_categoria(self, categoria_id, token):
        return list(ATRIBUTOS_ML)

    def esquema(self, categoria_id, token, categoria_nome=""):
        return None if self.falha else esquema_do_ml(categoria_id, categoria_nome, ATRIBUTOS_ML)


class FonteShopeeFalsa:
    def __init__(self, falha=False):
        self.falha, self.categorias = falha, []

    def descobrir_categoria(self, termos, token):
        self.categorias.append(termos)
        return CategoriaSugerida("100", "Tênis")

    def esquema(self, categoria_id, token, categoria_nome=""):
        if self.falha:
            return None
        return EsquemaDoCanal(SHOPEE, categoria_id, categoria_nome, (
            campo(SHOPEE, "1", "marca", nome="Marca"),
            campo(SHOPEE, "2", "cor", L, valores=("azul", "Verde")),
            campo(SHOPEE, "3", "peso_g", N, unidade="g", nome="Peso"),
            campo(SHOPEE, "100017", "", nome="Tipo de garantia"),
            campo(SHOPEE, "4", "estampa", obrigatorio=False),
        ))


class ContasFalsas:
    def __init__(self, conectados):
        self._conectados = list(conectados)

    def conectados(self, vendedor_id):
        return list(self._conectados)

    def token_mercado_livre(self, vendedor_id):
        return self.token(vendedor_id, ML)

    def token(self, vendedor_id, canal):
        return f"token-{canal}" if canal in self._conectados else None


class LeitorFalso(Falso):
    def __init__(self, falha_na_releitura=False):
        super().__init__("leitor", {"ler": LEITURA, "reler": RELIDA,
                                    "ligar": {"ligacoes": [{"chave": "acabamento", "id_ml": "FINISH"}]}})
        self.falha_na_releitura = falha_na_releitura
        self.relidas = []

    def reler(self, entrada, contexto):
        self.relidas.append((entrada, contexto))
        if self.falha_na_releitura:
            raise FalhaDoProvedor(self.nome, "fora do ar")
        return super().reler(entrada, contexto)


class OrcamentoFalso:
    def __init__(self, gasto):
        self.gasto = gasto

    def gasto_de_hoje_usd(self, agora):
        return self.gasto


class TestProcessoComExigencias(unittest.TestCase):
    def processar(self, conectados=(ML, SHOPEE), fonte_ml=None, shopee=None, nivel="gratis", orcamento=None,
                  falha_na_releitura=False):
        self.leitor = LeitorFalso(falha_na_releitura)
        self.repo = RepositorioDeAnalisesEmMemoria({"id": "a1", "vendedor_id": 1, "nivel": nivel, "avisos": [],
                                                    "fotos_meta": [{"indice": 0}, {"indice": 1}]})
        self.fotos = tuple(FotoPreparada(i, b"foto%d" % i, b"detalhe") for i in range(2))
        fonte_ml = fonte_ml or FonteMLFalsa()
        self.shopee = shopee or FonteShopeeFalsa()
        self.processo = ProcessoDaAnalise(DependenciasDaAnalise(
            analises=self.repo, preparador=None, tratador=SemTratamento(), guardiao=SemVerificacaoDeFidelidade(),
            provedores=ProvedoresDeIA(leitor_visao_pago=self.leitor, leitor_gemini_gratis=self.leitor,
                                      ligador_pago=self.leitor, ligador_gratis=self.leitor),
            fonte_ml=fonte_ml, contas=ContasFalsas(conectados), pesquisas=None,
            config=ConfiguracaoDaIA(orcamento_diario_usd=Decimal("0.30")), relogio=lambda: AGORA,
            fontes_de_esquema={ML: fonte_ml, SHOPEE: self.shopee}, orcamento=orcamento))
        self.processo.ler("a1", list(self.fotos))
        self.assertEqual(self.repo.analise["status"], "aguardando_confirmacao")
        return self.repo.analise["leitura"]

    def test_ml_e_shopee_cada_chave_uma_vez_so_o_que_falta_com_sugestao_da_leitura(self):
        dados = self.processar()
        exigencias = dados["exigencias"]
        self.assertEqual([(e["chave"], e["canais"]) for e in exigencias], [
            ("marca", [ML, SHOPEE]), ("cor", [ML, SHOPEE]), ("tamanho", [ML]), ("tipo_de_calcado", [ML]),
            ("acabamento_externo", [ML]), ("peso_g", [SHOPEE]), ("", [SHOPEE])])
        por_chave = {e["chave"]: e for e in exigencias}
        self.assertEqual((por_chave["cor"]["tipo"], por_chave["cor"]["valores"]), ("lista", ["Azul"]))
        self.assertEqual((por_chave["peso_g"]["tipo"], por_chave["peso_g"]["unidade"]), ("numero", "g"))
        self.assertEqual(por_chave[""]["proprio"], {"canal": SHOPEE, "id": "100017"})
        self.assertEqual((por_chave[""]["nome"], por_chave[""]["sugestao"]), ("Tipo de garantia", None))
        self.assertTrue(all(e["obrigatoria"] and (e["proprio"] is None) == bool(e["chave"]) for e in exigencias))
        self.assertEqual(por_chave["marca"]["sugestao"], {"valor": "Nike", "origem": "foto", "confianca": "alta",
                                                          "cartao": "a_ia_viu", "chave_lida": "marca"})
        self.assertEqual(por_chave["cor"]["sugestao"]["valor"], "Azul")  # a grafia da lista
        self.assertEqual(por_chave["acabamento_externo"]["sugestao"]["chave_lida"], "acabamento")  # pelo mapa do ML
        self.assertEqual(por_chave["peso_g"]["sugestao"], {"valor": "350", "origem": "deducao", "confianca": "media",
                                                           "cartao": "confere", "chave_lida": "peso_g"})
        # Uma releitura dirigida, só com o que faltou sem sugestão e dá para ver em foto
        self.assertEqual(len(self.leitor.relidas), 1)
        entrada, contexto = self.leitor.relidas[0]
        self.assertEqual((entrada.tipo, entrada.campos, entrada.imagem_jpeg, entrada.fotos_da_leitura, contexto.etapa),
                         ("campos", ("tamanho", "tipo_de_calcado"), b"", self.fotos, "releitura_campos"))
        self.assertEqual(por_chave["tamanho"]["sugestao"], {"valor": "42", "origem": "etiqueta", "confianca": "alta",
                                                            "cartao": "a_ia_viu", "chave_lida": "tamanho"})
        self.assertIsNone(por_chave["tipo_de_calcado"]["sugestao"])
        # A releitura só entra nas sugestões: leitura, ML e perguntas ficam como estavam
        tamanho = next(a for a in dados["atributos"] if a["chave"] == "tamanho")
        self.assertEqual(tamanho["valor"], "")
        self.assertIn("tamanho", [p["chave"] for p in dados["perguntas"]])
        self.assertEqual(dados["ml"]["obrigatorios"], ["SIZE", "FOOTWEAR_TYPE"])
        self.assertNotIn("peso_g", dados["ml"]["mapa"])  # embalagem fora da ligação com o ML
        self.assertEqual(self.shopee.categorias, [["tenis corrida"]])

    def test_so_ml_sem_sugestao_bate_com_as_perguntas_dos_obrigatorios_de_hoje(self):
        dados = self.processar(conectados=(ML,), falha_na_releitura=True)
        sem_sugestao = [e["chave"] for e in dados["exigencias"] if e["sugestao"] is None]
        hoje = perguntas_dos_obrigatorios([a for a in ATRIBUTOS_ML if a.id in dados["ml"]["obrigatorios"]])
        self.assertEqual(sem_sugestao, [p["chave"] for p in hoje])
        self.assertEqual(sem_sugestao, ["tamanho", "tipo_de_calcado"])
        self.assertEqual(self.leitor.relidas[0][0].campos, ("tamanho", "tipo_de_calcado"))

    def test_canal_que_falha_deixa_sem_exigencias_e_a_analise_segue(self):
        for fonte_ml, shopee in ((FonteMLFalsa(falha=True), None), (None, FonteShopeeFalsa(falha=True))):
            with self.subTest(ml_falha=fonte_ml is not None):
                dados = self.processar(fonte_ml=fonte_ml, shopee=shopee)
                self.assertNotIn("exigencias", dados)
                self.assertIn("ml", dados)
                self.assertEqual(self.leitor.relidas, [])

    def test_o_que_a_publicacao_do_ml_completa_nao_trava_e_fica_a_pergunta_de_hoje(self):
        com_gtin = [*ATRIBUTOS_ML, AtributoML("GTIN", "Código universal de produto", True)]

        class MLComGtin(FonteMLFalsa):
            def atributos_da_categoria(self, categoria_id, token):
                return list(com_gtin)

            def esquema(self, categoria_id, token, categoria_nome=""):
                return esquema_do_ml(categoria_id, categoria_nome, com_gtin)

        dados = self.processar(conectados=(ML,), fonte_ml=MLComGtin(), falha_na_releitura=True)
        chaves = [e["chave"] for e in dados["exigencias"]]
        self.assertNotIn("codigo_universal_de_produto", chaves)
        self.assertNotIn("marca", chaves)  # BRAND: a publicação usa a marca lida ou "Genérica"
        self.assertIn("codigo_universal_de_produto", [p["chave"] for p in dados["perguntas"]])

    def test_gtin_e_embalagem_nao_viram_fato_no_texto(self):
        confirmacao = normalizar_confirmacao({"atributos": [
            {"chave": "cor", "valor": "Azul"}, {"chave": "peso_g", "valor": "350 g"},
            {"chave": "gtin", "valor": "7891234567895"}]}, None)
        self.assertEqual(_fatos(confirmacao), (("cor", "Azul"),))

    def test_fonte_que_quebra_vira_nao_sei_e_a_analise_segue(self):
        class ShopeeQueQuebra(FonteShopeeFalsa):
            def esquema(self, categoria_id, token, categoria_nome=""):
                raise RuntimeError("fora do ar")

        with self.assertLogs("quickclick.ia", "WARNING"):
            dados = self.processar(shopee=ShopeeQueQuebra())
        self.assertNotIn("exigencias", dados)
        self.assertIn("ml", dados)

    def test_sugestao_de_booleano_so_sim_ou_nao(self):
        leitura = normalizar_leitura({"reconhecido": True, "atributos": [
            {"chave": "a", "valor": "sim", "origem": "foto", "evidencia": "x", "confianca": "alta"},
            {"chave": "b", "valor": "talvez", "origem": "foto", "evidencia": "x", "confianca": "alta"}]}, 1)
        self.assertEqual(_sugestao(["a"], "booleano", (), leitura)["valor"], "Sim")
        self.assertIsNone(_sugestao(["b"], "booleano", (), leitura))

    def test_sem_canal_com_fonte_nao_cria_a_chave(self):
        dados = self.processar(conectados=("amazon",))
        self.assertNotIn("exigencias", dados)
        self.assertNotIn("ml", dados)

    def test_campo_proprio_nao_vai_para_a_releitura(self):
        dados = self.processar(conectados=(SHOPEE,))
        self.assertEqual([e["chave"] for e in dados["exigencias"]], ["marca", "cor", "peso_g", ""])
        self.assertEqual(dados["exigencias"][1]["sugestao"]["valor"], "azul")
        self.assertEqual(self.leitor.relidas, [])

    def test_pago_com_orcamento_do_dia_estourado_pula_a_releitura_dirigida(self):
        with self.assertLogs("quickclick.ia", "INFO") as logs:
            dados = self.processar(nivel="pago", orcamento=OrcamentoFalso(Decimal("0.30")))
        self.assertEqual(self.leitor.relidas, [])
        self.assertIsNone(next(e for e in dados["exigencias"] if e["chave"] == "tamanho")["sugestao"])
        self.assertTrue(any("orçamento" in linha for linha in logs.output))
        self.processar(nivel="pago", orcamento=OrcamentoFalso(Decimal("0.10")))
        self.assertEqual(len(self.leitor.relidas), 1)

    def test_foto_extra_preserva_as_exigencias_e_preenche_a_sugestao_que_faltava(self):
        self.processar(falha_na_releitura=True)
        antes = copy.deepcopy(self.repo.analise["leitura"]["exigencias"])
        self.leitor.falha_na_releitura = False
        self.processo.ler_foto_extra("a1", FotoPreparada(2, b"etiqueta", b"d"), "etiqueta")
        entrada, contexto = self.leitor.relidas[-1]
        self.assertNotIn("exigencias", entrada.leitura_atual)
        self.assertNotIn("ml", entrada.leitura_atual)
        depois = self.repo.analise["leitura"]["exigencias"]
        self.assertEqual([e["chave"] for e in depois], [e["chave"] for e in antes])
        self.assertEqual(next(e for e in depois if e["chave"] == "tamanho")["sugestao"]["valor"], "42")
        self.assertEqual(next(e for e in depois if e["chave"] == "marca"), next(e for e in antes if e["chave"] == "marca"))
        self.assertIsNone(next(e for e in depois if e["chave"] == "tipo_de_calcado")["sugestao"])


if __name__ == "__main__":
    unittest.main()
