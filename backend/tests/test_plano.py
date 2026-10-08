"""Regra de negócio do limite de marketplaces por plano."""

import re
import unittest

from backend.domain.erros import LimiteDoPlanoAtingido
from backend.domain.plano import BUSINESS, ESSENCIAL, GRATIS, PLANOS, PRO, buscar_plano, plano_para_mais_marketplaces

# Regra de escrita dos textos de tela: sem travessão, meia risca, barra ou hífen (exceto NF-e)
FORA_DA_REGRA = re.compile(r"[—–/]|\s-\s|\w-\w")


class TestLimiteDoPlano(unittest.TestCase):
    def test_gratis_e_essencial_conectam_um_marketplace(self):
        for plano in (GRATIS, ESSENCIAL):
            with self.subTest(plano=plano.nome):
                self.assertEqual(plano.limite_marketplaces, 1)
                self.assertTrue(plano.permite_conectar(0))
                self.assertFalse(plano.permite_conectar(1))
                self.assertFalse(plano.multicanal)

    def test_pro_e_business_conectam_varios(self):
        for plano in (PRO, BUSINESS):
            with self.subTest(plano=plano.nome):
                for conectados in (0, 1, 2, 3, 9, 50):
                    self.assertTrue(plano.permite_conectar(conectados))
                self.assertTrue(plano.multicanal)

    def test_multicanal_comeca_no_pro(self):
        self.assertEqual(plano_para_mais_marketplaces(GRATIS), PRO)
        self.assertEqual(plano_para_mais_marketplaces(ESSENCIAL), PRO)
        self.assertIsNone(plano_para_mais_marketplaces(PRO))
        self.assertIsNone(plano_para_mais_marketplaces(BUSINESS))

    def test_garantir_vaga_deixa_passar_quando_cabe(self):
        GRATIS.garantir_vaga(0)
        ESSENCIAL.garantir_vaga(0)
        PRO.garantir_vaga(10)
        BUSINESS.garantir_vaga(10)

    def test_limite_atingido_diz_em_qual_plano_da_pra_conectar_mais(self):
        for plano in (GRATIS, ESSENCIAL):
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

    def test_gratis_custa_zero_e_os_pagos_ainda_nao_tem_preco(self):
        self.assertEqual(GRATIS.preco_mensal_centavos, 0)
        for plano in (ESSENCIAL, PRO, BUSINESS):
            self.assertIsNone(plano.preco_mensal_centavos)

    def test_buscar_plano(self):
        self.assertEqual(buscar_plano("pro"), PRO)
        self.assertIsNone(buscar_plano("premium"))


if __name__ == "__main__":
    unittest.main()
