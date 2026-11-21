"""
Aplicação · Estruturas e utilitários agnósticos de canal para publicação e gestão de anúncios
"""

import ipaddress
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from backend.application.ia.modelos import FotoPreparada
from backend.application.ia.portas import PreparadorDeFotos
from backend.application.portas import FalhaNoMarketplace, PublicadorDeCanal, RepositorioDeProdutos
from backend.domain.erros import PublicacaoRecusada
from backend.domain.ia.escrita import cortar_titulo
from backend.domain.ia.leitura import normalizar_chave

log = logging.getLogger("quickclick.marketplaces")

ANUNCIO_CLASSICO = "gold_special"
CONDICAO_PARA_CANAL = {"novo": "new", "new": "new", "usado": "used", "used": "used", "recondicionado": "used"}
STATUS_PARA_CANAL = {
    "pausado": "paused",
    "paused": "paused",
    "publicado": "active",
    "ativo": "active",
    "active": "active",
}
PRECO_MINIMO_CENTAVOS = 100
ESTOQUE_MAXIMO = 99_999
DESCRICAO_MAX = 50_000

_HOSTS_INTERNOS_BLOQUEADOS = {"localhost", "metadata.google.internal", "169.254.169.254"}
_SUFIXOS_INTERNOS_BLOQUEADOS = (".local", ".internal", ".localhost", ".lan", ".corp", ".home")


@dataclass(frozen=True)
class AnuncioParaPublicar:
    titulo: str
    descricao: str
    preco_centavos: int
    estoque: int
    condicao: str  # new | used
    atributos: tuple[tuple[str, str], ...]
    analise_id: str | None = None
    ml_categoria_id: str | None = None
    fotos_mantidas: tuple[str, ...] = ()
    produto_id: str | None = None


def _host_publico_seguro(host: str) -> bool:
    limpo = host.strip().lower().rstrip(".")
    if not limpo or limpo in _HOSTS_INTERNOS_BLOQUEADOS or "." not in limpo:
        return False
    if limpo.endswith(_SUFIXOS_INTERNOS_BLOQUEADOS):
        return False
    try:
        ip = ipaddress.ip_address(limpo)
        return ip.is_global and not (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
        )
    except ValueError:
        return True


def _validar_url_foto(url: Any, *, exigir_mlstatic: bool = True) -> str | None:
    texto = str(url or "").strip()
    if not texto or len(texto) > 500:
        return None
    partes = urlparse(texto)
    host = (partes.hostname or "").lower()
    if partes.scheme != "https" or not host or partes.username or partes.password:
        return None
    if exigir_mlstatic:
        if not (host == "mlstatic.com" or host.endswith(".mlstatic.com")):
            return None
    elif not _host_publico_seguro(host):
        return None
    return texto


def anuncio_de_dict(dados: dict[str, Any], *, exigir_mlstatic: bool = True) -> AnuncioParaPublicar:
    if not isinstance(dados, dict):
        raise ValueError("Anúncio inválido.")
    titulo = cortar_titulo(str(dados.get("titulo") or ""))
    if not titulo:
        raise ValueError("O anúncio precisa de um título.")
    try:
        preco = int(dados.get("preco_centavos"))
        estoque_bruto = dados.get("estoque")
        estoque = 1 if estoque_bruto is None or estoque_bruto == "" else int(estoque_bruto)
    except (TypeError, ValueError) as erro:
        raise ValueError("Preço ou estoque inválido.") from erro
    if preco < PRECO_MINIMO_CENTAVOS:
        raise ValueError("O preço precisa ser de pelo menos R$ 1,00.")
    if not 0 <= estoque <= ESTOQUE_MAXIMO:
        raise ValueError("O estoque informado é inválido.")
    atributos = []
    for item in dados.get("atributos") or []:
        if isinstance(item, dict):
            chave, valor = normalizar_chave(item.get("chave")), str(item.get("valor") or "").strip()[:120]
            if chave and valor:
                atributos.append((chave, valor))
    mantidas = tuple(
        url
        for url in (
            _validar_url_foto(u, exigir_mlstatic=exigir_mlstatic)
            for u in (dados.get("fotos_mantidas") or [])[:24]
        )
        if url
    )[:6]
    produto_id_bruto = str(dados.get("produto_id") or "").strip()
    return AnuncioParaPublicar(
        titulo=titulo,
        descricao=str(dados.get("descricao") or "").strip()[:DESCRICAO_MAX],
        preco_centavos=preco,
        estoque=estoque,
        condicao=CONDICAO_PARA_CANAL.get(str(dados.get("condicao") or "").lower(), "new"),
        atributos=tuple(atributos),
        analise_id=str(dados["analise_id"]) if dados.get("analise_id") else None,
        ml_categoria_id=str(dados["ml_categoria_id"]) if dados.get("ml_categoria_id") else None,
        fotos_mantidas=mantidas,
        produto_id=produto_id_bruto or None,
    )


def _resumir_fallback_erro(mensagem: str) -> str:
    texto = str(mensagem or "").strip()
    if not texto:
        return ""
    if ": " in texto:
        texto = texto.split(": ", 1)[1].strip()
    return texto[:300] if texto else ""


def _causas(corpo: Any, fallback_mensagem: str = "") -> list[str]:
    if isinstance(corpo, list):
        extraidos = []
        for item in corpo:
            if isinstance(item, dict):
                msg = str(item.get("message") or item.get("msg") or item.get("code") or "").strip()
                if msg:
                    extraidos.append(msg)
            elif isinstance(item, str) and item.strip():
                extraidos.append(item.strip())
        if extraidos:
            return extraidos
    if isinstance(corpo, str) and corpo.strip():
        return [corpo.strip()[:300]]
    if not isinstance(corpo, dict):
        resumo = _resumir_fallback_erro(fallback_mensagem)
        return [resumo] if resumo else []
    causas_brutas = [c for c in (corpo.get("cause") or []) if isinstance(c, dict)]
    erros_causa = [
        str(c.get("message") or c.get("code") or "").strip()
        for c in causas_brutas
        if str(c.get("type") or "").strip().lower() != "warning"
    ]
    erros_causa = [c for c in erros_causa if c]
    if erros_causa:
        return erros_causa
    avisos_causa = [
        str(c.get("message") or c.get("code") or "").strip()
        for c in causas_brutas
    ]
    avisos_causa = [c for c in avisos_causa if c]
    if avisos_causa:
        return avisos_causa
    if corpo.get("message"):
        return [str(corpo["message"]).strip()]
    detail = corpo.get("detail")
    if isinstance(detail, str) and detail.strip():
        return [detail.strip()]
    if isinstance(detail, list):
        detalhes = []
        for d in detail:
            if isinstance(d, dict):
                loc = ".".join(str(p) for p in (d.get("loc") or []) if str(p) not in ("body", "query", "path"))
                msg = str(d.get("msg") or d.get("message") or "").strip()
                if loc and msg:
                    detalhes.append(f"{loc}: {msg}")
                elif msg:
                    detalhes.append(msg)
            elif isinstance(d, str) and d.strip():
                detalhes.append(d.strip())
        if detalhes:
            return detalhes
    errors = corpo.get("errors")
    if isinstance(errors, dict):
        lista_erros = []
        for campo, msgs in errors.items():
            if isinstance(msgs, list):
                for m in msgs:
                    if str(m).strip():
                        lista_erros.append(f"{campo}: {str(m).strip()}")
            elif str(msgs).strip():
                lista_erros.append(f"{campo}: {str(msgs).strip()}")
        if lista_erros:
            return lista_erros
    if isinstance(errors, list):
        lista_erros = [str(e.get("message") or e if isinstance(e, dict) else e).strip() for e in errors]
        lista_erros = [e for e in lista_erros if e]
        if lista_erros:
            return lista_erros
    for chave in ("error", "title"):
        val = corpo.get(chave)
        if isinstance(val, str) and val.strip():
            return [val.strip()]
    resumo = _resumir_fallback_erro(fallback_mensagem)
    return [resumo] if resumo else []


def verificar_duplicidade_no_canal(
    produtos: RepositorioDeProdutos | None,
    publicador: PublicadorDeCanal,
    vendedor_id: int,
    produto_id: str | None,
    canal: str,
    token: str,
) -> None:
    if not produto_id or produtos is None:
        return
    produto = produtos.obter(vendedor_id, produto_id)
    if produto is None:
        return
    publicacao = next((p for p in produto.publicacoes if p.canal == canal), None)
    id_existente = str(publicacao.id_externo or "").strip() if publicacao else ""
    if publicacao and id_existente and publicacao.status != "nao_publicado":
        try:
            remoto = publicador.obter_anuncio(token, id_existente)
            status_remoto = str(remoto.get("status") or "").strip().lower()
            sub_status = remoto.get("sub_status") or []
            excluido_remoto = status_remoto == "closed" or (
                isinstance(sub_status, list) and "deleted" in sub_status
            )
        except FalhaNoMarketplace as erro:
            excluido_remoto = erro.status == 404
        if not excluido_remoto:
            raise PublicacaoRecusada(
                [
                    "Este produto já está publicado neste canal com um ID vinculado. "
                    "Atualize o anúncio existente em vez de criar outro."
                ],
                canal=canal,
            )


def subir_imagens_no_canal(
    publicador: PublicadorDeCanal,
    preparador: PreparadorDeFotos,
    token: str,
    preparadas: list[FotoPreparada],
    *,
    deve_ampliar: Callable[[Any], bool] | None = None,
) -> list[dict[str, str]]:
    enviadas: list[dict[str, str]] = []
    for foto in preparadas:
        nome = f"foto{foto.indice + 1}.jpg"
        try:
            pic_id = publicador.subir_imagem(token, foto.leitura_jpeg, nome)
        except FalhaNoMarketplace as erro:
            ampliar = getattr(preparador, "ampliar_para_publicacao", None)
            if not callable(ampliar) or deve_ampliar is None or not deve_ampliar(erro.corpo):
                raise
            log.info("Marketplace recusou %s por bordas brancas/tamanho; reenviando versão ampliada.", nome)
            ampliada = ampliar(foto.leitura_jpeg)
            pic_id = publicador.subir_imagem(token, ampliada, nome)
        if str(pic_id).startswith(("https://", "http://", "data:image/")):
            enviadas.append({"source": str(pic_id)})
        else:
            enviadas.append({"id": str(pic_id)})
    return enviadas


def executar_alterar_status(
    publicador: PublicadorDeCanal,
    token: str,
    codigo: str,
    status: str,
    *,
    canal: str,
    erro_desconectado: Callable[[], Exception],
) -> dict[str, Any]:
    destino = STATUS_PARA_CANAL.get(str(status or "").strip().lower())
    if not destino:
        raise ValueError("Status inválido para o anúncio.")
    try:
        publicador.atualizar_anuncio(token, codigo, {"status": destino})
        return publicador.obter_anuncio(token, codigo)
    except FalhaNoMarketplace as erro:
        if erro.status in (401, 403):
            raise erro_desconectado() from erro
        raise PublicacaoRecusada(_causas(erro.corpo, erro.mensagem), canal=canal) from erro


def executar_excluir(
    publicador: PublicadorDeCanal,
    token: str,
    codigo: str,
    *,
    canal: str,
    erro_desconectado: Callable[[], Exception],
) -> dict[str, Any]:
    try:
        publicador.excluir_anuncio(token, codigo)
    except FalhaNoMarketplace as erro:
        if erro.status in (401, 403):
            raise erro_desconectado() from erro
        raise PublicacaoRecusada(_causas(erro.corpo, erro.mensagem), canal=canal) from erro
    return {"id": codigo, "excluido": True}
