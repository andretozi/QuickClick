"""
Infraestrutura · Migrações do banco (Alembic), sempre aditivas.

Na partida (main.py) e pelo scripts/migrar.py:
    1. banco vazio: cria tudo (upgrade head);
    2. banco antigo, sem a tabela alembic_version: confere se as tabelas de antes batem com a
       revisão inicial e marca o banco nela (stamp), sem rodar nada nas tabelas;
    3. gera o SQL do que falta e só aplica se ele for aditivo (CREATE TABLE, ADD COLUMN, CREATE INDEX).
       Qualquer DROP, RENAME, ALTER COLUMN, DELETE, UPDATE ou TRUNCATE trava a migração.
"""

import io
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config as ConfigAlembic
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, inspect

from backend.infrastructure.configuracao import RAIZ_DO_PROJETO

log = logging.getLogger("quickclick.banco")

PASTA_MIGRACOES = Path(__file__).resolve().parent / "migracoes"
REVISAO_INICIAL = "0001_estado_atual"
TABELAS_DE_ANTES = ("users", "marketplace_tokens", "ai_usage", "vendedores", "contas_vinculadas")
# Colunas que as migrações seguintes acrescentam nas tabelas de antes (não contam como diferença)
COLUNAS_NOVAS_NAS_TABELAS_DE_ANTES = {("users", "confirmou_maioridade_em")}

_COMANDO_PROIBIDO = re.compile(
    r"^\s*(DROP\b|TRUNCATE\b|DELETE\b|UPDATE\b|ALTER\s+TABLE\s+\S+\s+(?:DROP|RENAME|ALTER)\b|"
    r"ALTER\s+TABLE\s+\S+\s+RENAME\b|ALTER\s+INDEX\b)",
    re.IGNORECASE,
)


class MigracaoNaoAditiva(RuntimeError):
    pass


@dataclass
class ResultadoDoBanco:
    revisao_antes: str | None = None
    revisao_depois: str | None = None
    marcado_na_inicial: bool = False
    aplicadas: bool = False
    avisos: list[str] = field(default_factory=list)


def config_alembic(url: str | None = None, conexao=None, saida: io.StringIO | None = None) -> ConfigAlembic:
    config = ConfigAlembic(str(RAIZ_DO_PROJETO / "alembic.ini"), output_buffer=saida)
    config.set_main_option("script_location", str(PASTA_MIGRACOES))
    if url:
        config.attributes["url"] = url
    if conexao is not None:
        config.attributes["connection"] = conexao
    return config


def revisao_head() -> str:
    return ScriptDirectory.from_config(config_alembic()).get_current_head()


def revisao_atual(conexao) -> str | None:
    return MigrationContext.configure(conexao).get_current_revision()


def sql_pendente(url: str, desde: str | None) -> str:
    """O SQL que levaria o banco de `desde` (None: vazio) até a última revisão, sem conectar."""
    saida = io.StringIO()
    intervalo = f"{desde}:head" if desde else "head"
    command.upgrade(config_alembic(url=url, saida=saida), intervalo, sql=True)
    return saida.getvalue()


def comandos_proibidos(sql: str) -> list[str]:
    """Os comandos que não são aditivos (o controle de versão do próprio Alembic não conta)."""
    proibidos = []
    for comando in sql.split(";"):
        comando = "\n".join(linha for linha in comando.splitlines() if not linha.strip().startswith("--")).strip()
        if not comando or "alembic_version" in comando:
            continue
        if _COMANDO_PROIBIDO.search(comando):
            proibidos.append(comando.splitlines()[0][:120])
    return proibidos


def _metadata_dos_modelos() -> MetaData:
    from backend.infrastructure.banco import models  # noqa: F401
    from backend.infrastructure.database import Base

    return Base.metadata


def _coluna_nova(item) -> bool:
    """add_column de uma coluna que a migração seguinte acrescenta (não é diferença do banco antigo)."""
    return item[0] == "add_column" and (item[2], item[3].name) in COLUNAS_NOVAS_NAS_TABELAS_DE_ANTES


def diferencas_das_tabelas_de_antes(conexao) -> tuple[list[str], list[str]]:
    """(diferenças que impedem marcar a revisão inicial, avisos que não impedem)."""
    existentes = set(inspect(conexao).get_table_names())
    faltando = [nome for nome in TABELAS_DE_ANTES if nome not in existentes]
    if faltando:
        return [f"tabela ausente: {nome}" for nome in faltando], []

    contexto = MigrationContext.configure(
        conexao,
        opts={
            "compare_type": True,
            # só as tabelas de antes, dos dois lados (banco e modelos)
            "include_name": lambda nome, tipo, _pai: tipo != "table" or nome in TABELAS_DE_ANTES,
            "include_object": lambda objeto, nome, tipo, _refletido, _par: tipo != "table" or nome in TABELAS_DE_ANTES,
        },
    )
    graves, avisos = [], []
    for diferenca in compare_metadata(contexto, _metadata_dos_modelos()):
        itens = diferenca if isinstance(diferenca, list) else [diferenca]
        for item in itens:
            tipo = item[0]
            if _coluna_nova(item):
                continue
            descricao = f"{tipo}: {item[1:]}"[:200]
            if tipo.endswith("_index") or tipo.endswith("_constraint") or tipo.endswith("_fk"):
                avisos.append(descricao)
            else:
                graves.append(descricao)
    return graves, avisos


def preparar_banco(engine, url: str) -> ResultadoDoBanco:
    """Deixa o banco na última revisão, só com migrações aditivas. Levanta MigracaoNaoAditiva se não der."""
    resultado = ResultadoDoBanco()
    with engine.begin() as conexao:
        resultado.revisao_antes = revisao_atual(conexao)
        existentes = set(inspect(conexao).get_table_names())

        if resultado.revisao_antes is None and existentes & set(TABELAS_DE_ANTES):
            graves, avisos = diferencas_das_tabelas_de_antes(conexao)
            resultado.avisos.extend(avisos)
            if graves:
                raise MigracaoNaoAditiva(
                    "O banco tem as tabelas de antes do Alembic, mas elas não batem com a revisão inicial: "
                    + "; ".join(graves)
                )
            command.stamp(config_alembic(url=url, conexao=conexao), REVISAO_INICIAL)
            resultado.marcado_na_inicial = True
            resultado.revisao_antes = REVISAO_INICIAL
            log.info("Banco antigo marcado na revisão inicial (%s), sem mexer nas tabelas.", REVISAO_INICIAL)

        head = revisao_head()
        if resultado.revisao_antes != head:
            proibidos = comandos_proibidos(sql_pendente(url, resultado.revisao_antes))
            if proibidos:
                raise MigracaoNaoAditiva("Migração não aditiva bloqueada: " + " | ".join(proibidos))
            command.upgrade(config_alembic(url=url, conexao=conexao), "head")
            resultado.aplicadas = True
        resultado.revisao_depois = revisao_atual(conexao)
    return resultado
