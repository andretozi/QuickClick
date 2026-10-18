"""
Troca o plano de um vendedor no banco (vendedores.plano), para testar. So roda no PC.

Uso (da raiz):  python -m scripts.trocar_plano --email andretozi95@gmail.com --plano pro
Planos: gratis, essencial, pro, business.

O back le o plano no banco a cada pedido; o front mostra o plano novo ao recarregar a pagina.
"""

import argparse
import sys

from backend.domain.erros import ServicoIndisponivel
from backend.domain.plano import PLANOS, buscar_plano
from backend.infrastructure.banco.models import User, VendedorModel
from backend.infrastructure.configuracao import configuracao
from backend.infrastructure.database import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser(description="Troca o plano de um vendedor (so no PC).")
    parser.add_argument("--email", required=True)
    parser.add_argument("--plano", required=True, choices=[plano.slug for plano in PLANOS])
    args = parser.parse_args()

    if not configuracao().ambiente_local:
        print("Recusado: este script so roda no PC, com QUICKCLICK_AMBIENTE=local no .env.")
        return 1

    plano = buscar_plano(args.plano)
    email = args.email.strip().lower()
    try:
        return _trocar(email, plano)
    except ServicoIndisponivel as erro:
        print(erro.mensagem)
        return 1


def _trocar(email: str, plano) -> int:
    with SessionLocal() as sessao:
        usuario = sessao.query(User).filter_by(email=email).first()
        if usuario is None:
            print(f"Nao achei conta com o email {email}.")
            return 1
        vendedor = sessao.query(VendedorModel).filter_by(id=usuario.id).first()
        if vendedor is None:
            vendedor = VendedorModel(id=usuario.id, nome=usuario.nome or email, plano="gratis")
            sessao.add(vendedor)
        antes = vendedor.plano
        vendedor.plano = plano.slug
        sessao.commit()
        depois = sessao.query(VendedorModel).filter_by(id=usuario.id).one().plano

    print(f"{email}: plano antes = {antes}, plano depois = {depois}")
    print("Recarregue a pagina do site para ver o plano novo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
