"""Regra de negócio do limite de marketplaces por plano."""

import re
import unittest

from backend.domain.erros import LimiteDoPlanoAtingido
from backend.domain.ia.capacidade import ANALISES_POR_MES
from pathlib import Path

from backend.domain.plano import (
    BUSINESS,
    ESSENCIAL,
    GRATIS,
    GRATIS_CONECTA_VARIOS_PROVISORIO,
    PLANOS,
    PRO,
    buscar_plano,
    plano_para_mais_marketplaces,
)

RAIZ = Path(__file__).resolve().parents[2]
CONTEUDO_DA_LANDING = "frontend/src/domain/content/landingContent.js"

# Regra de escrita dos textos de tela: sem travessão, meia risca, barra ou hífen (exceto NF-e)
FORA_DA_REGRA = re.compile(r"[—–/]|\s-\s|\w-\w")


class TestLimiteDoPlano(unittest.TestCase):
    def test_essencial_conecta_um_marketplace(self):
        self.assertEqual(ESSENCIAL.limite_marketplaces, 1)
        self.assertTrue(ESSENCIAL.permite_conectar(0))
        self.assertFalse(ESSENCIAL.permite_conectar(1))
        self.assertFalse(ESSENCIAL.multicanal)

    def test_gratis_segue_a_regra_provisoria(self):
        """Provisório: o Grátis conecta vários. Voltar ao limite de 1 é trocar a constante (e o card, e o front)."""
        self.assertEqual(GRATIS.limite_marketplaces, None if GRATIS_CONECTA_VARIOS_PROVISORIO else 1)
        self.assertEqual(GRATIS.permite_conectar(5), GRATIS_CONECTA_VARIOS_PROVISORIO)

    def test_front_espelha_a_regra_provisoria_do_gratis(self):
        regras = (RAIZ / "frontend/src/domain/plans/planRules.js").read_text(encoding="utf-8")
        valor = re.search(r"const FREE_CONNECTS_MANY = (true|false);", regras).group(1)
        self.assertEqual(valor == "true", GRATIS_CONECTA_VARIOS_PROVISORIO)
        cartao = re.search(r"id: 'gratis'.*?features: \[(.*?)\]", (RAIZ / CONTEUDO_DA_LANDING).read_text(encoding="utf-8"),
                           re.S).group(1)
        self.assertEqual("1 marketplace" in cartao, not GRATIS_CONECTA_VARIOS_PROVISORIO)

    def test_pro_e_business_conectam_varios(self):
        for plano in (PRO, BUSINESS):
            with self.subTest(plano=plano.nome):
                for conectados in (0, 1, 2, 3, 9, 50):
                    self.assertTrue(plano.permite_conectar(conectados))
                self.assertTrue(plano.multicanal)

    def test_multicanal_comeca_no_pro(self):
        self.assertEqual(plano_para_mais_marketplaces(GRATIS), None if GRATIS_CONECTA_VARIOS_PROVISORIO else PRO)
        self.assertEqual(plano_para_mais_marketplaces(ESSENCIAL), PRO)
        self.assertIsNone(plano_para_mais_marketplaces(PRO))
        self.assertIsNone(plano_para_mais_marketplaces(BUSINESS))

    def test_garantir_vaga_deixa_passar_quando_cabe(self):
        GRATIS.garantir_vaga(0)
        ESSENCIAL.garantir_vaga(0)
        PRO.garantir_vaga(10)
        BUSINESS.garantir_vaga(10)

    def test_limite_atingido_diz_em_qual_plano_da_pra_conectar_mais(self):
        for plano in (p for p in (GRATIS, ESSENCIAL) if p.limite_marketplaces == 1):
            with self.subTest(plano=plano.nome):
                with self.assertRaises(LimiteDoPlanoAtingido) as contexto:
                    plano.garantir_vaga(1)
                erro = contexto.exception
                self.assertEqual(erro.codigo, "limite_do_plano")
                self.assertEqual(erro.plano_sugerido, PRO)
                self.assertEqual(
                    erro.mensagem,
                    f"No plano {plano.nome} você conecta 1 marketplace. Pra conectar mais, mude para o plano Pro.",
                )
                self.assertIsNone(FORA_DA_REGRA.search(erro.mensagem))


class TestCatalogoDePlanos(unittest.TestCase):
    def test_ordem_do_mais_simples_ao_mais_completo(self):
        self.assertEqual([plano.slug for plano in PLANOS], ["gratis", "essencial", "pro", "business"])
        self.assertEqual([plano.nome for plano in PLANOS], ["Grátis", "Essencial", "Pro", "Business"])

    def test_gratis_custa_zero_e_os_pagos_tem_preco_crescente(self):
        self.assertEqual(GRATIS.preco_mensal_centavos, 0)
        precos = [plano.preco_mensal_centavos for plano in (ESSENCIAL, PRO, BUSINESS)]
        for preco in precos:
            self.assertGreater(preco, 0)
        self.assertEqual(precos, sorted(set(precos)))  # Essencial < Pro < Business, sem empate

    def test_cards_do_front_repetem_preco_e_analises_do_back(self):
        conteudo = (RAIZ / CONTEUDO_DA_LANDING).read_text(encoding="utf-8")
        self.assertNotIn("R$ __", conteudo)
        self.assertIn("const BILLING_NOTE = 'Cobrança ainda não ativada';", conteudo)
        for plano in PLANOS:
            with self.subTest(plano=plano.nome):
                card = re.search(rf"id: '{plano.slug}',(.*?)cta:", conteudo, re.S).group(1)
                texto = re.search(r"price: 'R\$ ([\d.]+),(\d{2})'", card)
                centavos = int(texto.group(1).replace(".", "")) * 100 + int(texto.group(2)) if texto else 0
                self.assertEqual(centavos, plano.preco_mensal_centavos)
                self.assertEqual("billingNote: BILLING_NOTE" in card, plano.preco_mensal_centavos > 0)
                self.assertIn(f"{ANALISES_POR_MES[plano.slug]} análises de IA por mês", card)

    def test_buscar_plano(self):
        self.assertEqual(buscar_plano("pro"), PRO)
        self.assertIsNone(buscar_plano("premium"))


if __name__ == "__main__":
    unittest.main()
