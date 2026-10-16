"""
Aplicação · Portas

O que os casos de uso precisam do mundo de fora, descrito como interfaces (Protocol).
A infraestrutura implementa estas portas; os testes usam versões falsas, em memória.
"""

from typing import Any, Protocol

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

    def salvar(self, email: str, password_hash: str, nome: str, loja: str, plano: str = "gratis") -> Usuario: ...


class ServicoToken(Protocol):
    def gerar_token(self, user_id: int, email: str) -> str: ...

    def validar_token(self, token: str) -> dict[str, Any]: ...


class ServicoHashSenha(Protocol):
    def gerar_hash(self, senha: str) -> str: ...

    def verificar(self, senha: str, hash_armazenado: str) -> bool: ...


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
