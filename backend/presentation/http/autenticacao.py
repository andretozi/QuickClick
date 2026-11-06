"""
Apresentação · Quem está pedindo: o vendedor do token JWT (Authorization: Bearer <token>).

`identificar_vendedor` é um fallback opcional para testes ou modo sem token.
Também confere a validade em tempo real contra punições e revogação de sessão.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request

from backend.application.portas import RepositorioUsuarios, ServicoToken
from backend.domain.erros import ContaBanida, ContaSuspensa, NaoAutenticado, TokenInvalido
from backend.domain.usuario import PAPEL_ADMIN, STATUS_BANIDA, STATUS_SUSPENSA, Usuario


def dependencia_do_vendedor(
    servico_token: ServicoToken | None,
    identificar_vendedor: Callable[..., int] | None = None,
    usuarios: RepositorioUsuarios | None = None,
    relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Callable[[Request], int]:
    def obter_vendedor_autenticado(request: Request) -> int:
        header = request.headers.get("Authorization")
        if header and header.startswith("Bearer "):
            token = header.split(" ", 1)[1].strip()
            if servico_token is not None:
                payload = servico_token.validar_token(token)
                vendedor_id = int(payload["sub"])
                if usuarios is not None:
                    registro = usuarios.obter_por_id(vendedor_id)
                    if registro is not None:
                        usuario, _ = registro
                        agora = relogio()
                        status = usuario.status_efetivo(agora)
                        if status == STATUS_BANIDA:
                            raise ContaBanida(usuario.motivo_moderacao)
                        if status == STATUS_SUSPENSA:
                            raise ContaSuspensa(usuario.suspensa_ate, usuario.motivo_moderacao)
                        token_ver = payload.get("ver")
                        if token_ver is not None and int(token_ver) != (usuario.token_versao or 0):
                            raise TokenInvalido("Sessão revogada ou expirada. Faça login novamente.")
                return vendedor_id
        if identificar_vendedor is not None:
            return identificar_vendedor()
        raise NaoAutenticado("Autenticação obrigatória. Envie o cabeçalho Authorization: Bearer <token>.")

    return obter_vendedor_autenticado


def dependencia_do_admin(
    servico_token: ServicoToken | None,
    usuarios: RepositorioUsuarios,
    emails_admin: frozenset[str] = frozenset(),
    relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Callable[[Request], Usuario]:
    """
    Exige autenticação de administrador.
    Se o solicitante não for admin, ou não estiver autenticado, devolve 404 estrito
    (idêntico a uma rota inexistente) para ocultar totalmente a existência do painel (anti-reconhecimento).
    """
    def obter_admin_autenticado(request: Request) -> Usuario:
        header = request.headers.get("Authorization")
        if not header or not header.startswith("Bearer "):
            raise HTTPException(status_code=404, detail="Esse endereço não existe na API.")
        token = header.split(" ", 1)[1].strip()
        if servico_token is None:
            raise HTTPException(status_code=404, detail="Esse endereço não existe na API.")
        try:
            payload = servico_token.validar_token(token)
            admin_id = int(payload["sub"])
        except Exception:
            raise HTTPException(status_code=404, detail="Esse endereço não existe na API.")

        registro = usuarios.obter_por_id(admin_id)
        if registro is None:
            raise HTTPException(status_code=404, detail="Esse endereço não existe na API.")

        usuario, _ = registro
        agora = relogio()
        if usuario.esta_bloqueado(agora):
            raise HTTPException(status_code=404, detail="Esse endereço não existe na API.")

        token_ver = payload.get("ver")
        if token_ver is not None and int(token_ver) != (usuario.token_versao or 0):
            raise HTTPException(status_code=404, detail="Esse endereço não existe na API.")

        email_norm = usuario.email.strip().lower()
        eh_admin_direto = usuario.papel == PAPEL_ADMIN
        eh_admin_por_lista = email_norm in emails_admin

        if not (eh_admin_direto or eh_admin_por_lista):
            # Resposta 404 opaca para evitar qualquer enumeração de rotas administrativas
            raise HTTPException(status_code=404, detail="Esse endereço não existe na API.")

        # Promove no banco caso esteja na lista de administradores por variável de ambiente
        if eh_admin_por_lista and not eh_admin_direto:
            usuario = usuarios.atribuir_papel(usuario.id, PAPEL_ADMIN)

        usuarios.registrar_acesso(usuario.id, agora)
        return usuario

    return obter_admin_autenticado
