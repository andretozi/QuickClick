"""
Infraestrutura · IA · Adaptadores do Gemini (plano Grátis, camada grátis do Google AI Studio)

    GeminiLeitor   leitura das fotos com o mesmo esquema da Anthropic (response_json_schema)
    GeminiRedator  título e descrição; a correção da regra de escrita fica com o Haiku
Erro ou 429 (limite da camada grátis): FalhaDoProvedor, e a análise usa a reserva (Haiku 5.5).
"""

import json
from typing import Any

from backend.application.ia.modelos import (
    ContextoDaChamada,
    EntradaDaLeitura,
    EntradaDaReleitura,
    EntradaDoTexto,
    RespostaDaIA,
)
from backend.domain.ia.fotos import MAX_FOTOS_NA_LEITURA
from backend.infrastructure.ia import esquemas
from backend.infrastructure.ia.anthropic_ia import em_json
from backend.infrastructure.ia.carregador_de_prompts import prompt
from backend.infrastructure.ia.cliente_gemini import ClienteGemini, parte_de_imagem


class _BaseGemini:
    def __init__(self, cliente: ClienteGemini, modelo: str, nome: str):
        self._cliente = cliente
        self._modelo = modelo
        self.nome = nome

    def disponivel(self) -> bool:
        return self._cliente.disponivel()

    def _gerar(self, etapa_prompt: str, partes: list[Any], esquema: dict, contexto: ContextoDaChamada,
               timeout_s: float, max_tokens: int = 8000) -> RespostaDaIA:
        p = prompt(etapa_prompt)
        dados = self._cliente.gerar_json(modelo=self._modelo, partes=partes, sistema=p.texto, esquema=esquema,
                                         contexto=contexto, versao_prompt=p.versao, timeout_s=timeout_s,
                                         max_tokens=max_tokens)
        return RespostaDaIA(dados, "gemini", self._modelo)


class GeminiLeitor(_BaseGemini):
    def __init__(self, cliente: ClienteGemini, modelo: str):
        super().__init__(cliente, modelo, f"leitura {modelo}")

    def ler(self, entrada: EntradaDaLeitura, contexto: ContextoDaChamada) -> RespostaDaIA:
        fotos = entrada.fotos[:MAX_FOTOS_NA_LEITURA]
        partes = [parte_de_imagem(f.leitura_jpeg) for f in fotos]
        partes.append(f"Fotos 0 a {len(fotos) - 1} do mesmo produto. Leia e responda.")
        return self._gerar("leitura", partes, esquemas.LEITURA, contexto, timeout_s=120)

    def reler(self, entrada: EntradaDaReleitura, contexto: ContextoDaChamada) -> RespostaDaIA:
        instrucao = prompt("releitura")
        partes = [parte_de_imagem(entrada.imagem_jpeg),
                  f"{instrucao.texto}\n\nTipo da imagem: {entrada.tipo}\nLeitura atual: {em_json(entrada.leitura_atual)}"]
        return self._gerar("leitura", partes, esquemas.RELEITURA, contexto, timeout_s=90, max_tokens=4000)


class GeminiRedator(_BaseGemini):
    def __init__(self, cliente: ClienteGemini, modelo: str):
        super().__init__(cliente, modelo, f"texto {modelo}")

    def escrever(self, entrada: EntradaDoTexto, contexto: ContextoDaChamada) -> RespostaDaIA:
        dados = em_json({
            "produto": entrada.produto, "categoria": entrada.categoria, "condicao": entrada.condicao,
            "atributos": [{"chave": c, "valor": v} for c, v in entrada.atributos],
            "defeitos": list(entrada.defeitos), "perfil_do_comprador": entrada.perfil,
        })
        return self._gerar("texto", [dados], esquemas.TEXTO_DO_ANUNCIO, contexto, timeout_s=90, max_tokens=4000)

    def corrigir(self, texto: dict[str, Any], trechos: list[str], contexto: ContextoDaChamada) -> RespostaDaIA:
        dados = json.dumps({"texto": texto, "trechos_com_problema": trechos}, ensure_ascii=False, sort_keys=True)
        return self._gerar("correcao", [dados], esquemas.TEXTO_DO_ANUNCIO, contexto, timeout_s=60, max_tokens=3000)
