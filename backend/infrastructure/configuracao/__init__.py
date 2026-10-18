"""
Infraestrutura · Configuração

O único lugar do back que lê configuração (ambiente, Gerenciador de Credenciais do Windows,
Azure Key Vault e o .env da raiz), na ordem descrita em leitor.py. O resto do código pede
os valores a este pacote e nunca usa os.getenv, os.environ ou dotenv.

Segredo nunca vai para o código, para o front nem para o Git.
"""

from dataclasses import dataclass
from pathlib import Path

from backend.infrastructure.configuracao.catalogo import (
    ITENS,
    NOMES_ANTIGOS,
    POR_NOME,
    SEGREDOS,
    ItemDeConfiguracao,
    nome_no_cofre,
)
from backend.infrastructure.configuracao.leitor import (
    LeitorDeConfiguracao,
    Origem,
    ValorLido,
    leitor_do_sistema,
    ler_arquivo_env,
)
from backend.infrastructure.configuracao.obrigatorias import (
    ConfiguracaoObrigatoriaAusente,
    database_url,
    normalizar_url_postgres,
    segredo_jwt,
)

RAIZ_DO_PROJETO = Path(__file__).resolve().parents[3]

__all__ = [
    "ITENS",
    "NOMES_ANTIGOS",
    "POR_NOME",
    "SEGREDOS",
    "RAIZ_DO_PROJETO",
    "Config",
    "ConfiguracaoObrigatoriaAusente",
    "ItemDeConfiguracao",
    "LeitorDeConfiguracao",
    "Origem",
    "ValorLido",
    "carregar_config",
    "configuracao",
    "database_url",
    "definir_configuracao",
    "leitor_do_sistema",
    "ler_arquivo_env",
    "nome_no_cofre",
    "normalizar_url_postgres",
    "segredo_jwt",
]


@dataclass(frozen=True)
class Config:
    raiz: Path
    pasta_front: Path  # front buildado (frontend/dist), servido fora de /api


def carregar_config(raiz: Path) -> Config:
    return Config(raiz=raiz, pasta_front=raiz / "frontend" / "dist")


_leitor: LeitorDeConfiguracao | None = None


def configuracao() -> LeitorDeConfiguracao:
    """O leitor do processo, criado na primeira vez que alguém pede uma configuração."""
    global _leitor
    if _leitor is None:
        _leitor = leitor_do_sistema(RAIZ_DO_PROJETO)
    return _leitor


def definir_configuracao(leitor: LeitorDeConfiguracao | None) -> None:
    """Troca o leitor do processo (os testes usam um leitor sem ambiente real, sem keyring e sem .env)."""
    global _leitor
    _leitor = leitor
