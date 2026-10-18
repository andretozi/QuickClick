"""
Confere a configuracao sem nunca mostrar valores.

Uso (da raiz):  python -m scripts.verificar_config            # tudo
                python -m scripts.verificar_config --sem-rede  # so a lista, sem banco e sem IA

1. Lista cada configuracao com "definida" ou "ausente" e de onde veio (ambiente,
   Gerenciador de Credenciais, Key Vault ou .env).
2. Testa a conexao com o banco (select 1).
3. Faz uma chamada minima e barata a cada provedor de IA: Haiku com 1 token de saida em
   cada workspace da Anthropic e o Gemini Flash da camada gratis. Chave recusada (401 ou 403)
   quer dizer chave vencida, revogada ou sem permissao: troque no Claude Console.
"""

import argparse
import logging
import sys

from backend.infrastructure.configuracao import (
    ITENS,
    NOMES_ANTIGOS,
    ConfiguracaoObrigatoriaAusente,
    configuracao,
    database_url,
)

OK = "ok"
FALHOU = "FALHOU"


def onde_guardar(leitor, nome: str) -> str:
    if leitor.em_producao:
        return "App Service > Configuracoes > Variaveis de ambiente"
    return f"no PC: python -m scripts.guardar_chave {nome}"


def listar(leitor) -> list[str]:
    faltando = []
    print("Configuracao (valores nunca aparecem aqui)")
    print(f"  {'nome':<30} {'situacao':<9} {'origem':<27} uso")
    for item in ITENS:
        lido = leitor.ler(item.nome)
        if lido.definida:
            situacao, origem = "definida", lido.origem.value
        elif item.padrao is not None:
            situacao, origem = "padrao", "valor padrao do codigo"
        else:
            situacao, origem = "ausente", "-"
        print(f"  {item.nome:<30} {situacao:<9} {origem:<27} {item.uso}")
        if situacao == "ausente" and item.segredo and item.usada_no_mvp:
            faltando.append(f"{item.nome}: {item.uso}. Valor: {item.de_onde_vem}. Onde: {onde_guardar(leitor, item.nome)}")
    sobrando = [f"{nome} ({motivo})" for nome, motivo in NOMES_ANTIGOS.items() if leitor.existe_no_ambiente(nome)]
    if sobrando:
        print("\nNomes antigos que o codigo nao le mais (apague depois do deploy):")
        for linha in sobrando:
            print(f"  {linha}")
    return faltando


def testar_banco(leitor) -> str:
    try:
        url = database_url(leitor)
    except ConfiguracaoObrigatoriaAusente:
        url = None
    if url is None:
        return "pulado (sem DATABASE_URL)"
    from sqlalchemy import text

    from backend.infrastructure.database import criar_engine

    engine = criar_engine(url, timeout_s=10)
    try:
        with engine.connect() as conexao:
            conexao.execute(text("select 1"))
        return OK
    except Exception as erro:  # a mensagem do driver pode trazer o endereco: mostramos so o diagnostico
        bruto = str(erro).lower()
        if "timeout" in bruto or "timed out" in bruto:
            dica = "sem resposta: libere o seu IP no firewall do db-quickclick (Networking)"
        elif "password" in bruto or "authentication" in bruto:
            dica = "usuario ou senha recusados: confira a DATABASE_URL"
        elif "ssl" in bruto:
            dica = "SSL: a URL precisa de ?sslmode=require"
        else:
            dica = "confira a DATABASE_URL e o firewall"
        return f"{FALHOU} ({type(erro).__name__}: {dica})"
    finally:
        engine.dispose()


def testar_anthropic(leitor, nome: str) -> str:
    chave = leitor.texto(nome)
    if not chave:
        return "pulado (ausente)"
    import anthropic

    modelo = leitor.texto("MODELO_RAPIDO")
    cliente = anthropic.Anthropic(api_key=chave, max_retries=0, timeout=30)
    try:
        cliente.messages.create(
            model=modelo,
            max_tokens=1,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": "ok"}],
        )
        return f"{OK} ({modelo})"
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as erro:
        return f"{FALHOU} ({erro.status_code}: {nome} recusada, chave vencida, revogada ou sem permissao)"
    except anthropic.RateLimitError:
        return f"{FALHOU} (429: a chave vale, mas a workspace esta no limite de uso ou de gasto)"
    except anthropic.NotFoundError:
        return f"{FALHOU} (404: modelo {modelo} nao encontrado; confira MODELO_RAPIDO)"
    except anthropic.APIStatusError as erro:
        return f"{FALHOU} ({erro.status_code}: {type(erro).__name__})"
    except anthropic.APIConnectionError:
        return f"{FALHOU} (sem conexao com a Anthropic)"


def testar_gemini(leitor, nome: str) -> str:
    chave = leitor.texto(nome)
    if not chave:
        return "pulado (ausente)"
    from google import genai
    from google.genai import errors, types

    modelo = leitor.texto("MODELO_GEMINI_TEXTO")
    try:
        genai.Client(api_key=chave).models.generate_content(
            model=modelo,
            contents="ok",
            config=types.GenerateContentConfig(max_output_tokens=1),
        )
        return f"{OK} ({modelo})"
    except errors.APIError as erro:
        if erro.code in (401, 403) or (erro.code == 400 and "api key" in str(erro).lower()):
            return f"{FALHOU} ({erro.code}: {nome} recusada, confira no Google AI Studio)"
        if erro.code == 429:
            return f"{FALHOU} (429: limite da camada gratis atingido; tente mais tarde)"
        if erro.code == 404:
            return f"{FALHOU} (404: modelo {modelo} nao encontrado; confira MODELO_GEMINI_TEXTO)"
        return f"{FALHOU} ({erro.code}: {type(erro).__name__})"
    except Exception as erro:
        return f"{FALHOU} ({type(erro).__name__})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Confere a configuracao sem mostrar valores.")
    parser.add_argument("--sem-rede", action="store_true", help="so a lista, sem testar banco e IA")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="  aviso: %(message)s")

    leitor = configuracao()
    local = "local" if leitor.ambiente_local else ("App Service" if leitor.em_producao else "PC sem QUICKCLICK_AMBIENTE=local")
    print(f"Ambiente: {local}\n")
    if not leitor.ambiente_local and not leitor.em_producao:
        print("Dica: crie o .env na raiz com a linha QUICKCLICK_AMBIENTE=local para o Gerenciador de "
              "Credenciais valer.\n")
    faltando = listar(leitor)

    falhas = 0
    if not args.sem_rede:
        print("\nTestes")
        resultados = [
            ("banco (select 1)", testar_banco(leitor)),
            ("Anthropic, workspace gratis", testar_anthropic(leitor, "ANTHROPIC_API_KEY_GRATIS")),
            ("Anthropic, workspace pago", testar_anthropic(leitor, "ANTHROPIC_API_KEY_PAGO")),
            ("Gemini, camada gratis", testar_gemini(leitor, "GEMINI_API_KEY_GRATIS")),
            ("Gemini, projeto pago", "nao testado (so na versao final)"),
        ]
        for nome, resultado in resultados:
            print(f"  {nome:<30} {resultado}")
        falhas = sum(1 for _, resultado in resultados if resultado.startswith(FALHOU))

    if faltando:
        print("\nO que falta:")
        for linha in faltando:
            print(f"  {linha}")
    if not faltando and not falhas:
        print("\nTudo certo.")
    return 1 if (faltando or falhas) else 0


if __name__ == "__main__":
    sys.exit(main())
