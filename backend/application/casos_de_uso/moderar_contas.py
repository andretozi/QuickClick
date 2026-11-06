"""
Aplicação · Caso de uso: Moderação de contas, punições, sessões e auditoria.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from backend.application.portas import (
    RepositorioContasVinculadas,
    RepositorioModeracao,
    RepositorioUsuarios,
)
from backend.domain.erros import OperacaoModeracaoInvalida, VendedorNaoEncontrado
from backend.domain.moderacao import (
    ACAO_ADVERTIR,
    ACAO_BANIR,
    ACAO_DESVINCULAR_MARKETPLACE,
    ACAO_ENCERRAR_SESSAO,
    ACAO_EXCLUIR_CONTA,
    ACAO_REATIVAR,
    ACAO_SUSPENDER,
    PainelModeracao,
    RegistroAuditoria,
)
from backend.domain.usuario import (
    STATUS_ADVERTIDA,
    STATUS_ATIVA,
    STATUS_BANIDA,
    STATUS_SUSPENSA,
    Usuario,
    mascarar_email,
    normalizar_email,
)


class ModerarContas:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        moderacao: RepositorioModeracao,
        contas_vinculadas: RepositorioContasVinculadas,
        relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._usuarios = usuarios
        self._moderacao = moderacao
        self._contas = contas_vinculadas
        self._relogio = relogio

    def obter_painel(self, admin: Usuario, filtro_status: str = "todos", busca: str = "") -> PainelModeracao:
        return self._moderacao.obter_painel(
            filtro_status=filtro_status,
            busca=busca,
            agora=self._relogio(),
        )

    def listar_auditoria(self, admin: Usuario, limite: int = 50) -> list[RegistroAuditoria]:
        return self._moderacao.listar_auditoria(limite=limite)

    def aplicar_punicao(
        self,
        admin: Usuario,
        alvo_id: int,
        tipo: str,
        motivo: str,
        dias_suspensao: int | None = None,
    ) -> Usuario:
        if admin.id == alvo_id:
            raise OperacaoModeracaoInvalida("Um administrador não pode aplicar punições na própria conta.")

        registro = self._usuarios.obter_por_id(alvo_id)
        if registro is None:
            raise VendedorNaoEncontrado(alvo_id)
        alvo, _ = registro

        if alvo.eh_admin:
            raise OperacaoModeracaoInvalida("Contas de administradores não podem ser punidas via moderação.")

        motivo_limpo = (motivo or "").strip()
        if len(motivo_limpo) < 3:
            raise ValueError("O motivo da ação de moderação é obrigatório.")

        agora = self._relogio()
        suspensa_ate = None
        incrementar_token = False

        if tipo == ACAO_ADVERTIR:
            status_novo = STATUS_ADVERTIDA
        elif tipo == ACAO_SUSPENDER:
            status_novo = STATUS_SUSPENSA
            dias = dias_suspensao or 7
            suspensa_ate = agora + timedelta(days=dias)
            incrementar_token = True  # derruba as sessões ativas
        elif tipo == ACAO_BANIR:
            status_novo = STATUS_BANIDA
            incrementar_token = True  # derruba as sessões ativas
        elif tipo == ACAO_REATIVAR:
            status_novo = STATUS_ATIVA
            motivo_limpo = ""
        else:
            raise OperacaoModeracaoInvalida(f"Ação de punição desconhecida: {tipo}")

        atualizado = self._usuarios.atualizar_status(
            user_id=alvo_id,
            status=status_novo,
            motivo=motivo_limpo or None,
            suspensa_ate=suspensa_ate,
            incrementar_token=incrementar_token,
        )

        self._moderacao.registrar_auditoria(
            admin_id=admin.id,
            admin_email=admin.email,
            alvo_id=alvo.id,
            alvo_identificador=mascarar_email(alvo.email),
            acao=tipo,
            motivo=motivo_limpo,
            detalhes={
                "status_anterior": alvo.status_conta,
                "status_novo": status_novo,
                "suspensa_ate": suspensa_ate.isoformat() if suspensa_ate else None,
                "sessoes_derrubadas": incrementar_token,
            },
            criado_em=agora,
        )
        return atualizado

    def encerrar_sessoes(self, admin: Usuario, alvo_id: int, motivo: str = "Encerramento forçado de sessão") -> int:
        registro = self._usuarios.obter_por_id(alvo_id)
        if registro is None:
            raise VendedorNaoEncontrado(alvo_id)
        alvo, _ = registro

        nova_versao = self._usuarios.incrementar_token_versao(alvo_id)
        self._moderacao.registrar_auditoria(
            admin_id=admin.id,
            admin_email=admin.email,
            alvo_id=alvo.id,
            alvo_identificador=mascarar_email(alvo.email),
            acao=ACAO_ENCERRAR_SESSAO,
            motivo=motivo.strip(),
            detalhes={"nova_versao_token": nova_versao},
            criado_em=self._relogio(),
        )
        return nova_versao

    def desvincular_marketplace(self, admin: Usuario, alvo_id: int, marketplace: str, motivo: str) -> None:
        registro = self._usuarios.obter_por_id(alvo_id)
        if registro is None:
            raise VendedorNaoEncontrado(alvo_id)
        alvo, _ = registro

        self._contas.remover(alvo_id, marketplace)
        self._moderacao.registrar_auditoria(
            admin_id=admin.id,
            admin_email=admin.email,
            alvo_id=alvo.id,
            alvo_identificador=mascarar_email(alvo.email),
            acao=ACAO_DESVINCULAR_MARKETPLACE,
            motivo=motivo.strip() if motivo else "Desvinculação forçada pela moderação",
            detalhes={"marketplace": marketplace},
            criado_em=self._relogio(),
        )

    def excluir_conta_definitivamente(
        self,
        admin: Usuario,
        alvo_id: int,
        confirmacao_email: str,
        motivo: str,
    ) -> None:
        if admin.id == alvo_id:
            raise OperacaoModeracaoInvalida("Use as configurações da sua própria conta para exclusão.")

        registro = self._usuarios.obter_por_id(alvo_id)
        if registro is None:
            raise VendedorNaoEncontrado(alvo_id)
        alvo, _ = registro

        if alvo.eh_admin:
            raise OperacaoModeracaoInvalida("Contas de administrador não podem ser excluídas pelo painel.")

        digitado = normalizar_email(confirmacao_email)
        esperado = normalizar_email(alvo.email)
        if digitado != esperado:
            raise OperacaoModeracaoInvalida(f"Confirmação incorreta: digite exatamente o email da conta ({alvo.email}).")

        motivo_limpo = (motivo or "").strip()
        if len(motivo_limpo) < 3:
            raise ValueError("O motivo da exclusão administrativa é obrigatório.")

        agora = self._relogio()
        self._moderacao.registrar_auditoria(
            admin_id=admin.id,
            admin_email=admin.email,
            alvo_id=alvo.id,
            alvo_identificador=mascarar_email(alvo.email),
            acao=ACAO_EXCLUIR_CONTA,
            motivo=motivo_limpo,
            detalhes={"loja": alvo.loja, "plano": alvo.plano},
            criado_em=agora,
        )

        # Exclui produtos, publicações, tokens de marketplaces, análises de IA e a conta do banco
        self._usuarios.remover(alvo_id)
