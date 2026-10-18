"""Migrações do Alembic em SQLite: batem com os modelos, marcam o banco antigo e recusam o que não é aditivo."""

import tempfile
import unittest
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, text

from backend.infrastructure.banco import models  # noqa: F401
from backend.infrastructure.banco.migrador import (
    REVISAO_INICIAL,
    TABELAS_DE_ANTES,
    MigracaoNaoAditiva,
    comandos_proibidos,
    preparar_banco,
    revisao_atual,
    revisao_head,
    sql_pendente,
)
from backend.infrastructure.database import Base, criar_engine


class BaseSQLite(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        self.url = f"sqlite:///{Path(self._pasta.name) / 'teste.sqlite3'}"
        self.engine = criar_engine(self.url)

    def tearDown(self):
        self.engine.dispose()
        self._pasta.cleanup()

    def criar_banco_antigo(self, sem_coluna: tuple[str, str] | None = None):
        """As tabelas como o create_all criava antes do Alembic (sem a coluna que a 0002 acrescenta)."""
        Base.metadata.create_all(self.engine, tables=[Base.metadata.tables[nome] for nome in TABELAS_DE_ANTES])
        with self.engine.begin() as conexao:
            for tabela, coluna in [("users", "confirmou_maioridade_em"), *([sem_coluna] if sem_coluna else [])]:
                conexao.execute(text(f"ALTER TABLE {tabela} DROP COLUMN {coluna}"))  # só no SQLite do teste


class TestMigracoes(BaseSQLite):
    def test_banco_vazio_vai_ate_a_ultima_revisao_e_bate_com_os_modelos(self):
        resultado = preparar_banco(self.engine, self.url)
        self.assertIsNone(resultado.revisao_antes)
        self.assertEqual(resultado.revisao_depois, revisao_head())
        with self.engine.connect() as conexao:
            diferencas = compare_metadata(MigrationContext.configure(conexao), Base.metadata)
        self.assertEqual(diferencas, [])

    def test_rodar_duas_vezes_nao_muda_nada(self):
        preparar_banco(self.engine, self.url)
        segundo = preparar_banco(self.engine, self.url)
        self.assertFalse(segundo.aplicadas)

    def test_banco_antigo_e_marcado_na_inicial_sem_mexer_nas_tabelas_e_depois_recebe_o_que_falta(self):
        self.criar_banco_antigo()
        with self.engine.begin() as conexao:
            conexao.execute(text("INSERT INTO vendedores (id, nome, plano) VALUES (1, 'Loja', 'pro')"))
        resultado = preparar_banco(self.engine, self.url)
        self.assertTrue(resultado.marcado_na_inicial)
        self.assertEqual(resultado.revisao_depois, revisao_head())
        with self.engine.connect() as conexao:
            self.assertEqual(conexao.execute(text("SELECT plano FROM vendedores")).scalar(), "pro")
            colunas = {c["name"] for c in inspect(conexao).get_columns("users")}
            self.assertIn("confirmou_maioridade_em", colunas)
            self.assertIn("ia_analises", inspect(conexao).get_table_names())

    def test_banco_antigo_diferente_da_revisao_inicial_nao_e_marcado(self):
        self.criar_banco_antigo(sem_coluna=("contas_vinculadas", "apelido"))
        with self.assertRaises(MigracaoNaoAditiva):
            preparar_banco(self.engine, self.url)
        with self.engine.connect() as conexao:
            self.assertIsNone(revisao_atual(conexao))


class TestTravaAditiva(unittest.TestCase):
    def test_sql_pendente_desde_a_inicial_e_so_aditivo(self):
        sql = sql_pendente("postgresql+psycopg2://", REVISAO_INICIAL)
        self.assertIn("CREATE TABLE ia_analises", sql)
        self.assertEqual(comandos_proibidos(sql), [])

    def test_comandos_que_nao_sao_aditivos_sao_achados(self):
        sql = """
            CREATE TABLE nova (id INTEGER);
            ALTER TABLE users ADD COLUMN x VARCHAR;
            ALTER TABLE users DROP COLUMN nome;
            ALTER TABLE users RENAME COLUMN loja TO loja2;
            ALTER TABLE users ALTER COLUMN nome TYPE TEXT;
            DROP TABLE ai_usage;
            DELETE FROM users;
            UPDATE vendedores SET plano = 'pro';
            UPDATE alembic_version SET version_num='x' WHERE alembic_version.version_num = 'y';
        """
        proibidos = comandos_proibidos(sql)
        self.assertEqual(len(proibidos), 6)
        self.assertFalse(any("alembic_version" in c or "ADD COLUMN" in c or "CREATE TABLE" in c for c in proibidos))


if __name__ == "__main__":
    unittest.main()


class TestAlinhamentoDoBancoAntigo(BaseSQLite):
    """O banco de produção como ele estava em 2026-10-17 (ver .claude/banco-estado-atual.md)."""

    def criar_banco_de_producao(self):
        with self.engine.begin() as conexao:
            conexao.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR, password_hash VARCHAR)"))
            conexao.execute(text("CREATE UNIQUE INDEX ix_users_email ON users (email)"))
            conexao.execute(text("CREATE INDEX ix_users_id ON users (id)"))
            conexao.execute(text("CREATE TABLE vendedores (id INTEGER PRIMARY KEY, nome VARCHAR NOT NULL, "
                                 "plano VARCHAR NOT NULL)"))
            conexao.execute(text(
                "CREATE TABLE contas_vinculadas (vendedor_id INTEGER NOT NULL REFERENCES vendedores (id) "
                "ON DELETE CASCADE, marketplace VARCHAR NOT NULL, conectada_em VARCHAR NOT NULL, "
                "access_token VARCHAR NOT NULL, refresh_token VARCHAR NOT NULL, token_expira_em VARCHAR NOT NULL, "
                "PRIMARY KEY (vendedor_id, marketplace))"))

    def test_so_as_colunas_que_faltam_e_rodar_duas_vezes_nao_muda_nada(self):
        from backend.infrastructure.banco.alinhamento import aplicar_alinhamento, operacoes_pendentes

        self.criar_banco_de_producao()
        with self.engine.connect() as conexao:
            pendentes = operacoes_pendentes(conexao)
        self.assertEqual([str(p) for p in pendentes], [
            "users.nome: acrescentar a coluna", "users.loja: acrescentar a coluna",
            "users.criado_em: acrescentar a coluna", "contas_vinculadas.conta_externa_id: acrescentar a coluna",
            "contas_vinculadas.apelido: acrescentar a coluna",
        ])  # email e password_hash já aceitam vazio: nada a fazer
        self.assertEqual(len(aplicar_alinhamento(self.engine)), 5)
        self.assertEqual(aplicar_alinhamento(self.engine), [])
        with self.engine.connect() as conexao:
            colunas = {c["name"]: c["nullable"] for c in inspect(conexao).get_columns("users")}
        self.assertEqual({k: colunas[k] for k in ("nome", "loja", "criado_em")},
                         {"nome": True, "loja": True, "criado_em": True})

    def test_sql_do_postgres_so_acrescenta_e_solta_not_null(self):
        from backend.infrastructure.banco.alinhamento import Operacao, sql_do_alinhamento

        sql = sql_do_alinhamento([Operacao("add_column", "users", "nome"),
                                  Operacao("aceitar_vazio", "users", "email")])
        self.assertIn("ALTER TABLE users ADD COLUMN nome VARCHAR", sql)
        self.assertIn("ALTER TABLE users ALTER COLUMN email DROP NOT NULL", sql)
        self.assertNotIn("SET NOT NULL", sql)
        self.assertNotIn("DROP COLUMN", sql)
