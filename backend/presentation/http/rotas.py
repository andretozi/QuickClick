"""
Apresentação · Rotas da API

Todas ficam debaixo de /api (o prefixo é aplicado em api.py). Cada rota só traduz
HTTP para um caso de uso e o resultado de volta para JSON: a regra mora no domínio.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.application.casos_de_uso import CasosDeUso
from backend.application.portas import ServicoToken
from backend.domain.erros import NaoAutenticado
from backend.presentation.http.esquemas import (
    ListaDeMarketplaces,
    ListaDePlanos,
    MarketplaceSaida,
    RequisicaoCadastro,
    RequisicaoLogin,
    RespostaAutenticacao,
    RespostaDeErro,
    Saude,
    UsuarioSaida,
    VendedorSaida,
    marketplace_saida,
    plano_saida,
    usuario_saida,
    vendedor_saida,
)

ERRO_401 = {401: {"model": RespostaDeErro, "description": "Token inválido, expirado ou ausente"}}
ERRO_404 = {404: {"model": RespostaDeErro, "description": "Marketplace ou vendedor não encontrado"}}
ERROS_AO_CONECTAR = {
    **ERRO_401,
    **ERRO_404,
    403: {"model": RespostaDeErro, "description": "Limite de marketplaces do plano atingido"},
    409: {"model": RespostaDeErro, "description": "Marketplace ainda em breve"},
}
ERROS_CADASTRO = {
    400: {"model": RespostaDeErro, "description": "Dados de cadastro inválidos"},
    409: {"model": RespostaDeErro, "description": "Email já cadastrado"},
}
ERROS_LOGIN = {
    401: {"model": RespostaDeErro, "description": "Email ou senha incorretos"},
}


def criar_rotas(
    casos: CasosDeUso,
    identificar_vendedor: Callable[..., int] | None = None,
    servico_token: ServicoToken | None = None,
) -> APIRouter:
    rotas = APIRouter()

    def obter_vendedor_autenticado(request: Request) -> int:
        header = request.headers.get("Authorization")
        if header and header.startswith("Bearer "):
            token = header.split(" ", 1)[1].strip()
            if servico_token is not None:
                payload = servico_token.validar_token(token)
                return int(payload["sub"])
        if identificar_vendedor is not None:
            return identificar_vendedor()
        raise NaoAutenticado("Autenticação obrigatória. Envie o cabeçalho Authorization: Bearer <token>.")

    VendedorAtual = Annotated[int, Depends(obter_vendedor_autenticado)]

    # -----------------------------------------------------------------------
    # Sistema
    # -----------------------------------------------------------------------

    @rotas.get("/health", tags=["sistema"], summary="Confere se a API está no ar", response_model=Saude)
    def health() -> Saude:
        return Saude(status="ok")

    @rotas.get("/plans", tags=["planos"], summary="Planos de assinatura, do Grátis ao Business", response_model=ListaDePlanos)
    def listar_planos() -> ListaDePlanos:
        return ListaDePlanos(planos=[plano_saida(plano) for plano in casos.listar_planos.executar()])

    # -----------------------------------------------------------------------
    # Autenticação (JWT)
    # -----------------------------------------------------------------------

    @rotas.post(
        "/auth/register",
        tags=["autenticacao"],
        summary="Cria uma nova conta e devolve o token JWT",
        response_model=RespostaAutenticacao,
        responses=ERROS_CADASTRO,
    )
    @rotas.post("/contas", include_in_schema=False)
    def cadastrar(dados: RequisicaoCadastro) -> RespostaAutenticacao:
        if casos.registrar_usuario is None:
            raise HTTPException(status_code=501, detail="Serviço de cadastro não disponível.")
        resultado = casos.registrar_usuario.executar(
            nome=dados.nome,
            email=dados.email,
            loja=dados.loja,
            senha=dados.senha,
        )
        return RespostaAutenticacao(
            token=resultado.token,
            usuario=usuario_saida(resultado.usuario),
        )

    @rotas.post(
        "/auth/login",
        tags=["autenticacao"],
        summary="Autentica com email e senha e devolve o token JWT",
        response_model=RespostaAutenticacao,
        responses=ERROS_LOGIN,
    )
    @rotas.post("/sessao", include_in_schema=False)
    def login(dados: RequisicaoLogin) -> RespostaAutenticacao:
        if casos.autenticar_usuario is None:
            raise HTTPException(status_code=501, detail="Serviço de autenticação não disponível.")
        resultado = casos.autenticar_usuario.executar(
            email=dados.email,
            senha=dados.senha,
        )
        return RespostaAutenticacao(
            token=resultado.token,
            usuario=usuario_saida(resultado.usuario),
        )

    @rotas.get(
        "/auth/me",
        tags=["autenticacao"],
        summary="Retorna os dados do usuário atual autenticado via token JWT",
        response_model=UsuarioSaida,
        responses={**ERRO_401, **ERRO_404},
    )
    def usuario_atual(vendedor_id: VendedorAtual) -> UsuarioSaida:
        if casos.obter_usuario_atual is None:
            raise HTTPException(status_code=501, detail="Serviço indisponível.")
        return usuario_saida(casos.obter_usuario_atual.executar(vendedor_id))

    # -----------------------------------------------------------------------
    # Vendedor e Marketplaces (Rotas Protegidas por JWT)
    # -----------------------------------------------------------------------

    @rotas.get(
        "/me",
        tags=["vendedor"],
        summary="Vendedor atual autenticado pelo token JWT",
        response_model=VendedorSaida,
        responses={**ERRO_401, **ERRO_404},
    )
    def vendedor_atual(vendedor_id: VendedorAtual) -> VendedorSaida:
        return vendedor_saida(casos.obter_vendedor_atual.executar(vendedor_id))

    @rotas.get(
        "/marketplaces",
        tags=["marketplaces"],
        summary="Catálogo de marketplaces, com o que o vendedor já conectou",
        response_model=ListaDeMarketplaces,
        responses=ERRO_401,
    )
    def listar_marketplaces(vendedor_id: VendedorAtual) -> ListaDeMarketplaces:
        itens = casos.listar_marketplaces.executar(vendedor_id)
        return ListaDeMarketplaces(marketplaces=[marketplace_saida(item) for item in itens])

    @rotas.post(
        "/marketplaces/{slug}/connection",
        tags=["marketplaces"],
        summary="Conecta uma conta que o vendedor já tem no marketplace",
        response_model=MarketplaceSaida,
        responses=ERROS_AO_CONECTAR,
    )
    def conectar(slug: str, vendedor_id: VendedorAtual) -> MarketplaceSaida:
        return marketplace_saida(casos.conectar_marketplace.executar(vendedor_id, slug))

    @rotas.delete(
        "/marketplaces/{slug}/connection",
        tags=["marketplaces"],
        summary="Desconecta o marketplace e libera a vaga do plano",
        response_model=MarketplaceSaida,
        responses={**ERRO_401, **ERRO_404},
    )
    def desconectar(slug: str, vendedor_id: VendedorAtual) -> MarketplaceSaida:
        return marketplace_saida(casos.desconectar_marketplace.executar(vendedor_id, slug))

    return rotas
