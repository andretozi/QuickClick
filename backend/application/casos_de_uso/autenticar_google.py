"""
Aplicação · Caso de uso: Autenticar e concluir cadastro via Google OAuth.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from backend.application.casos_de_uso.autenticar_usuario import ResultadoAutenticacao
from backend.application.portas import RepositorioUsuarios, ServicoToken, VerificadorGoogleToken
from backend.domain.erros import ContaBanida, ContaSuspensa, EmailJaCadastrado, TokenInvalido
from backend.domain.usuario import (
    PAPEL_ADMIN,
    PAPEL_VENDEDOR,
    STATUS_BANIDA,
    STATUS_SUSPENSA,
    Usuario,
    email_valido,
    normalizar_email,
)


@dataclass(frozen=True)
class ResultadoLoginGoogle:
    status: Literal["login", "needs_store_name"]
    access_token: str | None = None
    email: str | None = None
    google_id: str | None = None
    usuario: Usuario | None = None


class AutenticarComGoogle:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        verificador_google: VerificadorGoogleToken,
        token_service: ServicoToken,
        relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
        emails_admin: frozenset[str] = frozenset(),
    ):
        self._usuarios = usuarios
        self._verificador_google = verificador_google
        self._token_service = token_service
        self._relogio = relogio
        self._emails_admin = emails_admin

    @property
    def client_id(self) -> str:
        return self._verificador_google.client_id

    def executar(self, token: str) -> ResultadoLoginGoogle:
        token_limpo = (token or "").strip()
        if not token_limpo:
            raise TokenInvalido("Token do Google não fornecido.")

        identidade = self._verificador_google.verificar_id_token(token_limpo)
        registro = self._usuarios.obter_por_email(identidade.email)
        if registro is None:
            registro = self._usuarios.obter_por_google_id(identidade.google_id)

        if registro is not None:
            usuario, _ = registro
            agora = self._relogio()
            status = usuario.status_efetivo(agora)
            if status == STATUS_BANIDA:
                raise ContaBanida(usuario.motivo_moderacao)
            if status == STATUS_SUSPENSA:
                raise ContaSuspensa(usuario.suspensa_ate, usuario.motivo_moderacao)

            email_norm = usuario.email.strip().lower()
            if email_norm in self._emails_admin and usuario.papel != PAPEL_ADMIN:
                usuario = self._usuarios.atribuir_papel(usuario.id, PAPEL_ADMIN)

            self._usuarios.vincular_google_id(usuario.id, identidade.google_id)
            self._usuarios.registrar_login(usuario.id, agora)
            jwt_token = self._token_service.gerar_token(
                usuario.id,
                usuario.email,
                versao=usuario.token_versao,
                papel=usuario.papel,
            )
            return ResultadoLoginGoogle(
                status="login",
                access_token=jwt_token,
                usuario=usuario,
            )

        return ResultadoLoginGoogle(
            status="needs_store_name",
            email=identidade.email,
            google_id=identidade.google_id,
        )

    def completar_cadastro(
        self,
        email: str,
        google_id: str,
        store_name: str,
        nome: str = "",
    ) -> ResultadoAutenticacao:
        email_normalizado = normalizar_email(email)
        google_id_limpo = (google_id or "").strip()
        loja_limpa = (store_name or "").strip()
        nome_limpo = (nome or "").strip() or loja_limpa

        if not email_valido(email_normalizado):
            raise ValueError("Informe um email válido.")
        if not google_id_limpo:
            raise ValueError("Identificador do Google é obrigatório.")
        if len(loja_limpa) < 2:
            raise ValueError("Informe o nome da sua loja com pelo menos 2 caracteres.")

        if self._usuarios.obter_por_email(email_normalizado) is not None:
            raise EmailJaCadastrado()
        if self._usuarios.obter_por_google_id(google_id_limpo) is not None:
            raise EmailJaCadastrado()

        papel = PAPEL_ADMIN if email_normalizado in self._emails_admin else PAPEL_VENDEDOR
        usuario = self._usuarios.salvar(
            email=email_normalizado,
            password_hash=None,
            nome=nome_limpo,
            loja=loja_limpa,
            plano="gratis",
            google_id=google_id_limpo,
            papel=papel,
        )
        agora = self._relogio()
        self._usuarios.registrar_login(usuario.id, agora)
        jwt_token = self._token_service.gerar_token(
            usuario.id,
            usuario.email,
            versao=usuario.token_versao,
            papel=usuario.papel,
        )
        return ResultadoAutenticacao(usuario=usuario, token=jwt_token)
