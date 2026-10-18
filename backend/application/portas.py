"""
Aplicação · Portas

O que os casos de uso precisam do mundo de fora, descrito como interfaces (Protocol).
A infraestrutura implementa estas portas; os testes usam versões falsas, em memória.
"""

from typing import Any, Never, Protocol

from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.domain.usuario import Usuario
from backend.domain.vendedor import Vendedor


class RepositorioVendedores(Protocol):
    def obter(self, vendedor_id: int) -> Vendedor | None: ...

    def salvar(self, vendedor: Vendedor) -> None: ...


class RepositorioContasVinculadas(Protocol):
    def listar_do_vendedor(self, vendedor_id: int) -> list[ContaVinculada]: ...

    def buscar(self, vendedor_id: int, marketplace: str) -> ContaVinculada | None: ...

    def salvar(self, conta: ContaVinculada) -> None: ...

    def remover(self, vendedor_id: int, marketplace: str) -> None: ...


class RepositorioUsuarios(Protocol):
    def obter_por_id(self, user_id: int) -> tuple[Usuario, str] | None: ...

    def obter_por_email(self, email: str) -> tuple[Usuario, str] | None: ...

    def salvar(self, email: str, password_hash: str, nome: str, loja: str, plano: str = "gratis",
               confirmou_maioridade_em: str | None = None) -> Usuario: ...


class ServicoToken(Protocol):
    """Tokens com finalidade: "acesso" (login na API) ou "estado_oauth" (volta do marketplace)."""

    def gerar_token(self, user_id: int, email: str, finalidade: str = "acesso") -> str: ...

    def validar_token(self, token: str, finalidade: str = "acesso") -> dict[str, Any]: ...


class ServicoHashSenha(Protocol):
    def gerar_hash(self, senha: str) -> str: ...

    def verificar(self, senha: str, hash_armazenado: str) -> bool: ...


class GatewayMarketplace(Protocol):
    """
    Integração OAuth 2.0 com um marketplace. Existe uma implementação por marketplace,
    e o vendedor sempre autoriza direto no site do marketplace.
    """

    slug: str

    def _nao_implementado(self) -> Never:
        raise NotImplementedError(f"Integração com '{getattr(self, 'slug', 'marketplace')}' em desenvolvimento.")

    def gerar_url_autorizacao(self, estado: str) -> str:
        """URL do marketplace onde o vendedor entra e autoriza a Quick Click.
        `estado` volta igual no retorno e protege contra pedidos forjados (CSRF)."""
        self._nao_implementado()

    def trocar_codigo_por_token(self, codigo: str) -> CredenciaisOAuth:
        """Troca o código que o marketplace devolveu pelos tokens de acesso."""
        self._nao_implementado()

    def renovar_token(self, refresh_token: str) -> CredenciaisOAuth:
        """Pede tokens novos antes de o access token expirar."""
        self._nao_implementado()

    def obter_perfil_usuario(self, access_token: str) -> dict[str, Any]:
        """Obtém dados da conta autenticada no marketplace."""
        self._nao_implementado()

    def listar_anuncios(self, access_token: str, conta_externa_id: str | None = None) -> list[dict[str, Any]]:
        """Lista os produtos/anúncios para monitoramento."""
        self._nao_implementado()

    def publicar_anuncio(self, access_token: str, dados_produto: dict[str, Any]) -> dict[str, Any]:
        """Publica um novo produto no marketplace."""
        self._nao_implementado()


class FalhaNoMarketplace(RuntimeError):
    """Resposta de erro da API de um marketplace, com o status HTTP (0 quando nem respondeu) e o corpo."""

    def __init__(self, mensagem: str, status: int = 0, corpo: Any = None):
        super().__init__(mensagem)
        self.status = status
        self.corpo = corpo


class PublicadorMercadoLivre(Protocol):
    """O que a publicação montada no back precisa do Mercado Livre (com o token do vendedor)."""

    def subir_imagem(self, access_token: str, jpeg: bytes, nome: str = "foto.jpg") -> str: ...

    def publicar_anuncio(self, access_token: str, dados_produto: dict[str, Any]) -> dict[str, Any]: ...

    def gravar_descricao(self, access_token: str, item_id: str, texto: str) -> Any: ...

