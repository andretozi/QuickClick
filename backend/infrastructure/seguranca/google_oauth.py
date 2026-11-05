"""
Infraestrutura · Validação criptográfica de ID Tokens do Google OAuth 2.0.

Valida assinatura RSA, emissor (iss), audiência (GOOGLE_CLIENT_ID), expiração (exp)
e verificação de email (email_verified) utilizando google.auth.transport.requests
com timeout explícito para proteger a disponibilidade do servidor.
"""

from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import requests

from backend.application.portas import IdentidadeGoogle
from backend.domain.erros import ServicoIndisponivel, TokenInvalido

EMISSORES_GOOGLE = frozenset({"accounts.google.com", "https://accounts.google.com"})
TIMEOUT_GOOGLE_S = 10.0


class _SessaoComTimeout(requests.Session):
    """Garante timeout explícito na busca dos certificados públicos do Google."""

    def request(self, method, url, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None or (isinstance(timeout, (int, float)) and timeout > TIMEOUT_GOOGLE_S):
            kwargs["timeout"] = TIMEOUT_GOOGLE_S
        return super().request(method, url, **kwargs)


class VerificadorGoogleOAuth:
    def __init__(self, client_id: str | None):
        self._client_id = (client_id or "").strip()
        self._sessao = _SessaoComTimeout()

    @property
    def client_id(self) -> str:
        return self._client_id

    def verificar_id_token(self, token: str) -> IdentidadeGoogle:
        if not self._client_id:
            raise ServicoIndisponivel("O login com Google ainda não está configurado neste servidor.")

        requisicao = google_requests.Request(session=self._sessao)
        try:
            idinfo = id_token.verify_oauth2_token(token, requisicao, audience=self._client_id)
        except google_exceptions.TransportError as erro:
            raise ServicoIndisponivel(
                "Não foi possível validar o login com o Google agora. Tente novamente em instantes."
            ) from erro
        except (ValueError, google_exceptions.GoogleAuthError) as erro:
            raise TokenInvalido("Token do Google inválido ou expirado.") from erro

        emissor = str(idinfo.get("iss") or "").strip()
        if emissor not in EMISSORES_GOOGLE:
            raise TokenInvalido("Emissor do token Google inválido.")

        if idinfo.get("email_verified") is not True:
            raise TokenInvalido("O email da conta Google precisa estar verificado.")

        sub = str(idinfo.get("sub") or "").strip()
        email = str(idinfo.get("email") or "").strip().lower()
        nome = str(idinfo.get("name") or "").strip()
        if not sub or not email:
            raise TokenInvalido("Token do Google sem identificação de conta ou email.")

        return IdentidadeGoogle(google_id=sub, email=email, nome=nome)
