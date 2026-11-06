"""
Aplicação · Autoatendimento da conta do usuário autenticado (/api/auth/me).

Concentra em um único caso de uso todas as operações sobre a própria conta:
leitura dos dados atuais, edição do perfil, troca da senha local (apenas quando
a conta possui senha exclusiva local) e exclusão definitiva mediante confirmação do nome da loja.
"""

from collections.abc import Callable
from datetime import UTC, datetime

from backend.application.portas import RepositorioUsuarios, ServicoHashSenha
from backend.domain.erros import (
    ConfirmacaoExclusaoInvalida,
    ContaBanida,
    ContaSuspensa,
    SenhaAtualIncorreta,
    VendedorNaoEncontrado,
)
from backend.domain.usuario import (
    PAPEL_ADMIN,
    STATUS_BANIDA,
    STATUS_SUSPENSA,
    Usuario,
    email_valido,
    normalizar_email,
)


def _normalizar_confirmacao(texto: str) -> str:
    return " ".join((texto or "").strip().split()).casefold()


class ObterUsuarioAtual:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        hasher: ServicoHashSenha | None = None,
        relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
        emails_admin: frozenset[str] = frozenset(),
    ):
        self._usuarios = usuarios
        self._hasher = hasher
        self._relogio = relogio
        self._emails_admin = emails_admin

    def _obter_registro(self, usuario_id: int) -> tuple[Usuario, str | None]:
        resultado = self._usuarios.obter_por_id(usuario_id)
        if resultado is None:
            raise VendedorNaoEncontrado(usuario_id)
        usuario, hash_armazenado = resultado
        email_norm = normalizar_email(usuario.email)
        if email_norm in self._emails_admin and usuario.papel != PAPEL_ADMIN:
            usuario = self._usuarios.atribuir_papel(usuario.id, PAPEL_ADMIN)

        agora = self._relogio()
        status = usuario.status_efetivo(agora)
        if status == STATUS_BANIDA:
            raise ContaBanida(usuario.motivo_moderacao)
        if status == STATUS_SUSPENSA:
            raise ContaSuspensa(usuario.suspensa_ate, usuario.motivo_moderacao)
        return usuario, hash_armazenado

    def executar(self, usuario_id: int) -> Usuario:
        usuario, _ = self._obter_registro(usuario_id)
        self._usuarios.registrar_acesso(usuario.id, self._relogio())
        return usuario

    def atualizar_perfil(self, usuario_id: int, nome: str, email: str, loja: str) -> Usuario:
        self._obter_registro(usuario_id)
        nome_limpo = (nome or "").strip()
        email_limpo = normalizar_email(email)
        loja_limpa = (loja or "").strip()

        if len(nome_limpo) < 2:
            raise ValueError("Informe um nome com pelo menos 2 caracteres.")
        if not email_valido(email_limpo):
            raise ValueError("Informe um email válido.")
        if len(loja_limpa) < 2:
            raise ValueError("Informe o nome da sua loja com pelo menos 2 caracteres.")

        return self._usuarios.atualizar_perfil(
            user_id=usuario_id,
            nome=nome_limpo,
            email=email_limpo,
            loja=loja_limpa,
        )

    def alterar_senha(self, usuario_id: int, senha_atual: str, nova_senha: str) -> None:
        if self._hasher is None:
            raise RuntimeError("Serviço de hash de senha não configurado.")
        usuario, hash_atual = self._obter_registro(usuario_id)
        if not usuario.tem_senha or not hash_atual:
            raise ValueError("Esta conta usa login social e não possui senha local.")
        if not senha_atual or not self._hasher.verificar(senha_atual, hash_atual):
            raise SenhaAtualIncorreta()
        if len(nova_senha or "") < 8 or not any(c.isalpha() for c in nova_senha) or not any(c.isdigit() for c in nova_senha):
            raise ValueError("A nova senha precisa ter pelo menos 8 caracteres, com letras e números.")

        novo_hash = self._hasher.gerar_hash(nova_senha)
        self._usuarios.atualizar_senha(usuario_id, novo_hash)

    def excluir(self, usuario_id: int, confirmacao: str) -> None:
        usuario, _ = self._obter_registro(usuario_id)
        esperado = _normalizar_confirmacao(usuario.loja or usuario.email)
        digitado = _normalizar_confirmacao(confirmacao)
        if not digitado or digitado != esperado:
            raise ConfirmacaoExclusaoInvalida()
        self._usuarios.remover(usuario_id)
