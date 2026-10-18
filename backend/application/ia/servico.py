"""
Aplicação · IA · Serviço de análises (o que as rotas chamam)

Protege as chaves contra quem tenta gastar pelo app: cota do mês por plano (só conta análise
pronta), uma análise por vez, no máximo 10 por hora, e o orçamento do dia (estourou: o pago cai
no caminho grátis com aviso). A análise é sempre do vendedor que pede (senão, "não encontrada").
"""

import logging
import threading
import uuid
from datetime import timedelta
from typing import Any

from backend.application.casos_de_uso.comum import obter_vendedor
from backend.application.ia import escolha
from backend.application.ia.etapas import DependenciasDaAnalise, ProcessoDaAnalise, com_aviso
from backend.application.ia.modelos import ArquivoDeFoto
from backend.application.ia.portas import Executor, OrcamentoDeIA
from backend.application.portas import RepositorioVendedores
from backend.domain.erros import (
    AnaliseEmAndamento,
    AnaliseNaoEncontrada,
    EstadoDaAnaliseInvalido,
    FotosNecessarias,
    IAIndisponivel,
)
from backend.domain.ia.analise import (
    StatusAnalise,
    esta_em_processamento,
    etapa_de_retomada,
    pode_confirmar,
    pode_receber_foto_extra,
    pode_retomar,
    retomada_precisa_de_fotos,
)
from backend.domain.ia.capacidade import (
    ANALISES_AO_MESMO_TEMPO,
    CapacidadeIA,
    capacidade_do_plano,
    garantir_pode_comecar,
    nivel_efetivo,
    restantes,
)
from backend.domain.ia.leitura import normalizar_confirmacao, normalizar_leitura

log = logging.getLogger("quickclick.ia")

TIPOS_DE_FOTO_EXTRA = ("etiqueta", "verso", "detalhe")
MENSAGEM_INTERROMPIDA = "A análise parou no meio porque o servidor reiniciou. Toque em retomar."
AVISO_ORCAMENTO = ("orcamento_do_dia", "Hoje a IA completa já chegou no limite do dia, então usei a versão básica, "
                                      "a mesma do plano Grátis.")


class ServicoDeAnalises:
    def __init__(self, dependencias: DependenciasDaAnalise, vendedores: RepositorioVendedores,
                 orcamento: OrcamentoDeIA, executor: Executor):
        self.d = dependencias
        self._vendedores = vendedores
        self._orcamento = orcamento
        self._executor = executor
        self.processo = ProcessoDaAnalise(dependencias)
        self._trava = threading.Lock()

    def ao_iniciar(self) -> int:
        """Análises paradas há mais de 10 minutos (o servidor reiniciou no meio) viram interrompidas."""
        quantas = self.d.analises.marcar_paradas_como_interrompidas(self.d.relogio())
        if quantas:
            log.info("%d análise(s) marcadas como interrompidas na partida.", quantas)
        return quantas

    # ------------------------------------------------------------------

    def _capacidade(self, vendedor_id: int) -> CapacidadeIA:
        return capacidade_do_plano(obter_vendedor(self._vendedores, vendedor_id).plano.slug)

    def _nivel_agora(self, capacidade: CapacidadeIA):
        gasto = self._orcamento.gasto_de_hoje_usd(self.d.relogio())
        return nivel_efetivo(capacidade.nivel, gasto, self.d.config.orcamento_diario_usd)

    def _da_conta(self, vendedor_id: int, analise_id: str) -> dict[str, Any]:
        analise = self.d.analises.obter(analise_id)
        if analise is None or analise["vendedor_id"] != vendedor_id:
            raise AnaliseNaoEncontrada()
        return analise

    def cota(self, vendedor_id: int) -> dict[str, Any]:
        capacidade = self._capacidade(vendedor_id)
        agora = self.d.relogio()
        usadas = self.d.analises.prontas_no_mes(vendedor_id, agora)
        nivel, estourou = self._nivel_agora(capacidade)
        sobram = restantes(capacidade, usadas)
        motivo = None
        if not self.d.config.ia_ativa:
            motivo = "ia_desligada"
        elif not escolha.leitores(self.d.provedores, nivel):
            motivo = "provedor_indisponivel"
        elif sobram <= 0:
            motivo = "cota_esgotada"
        return {
            "plano": capacidade.plano,
            "nivel": capacidade.nivel.value,
            "nivel_agora": nivel.value,
            "analises_por_mes": capacidade.analises_por_mes,
            "usadas_no_mes": usadas,
            "restantes": sobram,
            "orcamento_do_dia_estourado": estourou,
            "disponivel": motivo is None,
            "motivo_indisponivel": motivo,
            "tem": {
                "leitura_da_foto": True,
                "pesquisa_de_mercado": capacidade.pesquisa_de_mercado,
                "preco_com_analise": capacidade.preco_com_analise,
                "busca_na_web": capacidade.pesquisa_de_mercado and self.d.config.pesquisa_web_ativa,
            },
            "aviso_de_dados_no_gratis": capacidade.plano == "gratis",
        }

    def criar(self, vendedor_id: int, arquivos: list[ArquivoDeFoto]) -> dict[str, Any]:
        capacidade = self._capacidade(vendedor_id)
        if not self.d.config.ia_ativa:
            raise IAIndisponivel()
        fotos = self.d.preparador.preparar(arquivos)  # fora da trava: é o trecho mais lento
        agora = self.d.relogio()
        with self._trava:
            garantir_pode_comecar(
                capacidade,
                usadas_no_mes=self.d.analises.prontas_no_mes(vendedor_id, agora),
                em_andamento=self.d.analises.em_andamento(vendedor_id),
                na_ultima_hora=self.d.analises.criadas_desde(vendedor_id, agora - timedelta(hours=1)),
            )
            nivel, estourou = self._nivel_agora(capacidade)
            if not escolha.leitores(self.d.provedores, nivel):
                raise IAIndisponivel()
            analise_id = str(uuid.uuid4())
            self.d.analises.criar({
                "id": analise_id, "vendedor_id": vendedor_id, "plano_no_momento": capacidade.plano,
                "nivel": nivel.value, "status": StatusAnalise.RECEBIDA.value, "etapa_atual": StatusAnalise.RECEBIDA.value,
                "fotos_meta": [f.meta() for f in fotos], "avisos": com_aviso([], *AVISO_ORCAMENTO) if estourou else [],
                "criado_em": agora, "atualizado_em": agora,
            })
        self._executor.submit(self.processo.ler, analise_id, fotos)
        return {"id": analise_id}

    def obter(self, vendedor_id: int, analise_id: str) -> dict[str, Any]:
        return self._para_tela(self._da_conta(vendedor_id, analise_id))

    def foto_extra(self, vendedor_id: int, analise_id: str, arquivo: ArquivoDeFoto, tipo: str) -> dict[str, Any]:
        analise = self._da_conta(vendedor_id, analise_id)
        if not pode_receber_foto_extra(StatusAnalise(analise["status"])):
            raise EstadoDaAnaliseInvalido("Essa análise não está esperando uma foto extra agora.")
        tipo = tipo if tipo in TIPOS_DE_FOTO_EXTRA else "detalhe"
        foto = self.d.preparador.preparar([arquivo], primeiro_indice=len(analise.get("fotos_meta") or []))[0]
        self.d.analises.atualizar(analise_id, {"status": StatusAnalise.LENDO_PRODUTO.value,
                                               "etapa_atual": StatusAnalise.LENDO_PRODUTO.value,
                                               "atualizado_em": self.d.relogio()})
        self._executor.submit(self.processo.ler_foto_extra, analise_id, foto, tipo)
        return self.obter(vendedor_id, analise_id)

    def confirmar(self, vendedor_id: int, analise_id: str, corpo: dict[str, Any]) -> dict[str, Any]:
        analise = self._da_conta(vendedor_id, analise_id)
        if not pode_confirmar(StatusAnalise(analise["status"])):
            raise EstadoDaAnaliseInvalido("Essa análise não está esperando a confirmação agora.")
        leitura = normalizar_leitura(analise.get("leitura") or {}, len(analise.get("fotos_meta") or []))
        confirmacao = normalizar_confirmacao(corpo, leitura)
        self.d.analises.atualizar(analise_id, {
            "atributos_confirmados": confirmacao.para_dict(), "status": StatusAnalise.PESQUISANDO_MERCADO.value,
            "etapa_atual": StatusAnalise.PESQUISANDO_MERCADO.value, "atualizado_em": self.d.relogio(),
        })
        self._executor.submit(self.processo.continuar, analise_id, StatusAnalise.PESQUISANDO_MERCADO)
        return self.obter(vendedor_id, analise_id)

    def retomar(self, vendedor_id: int, analise_id: str, arquivos: list[ArquivoDeFoto] | None) -> dict[str, Any]:
        analise = self._da_conta(vendedor_id, analise_id)
        if not pode_retomar(StatusAnalise(analise["status"])):
            raise EstadoDaAnaliseInvalido("Essa análise não precisa ser retomada.")
        try:
            etapa = StatusAnalise(analise.get("etapa_atual"))
        except ValueError:
            etapa = None
        tem_leitura = bool(analise.get("leitura"))
        precisa_fotos = retomada_precisa_de_fotos(etapa, tem_leitura)
        if precisa_fotos and not arquivos:
            raise FotosNecessarias()
        fotos = self.d.preparador.preparar(arquivos) if precisa_fotos else []
        agora = self.d.relogio()
        with self._trava:
            if self.d.analises.em_andamento(vendedor_id) >= ANALISES_AO_MESMO_TEMPO:
                raise AnaliseEmAndamento()
            limpar = {"erro_codigo": None, "erro_mensagem_usuario": None, "atualizado_em": agora}
            if precisa_fotos:
                self.d.analises.atualizar(analise_id, {**limpar, "status": StatusAnalise.RECEBIDA.value,
                                                       "etapa_atual": StatusAnalise.RECEBIDA.value,
                                                       "fotos_meta": [f.meta() for f in fotos]})
                self._executor.submit(self.processo.ler, analise_id, fotos)
                return self.obter(vendedor_id, analise_id)
            destino = etapa_de_retomada(etapa, tem_leitura, bool(analise.get("atributos_confirmados")))
            self.d.analises.atualizar(analise_id, {**limpar, "status": destino.value, "etapa_atual": destino.value})
        if destino is not StatusAnalise.AGUARDANDO_CONFIRMACAO:
            self._executor.submit(self.processo.continuar, analise_id, destino)
        return self.obter(vendedor_id, analise_id)

    # ------------------------------------------------------------------

    def _para_tela(self, analise: dict[str, Any]) -> dict[str, Any]:
        status = StatusAnalise(analise["status"])
        try:
            etapa = StatusAnalise(analise.get("etapa_atual"))
        except ValueError:
            etapa = None
        erro = None
        if status is StatusAnalise.FALHOU:
            erro = {"codigo": analise.get("erro_codigo") or "ia_indisponivel",
                    "mensagem": analise.get("erro_mensagem_usuario") or IAIndisponivel().mensagem}
        elif status is StatusAnalise.INTERROMPIDA:
            erro = {"codigo": "interrompida", "mensagem": MENSAGEM_INTERROMPIDA}
        pesquisa = None
        if analise.get("pesquisa_chave") and analise.get("nivel") == "pago":
            pesquisa = self.d.pesquisas.obter(analise["pesquisa_chave"], self.d.relogio())
        leitura = analise.get("leitura")
        return {
            "id": analise["id"],
            "status": status.value,
            "etapa_atual": etapa.value if etapa else None,
            "em_processamento": esta_em_processamento(status),
            "nivel": analise.get("nivel"),
            "plano": analise.get("plano_no_momento"),
            "fotos": analise.get("fotos_meta") or [],
            "leitura": {k: v for k, v in leitura.items() if k != "ml"} if leitura else None,
            "mercado_livre": ({k: (leitura["ml"] or {}).get(k) for k in ("categoria_id", "categoria_nome")}
                              if leitura and leitura.get("ml") else None),
            "atributos_confirmados": analise.get("atributos_confirmados"),
            "pesquisa": pesquisa,
            "preco": analise.get("preco"),
            "texto": analise.get("texto"),
            "canais": analise.get("canais"),
            "avisos": analise.get("avisos") or [],
            "erro": erro,
            "pode_retomar": pode_retomar(status),
            "precisa_fotos_para_retomar": pode_retomar(status) and retomada_precisa_de_fotos(etapa, bool(leitura)),
        }
