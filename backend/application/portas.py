"""
Aplicação · Portas

O que os casos de uso precisam do mundo de fora, descrito como interfaces (Protocol).
A infraestrutura implementa estas portas; os testes usam versões falsas, em memória.
"""

from typing import Protocol

from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.domain.vendedor import Vendedor


class RepositorioVendedores(Protocol):
    def obter(self, vendedor_id: int) -> Vendedor | None: ...

    def salvar(self, vendedor: Vendedor) -> None: ...


class RepositorioContasVinculadas(Protocol):
    def listar_do_vendedor(self, vendedor_id: int) -> list[ContaVinculada]: ...

    def buscar(self, vendedor_id: int, marketplace: str) -> ContaVinculada | None: ...

    def salvar(self, conta: ContaVinculada) -> None: ...

    def remover(self, vendedor_id: int, marketplace: str) -> None: ...


class GatewayMarketplace(Protocol):
    """
    Integração OAuth 2.0 com um marketplace. Existe uma implementação por marketplace,
    e o vendedor sempre autoriza direto no site do marketplace.
    """

    def gerar_url_autorizacao(self, estado: str) -> str:
        """URL do marketplace onde o vendedor entra e autoriza a Quick Click.
        `estado` volta igual no retorno e protege contra pedidos forjados (CSRF)."""
        ...

    def trocar_codigo_por_token(self, codigo: str) -> CredenciaisOAuth:
        """Troca o código que o marketplace devolveu pelos tokens de acesso."""
        ...

    def renovar_token(self, refresh_token: str) -> CredenciaisOAuth:
        """Pede tokens novos antes de o access token expirar."""
        ...
