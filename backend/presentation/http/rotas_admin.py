"""
Apresentação · Rotas do Painel Administrativo e Moderação (/api/admin)

Acesso restrito exclusivamente a administradores autorizados.
Se um usuário sem papel de administrador ou anônimo tentar acessar qualquer
endereço aqui, a rota levanta 401/404 opaco para não expor a existência do painel (anti-reconhecimento).
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException

from backend.application.casos_de_uso import CasosDeUso
from backend.domain.erros import ErroDeDominio, VendedorNaoEncontrado
from backend.domain.usuario import Usuario
from backend.presentation.http.esquemas import (
    PainelModeracaoSaida,
    RegistroAuditoriaSaida,
    RequisicaoExcluirContaAdmin,
    RequisicaoPunicaoConta,
    RespostaAcaoModeracao,
)


def criar_rotas_admin(casos: CasosDeUso, dependencia_admin) -> APIRouter:
    rotas = APIRouter(prefix="/admin", tags=["admin"])
    AdminAtual = Annotated[Usuario, dependencia_admin]

    @rotas.get(
        "/overview",
        summary="Retorna os números consolidados e a lista de contas monitoradas para moderação",
        response_model=PainelModeracaoSaida,
    )
    def painel_moderacao(
        admin: AdminAtual,
        status: str = "todos",
        busca: str = "",
    ) -> PainelModeracaoSaida:
        if casos.moderar_contas is None:
            raise HTTPException(status_code=501, detail="Serviço de moderação indisponível.")
        painel = casos.moderar_contas.obter_painel(admin=admin, filtro_status=status, busca=busca)
        return PainelModeracaoSaida(
            resumo=painel.resumo.__dict__,
            contas=[
                {
                    "id": c.usuario.id,
                    "email": c.usuario.email,
                    "nome": c.usuario.nome,
                    "loja": c.usuario.loja,
                    "plano": c.usuario.plano,
                    "papel": c.usuario.papel,
                    "status_conta": c.status_efetivo,
                    "motivo_moderacao": c.usuario.motivo_moderacao,
                    "suspensa_ate": c.usuario.suspensa_ate,
                    "sessao_ativa": c.sessao_ativa,
                    "usa_google": c.usa_google,
                    "criado_em": c.criado_em,
                    "ultimo_login_em": c.usuario.ultimo_login_em,
                    "ultimo_acesso_em": c.usuario.ultimo_acesso_em,
                    "marketplaces_conectados": [m.__dict__ for m in c.marketplaces_conectados],
                    "total_produtos": c.total_produtos,
                    "total_analises_ia": c.total_analises_ia,
                }
                for c in painel.contas
            ],
            total_filtrado=painel.total_filtrado,
        )

    @rotas.get(
        "/audit",
        summary="Lista a trilha de auditoria recente de ações administrativas",
        response_model=list[RegistroAuditoriaSaida],
    )
    def listar_auditoria(admin: AdminAtual, limite: int = 50) -> list[RegistroAuditoriaSaida]:
        if casos.moderar_contas is None:
            raise HTTPException(status_code=501, detail="Serviço de moderação indisponível.")
        registros = casos.moderar_contas.listar_auditoria(admin=admin, limite=min(max(limite, 1), 200))
        return [
            RegistroAuditoriaSaida(
                id=r.id,
                admin_id=r.admin_id,
                admin_email=r.admin_email,
                alvo_id=r.alvo_id,
                alvo_identificador=r.alvo_identificador,
                acao=r.acao,
                motivo=r.motivo,
                detalhes=r.detalhes,
                criado_em=r.criado_em,
            )
            for r in registros
        ]

    @rotas.post(
        "/users/{user_id}/punishment",
        summary="Aplica ou revoga punição em uma conta (advertência, suspensão temporária, banimento ou reativação)",
        response_model=RespostaAcaoModeracao,
    )
    def aplicar_punicao(
        user_id: int,
        dados: RequisicaoPunicaoConta,
        admin: AdminAtual,
    ) -> RespostaAcaoModeracao:
        if casos.moderar_contas is None:
            raise HTTPException(status_code=501, detail="Serviço de moderação indisponível.")
        usuario = casos.moderar_contas.aplicar_punicao(
            admin=admin,
            alvo_id=user_id,
            tipo=dados.tipo,
            motivo=dados.motivo,
            dias_suspensao=dados.dias_suspensao,
        )
        return RespostaAcaoModeracao(
            ok=True,
            acao=dados.tipo,
            alvo_id=usuario.id,
            mensagem=f"Ação '{dados.tipo}' aplicada com sucesso na conta {usuario.email}.",
        )

    @rotas.post(
        "/users/{user_id}/kill-sessions",
        summary="Invalida os tokens JWT e encerra as sessões conectadas de um vendedor",
        response_model=RespostaAcaoModeracao,
    )
    def derrubar_sessoes(user_id: int, admin: AdminAtual) -> RespostaAcaoModeracao:
        if casos.moderar_contas is None:
            raise HTTPException(status_code=501, detail="Serviço de moderação indisponível.")
        nova_versao = casos.moderar_contas.encerrar_sessoes(
            admin=admin,
            alvo_id=user_id,
            motivo="Sessão encerrada remotamente pela administração",
        )
        return RespostaAcaoModeracao(
            ok=True,
            acao="encerrar_sessao",
            alvo_id=user_id,
            mensagem=f"Sessões ativas derrubadas com sucesso (token v{nova_versao}).",
        )

    @rotas.delete(
        "/users/{user_id}/marketplaces/{slug}",
        summary="Desvincula forçadamente a conta de um marketplace do vendedor",
        response_model=RespostaAcaoModeracao,
    )
    def desvincular_marketplace_admin(
        user_id: int,
        slug: str,
        admin: AdminAtual,
    ) -> RespostaAcaoModeracao:
        if casos.moderar_contas is None:
            raise HTTPException(status_code=501, detail="Serviço de moderação indisponível.")
        casos.moderar_contas.desvincular_marketplace(
            admin=admin,
            alvo_id=user_id,
            marketplace=slug,
            motivo="Desvinculação forçada pela moderação",
        )
        return RespostaAcaoModeracao(
            ok=True,
            acao="desvincular_marketplace",
            alvo_id=user_id,
            mensagem=f"Marketplace '{slug}' desvinculado da conta #{user_id}.",
        )

    @rotas.delete(
        "/users/{user_id}",
        summary="Exclui definitivamente uma conta, expurgando todos os produtos, publicações e tokens",
        response_model=RespostaAcaoModeracao,
    )
    def excluir_conta_admin(
        user_id: int,
        dados: RequisicaoExcluirContaAdmin,
        admin: AdminAtual,
    ) -> RespostaAcaoModeracao:
        if casos.moderar_contas is None:
            raise HTTPException(status_code=501, detail="Serviço de moderação indisponível.")
        casos.moderar_contas.excluir_conta_definitivamente(
            admin=admin,
            alvo_id=user_id,
            confirmacao_email=dados.confirmacao_email,
            motivo=dados.motivo,
        )
        return RespostaAcaoModeracao(
            ok=True,
            acao="excluir_conta",
            alvo_id=user_id,
            mensagem=f"Conta #{user_id} excluída em definitivo e dados expurgados.",
        )

    return rotas
