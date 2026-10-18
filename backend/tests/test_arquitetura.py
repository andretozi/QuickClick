"""
Confere as regras de dependência entre as camadas do back lendo os imports de cada arquivo.

    domain          só biblioteca padrão (nada de framework nem de outra camada)
    application     biblioteca padrão + domain
    presentation    nunca importa infrastructure nem app
    infrastructure  nunca importa presentation nem app

E a configuração (os.getenv, os.environ, dotenv) só é lida em backend/infrastructure/configuracao
e no main.py.
"""

import ast
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
BIBLIOTECA_PADRAO = set(sys.stdlib_module_names) | {"__future__"}


def _modulo_do_arquivo(arquivo: Path) -> list[str]:
    partes = list(arquivo.relative_to(BACKEND.parent).with_suffix("").parts)
    return partes[:-1] if partes[-1] == "__init__" else partes


def _imports(arquivo: Path) -> set[str]:
    """Nomes absolutos de tudo que o arquivo importa (imports relativos são resolvidos)."""
    nomes = set()
    pacote = _modulo_do_arquivo(arquivo)
    if arquivo.name != "__init__.py":
        pacote = pacote[:-1]
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            nomes.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom):
            if no.level:
                base = pacote[: len(pacote) - (no.level - 1)]
                nomes.add(".".join(base + ([no.module] if no.module else [])))
            else:
                nomes.add(no.module)
    return nomes


def _pertence(modulo: str, prefixo: str) -> bool:
    return modulo == prefixo or modulo.startswith(prefixo + ".")


def _leituras_de_configuracao(arquivo: Path) -> list[str]:
    """Cada os.getenv, os.environ, getenv e environ importados do os, e import de dotenv, com a linha."""
    achados = []
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name) and no.value.id == "os" \
                and no.attr in {"getenv", "environ", "putenv"}:
            achados.append(f"linha {no.lineno}: os.{no.attr}")
        elif isinstance(no, ast.ImportFrom) and no.module == "os" \
                and any(alias.name in {"getenv", "environ"} for alias in no.names):
            achados.append(f"linha {no.lineno}: from os import ...")
        elif isinstance(no, (ast.Import, ast.ImportFrom)):
            nomes = [alias.name for alias in no.names] if isinstance(no, ast.Import) else [no.module or ""]
            if any(_pertence(nome, "dotenv") for nome in nomes):
                achados.append(f"linha {no.lineno}: dotenv")
    return achados


class TestArquitetura(unittest.TestCase):
    def _conferir(self, camada: str, permitido):
        for arquivo in sorted((BACKEND / camada).rglob("*.py")):
            for modulo in sorted(_imports(arquivo)):
                with self.subTest(arquivo=str(arquivo.relative_to(BACKEND)), importa=modulo):
                    self.assertTrue(
                        permitido(modulo),
                        f"backend/{arquivo.relative_to(BACKEND).as_posix()} não pode importar {modulo}",
                    )

    def test_domain_e_python_puro(self):
        self._conferir(
            "domain",
            lambda m: m.split(".")[0] in BIBLIOTECA_PADRAO or _pertence(m, "backend.domain"),
        )

    def test_application_depende_so_do_domain(self):
        self._conferir(
            "application",
            lambda m: m.split(".")[0] in BIBLIOTECA_PADRAO
            or _pertence(m, "backend.domain")
            or _pertence(m, "backend.application"),
        )

    def test_presentation_nao_conhece_a_infraestrutura(self):
        self._conferir(
            "presentation",
            lambda m: not (_pertence(m, "backend.infrastructure") or _pertence(m, "backend.app")),
        )

    def test_infrastructure_nao_conhece_a_apresentacao(self):
        self._conferir(
            "infrastructure",
            lambda m: not (_pertence(m, "backend.presentation") or _pertence(m, "backend.app")),
        )

    def test_configuracao_so_e_lida_pelo_modulo_de_configuracao(self):
        """os.getenv, os.environ e dotenv só no módulo de configuração e no main.py."""
        raiz = BACKEND.parent
        permitidos = {BACKEND / "infrastructure" / "configuracao", raiz / "main.py"}
        arquivos = [*BACKEND.rglob("*.py"), *(raiz / "scripts").rglob("*.py")]
        for arquivo in sorted(arquivos):
            if any(arquivo == p or p in arquivo.parents for p in permitidos):
                continue
            with self.subTest(arquivo=arquivo.relative_to(raiz).as_posix()):
                self.assertEqual(_leituras_de_configuracao(arquivo), [])


if __name__ == "__main__":
    unittest.main()
