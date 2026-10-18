"""
Infraestrutura · Criptografia dos tokens dos marketplaces (Fernet, chave TOKENS_CHAVE_CRIPTO).

O valor guardado no banco leva o prefixo "enc:v1:". Um valor sem prefixo é legado (de
antes da criptografia): é lido como está e volta cifrado na próxima gravação.
Sem a chave, a conexão com marketplaces fica desligada, com aviso no log.
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

from backend.domain.erros import ServicoIndisponivel

log = logging.getLogger("quickclick.seguranca")

PREFIXO = "enc:v1:"
MENSAGEM_DESLIGADO = "A conexão com os marketplaces está desligada agora. Tente de novo mais tarde."


class CifradorDeTokens:
    def __init__(self, chave: str | None, avisar: bool = True):
        self._fernet: Fernet | None = None
        if not chave:
            if avisar:
                log.warning("Conexão com marketplaces desligada: falta TOKENS_CHAVE_CRIPTO.")
            return
        try:
            self._fernet = Fernet(chave.encode("ascii"))
        except (ValueError, TypeError, UnicodeEncodeError):
            log.warning("Conexão com marketplaces desligada: TOKENS_CHAVE_CRIPTO não é uma chave Fernet válida.")

    @property
    def disponivel(self) -> bool:
        return self._fernet is not None

    def cifrar(self, texto: str) -> str:
        if self._fernet is None:
            raise ServicoIndisponivel(MENSAGEM_DESLIGADO)
        return PREFIXO + self._fernet.encrypt(texto.encode("utf-8")).decode("ascii")

    def decifrar(self, valor: str) -> str:
        if not valor.startswith(PREFIXO):
            return valor  # legado em texto puro
        if self._fernet is None:
            raise ServicoIndisponivel(MENSAGEM_DESLIGADO)
        try:
            return self._fernet.decrypt(valor[len(PREFIXO):].encode("ascii")).decode("utf-8")
        except InvalidToken as erro:
            log.error("Token de marketplace não decifra com a TOKENS_CHAVE_CRIPTO atual (a chave mudou?).")
            raise ServicoIndisponivel(MENSAGEM_DESLIGADO) from erro

    @staticmethod
    def esta_cifrado(valor: str | None) -> bool:
        return bool(valor) and valor.startswith(PREFIXO)
