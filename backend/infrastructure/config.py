"""
Infraestrutura · Configuração

Lê o arquivo .env da raiz do projeto, se existir, sem depender de biblioteca.
Variáveis de ambiente de verdade ganham do .env.
Segredo nunca vai para o código nem para o Git: use o .env.example como modelo.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

BANCO_PADRAO = Path("backend") / "data" / "quickclick.sqlite3"
PLANO_DEMO_PADRAO = "gratis"


@dataclass(frozen=True)
class Config:
    raiz: Path
    pasta_front: Path  # front buildado (frontend/dist), servido fora de /api
    caminho_banco: Path  # arquivo SQLite, fora do Git
    plano_demo: str = PLANO_DEMO_PADRAO  # slug do plano do vendedor de demonstração


def ler_arquivo_env(caminho: Path) -> dict[str, str]:
    """Lê linhas CHAVE=valor. Ignora linhas vazias e comentários (#) e tira aspas do valor."""
    if not caminho.is_file():
        return {}
    valores = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip().strip("\"'")
    return valores


def carregar_config(raiz: Path, ambiente: Mapping[str, str] | None = None) -> Config:
    valores = {**ler_arquivo_env(raiz / ".env"), **(os.environ if ambiente is None else ambiente)}
    banco = Path(valores.get("QUICKCLICK_BANCO") or BANCO_PADRAO)
    return Config(
        raiz=raiz,
        pasta_front=raiz / "frontend" / "dist",
        caminho_banco=banco if banco.is_absolute() else raiz / banco,
        plano_demo=(valores.get("QUICKCLICK_PLANO_DEMO") or PLANO_DEMO_PADRAO).strip().lower(),
    )
