"""
Apresentação · Fotos enviadas em multipart, sempre em memória

O Starlette guarda em arquivo temporário cada parte acima de 1 MB; aqui o limite sobe para 11 MB
(cada foto tem até 10 MB), então nenhuma foto vai para o disco.
"""

from fastapi import Request
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartParser

from backend.application.ia.modelos import ArquivoDeFoto
from backend.domain.erros import FotoInvalida
from backend.domain.ia.fotos import MAX_BYTES_POR_FOTO, MAX_FOTOS_POR_ANALISE

MultiPartParser.spool_max_size = MAX_BYTES_POR_FOTO + 1024 * 1024  # foto nunca vai para arquivo temporário
LIMITE_DO_PEDIDO = MAX_FOTOS_POR_ANALISE * MAX_BYTES_POR_FOTO + 1024 * 1024


async def ler_fotos(request: Request, campo: str, maximo: int) -> list[ArquivoDeFoto]:
    tamanho = request.headers.get("content-length")
    if tamanho and tamanho.isdigit() and int(tamanho) > LIMITE_DO_PEDIDO:
        raise FotoInvalida("As fotos passaram do tamanho máximo. Manda até 6 fotos de até 10 MB.")
    tipo = request.headers.get("content-type", "")
    if not tipo.startswith("multipart/form-data"):
        return []
    form = await request.form(max_files=maximo + 1, max_fields=10)
    arquivos = [item for item in form.getlist(campo) if isinstance(item, UploadFile)]
    if len(arquivos) > maximo:
        for arquivo in arquivos:
            await arquivo.close()
        raise FotoInvalida(f"Manda até {maximo} fotos por vez.")
    fotos = []
    for arquivo in arquivos:
        conteudo = await arquivo.read(MAX_BYTES_POR_FOTO + 1)
        await arquivo.close()
        fotos.append(ArquivoDeFoto(nome=arquivo.filename or "foto", conteudo=conteudo,
                                   tipo_declarado=arquivo.content_type or ""))
    return fotos


async def campo_de_texto(request: Request, nome: str) -> str:
    if not request.headers.get("content-type", "").startswith("multipart/form-data"):
        return ""
    form = await request.form(max_files=MAX_FOTOS_POR_ANALISE + 1, max_fields=10)
    valor = form.get(nome)
    return valor if isinstance(valor, str) else ""
