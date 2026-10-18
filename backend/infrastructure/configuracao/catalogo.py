"""
Infraestrutura · Configuração · Catálogo

Toda configuração que o back conhece, com o que depende dela e de onde vem o valor.
Os segredos também são procurados no Gerenciador de Credenciais do Windows (só no PC)
e no Azure Key Vault (quando ele existir), com o nome em minúsculas e hífens.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ItemDeConfiguracao:
    nome: str
    segredo: bool
    uso: str  # o que fica desligado sem ela
    de_onde_vem: str  # onde o André tira o valor
    obrigatoria_em_producao: bool = False
    usada_no_mvp: bool = True
    padrao: str | None = None  # valor usado quando ela falta (nunca para segredos)


COMANDO_SEGREDO_JWT = 'python -c "import secrets; print(secrets.token_urlsafe(48))"'
COMANDO_CHAVE_FERNET = 'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'

ITENS: tuple[ItemDeConfiguracao, ...] = (
    # Segredos (tabela 2.1.2 do prompt)
    ItemDeConfiguracao("QUICKCLICK_JWT_SECRET", True, "login (assinatura dos tokens)",
                       f"gerado por comando: {COMANDO_SEGREDO_JWT}", obrigatoria_em_producao=True),
    ItemDeConfiguracao("DATABASE_URL", True, "banco de dados",
                       "Azure Portal, db-quickclick, Settings > Connect (postgresql://... ?sslmode=require)",
                       obrigatoria_em_producao=True),
    ItemDeConfiguracao("TOKENS_CHAVE_CRIPTO", True, "conexão com o Mercado Livre (tokens criptografados)",
                       f"gerado por comando: {COMANDO_CHAVE_FERNET}"),
    ItemDeConfiguracao("MERCADO_LIVRE_CLIENT_ID", True, "conexão com o Mercado Livre",
                       "Mercado Livre Developers, Minhas aplicações (App ID)"),
    ItemDeConfiguracao("MERCADO_LIVRE_CLIENT_SECRET", True, "conexão com o Mercado Livre",
                       "Mercado Livre Developers, Minhas aplicações (Secret Key)"),
    ItemDeConfiguracao("ANTHROPIC_API_KEY_PAGO", True, "IA dos planos pagos (Claude)",
                       "Claude Console, workspace quickclick-pago, API keys"),
    ItemDeConfiguracao("ANTHROPIC_API_KEY_GRATIS", True, "reserva da IA do plano Grátis (Haiku)",
                       "Claude Console, workspace quickclick-gratis, API keys"),
    ItemDeConfiguracao("GEMINI_API_KEY_GRATIS", True, "IA do plano Grátis (Gemini)",
                       "Google AI Studio, projeto quickclick-gratis, Get API key"),
    ItemDeConfiguracao("GEMINI_API_KEY_PAGO", True, "tratamento de foto (versão final)",
                       "Google AI Studio, projeto quickclick-pago (sem saldo ainda)", usada_no_mvp=False),
    # Configurações comuns (não são segredo)
    ItemDeConfiguracao("MERCADO_LIVRE_REDIRECT_URI", False, "retorno do login do Mercado Livre",
                       "padrão do código", padrao="https://quickclick.azurewebsites.net/api/marketplaces/mercado-livre/callback"),
    ItemDeConfiguracao("QUICKCLICK_AMBIENTE", False, "modo local (Gerenciador de Credenciais e scripts)",
                       "só no .env do PC: QUICKCLICK_AMBIENTE=local"),
    ItemDeConfiguracao("QUICKCLICK_KEYVAULT", False, "leitura do Azure Key Vault",
                       "nome do cofre, quando ele existir"),
    ItemDeConfiguracao("DOCUMENTACAO_API_ATIVA", False, "exibição de /docs, /redoc e /openapi.json",
                       "interruptor (desligado por padrão para segurança)", padrao="false"),
    ItemDeConfiguracao("IA_ATIVA", False, "liga e desliga toda a IA", "interruptor", padrao="true"),
    ItemDeConfiguracao("PESQUISA_WEB_ATIVA", False, "busca na web da pesquisa de mercado", "interruptor", padrao="true"),
    ItemDeConfiguracao("ADVISOR_ATIVO", False, "orientador (Opus) na pesquisa de mercado", "interruptor",
                       padrao="false"),
    ItemDeConfiguracao("IA_ORCAMENTO_DIARIO_USD", False, "teto de gasto diário da IA paga", "em dólar", padrao="0.30"),
    ItemDeConfiguracao("IA_CACHE_TTL", False, "tempo do cache de prompt (5m ou 1h)", "5m ou 1h", padrao="5m"),
    ItemDeConfiguracao("TROCA_DE_PLANO_LIVRE", False, "troca de plano sem pagamento (MVP; false quando o "
                       "pagamento entrar)", "interruptor", padrao="true"),
    ItemDeConfiguracao("TRATAMENTO_FOTO_ATIVO", False, "tratamento de foto (versão final)", "interruptor",
                       usada_no_mvp=False, padrao="false"),
    ItemDeConfiguracao("MODELO_VISAO", False, "leitura da foto e preço (pago)", "ID do modelo", padrao="claude-opus-5-5"),
    ItemDeConfiguracao("MODELO_TEXTO", False, "pesquisa e descrição (pago)", "ID do modelo", padrao="claude-sonnet-5-5"),
    ItemDeConfiguracao("MODELO_RAPIDO", False, "reservas e correções", "ID do modelo", padrao="claude-haiku-5-5"),
    ItemDeConfiguracao("MODELO_GEMINI_TEXTO", False, "leitura e descrição do plano Grátis", "ID do modelo",
                       padrao="gemini-3.8-flash"),
)

# Nomes que o código já leu e não lê mais (o André apaga do App Service depois do deploy)
NOMES_ANTIGOS: dict[str, str] = {
    "JWT_SECRET": "trocada por QUICKCLICK_JWT_SECRET",
    "QUICKCLICK_PLANO_DEMO": "sem uso (o plano mora no banco, em vendedores.plano)",
    "QUICKCLICK_BANCO": "legado do SQLite",
    "AZURE_DB_USER": "trocada por DATABASE_URL",
    "AZURE_DB_PASSWORD": "trocada por DATABASE_URL",
    "AZURE_DB_HOST": "trocada por DATABASE_URL",
    "POSTGRESQLCONNSTR_DATABASE_URL": "trocada por DATABASE_URL",
}

POR_NOME = {item.nome: item for item in ITENS}
SEGREDOS = frozenset(item.nome for item in ITENS if item.segredo)


def nome_no_cofre(variavel: str) -> str:
    """ANTHROPIC_API_KEY_PAGO vira anthropic-api-key-pago (o Key Vault não aceita "_")."""
    return variavel.lower().replace("_", "-")
