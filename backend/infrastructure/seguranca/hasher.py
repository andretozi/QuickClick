"""
Infraestrutura · Serviço de hash de senhas com PBKDF2-HMAC-SHA256.

Padrão recomendado pelo NIST/OWASP, seguro e sem dependência de bibliotecas C externas.
Utiliza salt criptograficamente aleatório e comparação em tempo constante.
"""

import hashlib
import hmac
import os


class HasherPBKDF2:
    def __init__(self, iteracoes: int = 100_000):
        self._iteracoes = iteracoes

    def gerar_hash(self, senha: str) -> str:
        if not senha:
            raise ValueError("A senha não pode ser vazia.")
        salt = os.urandom(16)
        derivado = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt,
            self._iteracoes,
        )
        return f"pbkdf2_sha256${self._iteracoes}${salt.hex()}${derivado.hex()}"

    def verificar(self, senha: str, hash_armazenado: str) -> bool:
        if not senha or not hash_armazenado:
            return False
        partes = hash_armazenado.split("$")
        if len(partes) != 4 or partes[0] != "pbkdf2_sha256":
            return False

        try:
            iteracoes = int(partes[1])
            salt = bytes.fromhex(partes[2])
            esperado = bytes.fromhex(partes[3])
        except (ValueError, TypeError):
            return False

        calculado = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt,
            iteracoes,
        )
        return hmac.compare_digest(calculado, esperado)
