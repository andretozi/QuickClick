"""
Procura segredos nos arquivos versionados (git ls-files) e falha se achar algum.

Uso (da raiz):  python scripts/verificar_segredos.py
Sem dependências: roda no GitHub Actions antes do build.

O que conta como segredo:
    chaves da Anthropic (sk-ant-) e do Google (AIza...), chave privada (BEGIN ... PRIVATE KEY),
    URL do Postgres com senha, publish profile do Azure, tokens do GitHub, chaves da AWS,
    o antigo segredo JWT padrão, e qualquer variável VITE_ com KEY, SECRET, TOKEN ou SENHA
    no nome (o Vite coloca toda variável VITE_ dentro do JavaScript público).

Uma linha de teste com valor falso de propósito pode levar o marcador "verificar_segredos: ignorar".
"""

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MARCADOR_IGNORAR = "verificar_segredos: ignorar"
TAMANHO_MAXIMO = 2_000_000  # arquivos maiores (imagens, lock) não são texto de código

PADROES: tuple[tuple[str, re.Pattern], ...] = (
    ("chave da Anthropic", re.compile(r"sk-ant-[A-Za-z0-9_\-]{12,}")),
    ("chave do Google", re.compile(r"AIza[0-9A-Za-z_\-]{30,}")),
    ("chave privada", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----")),
    ("URL do Postgres com senha", re.compile(r"postgres(?:ql)?(?:\+\w+)?://[^\s:/@'\"]+:[^\s@'\"]+@[^\s'\"]+")),
    ("publish profile do Azure", re.compile("user" + "PWD=|<" + "publishData", re.IGNORECASE)),
    ("connection string do Azure Storage", re.compile(r"AccountKey=[A-Za-z0-9+/=]{20,}")),
    ("token do GitHub", re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}")),
    ("chave da AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("segredo JWT padrao antigo", re.compile("quickclick-default-" + "jwt-secret")),
    ("variavel VITE_ com segredo no nome", re.compile(r"\bVITE_[A-Z0-9_]*(?:KEY|SECRET|TOKEN|SENHA)[A-Z0-9_]*")),
)


def arquivos_versionados() -> list[Path]:
    saida = subprocess.run(
        # versionados e novos ainda nao adicionados (menos os ignorados pelo .gitignore)
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=RAIZ, capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return [RAIZ / nome for nome in saida.split("\0") if nome]


def procurar(arquivo: Path) -> list[str]:
    try:
        if arquivo.stat().st_size > TAMANHO_MAXIMO:
            return []
        texto = arquivo.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []  # apagado no disco ou binário
    achados = []
    for numero, linha in enumerate(texto.splitlines(), start=1):
        if MARCADOR_IGNORAR in linha:
            continue
        for descricao, padrao in PADROES:
            if padrao.search(linha):
                achados.append(f"{arquivo.relative_to(RAIZ).as_posix()}:{numero}: {descricao}")
    return achados


def main() -> int:
    achados = [achado for arquivo in arquivos_versionados() for achado in procurar(arquivo)]
    if achados:
        print("verificar_segredos: possivel segredo em arquivo do repositorio (o valor nao e mostrado):")
        for achado in achados:
            print(f"  {achado}")
        print("Tire o valor do arquivo, troque a chave no painel de onde ela veio e guarde a nova fora do Git.")
        return 1
    print("verificar_segredos: nenhum segredo nos arquivos do repositorio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
