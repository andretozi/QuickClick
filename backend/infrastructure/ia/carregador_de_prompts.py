"""
Infraestrutura · IA · Prompts das IAs

Um arquivo .txt por etapa em backend/infrastructure/ia/prompts/ (nunca .md: o .gitignore ignora
*.md e o prompt não chegaria ao Azure). A versão vai no nome (leitura_v1.txt) e é gravada em
ia_uso. Carregados uma vez, na partida; vale a versão mais nova de cada etapa.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PASTA_DE_PROMPTS = Path(__file__).resolve().parent / "prompts"
_NOME = re.compile(r"^(?P<etapa>[a-z_]+)_v(?P<versao>\d+)\.txt$")


@dataclass(frozen=True)
class Prompt:
    etapa: str
    versao: str  # ex.: "leitura_v1"
    texto: str


@lru_cache(maxsize=1)
def carregar_prompts(pasta: Path = PASTA_DE_PROMPTS) -> dict[str, Prompt]:
    escolhidos: dict[str, tuple[int, Prompt]] = {}
    for arquivo in sorted(pasta.glob("*.txt")):
        achado = _NOME.match(arquivo.name)
        if not achado:
            continue
        numero = int(achado["versao"])
        prompt = Prompt(achado["etapa"], arquivo.stem, arquivo.read_text(encoding="utf-8").strip())
        if achado["etapa"] not in escolhidos or numero > escolhidos[achado["etapa"]][0]:
            escolhidos[achado["etapa"]] = (numero, prompt)
    return {etapa: prompt for etapa, (_, prompt) in escolhidos.items()}


def prompt(etapa: str) -> Prompt:
    prompts = carregar_prompts()
    if etapa not in prompts:
        raise RuntimeError(f"Falta o prompt da etapa {etapa} em {PASTA_DE_PROMPTS}.")
    return prompts[etapa]
