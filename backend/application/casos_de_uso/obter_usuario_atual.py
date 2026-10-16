"""Aplicação · Obter dados do usuário atual autenticado."""

from backend.application.portas import RepositorioUsuarios
from backend.domain.erros import VendedorNaoEncontrado
from backend.domain.usuario import Usuario


class ObterUsuarioAtual:
    def __init__(self, usuarios: RepositorioUsuarios):
        self._usuarios = usuarios

    def executar(self, usuario_id: int) -> Usuario:
        resultado = self._usuarios.obter_por_id(usuario_id)
        if resultado is None:
            raise VendedorNaoEncontrado(f"Usuário #{usuario_id} não encontrado.")
        usuario, _ = resultado
        return usuario
