"""
Conferência do banco (scripts/migrar.py). Só roda no PC, com QUICKCLICK_AMBIENTE=local.

    python -m scripts.migrar          # migra o banco para a última revisão
    python -m scripts.migrar --status # só mostra a revisão atual e o que falta
    python -m scripts.migrar --sql    # mostra o SQL do que falta, sem aplicar

Também permite promover um usuário para administrador:
    python -m scripts.migrar --promover-admin usuario@email.com
"""

import argparse
import sys

from backend.domain.usuario import PAPEL_ADMIN, normalizar_email
from backend.infrastructure.banco.migrador import (
    comandos_proibidos,
    preparar_banco,
    revisao_atual,
    revisao_head,
    sql_pendente,
)
from backend.infrastructure.banco.models import User
from backend.infrastructure.configuracao import (
    ConfiguracaoObrigatoriaAusente,
    configuracao,
    database_url,
)
from backend.infrastructure.database import SessionLocal, criar_engine


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrações do banco (Alembic) e gestão de papéis.")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--status", action="store_true", help="mostra as revisões sem rodar nada")
    grupo.add_argument("--sql", action="store_true", help="mostra o SQL pendente, sem aplicar")
    grupo.add_argument("--promover-admin", metavar="EMAIL", help="atribui papel de administrador a um usuário")
    args = parser.parse_args()

    leitor = configuracao()
    if not leitor.ambiente_local and not leitor.em_producao:
        print("Recusado: execute com QUICKCLICK_AMBIENTE=local no .env do PC.")
        return 1

    if args.promover_admin:
        email = normalizar_email(args.promover_admin)
        with SessionLocal() as session:
            user = session.query(User).filter_by(email=email).first()
            if user is None:
                print(f"Usuário não encontrado: {email}")
                return 1
            user.papel = PAPEL_ADMIN
            user.token_versao = (user.token_versao or 0) + 1
            session.commit()
            print(f"Sucesso: Usuário {email} (ID #{user.id}) promovido para '{PAPEL_ADMIN}'.")
            print("Sessões anteriores foram invalidadas; faça login novamente para assumir os privilégios.")
            return 0

    try:
        url = database_url(leitor)
    except ConfiguracaoObrigatoriaAusente:
        url = None

    if url is None:
        print("DATABASE_URL ausente. Guarde a URL com: python -m scripts.guardar_chave DATABASE_URL")
        return 1

    engine = criar_engine(url)
    try:
        with engine.connect() as conexao:
            atual = revisao_atual(conexao)
        head = revisao_head()

        if args.status:
            print(f"Revisão atual: {atual or 'nenhuma (banco novo)'}")
            print(f"Última revisão do código: {head}")
            print("Em dia." if atual == head else "Faltam migrações: rode python -m scripts.migrar")
            return 0

        if args.sql:
            sql = sql_pendente(url, atual)
            if not sql.strip():
                print("Nada pendente: o banco já está na última revisão.")
                return 0
            proibidos = comandos_proibidos(sql)
            if proibidos:
                print("AVISO: o SQL pendente contém comandos que travam a migração:")
                for p in proibidos:
                    print(f"  {p}")
                print()
            print(sql)
            return 0

        print(f"Preparando o banco (revisão antes: {atual or 'vazio'})...")
        resultado = preparar_banco(engine, url)
        if resultado.marcado_na_inicial:
            print("Banco antigo reconhecido: marcado na revisão inicial, sem mexer nas tabelas de antes.")
        if resultado.aplicadas:
            print(f"Migrações aplicadas. Banco agora na revisão: {resultado.revisao_depois}")
        else:
            print(f"Banco já estava na última revisão ({resultado.revisao_depois}).")
        for aviso in resultado.avisos:
            print(f"  aviso: {aviso}")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
