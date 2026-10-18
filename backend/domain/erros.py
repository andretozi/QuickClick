"""
Domínio · Erros de negócio

Cada erro tem um código estável (para quem consome a API) e uma mensagem amigável,
que aparece na tela do vendedor. Por isso as mensagens seguem a regra de escrita:
sem traço e sem barra.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.domain.plano import Plano


def juntar_nomes(nomes: Sequence[str]) -> str:
    """["Mercado Livre", "Shopee", "Amazon"] vira "Mercado Livre, Shopee e Amazon"."""
    if len(nomes) <= 1:
        return "".join(nomes)
    return f"{', '.join(nomes[:-1])} e {nomes[-1]}"


class ErroDeDominio(Exception):
    codigo = "erro_de_negocio"

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class VendedorNaoEncontrado(ErroDeDominio):
    codigo = "vendedor_nao_encontrado"

    def __init__(self, vendedor_id: int):
        super().__init__("Não encontramos a sua conta de vendedor.")
        self.vendedor_id = vendedor_id


class MarketplaceNaoEncontrado(ErroDeDominio):
    codigo = "marketplace_nao_encontrado"

    def __init__(self, slug: str):
        super().__init__("Esse marketplace não existe no nosso catálogo.")
        self.slug = slug


class MarketplaceEmBreve(ErroDeDominio):
    codigo = "marketplace_em_breve"

    def __init__(self, nome: str, disponiveis: Sequence[str]):
        super().__init__(
            f"A integração com {nome} ainda está chegando. "
            f"Por enquanto dá pra conectar {juntar_nomes(disponiveis)}."
        )
        self.nome = nome


class LimiteDoPlanoAtingido(ErroDeDominio):
    codigo = "limite_do_plano"

    def __init__(self, plano: Plano, plano_sugerido: Plano | None):
        limite = plano.limite_marketplaces
        quantidade = f"{limite} marketplace" if limite == 1 else f"{limite} marketplaces"
        mensagem = f"No plano {plano.nome} você conecta {quantidade}."
        if plano_sugerido is not None:
            mensagem += f" Pra conectar mais, mude para o plano {plano_sugerido.nome}."
        super().__init__(mensagem)
        self.plano = plano
        self.plano_sugerido = plano_sugerido


class NaoAutenticado(ErroDeDominio):
    codigo = "nao_autenticado"

    def __init__(self, mensagem: str = "Autenticação necessária para acessar este recurso."):
        super().__init__(mensagem)


class CredenciaisInvalidas(ErroDeDominio):
    codigo = "credenciais_invalidas"

    def __init__(self, mensagem: str = "Email ou senha incorretos."):
        super().__init__(mensagem)


class MuitasTentativas(ErroDeDominio):
    codigo = "muitas_tentativas"

    def __init__(self, mensagem: str = "Muitas tentativas seguidas. Aguarde alguns minutos e tente novamente."):
        super().__init__(mensagem)


class EmailJaCadastrado(ErroDeDominio):
    codigo = "email_em_uso"

    def __init__(self, mensagem: str = "Este email já está cadastrado."):
        super().__init__(mensagem)


class TokenInvalido(ErroDeDominio):
    codigo = "token_invalido"

    def __init__(self, mensagem: str = "Token de autenticação inválido ou expirado."):
        super().__init__(mensagem)


class CotaEsgotada(ErroDeDominio):
    codigo = "cota_esgotada"

    def __init__(self, limite: int):
        super().__init__(
            f"Você já usou as {limite} análises de IA do mês. Dá pra terminar o anúncio à mão, "
            "ou mudar de plano para ter mais."
        )
        self.limite = limite


class LimitePorHora(ErroDeDominio):
    codigo = "limite_por_hora"

    def __init__(self, limite: int):
        super().__init__(f"Você fez {limite} análises na última hora. Espera um pouco e tenta de novo.")


class AnaliseEmAndamento(ErroDeDominio):
    codigo = "analise_em_andamento"

    def __init__(self):
        super().__init__("Já tem uma análise rodando. Espera ela terminar para começar outra.")


class IAIndisponivel(ErroDeDominio):
    codigo = "ia_indisponivel"

    def __init__(self, mensagem: str = "A IA está fora do ar agora. Você pode preencher o anúncio à mão."):
        super().__init__(mensagem)


class FotoInvalida(ErroDeDominio):
    codigo = "foto_invalida"

    def __init__(self, mensagem: str = "Não deu pra abrir essa foto. Use JPEG, PNG ou WEBP de até 10 MB."):
        super().__init__(mensagem)


class FotosNecessarias(ErroDeDominio):
    codigo = "fotos_necessarias"

    def __init__(self, mensagem: str = "Manda as fotos de novo para continuar a análise."):
        super().__init__(mensagem)


class ProdutoNaoReconhecido(ErroDeDominio):
    codigo = "produto_nao_reconhecido"

    def __init__(self):
        super().__init__("Não consegui reconhecer o produto nessa foto. Preencha os campos à mão.")


class MercadoLivreDesconectado(ErroDeDominio):
    codigo = "mercado_livre_desconectado"

    def __init__(self):
        super().__init__("Conecte sua conta do Mercado Livre para publicar e ver os preços da concorrência.")


class AnaliseNaoEncontrada(ErroDeDominio):
    codigo = "analise_nao_encontrada"

    def __init__(self):
        super().__init__("Não encontramos essa análise. Comece uma nova.")


class AnuncioNaoEncontrado(ErroDeDominio):
    codigo = "anuncio_nao_encontrado"

    def __init__(self):
        super().__init__("Não encontramos esse anúncio na sua conta do Mercado Livre.")


class EstadoDaAnaliseInvalido(ErroDeDominio):
    codigo = "estado_da_analise_invalido"

    def __init__(self, mensagem: str = "Essa análise não está esperando esse passo agora."):
        super().__init__(mensagem)


class PublicacaoRecusada(ErroDeDominio):
    """O marketplace recusou o anúncio. `detalhes` traz as causas que ele mandou (texto dele, não nosso)."""

    codigo = "publicacao_recusada"

    def __init__(self, detalhes: Sequence[str] = ()):
        super().__init__("O Mercado Livre recusou o anúncio. Confira os dados e tente de novo.")
        self.detalhes = list(detalhes)

    @property
    def extras(self) -> dict:
        return {"detalhes": self.detalhes} if self.detalhes else {}


class PlanoInvalido(ErroDeDominio):
    codigo = "plano_invalido"

    def __init__(self):
        super().__init__("Esse plano não existe. Escolha Grátis, Essencial, Pro ou Business.")


class TrocaDePlanoIndisponivel(ErroDeDominio):
    """A troca livre (sem pagamento) está desligada: ela volta junto com o pagamento, na versão final."""

    codigo = "troca_de_plano_indisponivel"

    def __init__(self):
        super().__init__("A troca de plano vai chegar junto com o pagamento. Por enquanto, fica o plano atual.")


class MaioridadeNaoConfirmada(ErroDeDominio):
    codigo = "maioridade_obrigatoria"

    def __init__(self):
        super().__init__("Para criar a conta, confirme que você tem 18 anos ou mais.")


class ServicoIndisponivel(ErroDeDominio):
    """Uma peça de fora (banco, chave, marketplace) não está configurada ou não responde."""

    codigo = "servico_indisponivel"

    def __init__(self, mensagem: str = "Esse serviço está fora do ar agora. Tente de novo em instantes."):
        super().__init__(mensagem)
