"""Segurança: JWT com finalidade e sem segredo padrão, criptografia dos tokens e a trava do banco nos testes."""

import unittest

import jwt

from backend.domain.erros import ServicoIndisponivel, TokenInvalido
from backend.infrastructure.database import criar_engine
from backend.infrastructure.seguranca import token_jwt
from backend.infrastructure.seguranca.cripto_tokens import CifradorDeTokens
from backend.infrastructure.seguranca.token_jwt import FINALIDADE_ESTADO_OAUTH, ServicoJWT

SEGREDO = "segredo-jwt-so-dos-testes-com-mais-de-32-caracteres"
CHAVE = "nN1Yc8pK0wVQx3vT1o6m2f9W1u0Hq2c5e7Kx8Zl4bD0="


class TestJWT(unittest.TestCase):
    def test_sem_segredo_padrao_no_codigo(self):
        self.assertFalse(hasattr(token_jwt, "SEGREDO_PADRAO"))
        with self.assertRaises(ValueError):
            ServicoJWT("")

    def test_token_de_acesso_vale_como_acesso(self):
        servico = ServicoJWT(SEGREDO)
        payload = servico.validar_token(servico.gerar_token(7, "A@B.com"))
        self.assertEqual((payload["sub"], payload["email"], payload["fin"]), ("7", "a@b.com", "acesso"))

    def test_estado_do_oauth_nao_serve_como_login(self):
        servico = ServicoJWT(SEGREDO)
        estado = servico.gerar_token(7, "oauth:mercado-livre", finalidade=FINALIDADE_ESTADO_OAUTH)
        with self.assertRaises(TokenInvalido):
            servico.validar_token(estado)
        self.assertEqual(servico.validar_token(estado, finalidade=FINALIDADE_ESTADO_OAUTH)["sub"], "7")

    def test_estado_antigo_sem_finalidade_tambem_nao_serve_como_login(self):
        antigo = jwt.encode({"sub": "7", "email": "oauth:mercado-livre"}, SEGREDO, algorithm="HS256")
        with self.assertRaises(TokenInvalido):
            ServicoJWT(SEGREDO).validar_token(antigo)

    def test_token_de_acesso_nao_serve_como_estado(self):
        servico = ServicoJWT(SEGREDO)
        with self.assertRaises(TokenInvalido):
            servico.validar_token(servico.gerar_token(7, "a@b.com"), finalidade=FINALIDADE_ESTADO_OAUTH)

    def test_token_assinado_com_outro_segredo_e_recusado(self):
        outro = ServicoJWT("outro-segredo-qualquer-com-mais-de-32-caracteres").gerar_token(7, "a@b.com")
        with self.assertRaises(TokenInvalido):
            ServicoJWT(SEGREDO).validar_token(outro)


class TestCifradorDeTokens(unittest.TestCase):
    def test_cifra_com_prefixo_e_decifra(self):
        cifrador = CifradorDeTokens(CHAVE)
        cifrado = cifrador.cifrar("APP_USR-123")
        self.assertTrue(cifrado.startswith("enc:v1:"))
        self.assertNotIn("APP_USR-123", cifrado)
        self.assertEqual(cifrador.decifrar(cifrado), "APP_USR-123")

    def test_valor_legado_sem_prefixo_e_lido_como_esta(self):
        self.assertEqual(CifradorDeTokens(CHAVE).decifrar("APP_USR-legado"), "APP_USR-legado")

    def test_sem_chave_fica_desligado(self):
        with self.assertLogs("quickclick.seguranca", "WARNING"):
            cifrador = CifradorDeTokens(None)
        self.assertFalse(cifrador.disponivel)
        with self.assertRaises(ServicoIndisponivel):
            cifrador.cifrar("x")

    def test_chave_invalida_fica_desligada(self):
        with self.assertLogs("quickclick.seguranca", "WARNING"):
            self.assertFalse(CifradorDeTokens("nao-e-uma-chave").disponivel)

    def test_chave_trocada_nao_decifra(self):
        cifrado = CifradorDeTokens(CHAVE).cifrar("x")
        outra = "o6l8D3mJ0q1v5rXyZb2c4e6g8i0k2m4o6q8s0u2w4y0="
        with self.assertRaises(ServicoIndisponivel), self.assertLogs("quickclick.seguranca", "ERROR"):
            CifradorDeTokens(outra).decifrar(cifrado)


class TestTravaDoBancoReal(unittest.TestCase):
    def test_teste_nao_cria_engine_para_o_banco_real(self):
        with self.assertRaises(RuntimeError) as erro:
            criar_engine("postgresql+psycopg2://u:s@db-quickclick.postgres.database.azure.com:5432/postgres")  # verificar_segredos: ignorar
        self.assertIn("banco real", str(erro.exception))


if __name__ == "__main__":
    unittest.main()
