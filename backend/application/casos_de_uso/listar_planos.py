"""Aplicação · Listar os planos de assinatura, do Grátis ao Business."""

from backend.domain.plano import PLANOS, Plano


class ListarPlanos:
    def executar(self) -> tuple[Plano, ...]:
        return PLANOS
