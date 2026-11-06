"""
Aplicação · Caso de uso: Autenticar usuário (Login).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from backend.application.portas import RepositorioUsuarios, ServicoHashSenha, ServicoToken
from backend.domain.erros import ContaBanida, ContaSuspensa, CredenciaisInvalidas
from backend.domain.usuario import STATUS_BANIDA, STATUS_SUSPENSA, Usuario


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
        relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._usuarios = usuarios
        self._hasher = hasher
        self._token_service = token_service
        self._relogio = relogio
        self._hash_falso = self._hasher.gerar_hash("senha_falsa_para_tempo_constante")

    def executar(self, email: str, senha: str) -> ResultadoAutenticacao:
        if not email or not senha:
            raise CredenciaisInvalidas()

        registro = self._usuarios.obter_por_email(email)
        if registro is None:
            # Mitigação de Timing Attack: gasta o mesmo tempo de hash quando o email não existe
            self._hasher.verificar(senha, self._hash_falso)
            raise CredenciaisInvalidas()

        usuario, hash_armazenado = registro
        if not hash_armazenado:
            # Conta criada via Google OAuth (sem senha local): mantém tempo constante
            self._hasher.verificar(senha, self._hash_falso)
            raise CredenciaisInvalidas()

        if not self._hasher.verificar(senha, hash_armazenado):
            raise CredenciaisInvalidas()

        agora = self._relogio()
        status = usuario.status_efetivo(agora)
        if status == STATUS_BANIDA:
            raise ContaBanida(usuario.motivo_moderacao)
        if status == STATUS_SUSPENSA:
            raise ContaSuspensa(usuario.suspensa_ate, usuario.motivo_moderacao)

        self._usuarios.registrar_login(usuario.id, agora)
        token = self._token_service.gerar_token(
            usuario.id,
            usuario.email,
            versao=usuario.token_versao,
            papel=usuario.papel,
        )
        return ResultadoAutenticacao(usuario=usuario, token=token)
