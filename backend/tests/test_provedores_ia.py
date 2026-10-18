"""Portas e provedores da IA, sem rede: clientes com SDK falso, Pillow com imagens geradas e Mercado Livre falso."""

import io
import json
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import anthropic
import httpx
from PIL import Image, ImageDraw, ImageFilter

from backend.application.ia import escolha
from backend.application.ia.modelos import ArquivoDeFoto, ContextoDaChamada, FalhaDoProvedor, RespostaDaIA
from backend.domain.erros import FotoInvalida
from backend.domain.ia.analise import Nivel
from backend.domain.ia.fotos import QualidadeFoto
from backend.infrastructure.ia import esquemas
from backend.infrastructure.ia.cliente_anthropic import ClienteAnthropic, json_da_resposta
from backend.infrastructure.ia.cliente_gemini import ClienteGemini, esquema_para_gemini
from backend.infrastructure.ia.fabrica import criar_provedores
from backend.infrastructure.ia.precos import custo_anthropic
from backend.infrastructure.ia.preparador_pillow import PillowPreparador
from backend.infrastructure.marketplaces.fonte_precos_ml import FontePrecosMercadoLivre
from backend.infrastructure.marketplaces.mercado_livre import ErroDoMercadoLivre
from backend.tests import leitor_de_teste

AGORA = datetime(2026, 10, 17, 15, 0, tzinfo=UTC)
CONTEXTO = ContextoDaChamada(vendedor_id=1, analise_id="a1", etapa="leitura")
CHAVE_FALSA = "chave-falsa-de-teste"


class RegistroEmMemoria:
    def __init__(self):
        self.usos = []

    def registrar(self, uso):
        self.usos.append(uso)


def resposta_anthropic(texto='{"ok": true}', stop="end_turn", modelo="claude-opus-5-5", buscas=0):
    uso = SimpleNamespace(input_tokens=1000, output_tokens=200, cache_read_input_tokens=3000,
                          cache_creation_input_tokens=0, server_tool_use=SimpleNamespace(web_search_requests=buscas))
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=texto)], stop_reason=stop, model=modelo, usage=uso)


def erro_da_api(classe, status):
    pedido = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return classe("erro", response=httpx.Response(status, request=pedido), body=None)


class SDKFalso:
    """Faz o papel de anthropic.Anthropic: devolve (ou levanta) o que estiver na fila."""

    def __init__(self, *respostas):
        self.fila = list(respostas)
        self.pedidos = []
        self.messages = SimpleNamespace(create=self._criar)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._criar))

    def _criar(self, **parametros):
        self.pedidos.append(parametros)
        proxima = self.fila.pop(0)
        if isinstance(proxima, Exception):
            raise proxima
        return proxima


def cliente_anthropic(*respostas, chave=CHAVE_FALSA):
    registro = RegistroEmMemoria()
    sdk = SDKFalso(*respostas)
    relogio = SimpleNamespace(agora=AGORA)
    cliente = ClienteAnthropic("ANTHROPIC_API_KEY_PAGO", chave, registro, "5m", relogio=lambda: relogio.agora,
                               dormir=lambda s: None, cliente=sdk)
    return cliente, sdk, registro, relogio


def chamar(cliente):
    return cliente.criar(contexto=CONTEXTO, versao_prompt="leitura_v1", timeout_s=10, model="claude-opus-5-5",
                         max_tokens=10, messages=[])


class TestClienteAnthropic(unittest.TestCase):
    def test_sucesso_registra_uso_com_custo(self):
        cliente, _, registro, _ = cliente_anthropic(resposta_anthropic())
        chamar(cliente)
        uso = registro.usos[0]
        self.assertEqual((uso.tokens_entrada, uso.tokens_saida, uso.cache_lido, uso.versao_prompt),
                         (1000, 200, 3000, "leitura_v1"))
        # 1000 × 4 + 200 × 20 + 3000 × 0,20 por milhão
        self.assertEqual(uso.custo_estimado_usd, Decimal("0.008600"))

    def test_chave_recusada_desliga_por_10_minutos_e_avisa_pelo_nome(self):
        cliente, sdk, _, relogio = cliente_anthropic(erro_da_api(anthropic.AuthenticationError, 401))
        with self.assertLogs("quickclick.ia", "ERROR") as logs, self.assertRaises(FalhaDoProvedor) as falha:
            chamar(cliente)
        self.assertTrue(falha.exception.chave_recusada)
        self.assertIn("ANTHROPIC_API_KEY_PAGO recusada", logs.output[0])
        self.assertNotIn(CHAVE_FALSA, logs.output[0])
        self.assertEqual(len(sdk.pedidos), 1)  # não tenta de novo
        self.assertFalse(cliente.disponivel())
        relogio.agora = AGORA + timedelta(minutes=11)
        self.assertTrue(cliente.disponivel())

    def test_erro_temporario_tenta_uma_vez_de_novo(self):
        cliente, sdk, _, _ = cliente_anthropic(erro_da_api(anthropic.RateLimitError, 429), resposta_anthropic())
        chamar(cliente)
        self.assertEqual(len(sdk.pedidos), 2)

    def test_erro_temporario_duas_vezes_vira_falha_temporaria(self):
        cliente, _, _, _ = cliente_anthropic(erro_da_api(anthropic.OverloadedError, 529),
                                             erro_da_api(anthropic.OverloadedError, 529))
        with self.assertRaises(FalhaDoProvedor) as falha:
            chamar(cliente)
        self.assertTrue(falha.exception.temporaria)

    def test_400_nao_tenta_de_novo(self):
        cliente, sdk, _, _ = cliente_anthropic(erro_da_api(anthropic.BadRequestError, 400))
        with self.assertRaises(FalhaDoProvedor):
            chamar(cliente)
        self.assertEqual(len(sdk.pedidos), 1)

    def test_recusa_e_resposta_cortada_viram_falha(self):
        for stop in ("refusal", "max_tokens"):
            cliente, _, registro, _ = cliente_anthropic(resposta_anthropic(stop=stop))
            with self.assertRaises(FalhaDoProvedor):
                chamar(cliente)
            self.assertEqual(len(registro.usos), 1)  # o uso é registrado mesmo assim

    def test_sem_chave_nao_chama(self):
        cliente, sdk, _, _ = cliente_anthropic(chave=None)
        self.assertFalse(cliente.disponivel())
        with self.assertRaises(FalhaDoProvedor):
            chamar(cliente)
        self.assertEqual(sdk.pedidos, [])

    def test_json_da_resposta(self):
        self.assertEqual(json_da_resposta(resposta_anthropic('{"a": 1}'), "x"), {"a": 1})
        with self.assertRaises(FalhaDoProvedor):
            json_da_resposta(resposta_anthropic("não é json"), "x")


class TestPrecos(unittest.TestCase):
    def test_busca_na_web_e_haiku(self):
        self.assertEqual(custo_anthropic("claude-sonnet-5-5", 0, 0, 0, 0, 4, "5m"), Decimal("0.040000"))
        self.assertEqual(custo_anthropic("claude-haiku-5-5", 1_000_000, 0, 0, 0, 0, "5m"), Decimal("0.500000"))
        self.assertEqual(custo_anthropic("claude-haiku-5-5", 10_000, 0, 0, 0, 0, "5m"), Decimal("0.001000"))

    def test_escrita_de_cache_1h_custa_mais(self):
        self.assertGreater(custo_anthropic("claude-opus-5-5", 0, 0, 0, 1000, 0, "1h"),
                           custo_anthropic("claude-opus-5-5", 0, 0, 0, 1000, 0, "5m"))


class GeminiFalso:
    def __init__(self, *respostas):
        self.fila = list(respostas)
        self.models = SimpleNamespace(generate_content=self._gerar)

    def _gerar(self, **_):
        proxima = self.fila.pop(0)
        if isinstance(proxima, Exception):
            raise proxima
        return proxima


class TestClienteGemini(unittest.TestCase):
    def _cliente(self, *respostas):
        return ClienteGemini("GEMINI_API_KEY_GRATIS", CHAVE_FALSA, RegistroEmMemoria(), relogio=lambda: AGORA,
                             dormir=lambda s: None, cliente=GeminiFalso(*respostas))

    def _gerar(self, cliente):
        return cliente.gerar_json(modelo="gemini-3.8-flash", partes=["x"], sistema="s", esquema=esquemas.TEXTO_DO_ANUNCIO,
                                  contexto=CONTEXTO, versao_prompt="texto_v1", timeout_s=5)

    def test_json_e_custo_zero(self):
        meta = SimpleNamespace(prompt_token_count=100, candidates_token_count=50, thoughts_token_count=10,
                               cached_content_token_count=0)
        cliente = self._cliente(SimpleNamespace(text='{"titulo": "x"}', usage_metadata=meta))
        self.assertEqual(self._gerar(cliente), {"titulo": "x"})

    def test_429_vira_falha_e_a_reserva_assume(self):
        from google.genai import errors

        cliente = self._cliente(errors.ClientError(429, {"error": {"message": "quota"}}))
        with self.assertRaises(FalhaDoProvedor) as falha:
            self._gerar(cliente)
        self.assertTrue(falha.exception.temporaria)
        self.assertTrue(cliente.disponivel())

    def test_chave_recusada_desliga(self):
        from google.genai import errors

        cliente = self._cliente(errors.ClientError(403, {"error": {"message": "denied"}}))
        with self.assertLogs("quickclick.ia", "ERROR"), self.assertRaises(FalhaDoProvedor):
            self._gerar(cliente)
        self.assertFalse(cliente.disponivel())

    def test_esquema_sem_additional_properties(self):
        self.assertNotIn("additionalProperties", json.dumps(esquema_para_gemini(esquemas.LEITURA)))


def jpeg(imagem: Image.Image, **extras) -> bytes:
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=92, **extras)
    return saida.getvalue()


def foto_com_detalhes(largura=1200, altura=900, brilho=200) -> Image.Image:
    imagem = Image.new("RGB", (largura, altura), (brilho, brilho, brilho))
    desenho = ImageDraw.Draw(imagem)
    for x in range(0, largura, 40):
        desenho.line([(x, 0), (x, altura)], fill=(20, 20, 20), width=3)
    for y in range(0, altura, 40):
        desenho.line([(0, y), (largura, y)], fill=(20, 20, 20), width=3)
    return imagem


class TestPillowPreparador(unittest.TestCase):
    def setUp(self):
        self.preparador = PillowPreparador()

    def test_apaga_exif_e_gps_e_gira_pela_orientacao(self):
        exif = Image.Exif()
        exif[0x0112] = 6  # orientação: girar 90 graus
        exif[0x8825] = {2: (23.0, 33.0, 0.0)}  # GPSInfo
        foto = self.preparador.preparar([ArquivoDeFoto("a.jpg", jpeg(foto_com_detalhes(1200, 900), exif=exif))])[0]
        self.assertEqual((foto.largura, foto.altura), (900, 1200))
        with Image.open(io.BytesIO(foto.leitura_jpeg)) as leitura:
            self.assertEqual(len(leitura.getexif()), 0)
            self.assertNotIn("exif", leitura.info)
        self.assertEqual(foto.meta(), {"indice": 0, "qualidade": "ok", "largura": 900, "altura": 1200})

    def test_versao_de_leitura_com_lado_maior_1568(self):
        foto = self.preparador.preparar([ArquivoDeFoto("a.jpg", jpeg(foto_com_detalhes(3000, 2000)))])[0]
        with Image.open(io.BytesIO(foto.leitura_jpeg)) as leitura:
            self.assertEqual(max(leitura.size), 1568)
        with Image.open(io.BytesIO(foto.detalhe_jpeg)) as detalhe:
            self.assertEqual(max(detalhe.size), 2576)

    def test_qualidade_escura_tremida_e_pequena(self):
        escura = foto_com_detalhes(brilho=25).point(lambda v: v // 4)
        tremida = foto_com_detalhes().filter(ImageFilter.GaussianBlur(14))
        pequena = foto_com_detalhes(400, 300)
        fotos = self.preparador.preparar([ArquivoDeFoto(f"{n}.jpg", jpeg(i)) for n, i in
                                          (("e", escura), ("t", tremida), ("p", pequena))])
        self.assertEqual([f.qualidade for f in fotos],
                         [QualidadeFoto.ESCURA, QualidadeFoto.TREMIDA, QualidadeFoto.PEQUENA])

    def test_png_transparente_ganha_fundo_branco(self):
        imagem = Image.new("RGBA", (800, 800), (0, 0, 0, 0))
        saida = io.BytesIO()
        imagem.save(saida, format="PNG")
        foto = self.preparador.preparar([ArquivoDeFoto("a.png", saida.getvalue())])[0]
        with Image.open(io.BytesIO(foto.leitura_jpeg)) as leitura:
            self.assertGreater(leitura.convert("L").getpixel((10, 10)), 240)

    def test_conteudo_que_nao_e_imagem_e_recusado_mesmo_com_extensao_jpg(self):
        with self.assertRaises(FotoInvalida):
            self.preparador.preparar([ArquivoDeFoto("a.jpg", b"isto nao e uma imagem")])

    def test_formato_fora_da_lista_e_recusado(self):
        saida = io.BytesIO()
        Image.new("RGB", (800, 800)).save(saida, format="GIF")
        with self.assertRaises(FotoInvalida):
            self.preparador.preparar([ArquivoDeFoto("a.gif", saida.getvalue())])

    def test_acima_de_40_megapixels_e_recusado(self):
        saida = io.BytesIO()
        Image.new("L", (6500, 6500)).save(saida, format="PNG")
        with self.assertRaises(FotoInvalida):
            self.preparador.preparar([ArquivoDeFoto("grande.png", saida.getvalue())])

    def test_mais_de_6_fotos_ou_nenhuma(self):
        foto = ArquivoDeFoto("a.jpg", jpeg(foto_com_detalhes()))
        with self.assertRaises(FotoInvalida):
            self.preparador.preparar([foto] * 7)
        with self.assertRaises(FotoInvalida):
            self.preparador.preparar([])

    def test_recorte_da_etiqueta(self):
        foto = self.preparador.preparar([ArquivoDeFoto("a.jpg", jpeg(foto_com_detalhes(3000, 2000)))])[0]
        with Image.open(io.BytesIO(self.preparador.recortar(foto, (0, 0, 500, 500)))) as recorte:
            self.assertGreater(recorte.width, 1200)


class ProvedorFalso:
    def __init__(self, nome, disponivel=True, falha=False):
        self.nome, self._disponivel, self._falha, self.chamado = nome, disponivel, falha, False

    def disponivel(self):
        return self._disponivel

    def chamar(self):
        self.chamado = True
        if self._falha:
            raise FalhaDoProvedor(self.nome, "erro")
        return RespostaDaIA({"de": self.nome}, "falso", self.nome)


class TestEscolha(unittest.TestCase):
    def test_ordem_por_nivel_e_pula_os_indisponiveis(self):
        p = escolha.ProvedoresDeIA(
            leitor_visao_pago=ProvedorFalso("opus"), leitor_rapido_pago=ProvedorFalso("haiku pago"),
            leitor_gemini_gratis=ProvedorFalso("gemini", disponivel=False), leitor_rapido_gratis=ProvedorFalso("haiku"),
        )
        self.assertEqual([x.nome for x in escolha.leitores(p, Nivel.PAGO)], ["opus", "haiku pago"])
        self.assertEqual([x.nome for x in escolha.leitores(p, Nivel.GRATIS)], ["haiku"])
        self.assertEqual(escolha.precificadores(p, Nivel.GRATIS), [])

    def test_tentar_em_ordem_usa_a_reserva(self):
        primeiro, segundo = ProvedorFalso("a", falha=True), ProvedorFalso("b")
        with self.assertLogs("quickclick.ia", "WARNING"):
            resposta, provedor = escolha.tentar_em_ordem([primeiro, segundo], lambda p: p.chamar())
        self.assertEqual((resposta.dados, provedor.nome), ({"de": "b"}, "b"))

    def test_todos_falham(self):
        with self.assertLogs("quickclick.ia", "WARNING"):
            self.assertIsNone(escolha.tentar_em_ordem([ProvedorFalso("a", falha=True)], lambda p: p.chamar()))


class TestFabrica(unittest.TestCase):
    def test_ia_desligada_nao_monta_nada(self):
        with self.assertLogs("quickclick.ia", "WARNING"):
            provedores = criar_provedores(leitor_de_teste(IA_ATIVA="false"), RegistroEmMemoria())
        self.assertEqual(escolha.leitores(provedores, Nivel.PAGO), [])

    def test_sem_chaves_nenhum_provedor_disponivel_e_o_log_diz_o_que_falta(self):
        with self.assertLogs("quickclick.ia", "WARNING") as logs:
            provedores = criar_provedores(leitor_de_teste(), RegistroEmMemoria())
        self.assertEqual(escolha.leitores(provedores, Nivel.GRATIS), [])
        self.assertTrue(any("ANTHROPIC_API_KEY_PAGO" in linha for linha in logs.output))

    def test_com_chaves_monta_na_ordem(self):
        leitor = leitor_de_teste(ANTHROPIC_API_KEY_PAGO="x", ANTHROPIC_API_KEY_GRATIS="y", GEMINI_API_KEY_GRATIS="z",
                                 PESQUISA_WEB_ATIVA="false")
        provedores = criar_provedores(leitor, RegistroEmMemoria())
        self.assertEqual([x.nome for x in escolha.leitores(provedores, Nivel.GRATIS)],
                         ["leitura gemini-3.8-flash", "leitura claude-haiku-5-5"])
        self.assertEqual([x.nome for x in escolha.redatores(provedores, Nivel.PAGO)],
                         ["texto claude-sonnet-5-5", "texto claude-haiku-5-5"])
        self.assertEqual(escolha.precos_na_web(provedores, Nivel.PAGO), [])  # busca na web desligada


class TestEsquemas(unittest.TestCase):
    PROIBIDOS = {"minLength", "maxLength", "minimum", "maximum", "maxItems", "multipleOf"}

    def _conferir(self, esquema, caminho="raiz"):
        if isinstance(esquema, dict):
            self.assertFalse(self.PROIBIDOS & set(esquema), caminho)
            if esquema.get("type") == "object":
                self.assertIs(esquema.get("additionalProperties"), False, caminho)
                self.assertEqual(set(esquema["required"]), set(esquema["properties"]), caminho)
            for chave, valor in esquema.items():
                self._conferir(valor, f"{caminho}.{chave}")
        elif isinstance(esquema, list):
            for item in esquema:
                self._conferir(item, caminho)

    def test_todos_os_esquemas_seguem_as_regras_da_api(self):
        for nome in ("LEITURA", "RELEITURA", "PESQUISA", "PESQUISA_SEM_WEB", "PRECO", "TEXTO_DO_ANUNCIO",
                     "ATRIBUTOS_ML", "PRECOS_NA_WEB"):
            with self.subTest(nome):
                self._conferir(getattr(esquemas, nome), nome)


class GatewayMLFalso:
    def __init__(self, busca=None, erro_busca=None, tarifa=None):
        self._busca, self._erro_busca, self._tarifa = busca, erro_busca, tarifa
        self.buscas = 0

    def descobrir_dominio(self, termos, token):
        return [{"category_id": "MLB23262", "category_name": "Tênis", "domain_name": "Tênis"}]

    def atributos_da_categoria(self, categoria_id, token):
        return [{"id": "BRAND", "name": "Marca", "tags": {"required": True}, "values": [], "hierarchy": "x"}]

    def buscar_itens(self, termos, categoria_id, condicao, token):
        self.buscas += 1
        if self._erro_busca:
            raise self._erro_busca
        return self._busca

    def custo_de_venda(self, preco, categoria_id, token):
        return self._tarifa


class CacheEmMemoria:
    def __init__(self):
        self.dados = {}

    def obter(self, chave, agora):
        return self.dados.get(chave)

    def salvar(self, chave, atributos, expira_em):
        self.dados[chave] = atributos


class TestFontePrecosML(unittest.TestCase):
    def test_busca_restrita_403_devolve_none_e_pausa_por_uma_hora(self):
        gateway = GatewayMLFalso(erro_busca=ErroDoMercadoLivre("proibido", 403))
        relogio = SimpleNamespace(agora=AGORA)
        fonte = FontePrecosMercadoLivre(gateway, CacheEmMemoria(), relogio=lambda: relogio.agora)
        with self.assertLogs("quickclick.marketplaces", "WARNING"):
            self.assertIsNone(fonte.buscar_parecidos(["tenis"], None, "novo", "t"))
        self.assertIsNone(fonte.buscar_parecidos(["tenis"], None, "novo", "t"))
        self.assertEqual(gateway.buscas, 1)
        relogio.agora = AGORA + timedelta(hours=1, minutes=1)
        with self.assertLogs("quickclick.marketplaces", "WARNING"):
            fonte.buscar_parecidos(["tenis"], None, "novo", "t")
        self.assertEqual(gateway.buscas, 2)

    def test_precos_em_centavos_e_frete(self):
        busca = {"results": [{"price": 189.9, "currency_id": "BRL", "shipping": {"free_shipping": True}},
                             {"price": 10, "currency_id": "USD"}, {"price": None}]}
        fonte = FontePrecosMercadoLivre(GatewayMLFalso(busca=busca), CacheEmMemoria(), relogio=lambda: AGORA)
        observados = fonte.buscar_parecidos(["tenis"], "MLB1", "usado", "t")
        self.assertEqual([(o.preco_centavos, o.frete_gratis) for o in observados], [(18990, True)])

    def test_categoria_atributos_com_cache_e_tarifa(self):
        cache = CacheEmMemoria()
        fonte = FontePrecosMercadoLivre(GatewayMLFalso(tarifa=[{"listing_type_id": "gold_special", "sale_fee_amount": 22.79}]),
                                        cache, relogio=lambda: AGORA)
        self.assertEqual(fonte.descobrir_categoria(["tenis corrida"], "t").categoria_id, "MLB23262")
        atributos = fonte.atributos_da_categoria("MLB23262", "t")
        self.assertEqual([(a.id, a.obrigatorio) for a in atributos], [("BRAND", True)])
        self.assertNotIn("hierarchy", cache.dados["MLB23262"][0])
        self.assertEqual(fonte.tarifa(18990, "MLB23262", "t"), 2279)


if __name__ == "__main__":
    unittest.main()
