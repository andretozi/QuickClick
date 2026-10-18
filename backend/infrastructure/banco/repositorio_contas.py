"""
Infraestrutura · Contas vinculadas no banco via SQLAlchemy (Azure PostgreSQL).

Os tokens OAuth ficam cifrados (prefixo "enc:v1:"). Um token antigo em texto puro é lido
como está e volta cifrado na próxima gravação (a renovação do token, por exemplo).
"""

from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.infrastructure.banco.models import ContaVinculadaModel
from backend.infrastructure.database import SessionLocal
from backend.infrastructure.seguranca.cripto_tokens import CifradorDeTokens


class RepositorioContasVinculadasSQL:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal, cifrador: CifradorDeTokens | None = None):
        self._session_factory = session_factory
        self._cifrador = cifrador or CifradorDeTokens(None, avisar=False)

    def _para_conta(self, linha: ContaVinculadaModel) -> ContaVinculada:
        return ContaVinculada(
            vendedor_id=linha.vendedor_id,
            marketplace=linha.marketplace,
            conectada_em=datetime.fromisoformat(linha.conectada_em),
            credenciais=CredenciaisOAuth(
                access_token=self._cifrador.decifrar(linha.access_token),
                refresh_token=self._cifrador.decifrar(linha.refresh_token),
                expira_em=datetime.fromisoformat(linha.token_expira_em),
                conta_externa_id=linha.conta_externa_id,
                apelido=linha.apelido,
            ),
        )

    def listar_do_vendedor(self, vendedor_id: int) -> list[ContaVinculada]:
        with self._session_factory() as session:
            linhas = (
                session.query(ContaVinculadaModel)
                .filter_by(vendedor_id=vendedor_id)
                .order_by(ContaVinculadaModel.conectada_em)
                .all()
            )
            return [self._para_conta(linha) for linha in linhas]

    def buscar(self, vendedor_id: int, marketplace: str) -> ContaVinculada | None:
        with self._session_factory() as session:
            linha = (
                session.query(ContaVinculadaModel)
                .filter_by(vendedor_id=vendedor_id, marketplace=marketplace)
                .first()
            )
            return None if linha is None else self._para_conta(linha)

    def salvar(self, conta: ContaVinculada) -> None:
        access_token = self._cifrador.cifrar(conta.credenciais.access_token)
        refresh_token = self._cifrador.cifrar(conta.credenciais.refresh_token)
        with self._session_factory() as session:
            linha = (
                session.query(ContaVinculadaModel)
                .filter_by(vendedor_id=conta.vendedor_id, marketplace=conta.marketplace)
                .first()
            )
            if linha is None:
                linha = ContaVinculadaModel(
                    vendedor_id=conta.vendedor_id,
                    marketplace=conta.marketplace,
                )
                session.add(linha)

            linha.conectada_em = conta.conectada_em.isoformat()
            linha.access_token = access_token
            linha.refresh_token = refresh_token
            linha.token_expira_em = conta.credenciais.expira_em.isoformat()
            linha.conta_externa_id = conta.credenciais.conta_externa_id
            linha.apelido = conta.credenciais.apelido
            session.commit()

    def remover(self, vendedor_id: int, marketplace: str) -> None:
        with self._session_factory() as session:
            session.query(ContaVinculadaModel).filter_by(
                vendedor_id=vendedor_id, marketplace=marketplace
            ).delete()
            session.commit()


# Alias para retrocompatibilidade
RepositorioContasVinculadasSQLite = RepositorioContasVinculadasSQL
