"""
Apresentação · Erros

Cada erro de negócio vira uma resposta HTTP clara, sempre no mesmo formato:
    {"erro": {"codigo": "...", "mensagem": "...", "plano_sugerido": "..."}}
A mensagem já vem pronta para aparecer na tela do vendedor.
"""

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from backend.domain.erros import (
    AnaliseEmAndamento,
    AnaliseNaoEncontrada,
    AnuncioNaoEncontrado,
    CotaEsgotada,
    CredenciaisInvalidas,
    EmailJaCadastrado,
    ErroDeDominio,
    EstadoDaAnaliseInvalido,
    FotoInvalida,
    FotosNecessarias,
    IAIndisponivel,
    LimiteDoPlanoAtingido,
    LimitePorHora,
    MaioridadeNaoConfirmada,
    MarketplaceEmBreve,
    MarketplaceNaoEncontrado,
    MercadoLivreDesconectado,
    MuitasTentativas,
    NaoAutenticado,
    PlanoInvalido,
    ProdutoNaoReconhecido,
    PublicacaoRecusada,
    ServicoIndisponivel,
    TokenInvalido,
    TrocaDePlanoIndisponivel,
    VendedorNaoEncontrado,
)

STATUS_POR_ERRO: tuple[tuple[type[ErroDeDominio], int], ...] = (
    (MarketplaceNaoEncontrado, 404),
    (VendedorNaoEncontrado, 404),
    (MarketplaceEmBreve, 409),
    (LimiteDoPlanoAtingido, 403),
    (NaoAutenticado, 401),
    (CredenciaisInvalidas, 401),
    (MuitasTentativas, 429),
    (TokenInvalido, 401),
    (EmailJaCadastrado, 409),
    (ServicoIndisponivel, 503),
    (CotaEsgotada, 403),
    (LimitePorHora, 429),
    (AnaliseEmAndamento, 409),
    (IAIndisponivel, 503),
    (FotoInvalida, 400),
    (FotosNecessarias, 409),
    (ProdutoNaoReconhecido, 422),
    (MercadoLivreDesconectado, 409),
    (AnaliseNaoEncontrada, 404),
    (AnuncioNaoEncontrado, 404),
    (EstadoDaAnaliseInvalido, 409),
    (PublicacaoRecusada, 422),
    (MaioridadeNaoConfirmada, 400),
    (PlanoInvalido, 400),
    (TrocaDePlanoIndisponivel, 402),
)

ERROS_HTTP = {
    400: ("parametro_invalido", "Parâmetro inválido na requisição."),
    401: ("nao_autenticado", "Autenticação necessária para acessar este recurso."),
    404: ("nao_encontrado", "Esse endereço não existe na API."),
    405: ("metodo_nao_permitido", "Esse endereço não aceita esse tipo de pedido."),
    413: ("pedido_grande_demais", "O pedido passou do tamanho máximo."),
    422: ("parametro_invalido", "Faltou ou veio errado algum dado do pedido."),
    429: ("muitas_tentativas", "Muitas tentativas seguidas. Aguarde alguns minutos e tente novamente."),
}

MAX_MENSAGEM_VALOR = 200


def _mensagem_valor_segura(erro: ValueError) -> str:
    """Retorna apenas mensagens curtas de validação, ocultando detalhes internos multi-linha."""
    texto = str(erro).strip()
    if not texto or "\n" in texto or len(texto) > MAX_MENSAGEM_VALOR:
        return ERROS_HTTP[400][1]
    return texto


def _resposta(status: int, codigo: str, mensagem: str, **extras) -> JSONResponse:
    return JSONResponse(status_code=status, content={"erro": {"codigo": codigo, "mensagem": mensagem, **extras}})


def registrar_tratamento_de_erros(app: FastAPI) -> None:
    @app.exception_handler(ErroDeDominio)
    async def erro_de_negocio(request: Request, erro: ErroDeDominio) -> JSONResponse:
        status = next((codigo for tipo, codigo in STATUS_POR_ERRO if isinstance(erro, tipo)), 400)
        extras = {}
        if isinstance(erro, LimiteDoPlanoAtingido) and erro.plano_sugerido is not None:
            extras["plano_sugerido"] = erro.plano_sugerido.slug
        extras.update(getattr(erro, "extras", None) or {})
        return _resposta(status, erro.codigo, erro.mensagem, **extras)

    @app.exception_handler(ValueError)
    async def erro_valor(request: Request, erro: ValueError) -> JSONResponse:
        return _resposta(400, "parametro_invalido", _mensagem_valor_segura(erro))

    @app.exception_handler(RequestValidationError)
    async def erro_de_validacao(request: Request, erro: RequestValidationError) -> JSONResponse:
        codigo, mensagem = ERROS_HTTP[422]
        return _resposta(422, codigo, mensagem)

    @app.exception_handler(HTTPException)
    async def erro_http(request: Request, erro: HTTPException):
        # Dentro de /api, o mesmo formato dos erros de negócio; fora dela, o padrão do FastAPI
        if not request.url.path.startswith("/api"):
            return await http_exception_handler(request, erro)
        codigo, mensagem = ERROS_HTTP.get(erro.status_code, ("erro_http", erro.detail or "Não deu pra atender esse pedido."))
        return _resposta(erro.status_code, codigo, mensagem)
