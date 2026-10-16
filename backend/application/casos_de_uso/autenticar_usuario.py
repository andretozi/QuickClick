"""
Aplicação · Caso de uso: Autenticar usuário (Login).
"""

from dataclasses import dataclass

from backend.application.portas import RepositorioUsuarios, ServicoHashSenha, ServicoToken
from backend.domain.erros import CredenciaisInvalidas
from backend.domain.usuario import Usuario


@dataclass(frozen=True)
class ResultadoAutenticacao:
    usuario: Usuario
    token: str


class AutenticarUsuario:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        hasher: ServicoHashSenha,
        token_service: ServicoToken,
    ):
        self._usuarios = usuarios
        self._hasher = hasher
        self._token_service = token_service

    def executar(self, email: str, senha: str) -> ResultadoAutenticacao:
        if not email or not senha:
            raise CredenciaisInvalidas()

        registro = self._usuarios.obter_por_email(email)
        if registro is None:
            raise CredenciaisInvalidas()

        usuario, hash_armazenado = registro
        if not self._hasher.verificar(senha, hash_armazenado):
            raise CredenciaisInvalidas()

        token = self._token_service.gerar_token(usuario.id, usuario.email)
        return ResultadoAutenticacao(usuario=usuario, token=token)
