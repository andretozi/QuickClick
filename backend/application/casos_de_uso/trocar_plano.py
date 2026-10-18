"""
Aplicação · O próprio vendedor troca o próprio plano (MVP: instantâneo e sem pagamento).

A troca livre fica atrás do interruptor TROCA_DE_PLANO_LIVRE (padrão true no MVP). Quando o
pagamento entrar, ele vira false: a troca só acontece depois do pagamento confirmado.
"""

from backend.application.portas import RepositorioUsuarios, RepositorioVendedores
from backend.domain.erros import PlanoInvalido, TrocaDePlanoIndisponivel, VendedorNaoEncontrado
from backend.domain.plano import buscar_plano
from backend.domain.usuario import Usuario
from backend.domain.vendedor import Vendedor


class TrocarPlano:
    def __init__(self, vendedores: RepositorioVendedores, usuarios: RepositorioUsuarios, livre: bool = True):
        self._vendedores = vendedores
        self._usuarios = usuarios
        self.livre = livre

    def executar(self, vendedor_id: int, slug: str) -> Usuario:
        if not self.livre:
            raise TrocaDePlanoIndisponivel()
        plano = buscar_plano(str(slug or "").strip().lower())
        if plano is None:
            raise PlanoInvalido()
        encontrado = self._usuarios.obter_por_id(vendedor_id)
        if encontrado is None:
            raise VendedorNaoEncontrado(vendedor_id)
        usuario, _ = encontrado
        vendedor = self._vendedores.obter(vendedor_id)
        # Conta antiga sem linha em vendedores (o plano lido era "gratis"): a linha nasce agora
        nome = vendedor.nome if vendedor else (usuario.nome or usuario.email)
        self._vendedores.salvar(Vendedor(id=vendedor_id, nome=nome, plano=plano))
        atualizado = self._usuarios.obter_por_id(vendedor_id)
        return atualizado[0] if atualizado else usuario
