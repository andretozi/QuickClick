"""
Aplicação · Caso de uso: Registrar novo usuário (Cadastro).
"""

from datetime import UTC, datetime

from backend.application.casos_de_uso.autenticar_usuario import ResultadoAutenticacao
from backend.application.portas import RepositorioUsuarios, ServicoHashSenha, ServicoToken
from backend.domain.erros import EmailJaCadastrado, MaioridadeNaoConfirmada


class RegistrarUsuario:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        hasher: ServicoHashSenha,
        token_service: ServicoToken,
    ):
        self._usuarios = usuarios
        self._hasher = hasher
        self._token_service = token_service

    def executar(
        self,
        nome: str,
        email: str,
        loja: str,
        senha: str,
        plano: str = "gratis",
        maior_de_idade: bool = False,
    ) -> ResultadoAutenticacao:
        email_normalizado = email.strip().lower()
        if not email_normalizado or not senha:
            raise ValueError("Email e senha são obrigatórios.")
        if not maior_de_idade:
            raise MaioridadeNaoConfirmada()

        existente = self._usuarios.obter_por_email(email_normalizado)
        if existente is not None:
            raise EmailJaCadastrado()

        password_hash = self._hasher.gerar_hash(senha)
        usuario = self._usuarios.salvar(
            email=email_normalizado,
            password_hash=password_hash,
            nome=nome,
            loja=loja,
            plano=plano,
            confirmou_maioridade_em=datetime.now(UTC).isoformat(),
        )

        token = self._token_service.gerar_token(usuario.id, usuario.email)
        return ResultadoAutenticacao(usuario=usuario, token=token)
