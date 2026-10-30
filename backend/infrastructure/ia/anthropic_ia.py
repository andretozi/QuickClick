"""
Infraestrutura · IA · Adaptadores da Anthropic (Claude)

    AnthropicLeitor        leitura das fotos (Opus 5.5 effort high; reserva Haiku 5.5 effort low)
    AnthropicPesquisador   perfil do comprador (Sonnet 5.5 effort medium, busca na web e orientador opcionais)
    AnthropicPrecificador  preço e canais (Opus 5.5 effort medium, sem fotos, só os números)
    AnthropicPrecosNaWeb   reserva do preço no pago: preços em marketplaces brasileiros pela busca na web
    AnthropicRedator       título e descrição (Sonnet 5.5 effort medium) e a correção da regra de escrita (Haiku)
    AnthropicLigador       sobras dos atributos do Mercado Livre (Haiku 5.5 effort low)

Cache: a instrução fixa (system, mais de 512 tokens) leva cache_control com o TTL de IA_CACHE_TTL; as
ferramentas são fixas e vêm antes do system. Nada que muda (data, id, nome do vendedor) entra no trecho
cacheado: o que varia vai no fim, na mensagem do usuário, com as imagens antes do texto.
"""

import base64
import json
from typing import Any

from backend.application.ia.modelos import (
    ContextoDaChamada,
    EntradaDaLeitura,
    EntradaDaPesquisa,
    EntradaDaReleitura,
    EntradaDoPreco,
    EntradaDoTexto,
    FalhaDoProvedor,
    RespostaDaIA,
)
from backend.domain.ia.atributos_ml import AtributoML
from backend.domain.ia.fotos import MAX_FOTOS_NA_LEITURA
from backend.infrastructure.ia import esquemas
from backend.infrastructure.ia.carregador_de_prompts import prompt
from backend.infrastructure.ia.cliente_anthropic import ClienteAnthropic, entrada_da_ferramenta, json_da_resposta

TIPO_BUSCA_WEB = "web_search_20260318"  # a versão mais nova (dynamic filtering + response_inclusion)
BETA_ORIENTADOR = "advisor-tool-2026-03-01"
TIPO_ORIENTADOR = "advisor_20260301"
MAX_BUSCAS = 4
MAX_CONTINUACOES = 3  # pause_turn da busca na web
LOCAL_DO_COMPRADOR = {"type": "approximate", "country": "BR", "timezone": "America/Sao_Paulo"}
DOMINIOS_DE_MARKETPLACES = [
    "mercadolivre.com.br", "shopee.com.br", "amazon.com.br", "magazineluiza.com.br",
    "americanas.com.br", "casasbahia.com.br",
]


def em_json(dados: Any) -> str:
    """JSON estável (mesmas chaves na mesma ordem): não quebra o cache à toa."""
    return json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def pedido_da_releitura(entrada: EntradaDaReleitura) -> tuple[list[bytes], str, str]:
    """(imagens, texto, versão da instrução). Releitura dirigida ("campos"): as fotos da leitura e só as chaves
    pedidas; etiqueta e foto extra: a imagem nova."""
    if entrada.tipo == "campos":
        instrucao = prompt("releitura_campos")
        imagens = [f.leitura_jpeg for f in entrada.fotos_da_leitura[:MAX_FOTOS_NA_LEITURA]]
        texto = (f"{instrucao.texto}\n\nChaves pedidas: {em_json(list(entrada.campos))}\n"
                 f"Leitura atual: {em_json(entrada.leitura_atual)}")
        return imagens, texto, instrucao.versao
    instrucao = prompt("releitura")
    texto = f"{instrucao.texto}\n\nTipo da imagem: {entrada.tipo}\nLeitura atual: {em_json(entrada.leitura_atual)}"
    return [entrada.imagem_jpeg], texto, instrucao.versao


def bloco_de_imagem(jpeg: bytes) -> dict[str, Any]:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.standard_b64encode(jpeg).decode("ascii")}}


class _BaseAnthropic:
    def __init__(self, cliente: ClienteAnthropic, modelo: str, nome: str):
        self._cliente = cliente
        self._modelo = modelo
        self.nome = nome

    def disponivel(self) -> bool:
        return self._cliente.disponivel()

    def _sistema(self, etapa: str) -> tuple[list[dict[str, Any]], str]:
        p = prompt(etapa)
        return [{"type": "text", "text": p.texto, "cache_control": self._cliente.cache()}], p.versao

    def _json(self, *, etapa_prompt: str, contexto: ContextoDaChamada, conteudo: list[dict[str, Any]],
              esquema: dict, effort: str, max_tokens: int, timeout_s: float,
              instrucao_extra: str | None = None) -> RespostaDaIA:
        """`instrucao_extra`: versão do prompt que vai na mensagem do usuário (a releitura): entra junto em ia_uso."""
        sistema, versao = self._sistema(etapa_prompt)
        if instrucao_extra:
            versao = f"{versao}+{instrucao_extra}"
        resposta = self._cliente.criar(
            contexto=contexto, versao_prompt=versao, timeout_s=timeout_s,
            model=self._modelo, max_tokens=max_tokens, system=sistema,
            messages=[{"role": "user", "content": conteudo}],
            output_config={"effort": effort, "format": esquemas.formato(esquema)},
        )
        return RespostaDaIA(json_da_resposta(resposta, self._modelo), "anthropic", resposta.model)

    def _com_ferramentas(self, *, etapa_prompt: str, contexto: ContextoDaChamada, texto: str,
                         ferramentas: list[dict[str, Any]], saida: str, effort: str, max_tokens: int,
                         timeout_s: float, betas: list[str] | None = None) -> RespostaDaIA:
        """Busca na web com a saída por uma ferramenta strict; continua o turno em pause_turn."""
        sistema, versao = self._sistema(etapa_prompt)
        pedido = {"role": "user", "content": [{"type": "text", "text": texto}]}
        mensagens: list[dict[str, Any]] = [pedido]
        do_assistente: list[Any] = []
        for _ in range(MAX_CONTINUACOES + 1):
            resposta = self._cliente.criar(
                contexto=contexto, versao_prompt=versao, timeout_s=timeout_s, betas=betas,
                model=self._modelo, max_tokens=max_tokens, system=sistema, tools=ferramentas,
                messages=mensagens, output_config={"effort": effort},
            )
            if resposta.stop_reason != "pause_turn":
                return RespostaDaIA(entrada_da_ferramenta(resposta, saida, self._modelo), "anthropic", resposta.model)
            # Continua o mesmo turno: devolve o que o assistente já fez, sem mudar nada
            do_assistente = [*do_assistente, *resposta.content]
            mensagens = [pedido, {"role": "assistant", "content": do_assistente}]
        raise FalhaDoProvedor(self._modelo, "a busca na web não terminou")


class AnthropicLeitor(_BaseAnthropic):
    def __init__(self, cliente: ClienteAnthropic, modelo: str, effort_leitura: str = "high",
                 effort_releitura: str = "medium", max_tokens: int = 8000):
        super().__init__(cliente, modelo, f"leitura {modelo}")
        self._effort_leitura = effort_leitura
        self._effort_releitura = effort_releitura
        self._max_tokens = max_tokens

    def ler(self, entrada: EntradaDaLeitura, contexto: ContextoDaChamada) -> RespostaDaIA:
        fotos = entrada.fotos[:MAX_FOTOS_NA_LEITURA]
        conteudo = [bloco_de_imagem(f.leitura_jpeg) for f in fotos]  # imagens antes do texto
        conteudo.append({"type": "text", "text": f"Fotos 0 a {len(fotos) - 1} do mesmo produto. Leia e responda."})
        return self._json(etapa_prompt="leitura", contexto=contexto, conteudo=conteudo, esquema=esquemas.LEITURA,
                          effort=self._effort_leitura, max_tokens=self._max_tokens, timeout_s=180)

    def reler(self, entrada: EntradaDaReleitura, contexto: ContextoDaChamada) -> RespostaDaIA:
        imagens, texto, versao = pedido_da_releitura(entrada)
        conteudo = [*(bloco_de_imagem(i) for i in imagens), {"type": "text", "text": texto}]
        return self._json(etapa_prompt="leitura", contexto=contexto, conteudo=conteudo, esquema=esquemas.RELEITURA,
                          effort=self._effort_releitura, max_tokens=4000, timeout_s=120, instrucao_extra=versao)


class AnthropicPesquisador(_BaseAnthropic):
    def __init__(self, cliente: ClienteAnthropic, modelo: str, com_web: bool, orientador: str | None = None,
                 effort: str = "medium"):
        super().__init__(cliente, modelo, f"pesquisa {modelo}")
        self._com_web = com_web
        self._orientador = orientador  # modelo do orientador (ADVISOR_ATIVO), ou None
        self._effort = effort

    def pesquisar(self, entrada: EntradaDaPesquisa, contexto: ContextoDaChamada) -> RespostaDaIA:
        produto = em_json({"produto": entrada.produto, "categoria": entrada.categoria, "condicao": entrada.condicao,
                           "atributos": [{"chave": c, "valor": v} for c, v in entrada.atributos]})
        if not (entrada.com_web and self._com_web):
            return self._json(etapa_prompt="perfil", contexto=contexto,
                              conteudo=[{"type": "text", "text": f"Produto: {produto}"}],
                              esquema=esquemas.PESQUISA_SEM_WEB, effort=self._effort, max_tokens=3000, timeout_s=90)
        ferramentas = [{"type": TIPO_BUSCA_WEB, "name": "web_search", "max_uses": MAX_BUSCAS,
                        "user_location": LOCAL_DO_COMPRADOR, "response_inclusion": "excluded"}]
        betas = None
        if self._orientador:
            ferramentas.append({"type": TIPO_ORIENTADOR, "name": "advisor", "model": self._orientador,
                                "max_uses": 1, "max_tokens": 2048})
            betas = [BETA_ORIENTADOR]
        ferramentas.append(esquemas.ferramenta_de_saida(
            "registrar_pesquisa", "Registra o resultado final da pesquisa. Chame uma vez, no fim.", esquemas.PESQUISA))
        return self._com_ferramentas(etapa_prompt="pesquisa", contexto=contexto, texto=f"Produto: {produto}",
                                     ferramentas=ferramentas, saida="registrar_pesquisa", effort=self._effort,
                                     max_tokens=6000, timeout_s=240, betas=betas)


class AnthropicPrecificador(_BaseAnthropic):
    def __init__(self, cliente: ClienteAnthropic, modelo: str, effort: str = "medium"):
        super().__init__(cliente, modelo, f"preço {modelo}")
        self._effort = effort

    def precificar(self, entrada: EntradaDoPreco, contexto: ContextoDaChamada) -> RespostaDaIA:
        dados = em_json({
            "mercado": entrada.dados_do_mercado,
            "produto": {"atributos": [{"chave": c, "valor": v} for c, v in entrada.atributos],
                        "condicao": entrada.condicao, "defeitos": list(entrada.defeitos)},
            "canais": list(entrada.canais_candidatos),
        })
        return self._json(etapa_prompt="preco", contexto=contexto, conteudo=[{"type": "text", "text": dados}],
                          esquema=esquemas.PRECO, effort=self._effort, max_tokens=4000, timeout_s=120)


class AnthropicPrecosNaWeb(_BaseAnthropic):
    def __init__(self, cliente: ClienteAnthropic, modelo: str, effort: str = "medium"):
        super().__init__(cliente, modelo, f"preços na web {modelo}")
        self._effort = effort

    def buscar_precos(self, produto: str, condicao: str, atributos: tuple[tuple[str, str], ...],
                      contexto: ContextoDaChamada) -> RespostaDaIA:
        ferramentas = [
            {"type": TIPO_BUSCA_WEB, "name": "web_search", "max_uses": MAX_BUSCAS, "user_location": LOCAL_DO_COMPRADOR,
             "allowed_domains": DOMINIOS_DE_MARKETPLACES, "response_inclusion": "excluded"},
            esquemas.ferramenta_de_saida("registrar_precos", "Registra os preços encontrados. Chame uma vez, no fim.",
                                         esquemas.PRECOS_NA_WEB),
        ]
        texto = "Produto: " + em_json({"produto": produto, "condicao": condicao,
                                       "atributos": [{"chave": c, "valor": v} for c, v in atributos]})
        return self._com_ferramentas(etapa_prompt="precos_web", contexto=contexto, texto=texto, ferramentas=ferramentas,
                                     saida="registrar_precos", effort=self._effort, max_tokens=6000, timeout_s=240)


class AnthropicRedator(_BaseAnthropic):
    def __init__(self, cliente: ClienteAnthropic, modelo: str, effort: str = "medium"):
        super().__init__(cliente, modelo, f"texto {modelo}")
        self._effort = effort

    def escrever(self, entrada: EntradaDoTexto, contexto: ContextoDaChamada) -> RespostaDaIA:
        dados = em_json({
            "produto": entrada.produto, "categoria": entrada.categoria, "condicao": entrada.condicao,
            "atributos": [{"chave": c, "valor": v} for c, v in entrada.atributos],
            "defeitos": list(entrada.defeitos), "perfil_do_comprador": entrada.perfil,
        })
        return self._json(etapa_prompt="texto", contexto=contexto, conteudo=[{"type": "text", "text": dados}],
                          esquema=esquemas.TEXTO_DO_ANUNCIO, effort=self._effort, max_tokens=4000, timeout_s=120)

    def corrigir(self, texto: dict[str, Any], trechos: list[str], contexto: ContextoDaChamada) -> RespostaDaIA:
        dados = em_json({"texto": texto, "trechos_com_problema": trechos})
        return self._json(etapa_prompt="correcao", contexto=contexto, conteudo=[{"type": "text", "text": dados}],
                          esquema=esquemas.TEXTO_DO_ANUNCIO, effort="low", max_tokens=3000, timeout_s=60)


class AnthropicLigador(_BaseAnthropic):
    def __init__(self, cliente: ClienteAnthropic, modelo: str):
        super().__init__(cliente, modelo, f"atributos {modelo}")

    def ligar(self, sobras: list[tuple[str, str]], da_categoria: list[AtributoML],
              contexto: ContextoDaChamada) -> RespostaDaIA:
        dados = em_json({"sobras": [{"chave": c, "valor": v} for c, v in sobras],
                         "atributos_da_categoria": [{"id": a.id, "nome": a.nome} for a in da_categoria]})
        return self._json(etapa_prompt="atributos_ml", contexto=contexto, conteudo=[{"type": "text", "text": dados}],
                          esquema=esquemas.ATRIBUTOS_ML, effort="low", max_tokens=1500, timeout_s=45)
