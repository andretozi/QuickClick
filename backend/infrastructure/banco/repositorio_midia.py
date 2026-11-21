"""
Infraestrutura · Repositório SQL de fotos de anúncios servidas via URL pública https://
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.infrastructure.banco.models import MidiaFotoModel


def _agora_utc() -> datetime:
    return datetime.now(UTC)


class RepositorioDeMidiaSQL:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        relogio: Callable[[], datetime] = _agora_utc,
    ):
        self._session_factory = session_factory
        self._relogio = relogio

    def salvar(self, vendedor_id: int | None, conteudo: bytes, content_type: str = "image/jpeg") -> str:
        foto_id = uuid.uuid4().hex
        agora = self._relogio()
        with self._session_factory() as sessao:
            registro = MidiaFotoModel(
                id=foto_id,
                vendedor_id=vendedor_id,
                content_type=content_type or "image/jpeg",
                conteudo=bytes(conteudo),
                criado_em=agora,
            )
            sessao.add(registro)
            sessao.commit()
        return foto_id

    def obter(self, foto_id: str) -> tuple[bytes, str] | None:
        codigo = str(foto_id or "").strip()
        if not codigo:
            return None
        with self._session_factory() as sessao:
            registro = sessao.get(MidiaFotoModel, codigo)
            if registro is None:
                return None
            return bytes(registro.conteudo), str(registro.content_type or "image/jpeg")
