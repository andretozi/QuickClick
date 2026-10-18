"""Módulo único de configuração: ordem das fontes, Key Vault, keyring só no PC, .env por último."""

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from backend.infrastructure.configuracao import (
    ConfiguracaoObrigatoriaAusente,
    LeitorDeConfiguracao,
    Origem,
    database_url,
    nome_no_cofre,
    segredo_jwt,
)

RAIZ = Path(__file__).resolve().parents[2]


class KeyringFalso:
    def __init__(self, **valores):
        self.valores = valores
        self.pedidos = []

    def get_password(self, servico, nome):
        self.pedidos.append((servico, nome))
        return self.valores.get(nome)


class KeyringQuebrado:
    def get_password(self, servico, nome):
        raise RuntimeError("sem backend")


class CofreFalso:
    def __init__(self, **valores):
        self.valores = valores
        self.pedidos = []

    def ler(self, nome):
        self.pedidos.append(nome)
        return self.valores.get(nome)


def leitor(ambiente=None, env_texto=None, keyring=None, cofre=None):
    arquivo = None
    if env_texto is not None:
        pasta = tempfile.TemporaryDirectory()
        arquivo = Path(pasta.name) / ".env"
        arquivo.write_text(env_texto, encoding="utf-8")
        leitor.pastas.append(pasta)
    return LeitorDeConfiguracao(
        RAIZ,
        ambiente or {},
        arquivo_env=arquivo,
        keyring=keyring,
        criar_cofre=(lambda nome: cofre) if cofre is not None else None,
    )


leitor.pastas = []


class TestOrdemDasFontes(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        for pasta in leitor.pastas:
            pasta.cleanup()

    def test_ambiente_ganha_de_tudo(self):
        lido = leitor(
            {"QUICKCLICK_AMBIENTE": "local", "DATABASE_URL": "do-ambiente"},
            env_texto="DATABASE_URL=do-env\n",
            keyring=KeyringFalso(DATABASE_URL="do-keyring"),
        ).ler("DATABASE_URL")
        self.assertEqual((lido.valor, lido.origem), ("do-ambiente", Origem.AMBIENTE))

    def test_referencia_do_key_vault_que_nao_resolveu_vale_como_ausente(self):
        with self.assertLogs("quickclick.config", "WARNING") as logs:
            lido = leitor({"ANTHROPIC_API_KEY_PAGO": "@Microsoft.KeyVault(SecretUri=https://x/secrets/y)"}).ler(
                "ANTHROPIC_API_KEY_PAGO"
            )
        self.assertFalse(lido.definida)
        self.assertIn("ANTHROPIC_API_KEY_PAGO", logs.output[0])
        self.assertNotIn("SecretUri", logs.output[0])

    def test_keyring_so_no_pc_com_ambiente_local(self):
        keyring = KeyringFalso(ANTHROPIC_API_KEY_PAGO="do-keyring")
        self.assertEqual(leitor({"QUICKCLICK_AMBIENTE": "local"}, keyring=keyring).ler("ANTHROPIC_API_KEY_PAGO").origem,
                         Origem.KEYRING)
        self.assertFalse(leitor({}, keyring=keyring).ler("ANTHROPIC_API_KEY_PAGO").definida)

    def test_ambiente_local_pode_vir_do_env(self):
        keyring = KeyringFalso(QUICKCLICK_JWT_SECRET="do-keyring")
        lido = leitor(env_texto="QUICKCLICK_AMBIENTE=local\n", keyring=keyring).ler("QUICKCLICK_JWT_SECRET")
        self.assertEqual(lido.origem, Origem.KEYRING)

    def test_keyring_so_para_segredos(self):
        keyring = KeyringFalso(IA_ATIVA="false")
        leitor({"QUICKCLICK_AMBIENTE": "local"}, keyring=keyring).ler("IA_ATIVA")
        self.assertEqual(keyring.pedidos, [])

    def test_keyring_quebrado_e_pulado_sem_erro(self):
        lido = leitor({"QUICKCLICK_AMBIENTE": "local"}, env_texto="DATABASE_URL=do-env\n",
                      keyring=KeyringQuebrado()).ler("DATABASE_URL")
        self.assertEqual(lido.origem, Origem.ARQUIVO_ENV)

    def test_key_vault_so_com_quickclick_keyvault(self):
        cofre = CofreFalso(**{"gemini-api-key-gratis": "do-cofre"})
        self.assertFalse(leitor({}, cofre=cofre).ler("GEMINI_API_KEY_GRATIS").definida)
        lido = leitor({"QUICKCLICK_KEYVAULT": "cofre"}, cofre=cofre).ler("GEMINI_API_KEY_GRATIS")
        self.assertEqual((lido.valor, lido.origem), ("do-cofre", Origem.KEYVAULT))

    def test_no_pc_o_segredo_dev_do_cofre_tem_preferencia(self):
        cofre = CofreFalso(**{"anthropic-api-key-pago": "producao", "anthropic-api-key-pago-dev": "desenvolvimento"})
        lido = leitor({"QUICKCLICK_KEYVAULT": "cofre", "QUICKCLICK_AMBIENTE": "local"}, cofre=cofre).ler(
            "ANTHROPIC_API_KEY_PAGO"
        )
        self.assertEqual(lido.valor, "desenvolvimento")
        self.assertEqual(cofre.pedidos, ["anthropic-api-key-pago-dev"])

    def test_env_e_a_ultima_reserva(self):
        lido = leitor({}, env_texto="# comentario\nexport IA_ATIVA='false'\n").ler("IA_ATIVA")
        self.assertEqual((lido.valor, lido.origem), ("false", Origem.ARQUIVO_ENV))

    def test_ausente(self):
        lido = leitor({}).ler("ANTHROPIC_API_KEY_GRATIS")
        self.assertEqual((lido.valor, lido.origem, lido.definida), (None, Origem.AUSENTE, False))

    def test_valor_lido_nunca_aparece_no_repr(self):
        self.assertNotIn("segredo-de-verdade", repr(leitor({"DATABASE_URL": "segredo-de-verdade"}).ler("DATABASE_URL")))

    def test_cache_em_memoria(self):
        keyring = KeyringFalso(DATABASE_URL="x")
        config = leitor({"QUICKCLICK_AMBIENTE": "local"}, keyring=keyring)
        config.ler("DATABASE_URL")
        config.ler("DATABASE_URL")
        self.assertEqual(len(keyring.pedidos), 1)


class TestTipos(unittest.TestCase):
    def test_booleano(self):
        config = leitor({"IA_ATIVA": "false", "ADVISOR_ATIVO": "1", "PESQUISA_WEB_ATIVA": "talvez"})
        self.assertFalse(config.booleano("IA_ATIVA", True))
        self.assertTrue(config.booleano("ADVISOR_ATIVO", False))
        with self.assertLogs("quickclick.config", "WARNING"):
            self.assertTrue(config.booleano("PESQUISA_WEB_ATIVA", True))
        self.assertTrue(config.booleano("TRATAMENTO_FOTO_ATIVO", True))

    def test_decimal_aceita_virgula(self):
        self.assertEqual(leitor({"IA_ORCAMENTO_DIARIO_USD": "0,45"}).decimal("IA_ORCAMENTO_DIARIO_USD", Decimal("0.30")),
                         Decimal("0.45"))
        self.assertEqual(leitor({}).decimal("IA_ORCAMENTO_DIARIO_USD", Decimal("0.30")), Decimal("0.30"))

    def test_nome_no_cofre(self):
        self.assertEqual(nome_no_cofre("ANTHROPIC_API_KEY_PAGO"), "anthropic-api-key-pago")


class TestObrigatorias(unittest.TestCase):
    def test_em_producao_sem_jwt_nao_sobe(self):
        with self.assertRaises(ConfiguracaoObrigatoriaAusente) as erro:
            segredo_jwt(leitor({"WEBSITE_SITE_NAME": "quickclick"}))
        self.assertIn("QUICKCLICK_JWT_SECRET", str(erro.exception))

    def test_jwt_le_so_quickclick_jwt_secret(self):
        self.assertEqual(segredo_jwt(leitor({"QUICKCLICK_JWT_SECRET": "x" * 40})), "x" * 40)
        with self.assertRaises(ConfiguracaoObrigatoriaAusente):
            segredo_jwt(leitor({"WEBSITE_SITE_NAME": "quickclick", "JWT_SECRET": "x" * 40}))

    def test_no_pc_sem_jwt_gera_segredo_aleatorio_e_avisa(self):
        from backend.infrastructure.configuracao import obrigatorias

        obrigatorias._segredo_jwt_desta_execucao = None
        with self.assertLogs("quickclick.config", "WARNING"):
            primeiro = segredo_jwt(leitor({}))
        self.assertGreaterEqual(len(primeiro), 32)
        self.assertEqual(segredo_jwt(leitor({})), primeiro)  # o mesmo durante a execução

    def test_em_producao_sem_database_url_nao_sobe(self):
        with self.assertRaises(ConfiguracaoObrigatoriaAusente):
            database_url(leitor({"WEBSITE_SITE_NAME": "quickclick"}))

    def test_no_pc_sem_database_url_devolve_none(self):
        self.assertIsNone(database_url(leitor({})))

    def test_database_url_normalizada_para_o_psycopg2(self):
        url_falsa = "postgres://u:s@h:5432/db"  # verificar_segredos: ignorar
        self.assertEqual(database_url(leitor({"DATABASE_URL": url_falsa})),
                         "postgresql+psycopg2://u:s@h:5432/db")  # verificar_segredos: ignorar


if __name__ == "__main__":
    unittest.main()
