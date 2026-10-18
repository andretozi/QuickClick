"""
Infraestrutura · IA · Tratamento de foto no MVP: nenhum (encaixe pronto para a versão final)

Na versão final entram o tratamento (Nano Banana, fundo branco na capa, 2K, 1:1, preservando forma,
cores, textos, logos e todos os defeitos; reserva com Pillow) e o guardião da fidelidade (Sonnet 5.5
comparando original e tratada). Ver a seção "Versão final" do .claude/progresso-ia.md.
"""

from backend.application.ia.modelos import ContextoDaChamada, Fidelidade, FotoPreparada


class SemTratamento:
    """TratadorDeFoto do MVP: devolve a mesma foto, sem custo."""

    def tratar(self, foto: FotoPreparada, contexto: ContextoDaChamada) -> FotoPreparada:
        return foto


class SemVerificacaoDeFidelidade:
    """GuardiaoDeFidelidade do MVP: sem tratamento, nada a comparar."""

    def verificar(self, original: FotoPreparada, tratada: FotoPreparada, contexto: ContextoDaChamada) -> Fidelidade:
        return Fidelidade.NAO_VERIFICADA
