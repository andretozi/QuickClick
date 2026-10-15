"""Partida no Azure App Service: endereço do servidor e limite de tempo da conexão com o Postgres."""

import time
import unittest

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

import main
from backend.infrastructure.database import TIMEOUT_CONEXAO_S, criar_engine

# Endereço de documentação (RFC 5737): nunca responde, como o Postgres atrás de um firewall fechado.
ENDERECO_QUE_NAO_RESPONDE = "postgresql+psycopg2://usuario:senha@192.0.2.1:5432/postgres"


class TestEnderecoDoServidor(unittest.TestCase):
    def test_local_continua_em_127_0_0_1_8080(self):
        self.assertEqual(main.endereco_do_servidor({}), ("127.0.0.1", 8080))

    def test_app_service_escuta_em_todas_as_interfaces_na_porta_do_azure(self):
        ambiente = {"WEBSITE_SITE_NAME": "quickclick", "PORT": "8181"}
        self.assertEqual(main.endereco_do_servidor(ambiente), ("0.0.0.0", 8181))

    def test_app_service_sem_port_usa_8000(self):
        self.assertEqual(main.endereco_do_servidor({"WEBSITE_SITE_NAME": "quickclick"}), ("0.0.0.0", 8000))


class TestTimeoutDaConexao(unittest.TestCase):
    def test_limite_cabe_duas_vezes_nos_230_s_do_app_service(self):
        self.assertLessEqual(2 * TIMEOUT_CONEXAO_S, 60)

    def test_banco_que_nao_responde_falha_no_limite_e_nao_no_timeout_do_sistema(self):
        engine = criar_engine(ENDERECO_QUE_NAO_RESPONDE, timeout_s=2)
        self.addCleanup(engine.dispose)
        inicio = time.monotonic()
        with self.assertRaises(OperationalError):
            with engine.connect() as conexao:
                conexao.execute(text("select 1"))
        self.assertLess(time.monotonic() - inicio, 8)


if __name__ == "__main__":
    unittest.main()
