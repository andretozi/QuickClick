"""
Infraestrutura · IA · Esquemas JSON da saída estruturada de cada etapa

Regras da API (conferidas na documentação): todo objeto com additionalProperties false e todos
os campos em required; sem minLength, maxLength, minimum, maximum e maxItems (o Python confere
os tamanhos depois, no domínio). Chaves curtas e enums fechados.
"""

from backend.domain.ia.leitura import CATEGORIAS, Confianca, CondicaoProduto, OrigemAtributo, SugestaoDeFoto


def _objeto(propriedades: dict) -> dict:
    return {"type": "object", "properties": propriedades, "required": list(propriedades), "additionalProperties": False}


TEXTO = {"type": "string"}
INTEIRO = {"type": "integer"}
LISTA_DE_TEXTOS = {"type": "array", "items": TEXTO}


def _enum(tipo) -> dict:
    return {"type": "string", "enum": [membro.value for membro in tipo]}


LEITURA = _objeto({
    "reconhecido": {"type": "boolean"},
    "motivo_nao_reconhecido": TEXTO,
    "produto": TEXTO,
    "categoria": {"type": "string", "enum": list(CATEGORIAS)},
    "termos_busca": LISTA_DE_TEXTOS,
    "atributos": {"type": "array", "items": _objeto({
        "chave": TEXTO,
        "valor": TEXTO,
        "origem": _enum(OrigemAtributo),
        "evidencia": TEXTO,
        "confianca": _enum(Confianca),
    })},
    "condicao": _objeto({
        "valor": _enum(CondicaoProduto),
        "sinais": LISTA_DE_TEXTOS,
        "confianca": _enum(Confianca),
    }),
    "defeitos_visiveis": LISTA_DE_TEXTOS,
    "texto_legivel": LISTA_DE_TEXTOS,
    "etiqueta_ilegivel": {"type": "array", "items": _objeto({
        "foto": INTEIRO,
        "caixa": {"type": "array", "items": INTEIRO},
    })},
    "perguntas": {"type": "array", "items": _objeto({
        "chave": TEXTO,
        "pergunta": TEXTO,
        "sugerir_foto": _enum(SugestaoDeFoto),
    })},
})

# Releitura da etiqueta (recorte) e da foto extra: só o que a imagem nova pode trazer
RELEITURA = _objeto({
    "texto_legivel": LISTA_DE_TEXTOS,
    "atributos": LEITURA["properties"]["atributos"],
    "defeitos_visiveis": LISTA_DE_TEXTOS,
})

PESQUISA = _objeto({
    "perfil_comprador": TEXTO,
    "o_que_valoriza": LISTA_DE_TEXTOS,
    "objecoes": LISTA_DE_TEXTOS,
    "termos_que_usam": LISTA_DE_TEXTOS,
    "fontes": LISTA_DE_TEXTOS,
})
PESQUISA_SEM_WEB = _objeto({k: v for k, v in PESQUISA["properties"].items() if k != "fontes"})

PRECO = _objeto({
    "preco_sugerido_centavos": INTEIRO,
    "faixa": _objeto({"min": INTEIRO, "max": INTEIRO}),
    "estrategia": {"type": "string", "enum": ["vender_rapido", "equilibrado", "maximo"]},
    "justificativa": TEXTO,
    "alertas": LISTA_DE_TEXTOS,
    "canais": {"type": "array", "items": _objeto({"slug": TEXTO, "motivo": TEXTO})},
})

TEXTO_DO_ANUNCIO = _objeto({
    "titulo": TEXTO,
    "descricao": TEXTO,
    "especificacoes": {"type": "array", "items": _objeto({"rotulo": TEXTO, "valor": TEXTO})},
})

ATRIBUTOS_ML = _objeto({
    "ligacoes": {"type": "array", "items": _objeto({"chave": TEXTO, "id_ml": TEXTO})},
})

PRECOS_NA_WEB = _objeto({
    "itens": {"type": "array", "items": _objeto({
        "preco_centavos": INTEIRO,
        "frete_gratis": {"type": "boolean"},
        "url": TEXTO,
    })},
})


def formato(esquema: dict) -> dict:
    """output_config.format da Anthropic."""
    return {"type": "json_schema", "schema": esquema}


def ferramenta_de_saida(nome: str, descricao: str, esquema: dict) -> dict:
    """Ferramenta strict que faz as vezes de saída estruturada quando há busca na web
    (citações da busca e output_config.format não andam juntos: a API recusa com 400)."""
    return {"name": nome, "description": descricao, "strict": True, "input_schema": esquema}
