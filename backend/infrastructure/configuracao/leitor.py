"""
Infraestrutura · Configuração · Leitor

Ordem de leitura de cada configuração (a primeira que tiver valor ganha):
    1. variável de ambiente de verdade (no App Service ela já vem resolvida do Key Vault;
       se ainda começar com "@Microsoft.KeyVault(", a referência não resolveu: vale como ausente);
    2. só no PC (QUICKCLICK_AMBIENTE=local) e só para segredos: o Gerenciador de Credenciais do
       Windows, pela biblioteca keyring (serviço "quickclick", usuário = nome da variável);
    3. só para segredos e só com QUICKCLICK_KEYVAULT definida: o Azure Key Vault, pela
       DefaultAzureCredential (no PC, primeiro o nome com o sufixo -dev);
    4. o arquivo .env da raiz (última reserva);
    5. ausente: quem depende dela fica desligado, com aviso no log.

Os valores ficam só em memória. Nada aqui escreve valor em disco nem em log.
"""

import logging
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from backend.infrastructure.configuracao.catalogo import POR_NOME, SEGREDOS, nome_no_cofre

log = logging.getLogger("quickclick.config")

PREFIXO_REFERENCIA_COFRE = "@Microsoft.KeyVault("
SERVICO_KEYRING = "quickclick"
SUFIXO_DEV = "-dev"
VERDADEIROS = {"1", "true", "sim", "yes", "on"}
FALSOS = {"0", "false", "nao", "não", "no", "off"}


class Origem(StrEnum):
    AMBIENTE = "ambiente"
    KEYRING = "Gerenciador de Credenciais"
    KEYVAULT = "Key Vault"
    ARQUIVO_ENV = ".env"
    AUSENTE = "ausente"


@dataclass(frozen=True)
class ValorLido:
    nome: str
    valor: str | None = field(repr=False)  # repr=False: o valor nunca aparece em log
    origem: Origem

    @property
    def definida(self) -> bool:
        return bool(self.valor)


class Cofre(Protocol):
    def ler(self, nome_segredo: str) -> str | None: ...


class FonteKeyring(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...


def ler_arquivo_env(caminho: Path) -> dict[str, str]:
    """Lê linhas CHAVE=valor. Ignora linhas vazias e comentários (#) e tira aspas do valor."""
    if not caminho.is_file():
        return {}
    valores = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha.startswith("export "):
            linha = linha[len("export "):].strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip().strip("\"'")
    return valores


def _keyring_do_sistema() -> FonteKeyring | None:
    try:
        import keyring
    except Exception:  # sem a biblioteca, essa fonte só não existe
        return None
    return keyring


class CofreAzure:
    """Azure Key Vault pela DefaultAzureCredential (identidade gerenciada no App Service, az login no PC)."""

    def __init__(self, nome_ou_url: str):
        self._url = nome_ou_url if nome_ou_url.startswith("https://") else f"https://{nome_ou_url}.vault.azure.net"
        self._cliente = None
        self._desligado = False

    def _obter_cliente(self):
        if self._cliente is None:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            self._cliente = SecretClient(vault_url=self._url, credential=DefaultAzureCredential())
        return self._cliente

    def ler(self, nome_segredo: str) -> str | None:
        if self._desligado:
            return None
        try:
            from azure.core.exceptions import ResourceNotFoundError
        except Exception:
            log.warning("Key Vault desligado: faltam as bibliotecas azure-identity e azure-keyvault-secrets.")
            self._desligado = True
            return None
        try:
            return self._obter_cliente().get_secret(nome_segredo).value
        except ResourceNotFoundError:
            return None
        except Exception as erro:
            # Login, rede ou permissão: avisa uma vez e segue sem o cofre (nunca derruba o site)
            log.warning("Key Vault indisponível (%s): seguindo sem ele nesta execução.", type(erro).__name__)
            self._desligado = True
            return None


class LeitorDeConfiguracao:
    """Lê cada configuração uma vez, pela ordem do módulo, e guarda o resultado em memória."""

    def __init__(
        self,
        raiz: Path,
        ambiente: Mapping[str, str],
        *,
        arquivo_env: Path | None = None,
        keyring: FonteKeyring | None = None,
        criar_cofre: Callable[[str], Cofre] | None = CofreAzure,
    ):
        self.raiz = raiz
        self._ambiente = ambiente
        self._arquivo_env = ler_arquivo_env(arquivo_env) if arquivo_env is not None else {}
        self._keyring = keyring
        self._criar_cofre = criar_cofre
        self._cofre: Cofre | None = None
        self._cofre_pronto = False
        self._cache: dict[str, ValorLido] = {}
        self._trava = threading.RLock()

    # ------------------------------------------------------------------
    # fontes
    # ------------------------------------------------------------------

    def _do_ambiente(self, nome: str) -> str | None:
        valor = (self._ambiente.get(nome) or "").strip()
        if not valor:
            return None
        if valor.startswith(PREFIXO_REFERENCIA_COFRE):
            log.warning("%s: a referência ao Key Vault não resolveu no App Service; tratando como ausente.", nome)
            return None
        return valor

    def _basica(self, nome: str) -> str | None:
        """Ambiente e .env: as únicas fontes de QUICKCLICK_AMBIENTE e QUICKCLICK_KEYVAULT."""
        return self._do_ambiente(nome) or (self._arquivo_env.get(nome) or "").strip() or None

    @property
    def ambiente_local(self) -> bool:
        return (self._basica("QUICKCLICK_AMBIENTE") or "").lower() == "local"

    @property
    def em_producao(self) -> bool:
        """Dentro do Azure App Service, que sempre define WEBSITE_SITE_NAME."""
        return bool(self._do_ambiente("WEBSITE_SITE_NAME"))

    def _do_keyring(self, nome: str) -> str | None:
        if self._keyring is None or not self.ambiente_local:
            return None
        try:
            return (self._keyring.get_password(SERVICO_KEYRING, nome) or "").strip() or None
        except Exception as erro:  # sem backend no sistema (ex.: Linux do App Service): pula
            log.info("Gerenciador de Credenciais indisponível (%s).", type(erro).__name__)
            self._keyring = None
            return None

    def _obter_cofre(self) -> Cofre | None:
        if not self._cofre_pronto:
            self._cofre_pronto = True
            nome = self._basica("QUICKCLICK_KEYVAULT")
            if nome and self._criar_cofre is not None:
                self._cofre = self._criar_cofre(nome)
        return self._cofre

    def _do_cofre(self, nome: str) -> str | None:
        cofre = self._obter_cofre()
        if cofre is None:
            return None
        nomes = [nome_no_cofre(nome)]
        if self.ambiente_local:
            nomes.insert(0, nome_no_cofre(nome) + SUFIXO_DEV)
        for nome_segredo in nomes:
            valor = (cofre.ler(nome_segredo) or "").strip()
            if valor:
                return valor
        return None

    # ------------------------------------------------------------------
    # leitura
    # ------------------------------------------------------------------

    def ler(self, nome: str) -> ValorLido:
        with self._trava:
            if nome in self._cache:
                return self._cache[nome]
            lido = self._ler_sem_cache(nome)
            self._cache[nome] = lido
            return lido

    def _ler_sem_cache(self, nome: str) -> ValorLido:
        valor = self._do_ambiente(nome)
        if valor:
            return ValorLido(nome, valor, Origem.AMBIENTE)
        if nome in SEGREDOS:
            valor = self._do_keyring(nome)
            if valor:
                return ValorLido(nome, valor, Origem.KEYRING)
            valor = self._do_cofre(nome)
            if valor:
                return ValorLido(nome, valor, Origem.KEYVAULT)
        valor = (self._arquivo_env.get(nome) or "").strip()
        if valor:
            return ValorLido(nome, valor, Origem.ARQUIVO_ENV)
        return ValorLido(nome, None, Origem.AUSENTE)

    def texto(self, nome: str, padrao: str | None = None) -> str | None:
        """O valor, ou o padrão dado, ou o padrão do catálogo (que nunca existe para segredos)."""
        item = POR_NOME.get(nome)
        return self.ler(nome).valor or padrao or (item.padrao if item else None)

    def existe_no_ambiente(self, nome: str) -> bool:
        """Só diz se o nome existe nas variáveis de ambiente (para achar nomes antigos), sem ler o valor."""
        return nome in self._ambiente

    def booleano(self, nome: str, padrao: bool) -> bool:
        valor = (self.ler(nome).valor or "").strip().lower()
        if valor in VERDADEIROS:
            return True
        if valor in FALSOS:
            return False
        if valor:
            log.warning("%s com valor que não é verdadeiro nem falso; usando o padrão (%s).", nome, padrao)
        return padrao

    def decimal(self, nome: str, padrao: Decimal) -> Decimal:
        valor = (self.ler(nome).valor or "").strip().replace(",", ".")
        if not valor:
            return padrao
        try:
            return Decimal(valor)
        except InvalidOperation:
            log.warning("%s não é um número; usando o padrão (%s).", nome, padrao)
            return padrao

    def esquecer(self) -> None:
        """Esquece o que foi lido (só para scripts e testes)."""
        with self._trava:
            self._cache.clear()


def leitor_do_sistema(raiz: Path) -> LeitorDeConfiguracao:
    """O leitor de verdade: ambiente do processo, Gerenciador de Credenciais, Key Vault e .env da raiz."""
    import os

    return LeitorDeConfiguracao(
        raiz,
        os.environ,
        arquivo_env=raiz / ".env",
        keyring=_keyring_do_sistema(),
    )
