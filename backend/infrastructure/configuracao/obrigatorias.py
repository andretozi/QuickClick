"""
Infraestrutura · Configuração · O que derruba a partida

Em produção (App Service), sem QUICKCLICK_JWT_SECRET ou sem DATABASE_URL a aplicação
não sobe: melhor um erro claro no Log Stream do que um site que aceita qualquer token
ou que não guarda nada. No PC, o JWT ganha um segredo aleatório só para aquela execução.
"""

import logging
import secrets

from backend.infrastructure.configuracao.leitor import LeitorDeConfiguracao

log = logging.getLogger("quickclick.config")

TAMANHO_MINIMO_SEGREDO_JWT = 32


class ConfiguracaoObrigatoriaAusente(RuntimeError):
    def __init__(self, nome: str):
        super().__init__(
            f"Falta {nome}: sem ela a aplicação não sobe em produção. "
            "Defina a variável no App Service (Configurações > Variáveis de ambiente) e reinicie."
        )
        self.nome = nome


_segredo_jwt_desta_execucao: str | None = None


def segredo_jwt(leitor: LeitorDeConfiguracao) -> str:
    global _segredo_jwt_desta_execucao
    valor = leitor.texto("QUICKCLICK_JWT_SECRET")
    if valor:
        if len(valor) < TAMANHO_MINIMO_SEGREDO_JWT:
            log.warning("QUICKCLICK_JWT_SECRET tem menos de %d caracteres: gere um mais longo.", TAMANHO_MINIMO_SEGREDO_JWT)
        return valor
    if leitor.em_producao:
        raise ConfiguracaoObrigatoriaAusente("QUICKCLICK_JWT_SECRET")
    if _segredo_jwt_desta_execucao is None:
        _segredo_jwt_desta_execucao = secrets.token_urlsafe(48)
        log.warning(
            "QUICKCLICK_JWT_SECRET ausente: usando um segredo aleatório só nesta execução "
            "(os logins caem quando o servidor reiniciar). Guarde um com: python -m scripts.guardar_chave QUICKCLICK_JWT_SECRET"
        )
    return _segredo_jwt_desta_execucao


def normalizar_url_postgres(url: str) -> str:
    """postgres:// e postgresql:// viram postgresql+psycopg2:// (o driver instalado)."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def database_url(leitor: LeitorDeConfiguracao) -> str | None:
    """A URL do banco, ou None no PC sem DATABASE_URL (o site sobe, mas o que usa o banco avisa)."""
    valor = leitor.texto("DATABASE_URL")
    if valor:
        return normalizar_url_postgres(valor)
    if leitor.em_producao:
        raise ConfiguracaoObrigatoriaAusente("DATABASE_URL")
    return None
