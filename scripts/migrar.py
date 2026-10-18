"""
Migracoes do banco (Alembic), sempre aditivas. A URL vem do modulo de configuracao.

Uso (da raiz):
    python -m scripts.migrar --status     # revisao do banco e a ultima do codigo
    python -m scripts.migrar --alinhar-sql  # banco antigo: mostra o SQL do alinhamento (so le o banco)
    python -m scripts.migrar --alinhar      # banco antigo: aplica o alinhamento (so ADD COLUMN e DROP NOT NULL)
    python -m scripts.migrar --sql        # gera o SQL pendente em .claude/migracoes/ (sem conectar para aplicar)
    python -m scripts.migrar --conferir   # confere se as tabelas de antes batem com a revisao inicial (so le)
    python -m scripts.migrar --marcar     # marca o banco antigo na revisao inicial (stamp), depois de conferir
    python -m scripts.migrar --aplicar    # aplica o que falta, so se for aditivo (o main.py faz isso na partida)
"""

import argparse
import logging
import sys
from datetime import datetime

from alembic import command
from sqlalchemy import text

from backend.infrastructure.banco.alinhamento import aplicar_alinhamento, operacoes_pendentes, sql_do_alinhamento
from backend.infrastructure.banco.migrador import (
    REVISAO_INICIAL,
    MigracaoNaoAditiva,
    comandos_proibidos,
    config_alembic,
    diferencas_das_tabelas_de_antes,
    preparar_banco,
    revisao_atual,
    revisao_head,
    sql_pendente,
)
from backend.infrastructure.configuracao import RAIZ_DO_PROJETO, configuracao, database_url
from backend.infrastructure.database import criar_engine

URL_SO_DIALETO = "postgresql+psycopg2://"  # gera o SQL do Postgres sem conectar


def _url_ou_sair() -> str:
    url = database_url(configuracao())
    if not url:
        raise SystemExit("Falta DATABASE_URL. Rode python -m scripts.verificar_config para ver onde guardar.")
    return url


def status() -> int:
    engine = criar_engine(_url_ou_sair())
    try:
        with engine.connect() as conexao:
            atual = revisao_atual(conexao)
    finally:
        engine.dispose()
    print(f"Banco: {atual or 'sem Alembic (banco antigo ou vazio)'}")
    print(f"Codigo: {revisao_head()}")
    return 0


def gerar_sql(desde: str | None) -> int:
    pasta = RAIZ_DO_PROJETO / ".claude" / "migracoes"
    pasta.mkdir(parents=True, exist_ok=True)
    sql = sql_pendente(URL_SO_DIALETO, desde)
    nome = f"{datetime.now():%Y%m%d-%H%M}-{desde or 'vazio'}-ate-{revisao_head()}.sql"
    (pasta / nome).write_text(sql, encoding="utf-8")
    proibidos = comandos_proibidos(sql)
    print(f"SQL salvo em .claude/migracoes/{nome}")
    if proibidos:
        print("ATENCAO: comandos que nao sao aditivos (a migracao sera recusada):")
        for comando in proibidos:
            print(f"  {comando}")
        return 1
    print("Conferido: so CREATE TABLE, ADD COLUMN e CREATE INDEX (mais o controle de versao do Alembic).")
    return 0


def alinhar_sql() -> int:
    engine = criar_engine(_url_ou_sair())
    try:
        with engine.connect() as conexao:
            conexao.execute(text("set transaction read only"))  # so le o catalogo
            pendentes = operacoes_pendentes(conexao)
    finally:
        engine.dispose()
    if not pendentes:
        print("Nada a alinhar: o banco ja tem essas colunas como o codigo espera.")
        return 0
    print("Operacoes pendentes:")
    for operacao in pendentes:
        print(f"  {operacao}")
    sql = sql_do_alinhamento(pendentes)
    pasta = RAIZ_DO_PROJETO / ".claude" / "migracoes"
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{datetime.now():%Y%m%d-%H%M}-alinhamento.sql"
    (pasta / nome).write_text(sql, encoding="utf-8")
    print(f"\nSQL (salvo em .claude/migracoes/{nome}), nada foi aplicado:\n")
    print(sql)
    return 0


def alinhar() -> int:
    engine = criar_engine(_url_ou_sair())
    try:
        with engine.connect() as conexao:
            if revisao_atual(conexao) is not None:
                print("O banco ja tem controle do Alembic: o alinhamento e so para o banco antigo.")
                return 1
        feitas = aplicar_alinhamento(engine)
    finally:
        engine.dispose()
    if not feitas:
        print("Nada a alinhar: o banco ja estava como o codigo espera.")
    for operacao in feitas:
        print(f"feito: {operacao}")
    return 0


def conferir() -> int:
    engine = criar_engine(_url_ou_sair())
    try:
        with engine.connect() as conexao:
            graves, avisos = diferencas_das_tabelas_de_antes(conexao)
    finally:
        engine.dispose()
    for aviso in avisos:
        print(f"aviso (nao impede): {aviso}")
    if graves:
        print("As tabelas de antes NAO batem com a revisao inicial:")
        for grave in graves:
            print(f"  {grave}")
        return 1
    print(f"As tabelas de antes batem com a revisao inicial ({REVISAO_INICIAL}).")
    return 0


def marcar() -> int:
    if conferir() != 0:
        print("Nada foi marcado.")
        return 1
    url = _url_ou_sair()
    engine = criar_engine(url)
    try:
        with engine.begin() as conexao:
            if revisao_atual(conexao) is not None:
                print("O banco ja tem controle do Alembic: nada a marcar.")
                return 0
            command.stamp(config_alembic(url=url, conexao=conexao), REVISAO_INICIAL)
    finally:
        engine.dispose()
    print(f"Banco marcado na revisao {REVISAO_INICIAL} (so a tabela alembic_version foi criada).")
    return 0


def aplicar() -> int:
    url = _url_ou_sair()
    engine = criar_engine(url)
    try:
        resultado = preparar_banco(engine, url)
    except MigracaoNaoAditiva as erro:
        print(f"Recusado: {erro}")
        return 1
    finally:
        engine.dispose()
    print(f"Banco: {resultado.revisao_antes or 'vazio'} -> {resultado.revisao_depois}"
          + (" (marcado na revisao inicial)" if resultado.marcado_na_inicial else ""))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Migracoes aditivas do banco da Quick Click.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--status", action="store_true")
    grupo.add_argument("--alinhar-sql", action="store_true", help="mostra o SQL do alinhamento do banco antigo")
    grupo.add_argument("--alinhar", action="store_true", help="aplica o alinhamento do banco antigo")
    grupo.add_argument("--sql", action="store_true", help="gera o SQL pendente desde a revisao inicial")
    grupo.add_argument("--sql-do-zero", action="store_true", help="gera o SQL de um banco vazio")
    grupo.add_argument("--conferir", action="store_true")
    grupo.add_argument("--marcar", action="store_true")
    grupo.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="  aviso: %(message)s")
    if args.status:
        return status()
    if args.alinhar_sql:
        return alinhar_sql()
    if args.alinhar:
        return alinhar()
    if args.sql:
        return gerar_sql(REVISAO_INICIAL)
    if args.sql_do_zero:
        return gerar_sql(None)
    if args.conferir:
        return conferir()
    if args.marcar:
        return marcar()
    return aplicar()


if __name__ == "__main__":
    sys.exit(main())
