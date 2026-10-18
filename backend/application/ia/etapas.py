"""
Aplicação · IA · As etapas da análise, em segundo plano

    0 preparar (já feito no pedido) → tratar → verificar → 1 ler (releitura da etiqueta e atributos do ML)
    → aguardando_confirmacao → 3 pesquisa de mercado → 4 preço e canais → 5 título e descrição → pronta

Cada etapa grava o resultado parcial no banco (nunca a foto). As fotos só existem na memória
deste processo enquanto a leitura roda. Erro de provedor: a cadeia de reserva; sem reserva, a análise
falha com "ia_indisponivel" (não conta na cota) e pode ser retomada. Contas e estatística ficam no
Python; a IA só interpreta e escreve.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.application.ia import escolha
from backend.application.ia.modelos import (
    ConfiguracaoDaIA,
    ContextoDaChamada,
    EntradaDaLeitura,
    EntradaDaPesquisa,
    EntradaDaReleitura,
    EntradaDoPreco,
    EntradaDoTexto,
    FalhaDoProvedor,
    Fidelidade,
    FotoPreparada,
)
from backend.application.ia.portas import (
    CacheDePesquisas,
    ContasDoVendedor,
    FontePrecosMarketplace,
    GuardiaoDeFidelidade,
    PreparadorDeFotos,
    RepositorioDeAnalises,
    TratadorDeFoto,
)
from backend.domain.erros import ErroDeDominio, IAIndisponivel
from backend.domain.ia.analise import Nivel, StatusAnalise, posicao
from backend.domain.ia.atributos_ml import (
    ligar_por_regra,
    ligar_sugestoes_da_ia,
    mapa_de_chaves,
    obrigatorios_faltando,
    perguntas_dos_obrigatorios,
)
from backend.domain.ia.canais import aplicar_motivos, canais_candidatos
from backend.domain.ia.escrita import (
    DESCRICAO_MAX,
    ESPECIFICACOES_MAX,
    limpar_escrita,
    problemas_de_escrita,
    titulo_valido,
)
from backend.domain.ia.fotos import MAX_FOTOS_NA_LEITURA
from backend.domain.ia.leitura import (
    CATEGORIAS,
    Cartao,
    Confirmacao,
    Leitura,
    OrigemAtributo,
    juntar_leitura_parcial,
    normalizar_confirmacao,
    normalizar_leitura,
)
from backend.domain.ia.pesquisa import VALIDADE, chave_da_pesquisa, normalizar_perfil
from backend.domain.ia.preco import (
    Concorrente,
    EstatisticaDePreco,
    estatistica,
    preco_da_ia_aceitavel,
    preco_sugerido_por_regra,
)

log = logging.getLogger("quickclick.ia")

MAX_ETIQUETAS_RELIDAS = 2
ESTRATEGIAS = ("vender_rapido", "equilibrado", "maximo")


@dataclass
class DependenciasDaAnalise:
    analises: RepositorioDeAnalises
    preparador: PreparadorDeFotos
    tratador: TratadorDeFoto
    guardiao: GuardiaoDeFidelidade
    provedores: escolha.ProvedoresDeIA
    fonte_ml: FontePrecosMarketplace | None
    contas: ContasDoVendedor
    pesquisas: CacheDePesquisas
    config: ConfiguracaoDaIA
    relogio: Callable[[], datetime]


def com_aviso(avisos: list[dict[str, str]] | None, codigo: str, mensagem: str) -> list[dict[str, str]]:
    avisos = list(avisos or [])
    if all(a.get("codigo") != codigo for a in avisos):
        avisos.append({"codigo": codigo, "mensagem": mensagem})
    return avisos


class ProcessoDaAnalise:
    def __init__(self, dependencias: DependenciasDaAnalise):
        self.d = dependencias

    # ------------------------------------------------------------------
    # apoio
    # ------------------------------------------------------------------

    def _salvar(self, analise_id: str, **campos: Any) -> None:
        campos["atualizado_em"] = self.d.relogio()
        self.d.analises.atualizar(analise_id, campos)

    def _contexto(self, analise: dict[str, Any], etapa: str) -> ContextoDaChamada:
        return ContextoDaChamada(vendedor_id=analise["vendedor_id"], analise_id=analise["id"], etapa=etapa)

    def _falhar(self, analise_id: str, etapa: StatusAnalise, erro: ErroDeDominio) -> None:
        self._salvar(analise_id, status=StatusAnalise.FALHOU.value, etapa_atual=etapa.value,
                     erro_codigo=erro.codigo, erro_mensagem_usuario=erro.mensagem)

    def _proteger(self, analise_id: str, etapa: StatusAnalise, trabalho: Callable[[], None]) -> None:
        """Nenhum erro inesperado deixa a análise presa: vira falha que pode ser retomada."""
        try:
            trabalho()
        except ErroDeDominio as erro:
            self._falhar(analise_id, etapa, erro)
        except Exception as erro:  # o tipo vai para o log; dados e fotos nunca
            log.error("Análise %s falhou na etapa %s (%s).", analise_id, etapa.value, type(erro).__name__)
            self._falhar(analise_id, etapa, IAIndisponivel("Algo deu errado na análise. Tente de novo ou preencha à mão."))

    # ------------------------------------------------------------------
    # etapa 0 e 1: tratar, verificar e ler (com as fotos em memória)
    # ------------------------------------------------------------------

    def ler(self, analise_id: str, fotos: list[FotoPreparada]) -> None:
        self._proteger(analise_id, StatusAnalise.LENDO_PRODUTO, lambda: self._ler(analise_id, fotos))

    def _ler(self, analise_id: str, fotos: list[FotoPreparada]) -> None:
        analise = self.d.analises.obter(analise_id)
        self._salvar(analise_id, status=StatusAnalise.PREPARANDO_FOTOS.value,
                     etapa_atual=StatusAnalise.PREPARANDO_FOTOS.value, erro_codigo=None, erro_mensagem_usuario=None)
        fotos, avisos = self._tratar_e_verificar(analise, fotos)
        self._salvar(analise_id, status=StatusAnalise.LENDO_PRODUTO.value, etapa_atual=StatusAnalise.LENDO_PRODUTO.value)

        nivel = Nivel(analise["nivel"])
        entrada = EntradaDaLeitura(tuple(fotos[:MAX_FOTOS_NA_LEITURA]), CATEGORIAS)
        resultado = escolha.tentar_em_ordem(escolha.leitores(self.d.provedores, nivel),
                                            lambda p: p.ler(entrada, self._contexto(analise, "leitura")))
        if resultado is None:
            self._falhar(analise_id, StatusAnalise.LENDO_PRODUTO, IAIndisponivel())
            return
        resposta, leitor = resultado
        leitura = normalizar_leitura(resposta.dados, len(entrada.fotos))

        for etiqueta in leitura.etiqueta_ilegivel[:MAX_ETIQUETAS_RELIDAS]:
            recorte = self.d.preparador.recortar(fotos[etiqueta.foto], etiqueta.caixa)
            try:
                relida = leitor.reler(EntradaDaReleitura((), leitura.para_dict(), recorte, "etiqueta"),
                                      self._contexto(analise, "releitura"))
            except FalhaDoProvedor as falha:
                log.info("Releitura da etiqueta pulada (%s).", falha.motivo)
                continue
            leitura = juntar_leitura_parcial(leitura, relida.dados, OrigemAtributo.ETIQUETA)

        dados = leitura.para_dict()
        ml = self._atributos_do_ml(analise, leitura)
        if ml is not None:
            dados["ml"], perguntas_ml = ml
            dados["perguntas"] = _juntar_perguntas(dados["perguntas"], perguntas_ml, leitura)
        if not leitura.reconhecido:
            avisos = com_aviso(avisos, "produto_nao_reconhecido", "Não consegui reconhecer o produto nessa foto.")
        # As fotos saem da memória quando este método termina (nada guarda referência a elas)
        self._salvar(analise_id, status=StatusAnalise.AGUARDANDO_CONFIRMACAO.value,
                     etapa_atual=StatusAnalise.AGUARDANDO_CONFIRMACAO.value, leitura=dados,
                     ml_categoria_id=(dados.get("ml") or {}).get("categoria_id"), avisos=avisos)

    def _tratar_e_verificar(self, analise: dict[str, Any], fotos: list[FotoPreparada]
                            ) -> tuple[list[FotoPreparada], list[dict[str, str]]]:
        """Versão final: tratar, depois verificar. No MVP (SemTratamento) a foto volta igual, sem custo."""
        avisos = list(analise.get("avisos") or [])
        ativo = self.d.config.tratamento_foto_ativo
        if ativo:
            self._salvar(analise["id"], status=StatusAnalise.TRATANDO_FOTOS.value,
                         etapa_atual=StatusAnalise.TRATANDO_FOTOS.value)
        tratadas = [self.d.tratador.tratar(f, self._contexto(analise, "tratamento")) for f in fotos]
        if ativo:
            self._salvar(analise["id"], status=StatusAnalise.VERIFICANDO_FOTOS.value,
                         etapa_atual=StatusAnalise.VERIFICANDO_FOTOS.value)
        finais = []
        for original, tratada in zip(fotos, tratadas, strict=True):
            fidelidade = self.d.guardiao.verificar(original, tratada, self._contexto(analise, "fidelidade"))
            if fidelidade is Fidelidade.GRAVE:
                finais.append(original)
                avisos = com_aviso(avisos, "tratamento_descartado", "Usei a foto original: o tratamento mudou o produto.")
            else:
                finais.append(tratada)
                if fidelidade is Fidelidade.LEVE:
                    avisos = com_aviso(avisos, "tratamento_leve", "A foto tratada tem uma diferença pequena. Confira.")
        return finais, avisos

    def _atributos_do_ml(self, analise: dict[str, Any], leitura: Leitura
                         ) -> tuple[dict[str, Any], list[dict[str, str]]] | None:
        """Categoria do Mercado Livre e os atributos dela (só com o Mercado Livre conectado)."""
        if not leitura.reconhecido or self.d.fonte_ml is None:
            return None
        token = self.d.contas.token_mercado_livre(analise["vendedor_id"])
        if not token:
            return None
        categoria = self.d.fonte_ml.descobrir_categoria(list(leitura.termos_busca) or [leitura.produto], token)
        if categoria is None:
            return None
        da_categoria = self.d.fonte_ml.atributos_da_categoria(categoria.categoria_id, token)
        com_valor = [(a.chave, a.valor) for a in leitura.atributos if a.cartao is not Cartao.PERGUNTA]
        ligados, sobras = ligar_por_regra(com_valor, da_categoria)
        if sobras and da_categoria:
            resultado = escolha.tentar_em_ordem(
                escolha.ligadores(self.d.provedores, Nivel(analise["nivel"])),
                lambda p: p.ligar(sobras, da_categoria, self._contexto(analise, "atributos_ml")))
            if resultado is not None:
                ligados += ligar_sugestoes_da_ia(resultado[0].dados.get("ligacoes"), sobras, da_categoria, ligados)
        faltando = obrigatorios_faltando(da_categoria, ligados)
        ml = {
            "categoria_id": categoria.categoria_id,
            "categoria_nome": categoria.nome,
            "mapa": mapa_de_chaves({l.chave: l.id for l in ligados if l.chave}, faltando),
            "obrigatorios": [a.id for a in faltando],
        }
        return ml, perguntas_dos_obrigatorios(faltando)

    def ler_foto_extra(self, analise_id: str, foto: FotoPreparada, tipo: str) -> None:
        """A foto extra (etiqueta, verso, detalhe) reabre só a leitura dela, com a leitura atual como contexto."""
        def trabalho():
            analise = self.d.analises.obter(analise_id)
            atual = analise.get("leitura") or {}
            leitura = normalizar_leitura(atual, len(analise.get("fotos_meta") or []))
            contexto_sem_ml = {k: v for k, v in atual.items() if k != "ml"}
            resultado = escolha.tentar_em_ordem(
                escolha.leitores(self.d.provedores, Nivel(analise["nivel"])),
                lambda p: p.reler(EntradaDaReleitura((), contexto_sem_ml, foto.leitura_jpeg, tipo),
                                  self._contexto(analise, "foto_extra")))
            avisos = analise.get("avisos") or []
            dados = atual
            if resultado is None:
                avisos = com_aviso(avisos, "foto_extra_falhou", "Não consegui ler essa foto agora. Preencha à mão.")
            else:
                origem = OrigemAtributo.ETIQUETA if tipo == "etiqueta" else OrigemAtributo.FOTO
                nova = juntar_leitura_parcial(leitura, resultado[0].dados, origem)
                dados = nova.para_dict()
                if atual.get("ml"):
                    dados["ml"] = atual["ml"]
                    perguntas_ml = [p for p in atual.get("perguntas") or [] if p.get("chave") in atual["ml"]["mapa"]]
                    dados["perguntas"] = _juntar_perguntas(dados["perguntas"], perguntas_ml, nova)
            self._salvar(analise_id, status=StatusAnalise.AGUARDANDO_CONFIRMACAO.value,
                         etapa_atual=StatusAnalise.AGUARDANDO_CONFIRMACAO.value, leitura=dados, avisos=avisos,
                         fotos_meta=[*(analise.get("fotos_meta") or []), foto.meta()])

        self._proteger(analise_id, StatusAnalise.LENDO_PRODUTO, trabalho)

    # ------------------------------------------------------------------
    # etapas 3 a 6: pesquisa, preço e canais, texto, pronta
    # ------------------------------------------------------------------

    def continuar(self, analise_id: str, desde: StatusAnalise) -> None:
        etapa_atual = {"valor": desde}

        def trabalho():
            analise = self.d.analises.obter(analise_id)
            leitura = normalizar_leitura(analise.get("leitura") or {}, len(analise.get("fotos_meta") or []))
            confirmacao = normalizar_confirmacao(analise.get("atributos_confirmados") or {}, leitura)
            nivel = Nivel(analise["nivel"])
            perfil = None

            if posicao(desde) <= posicao(StatusAnalise.PESQUISANDO_MERCADO):
                etapa_atual["valor"] = StatusAnalise.PESQUISANDO_MERCADO
                self._salvar(analise_id, status=StatusAnalise.PESQUISANDO_MERCADO.value,
                             etapa_atual=StatusAnalise.PESQUISANDO_MERCADO.value)
                chave, perfil = self._pesquisar(analise, confirmacao, nivel)
                analise["pesquisa_chave"] = chave
                if chave is None:
                    analise["avisos"] = com_aviso(analise.get("avisos"), "pesquisa_indisponivel",
                                                  "A pesquisa de mercado não respondeu; segui sem ela.")
                self._salvar(analise_id, pesquisa_chave=chave, avisos=analise.get("avisos"))
            elif analise.get("pesquisa_chave"):
                perfil = self.d.pesquisas.obter(analise["pesquisa_chave"], self.d.relogio())

            if posicao(desde) <= posicao(StatusAnalise.PRECIFICANDO):
                etapa_atual["valor"] = StatusAnalise.PRECIFICANDO
                self._salvar(analise_id, status=StatusAnalise.PRECIFICANDO.value,
                             etapa_atual=StatusAnalise.PRECIFICANDO.value)
                preco, canais, avisos = self._precificar(analise, leitura, confirmacao, nivel)
                self._salvar(analise_id, preco=preco, canais=canais, avisos=avisos)

            etapa_atual["valor"] = StatusAnalise.ESCREVENDO
            self._salvar(analise_id, status=StatusAnalise.ESCREVENDO.value, etapa_atual=StatusAnalise.ESCREVENDO.value)
            texto = self._escrever(analise, confirmacao, nivel, perfil)
            if texto is None:
                self._falhar(analise_id, StatusAnalise.ESCREVENDO, IAIndisponivel(
                    "A IA não conseguiu escrever o texto agora. Tente de novo ou escreva à mão."))
                return
            agora = self.d.relogio()
            self._salvar(analise_id, texto=texto, status=StatusAnalise.PRONTA.value,
                         etapa_atual=StatusAnalise.PRONTA.value, concluida_em=agora)

        try:
            trabalho()
        except ErroDeDominio as erro:
            self._falhar(analise_id, etapa_atual["valor"], erro)
        except Exception as erro:
            log.error("Análise %s falhou na etapa %s (%s).", analise_id, etapa_atual["valor"].value, type(erro).__name__)
            self._falhar(analise_id, etapa_atual["valor"],
                         IAIndisponivel("Algo deu errado na análise. Tente de novo ou preencha à mão."))

    def _pesquisar(self, analise: dict[str, Any], confirmacao: Confirmacao, nivel: Nivel
                   ) -> tuple[str | None, dict[str, Any] | None]:
        agora = self.d.relogio()
        chave = chave_da_pesquisa(nivel.value, analise.get("ml_categoria_id"), confirmacao.produto,
                                  confirmacao.condicao.value)
        guardada = self.d.pesquisas.obter(chave, agora)
        if guardada is not None:
            return chave, guardada
        entrada = EntradaDaPesquisa(
            produto=confirmacao.produto, categoria=confirmacao.categoria, condicao=confirmacao.condicao.value,
            atributos=tuple((a.chave, a.valor) for a in confirmacao.atributos),
            com_web=nivel is Nivel.PAGO and self.d.config.pesquisa_web_ativa,
        )
        resultado = escolha.tentar_em_ordem(escolha.pesquisadores(self.d.provedores, nivel),
                                            lambda p: p.pesquisar(entrada, self._contexto(analise, "pesquisa")))
        if resultado is None:
            return None, None
        perfil = normalizar_perfil(resultado[0].dados)
        conteudo = perfil.para_dict()
        self.d.pesquisas.salvar(chave, conteudo, list(perfil.fontes), agora, agora + VALIDADE)
        return chave, conteudo

    def _estatistica_do_mercado(self, analise: dict[str, Any], leitura: Leitura, confirmacao: Confirmacao,
                                nivel: Nivel, token: str | None) -> tuple[EstatisticaDePreco | None, str | None]:
        termos = list(leitura.termos_busca) or [confirmacao.produto]
        if token and self.d.fonte_ml is not None:
            observados = self.d.fonte_ml.buscar_parecidos(termos, analise.get("ml_categoria_id"),
                                                          confirmacao.condicao.value, token)
            est = estatistica([Concorrente(o.preco_centavos, o.frete_gratis) for o in observados or []])
            if est is not None:
                return est, "mercado_livre"
        if nivel is Nivel.PAGO and self.d.config.pesquisa_web_ativa:
            atributos = tuple((a.chave, a.valor) for a in confirmacao.atributos)
            resultado = escolha.tentar_em_ordem(
                escolha.precos_na_web(self.d.provedores, nivel),
                lambda p: p.buscar_precos(confirmacao.produto, confirmacao.condicao.value, atributos,
                                          self._contexto(analise, "precos_web")))
            if resultado is not None:
                itens = resultado[0].dados.get("itens") or []
                concorrentes = []
                for item in itens if isinstance(itens, list) else []:
                    try:
                        concorrentes.append(Concorrente(int(item.get("preco_centavos")), bool(item.get("frete_gratis"))))
                    except (TypeError, ValueError, AttributeError):
                        continue
                est = estatistica(concorrentes)
                if est is not None:
                    return est, "web"
        return None, None

    def _precificar(self, analise: dict[str, Any], leitura: Leitura, confirmacao: Confirmacao, nivel: Nivel
                    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]]]:
        vendedor_id = analise["vendedor_id"]
        token = self.d.contas.token_mercado_livre(vendedor_id)
        avisos = list(analise.get("avisos") or [])
        est, fonte = self._estatistica_do_mercado(analise, leitura, confirmacao, nivel, token)
        condicao = confirmacao.condicao.value
        candidatos = canais_candidatos(self.d.contas.conectados(vendedor_id), confirmacao.categoria,
                                       est.mediana if est else None, condicao)
        if est is None:
            motivo = "mercado_livre_desconectado" if not token else "sem_resultados"
            avisos = com_aviso(avisos, "preco_sem_dados", "Não achei preços parecidos para comparar. Digite o seu preço.")
            return {"sem_dados": True, "motivo": motivo}, [c.para_dict() for c in candidatos], avisos

        categoria_ml = analise.get("ml_categoria_id")

        def tarifa_de(preco: int) -> int | None:
            if token and categoria_ml and self.d.fonte_ml is not None:
                return self.d.fonte_ml.tarifa(preco, categoria_ml, token)
            return None

        regra = preco_sugerido_por_regra(est, condicao)
        preco: dict[str, Any] = {
            "sem_dados": False, "fonte": fonte, "mercado": est.para_dict(), "por_ia": False,
            "sugerido_centavos": regra, "faixa": {"min": est.p25, "max": est.p75},
            "estrategia": None, "justificativa": None, "alertas": [],
        }
        if nivel is Nivel.PAGO:
            tarifa_da_regra = tarifa_de(regra)
            entrada = EntradaDoPreco(
                dados_do_mercado={**est.para_dict(), "fonte": fonte, "tarifa_classico_centavos": tarifa_da_regra,
                                  "sugerido_pela_regra_centavos": regra},
                atributos=tuple((a.chave, a.valor) for a in confirmacao.atributos), condicao=condicao,
                defeitos=confirmacao.defeitos, canais_candidatos=tuple(c.para_dict() for c in candidatos),
            )
            resultado = escolha.tentar_em_ordem(escolha.precificadores(self.d.provedores, nivel),
                                                lambda p: p.precificar(entrada, self._contexto(analise, "preco")))
            if resultado is not None:
                preco, candidatos = _aplicar_preco_da_ia(preco, resultado[0].dados, est, candidatos)
        tarifa = tarifa_de(preco["sugerido_centavos"])
        preco["tarifa_centavos"] = tarifa
        preco["liquido_centavos"] = preco["sugerido_centavos"] - tarifa if tarifa is not None else None
        return preco, [c.para_dict() for c in candidatos], avisos

    def _escrever(self, analise: dict[str, Any], confirmacao: Confirmacao, nivel: Nivel,
                  perfil: dict[str, Any] | None) -> dict[str, Any] | None:
        entrada = EntradaDoTexto(
            produto=confirmacao.produto, categoria=confirmacao.categoria, condicao=confirmacao.condicao.value,
            atributos=tuple((a.chave, a.valor) for a in confirmacao.atributos), defeitos=confirmacao.defeitos,
            perfil={k: v for k, v in (perfil or {}).items() if k != "fontes"} or None,
        )
        resultado = escolha.tentar_em_ordem(escolha.redatores(self.d.provedores, nivel),
                                            lambda p: p.escrever(entrada, self._contexto(analise, "texto")))
        if resultado is None:
            return None
        return self._conferir_texto(analise, resultado[0].dados, nivel)

    def _conferir_texto(self, analise: dict[str, Any], dados: dict[str, Any], nivel: Nivel) -> dict[str, Any]:
        """Regra de escrita: uma correção pela IA rápida mandando só os trechos errados; falhou de novo,
        limpeza determinística no Python. Título acima de 60 é cortado na última palavra inteira."""
        texto = _texto_bruto(dados)
        problemas = _problemas_do_texto(texto)
        corrigido = False
        if problemas:
            trechos = [p.trecho for p in problemas][:12]
            resultado = escolha.tentar_em_ordem(escolha.corretores(self.d.provedores, nivel),
                                                lambda p: p.corrigir(texto, trechos, self._contexto(analise, "correcao")))
            if resultado is not None:
                texto = _texto_bruto(resultado[0].dados)
                corrigido = True
            if _problemas_do_texto(texto):
                texto = {
                    "titulo": limpar_escrita(texto["titulo"]),
                    "descricao": limpar_escrita(texto["descricao"]),
                    "especificacoes": [{"rotulo": limpar_escrita(e["rotulo"]), "valor": limpar_escrita(e["valor"])}
                                       for e in texto["especificacoes"]],
                }
                corrigido = True
        return {
            "titulo": titulo_valido(texto["titulo"]),
            "descricao": texto["descricao"][:DESCRICAO_MAX].strip(),
            "especificacoes": [e for e in texto["especificacoes"] if e["rotulo"] and e["valor"]][:ESPECIFICACOES_MAX],
            "corrigido": corrigido,
        }


def _juntar_perguntas(perguntas: list[dict[str, Any]], extras: list[dict[str, str]], leitura: Leitura
                      ) -> list[dict[str, Any]]:
    """Perguntas da leitura + as do Mercado Livre, sem repetir chave e sem perguntar o que já tem valor."""
    com_valor = {a.chave for a in leitura.atributos if a.cartao is not Cartao.PERGUNTA}
    vistas = {p.get("chave") for p in perguntas}
    juntas = list(perguntas)
    for extra in extras:
        if extra["chave"] not in vistas and extra["chave"] not in com_valor:
            juntas.append(extra)
            vistas.add(extra["chave"])
    return juntas


def _texto_bruto(dados: dict[str, Any]) -> dict[str, Any]:
    especificacoes = []
    for item in dados.get("especificacoes") or []:
        if isinstance(item, dict):
            especificacoes.append({"rotulo": str(item.get("rotulo") or "").strip()[:40],
                                   "valor": str(item.get("valor") or "").strip()[:120]})
    return {"titulo": str(dados.get("titulo") or "").strip(), "descricao": str(dados.get("descricao") or "").strip(),
            "especificacoes": especificacoes}


def _problemas_do_texto(texto: dict[str, Any]) -> list:
    problemas = problemas_de_escrita(texto["titulo"]) + problemas_de_escrita(texto["descricao"], DESCRICAO_MAX)
    for item in texto["especificacoes"]:
        problemas += problemas_de_escrita(f"{item['rotulo']}: {item['valor']}")
    return problemas


def _aplicar_preco_da_ia(preco: dict[str, Any], dados: dict[str, Any], est: EstatisticaDePreco, candidatos):
    """Aceita o preço da IA só perto dos dados reais; a faixa fica dentro do que o mercado mostrou."""
    try:
        sugerido = int(dados.get("preco_sugerido_centavos"))
    except (TypeError, ValueError):
        return preco, candidatos
    if not preco_da_ia_aceitavel(sugerido, est):
        log.info("Preço da IA fora dos dados reais: ficou o da regra.")
        return preco, candidatos
    faixa = dados.get("faixa") if isinstance(dados.get("faixa"), dict) else {}
    try:
        minimo = max(est.minimo, int(faixa.get("min")))
        maximo = min(est.maximo, int(faixa.get("max")))
    except (TypeError, ValueError):
        minimo, maximo = est.p25, est.p75
    if not minimo <= sugerido <= maximo:
        minimo, maximo = min(est.p25, sugerido), max(est.p75, sugerido)
    estrategia = dados.get("estrategia") if dados.get("estrategia") in ESTRATEGIAS else "equilibrado"
    alertas = [limpar_escrita(str(a))[:200] for a in (dados.get("alertas") or []) if str(a).strip()][:3]
    motivos = {}
    for canal in dados.get("canais") or []:
        if isinstance(canal, dict) and canal.get("slug") and canal.get("motivo"):
            motivos[str(canal["slug"])] = limpar_escrita(str(canal["motivo"]))[:200]
    preco = {
        **preco, "por_ia": True, "sugerido_centavos": sugerido, "faixa": {"min": minimo, "max": maximo},
        "estrategia": estrategia, "justificativa": limpar_escrita(str(dados.get("justificativa") or ""))[:400] or None,
        "alertas": alertas,
    }
    return preco, aplicar_motivos(candidatos, motivos)
