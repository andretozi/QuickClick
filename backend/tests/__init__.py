"""
Testes do back (unittest). Rode da raiz: python -m unittest discover -s backend/tests -t .

Os testes nunca tocam o banco real nem leem segredos de verdade: ao importar este pacote,
a configuração do processo vira um leitor vazio (sem o ambiente do PC, sem o Gerenciador de
Credenciais e sem o .env), e criar um engine para postgres.database.azure.com vira erro.
"""

from backend.infrastructure.configuracao import RAIZ_DO_PROJETO, LeitorDeConfiguracao, definir_configuracao
from backend.infrastructure.database import ativar_trava_de_testes

AMBIENTE_DE_TESTE = {"QUICKCLICK_AMBIENTE": "teste"}

definir_configuracao(LeitorDeConfiguracao(RAIZ_DO_PROJETO, AMBIENTE_DE_TESTE, keyring=None, criar_cofre=None))
ativar_trava_de_testes()


def leitor_de_teste(**valores: str) -> LeitorDeConfiguracao:
    """Um leitor só com os valores dados (nada do PC, nada da nuvem)."""
    return LeitorDeConfiguracao(RAIZ_DO_PROJETO, {**AMBIENTE_DE_TESTE, **valores}, keyring=None, criar_cofre=None)
