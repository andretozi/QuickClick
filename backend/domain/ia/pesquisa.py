"""
Domínio · IA · Pesquisa de mercado (perfil do comprador)

Cache por chave: o nível (o Grátis não tem busca na web), a categoria do Mercado Livre (ou o
produto normalizado, sem categoria) e a condição. Vale por 15 dias.
"""

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from typing import Any

VALIDADE = timedelta(days=15)
MAX_CHAVE = 200


def normalizar_produto(produto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", produto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")[:80] or "produto"


def chave_da_pesquisa(nivel: str, ml_categoria_id: str | None, produto: str, condicao: str) -> str:
    base = ml_categoria_id or normalizar_produto(produto)
    return f"{nivel}:{base}:{condicao or 'desconhecido'}"[:MAX_CHAVE]


@dataclass(frozen=True)
class PerfilDoComprador:
    perfil_comprador: str
    o_que_valoriza: tuple[str, ...] = ()
    objecoes: tuple[str, ...] = ()
    termos_que_usam: tuple[str, ...] = ()
    fontes: tuple[str, ...] = field(default=())

    def para_dict(self) -> dict[str, Any]:
        return asdict(self)


def _lista(valores: Any, maximo: int, limite: int = 160) -> tuple[str, ...]:
    if not isinstance(valores, list):
        return ()
    saida = []
    for valor in valores:
        if isinstance(valor, str) and (texto := re.sub(r"\s+", " ", valor).strip()[:limite]):
            if texto not in saida:
                saida.append(texto)
        if len(saida) == maximo:
            break
    return tuple(saida)


def normalizar_perfil(bruto: dict[str, Any]) -> PerfilDoComprador:
    bruto = bruto if isinstance(bruto, dict) else {}
    fontes = tuple(f for f in _lista(bruto.get("fontes"), 8, 300) if f.startswith(("https://", "http://")))
    return PerfilDoComprador(
        perfil_comprador=re.sub(r"\s+", " ", str(bruto.get("perfil_comprador") or "")).strip()[:600],
        o_que_valoriza=_lista(bruto.get("o_que_valoriza"), 5),
        objecoes=_lista(bruto.get("objecoes"), 4),
        termos_que_usam=_lista(bruto.get("termos_que_usam"), 6, 60),
        fontes=fontes,
    )
