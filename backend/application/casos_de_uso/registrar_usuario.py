"""
Aplicação · Caso de uso: Registrar novo usuário (Cadastro).
"""

from datetime import UTC, datetime

from backend.application.casos_de_uso.autenticar_usuario import ResultadoAutenticacao
from backend.application.portas import RepositorioUsuarios, ServicoHashSenha, ServicoToken
from backend.domain.erros import EmailJaCadastrado, MaioridadeNaoConfirmada
from backend.domain.usuario import PAPEL_ADMIN, PAPEL_VENDEDOR, email_valido, normalizar_email


class RegistrarUsuario:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        hasher: ServicoHashSenha,
        token_service: ServicoToken,
        emails_admin: frozenset[str] = frozenset(),
    ):
        self._usuarios = usuarios
        self._hasher = hasher
        self._token_service = token_service
        self._emails_admin = emails_admin

    def executar(
        self,
        nome: str,
        email: str,
        loja: str,
        senha: str,
        plano: str = "gratis",
        maior_de_idade: bool = False,
    ) -> ResultadoAutenticacao:
        email_normalizado = normalizar_email(email)
        if not email_normalizado or not senha:
            raise ValueError("Email e senha são obrigatórios.")
        if not email_valido(email_normalizado):
            raise ValueError("Informe um email válido.")
        if not maior_de_idade:
            raise MaioridadeNaoConfirmada()

        existente = self._usuarios.obter_por_email(email_normalizado)
        if existente is not None:
            raise EmailJaCadastrado()

        papel = PAPEL_ADMIN if email_normalizado in self._emails_admin else PAPEL_VENDEDOR
        password_hash = self._hasher.gerar_hash(senha)
        usuario = self._usuarios.salvar(
            email=email_normalizado,
            password_hash=password_hash,
            nome=nome,
            loja=loja,
            plano=plano,
            confirmou_maioridade_em=datetime.now(UTC).isoformat(),
            papel=papel,
        )

        token = self._token_service.gerar_token(
            usuario.id,
            usuario.email,
            versao=usuario.token_versao,
            papel=usuario.papel,
        )
        return ResultadoAutenticacao(usuario=usuario, token=token)
