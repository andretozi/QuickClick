"""
Domínio · Planos de assinatura

Nenhum plano cobra comissão sobre as vendas. Quanto mais avançado o plano, mais automação.

Regra do limite de marketplaces:
    Grátis e Essencial conectam 1 marketplace.
    Pro e Business conectam vários: o multicanal começa no Pro.
"""

from dataclasses import dataclass

from backend.domain.erros import LimiteDoPlanoAtingido


@dataclass(frozen=True)
class Plano:
    slug: str
    nome: str
    limite_marketplaces: int | None  # None: conecta vários marketplaces (sem limite fixo)
    preco_mensal_centavos: int | None  # None: preço ainda não definido pela equipe

    @property
    def multicanal(self) -> bool:
        return self.limite_marketplaces is None or self.limite_marketplaces > 1

    def permite_conectar(self, conectados: int) -> bool:
        """True se ainda cabe mais um marketplace, com `conectados` já ligados."""
        return self.limite_marketplaces is None or conectados < self.limite_marketplaces

    def garantir_vaga(self, conectados: int) -> None:
        """Barra a conexão quando o limite do plano foi atingido, sugerindo o plano certo."""
        if not self.permite_conectar(conectados):
            raise LimiteDoPlanoAtingido(self, plano_para_mais_marketplaces(self))


GRATIS = Plano("gratis", "Grátis", limite_marketplaces=1, preco_mensal_centavos=0)
ESSENCIAL = Plano("essencial", "Essencial", limite_marketplaces=1, preco_mensal_centavos=None)
PRO = Plano("pro", "Pro", limite_marketplaces=None, preco_mensal_centavos=None)
BUSINESS = Plano("business", "Business", limite_marketplaces=None, preco_mensal_centavos=None)

# Do mais simples para o mais completo
PLANOS: tuple[Plano, ...] = (GRATIS, ESSENCIAL, PRO, BUSINESS)


def buscar_plano(slug: str) -> Plano | None:
    return next((plano for plano in PLANOS if plano.slug == slug), None)


def plano_para_mais_marketplaces(plano: Plano) -> Plano | None:
    """O primeiro plano acima deste que conecta mais marketplaces (para Grátis e Essencial, o Pro)."""
    if plano.limite_marketplaces is None:
        return None
    acima = PLANOS[PLANOS.index(plano) + 1 :]
    return next(
        (
            candidato
            for candidato in acima
            if candidato.limite_marketplaces is None or candidato.limite_marketplaces > plano.limite_marketplaces
        ),
        None,
    )
