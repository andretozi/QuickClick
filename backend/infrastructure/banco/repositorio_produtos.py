"""
Infraestrutura · Banco · Produtos (anúncios da Quick Click) e publicações, por vendedor

Toda consulta filtra pelo vendedor do token. As publicações saem antes do produto na mesma
transação, sem depender do PRAGMA foreign_keys do SQLite. Datas em UTC; o SQLite devolve sem fuso.
"""

from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.domain.erros import AnuncioDesatualizado
from backend.domain.produto import Produto, Publicacao
from backend.infrastructure.banco.models import AnaliseIAModel, ProdutoModel, PublicacaoModel
from backend.infrastructure.banco.repositorio_ia import _utc
from backend.infrastructure.database import SessionLocal

CAMPOS_DO_PRODUTO = (
    "titulo", "descricao", "categoria", "condicao", "preco_centavos", "preco_sugerido_centavos", "estoque",
    "fotos", "capa", "atributos",
)


def _para_publicacao(linha: PublicacaoModel) -> Publicacao:
    return Publicacao(canal=linha.canal, status=linha.status, id_externo=linha.id_externo, permalink=linha.permalink,
                      categoria_id=linha.categoria_id, saude=linha.saude, vendidos=linha.vendidos)


def _para_produto(linha: ProdutoModel, publicacoes: list[PublicacaoModel]) -> Produto:
    return Produto(
        id=linha.id,
        **{campo: getattr(linha, campo) for campo in CAMPOS_DO_PRODUTO},
        analise_id=linha.analise_id,
        criado_em=_utc(linha.criado_em),
        atualizado_em=_utc(linha.atualizado_em),
        publicacoes=[_para_publicacao(p) for p in sorted(publicacoes, key=lambda p: p.canal)],
    )


class RepositorioDeProdutosSQL:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def listar(self, vendedor_id: int) -> list[Produto]:
        with self._session_factory() as session:
            linhas = (
                session.query(ProdutoModel)
                .filter_by(vendedor_id=vendedor_id)
                .order_by(ProdutoModel.atualizado_em.desc(), ProdutoModel.id)
                .all()
            )
            por_produto: dict[str, list[PublicacaoModel]] = {}
            for publicacao in session.query(PublicacaoModel).filter_by(vendedor_id=vendedor_id):
                por_produto.setdefault(publicacao.produto_id, []).append(publicacao)
            return [_para_produto(linha, por_produto.get(linha.id, [])) for linha in linhas]

    def obter(self, vendedor_id: int, produto_id: str) -> Produto | None:
        with self._session_factory() as session:
            linha = session.query(ProdutoModel).filter_by(vendedor_id=vendedor_id, id=produto_id).first()
            return None if linha is None else _para_produto(linha, self._publicacoes(session, vendedor_id, produto_id))

    def salvar(self, vendedor_id: int, produto: Produto, agora: datetime) -> Produto:
        with self._session_factory() as session:
            linha = (
                session.query(ProdutoModel)
                .filter_by(vendedor_id=vendedor_id, id=produto.id)
                .with_for_update()
                .first()
            )
            if linha is None:
                linha = ProdutoModel(vendedor_id=vendedor_id, id=produto.id, criado_em=_utc(produto.criado_em))
                session.add(linha)
            elif _utc(linha.atualizado_em) > _utc(produto.atualizado_em):
                raise AnuncioDesatualizado()
            else:
                # A versão sempre anda, mesmo com duas gravações no mesmo milissegundo
                agora = max(_utc(agora), _utc(linha.atualizado_em) + timedelta(milliseconds=1))
                self._apagar_publicacoes(session, vendedor_id, produto.id)
            try:
                self._preencher(session, linha, vendedor_id, produto, _utc(agora))
                session.commit()
            except IntegrityError as erro:  # outra gravação ao mesmo tempo, ou o item já é de outro produto
                session.rollback()
                raise AnuncioDesatualizado() from erro
            return _para_produto(linha, self._publicacoes(session, vendedor_id, produto.id))

    def importar(self, vendedor_id: int, produto: Produto) -> bool:
        """Grava só se o id e os itens dos canais ainda não existem para o vendedor; guarda os horários do corpo."""
        externos = [and_(PublicacaoModel.canal == p.canal, PublicacaoModel.id_externo == p.id_externo)
                    for p in produto.publicacoes if p.id_externo]
        with self._session_factory() as session:
            if session.query(ProdutoModel.id).filter_by(vendedor_id=vendedor_id, id=produto.id).first():
                return False
            if externos and session.query(PublicacaoModel.produto_id).filter(
                PublicacaoModel.vendedor_id == vendedor_id, or_(*externos)
            ).first():
                return False
            linha = ProdutoModel(vendedor_id=vendedor_id, id=produto.id, criado_em=_utc(produto.criado_em))
            session.add(linha)
            try:
                self._preencher(session, linha, vendedor_id, produto, _utc(produto.atualizado_em))
                session.commit()
            except IntegrityError:  # duas abas importando juntas: a outra já gravou
                session.rollback()
                return False
            return True

    def remover(self, vendedor_id: int, produto_id: str) -> bool:
        with self._session_factory() as session:
            self._apagar_publicacoes(session, vendedor_id, produto_id)
            apagados = session.query(ProdutoModel).filter_by(vendedor_id=vendedor_id, id=produto_id).delete()
            session.commit()
            return apagados > 0

    @staticmethod
    def _publicacoes(session: Session, vendedor_id: int, produto_id: str) -> list[PublicacaoModel]:
        return session.query(PublicacaoModel).filter_by(vendedor_id=vendedor_id, produto_id=produto_id).all()

    @staticmethod
    def _apagar_publicacoes(session: Session, vendedor_id: int, produto_id: str) -> None:
        session.query(PublicacaoModel).filter_by(vendedor_id=vendedor_id, produto_id=produto_id).delete()

    @staticmethod
    def _preencher(session: Session, linha: ProdutoModel, vendedor_id: int, produto: Produto,
                   atualizado_em: datetime) -> None:
        """Copia os campos e troca as publicações. `analise_id` só fica se a análise for do vendedor."""
        for campo in CAMPOS_DO_PRODUTO:
            setattr(linha, campo, getattr(produto, campo))
        analise_do_vendedor = produto.analise_id and session.query(AnaliseIAModel.id).filter_by(
            id=produto.analise_id, vendedor_id=vendedor_id
        ).first()
        linha.analise_id = produto.analise_id if analise_do_vendedor else None
        linha.atualizado_em = atualizado_em
        session.flush()  # o produto entra antes das publicações (chave estrangeira no Postgres)
        session.add_all(
            PublicacaoModel(vendedor_id=vendedor_id, produto_id=produto.id, canal=p.canal, status=p.status,
                            id_externo=p.id_externo, permalink=p.permalink, categoria_id=p.categoria_id,
                            saude=p.saude, vendidos=p.vendidos, atualizado_em=atualizado_em)
            for p in produto.publicacoes
        )
