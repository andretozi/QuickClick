"""
Guarda segredos no Gerenciador de Credenciais do Windows (biblioteca keyring), so no PC.
O valor fica criptografado pelo Windows na sua conta, sem arquivo de texto no disco.

Uso (da raiz, no terminal):
    python -m scripts.guardar_chave ANTHROPIC_API_KEY_PAGO   # pede o valor sem mostrar na tela
    python -m scripts.guardar_chave --listar                 # so os nomes guardados
    python -m scripts.guardar_chave --apagar NOME
    python -m scripts.guardar_chave --importar-env           # passa os segredos do .env para o Gerenciador

Rode num terminal de verdade (PowerShell ou o Terminal do PyCharm): o getpass esconde o que
voce digita ou cola, e o valor nao vai para o historico. Nenhum comando daqui mostra valores.
"""

import argparse
import getpass
import sys

from backend.infrastructure.configuracao import RAIZ_DO_PROJETO, SEGREDOS, ler_arquivo_env

SERVICO = "quickclick"


def _keyring():
    try:
        import keyring
    except ImportError:
        raise SystemExit("Falta a biblioteca keyring: pip install -r requirements.txt")
    return keyring


def _conferir_nome(nome: str) -> str:
    nome = nome.strip().upper()
    if nome not in SEGREDOS:
        raise SystemExit(f"{nome} nao e um segredo conhecido. Os nomes aceitos: {', '.join(sorted(SEGREDOS))}")
    return nome


def _avisos_sobre_o_valor(nome: str, valor: str) -> list[str]:
    avisos = []
    if "..." in valor or "…" in valor:
        avisos.append("o valor tem '...': parece a previa da lista do Console, que nao funciona. "
                      "Copie o valor completo na hora da criacao da chave.")
    if nome.startswith("ANTHROPIC_") and not valor.startswith("sk-ant-"):
        avisos.append("chaves da Anthropic comecam com sk-ant-. Confira se colou a chave certa.")
    if nome.startswith("GEMINI_") and not valor.startswith("AIza"):
        avisos.append("chaves do Google AI Studio costumam comecar com AIza. Confira se colou a chave certa.")
    return avisos


def guardar(nome: str) -> int:
    nome = _conferir_nome(nome)
    valor = getpass.getpass(f"Cole o valor de {nome} (nao aparece na tela) e tecle Enter: ").strip()
    if not valor:
        print("Nada foi guardado (valor vazio).")
        return 1
    for aviso in _avisos_sobre_o_valor(nome, valor):
        print(f"Aviso: {aviso}")
    _keyring().set_password(SERVICO, nome, valor)
    print(f"{nome} guardada no Gerenciador de Credenciais do Windows.")
    print("Confira com: python -m scripts.verificar_config")
    return 0


def listar() -> int:
    keyring = _keyring()
    guardados = [nome for nome in sorted(SEGREDOS) if keyring.get_password(SERVICO, nome)]
    if not guardados:
        print("Nenhum segredo da Quick Click guardado neste PC.")
        return 0
    print("Guardados no Gerenciador de Credenciais (so os nomes):")
    for nome in guardados:
        print(f"  {nome}")
    return 0


def apagar(nome: str) -> int:
    nome = _conferir_nome(nome)
    keyring = _keyring()
    if not keyring.get_password(SERVICO, nome):
        print(f"{nome} nao estava guardada.")
        return 0
    keyring.delete_password(SERVICO, nome)
    print(f"{nome} apagada do Gerenciador de Credenciais.")
    return 0


def importar_env() -> int:
    arquivo = RAIZ_DO_PROJETO / ".env"
    valores = ler_arquivo_env(arquivo)
    if not valores:
        print("Nao achei .env na raiz do projeto (ou ele esta vazio). Nada a importar.")
        return 0
    keyring = _keyring()
    importados, ficam = [], []
    for nome, valor in valores.items():
        if nome in SEGREDOS and valor:
            keyring.set_password(SERVICO, nome, valor)
            importados.append(nome)
        else:
            ficam.append(nome)
    if importados:
        print("Guardados no Gerenciador de Credenciais (pode apagar estas linhas do .env):")
        for nome in importados:
            print(f"  {nome}")
    if ficam:
        print("Ficam no .env (nao sao segredos, ou estao vazios):")
        for nome in ficam:
            print(f"  {nome}")
    print("No fim, o .env deve ter so: QUICKCLICK_AMBIENTE=local")
    print("Confira com: python -m scripts.verificar_config")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guarda segredos no Gerenciador de Credenciais do Windows.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("nome", nargs="?", help="nome da variavel, ex.: ANTHROPIC_API_KEY_PAGO")
    grupo.add_argument("--listar", action="store_true", help="mostra so os nomes guardados")
    grupo.add_argument("--apagar", metavar="NOME", help="apaga um segredo guardado")
    grupo.add_argument("--importar-env", action="store_true", help="passa os segredos do .env para o Gerenciador")
    args = parser.parse_args()
    if args.listar:
        return listar()
    if args.apagar:
        return apagar(args.apagar)
    if args.importar_env:
        return importar_env()
    return guardar(args.nome)


if __name__ == "__main__":
    sys.exit(main())
