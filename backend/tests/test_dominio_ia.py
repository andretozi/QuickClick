"""Domínio da IA (Python puro): estados, cotas, leitura, regra de escrita, canais, preço e atributos do ML."""

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from backend.domain.erros import AnaliseEmAndamento, CotaEsgotada, LimitePorHora
from backend.domain.ia import analise as estados
from backend.domain.ia.analise import Nivel, StatusAnalise
from backend.domain.ia.atributos_ml import (
    AtributoML,
    ligar_por_regra,
    ligar_sugestoes_da_ia,
    obrigatorios_faltando,
)
from backend.domain.ia.canais import aplicar_motivos, canais_candidatos
from backend.domain.ia.capacidade import capacidade_do_plano, garantir_pode_comecar, nivel_efetivo, restantes
from backend.domain.ia.escrita import cortar_titulo, limpar_escrita, problemas_de_escrita, titulo_valido
from backend.domain.ia.fotos import QualidadeFoto, caixa_em_pixels, classificar_qualidade, tamanho_para_lado_maior
from backend.domain.ia.leitura import (
    Cartao,
    Confianca,
    CondicaoProduto,
    OrigemAtributo,
    juntar_leitura_parcial,
    normalizar_confirmacao,
    normalizar_leitura,
)
from backend.domain.ia.pesquisa import chave_da_pesquisa, normalizar_perfil
from backend.domain.ia.preco import (
    Concorrente,
    arredondar_para_vitrine,
    estatistica,
    percentil,
    preco_da_ia_aceitavel,
    preco_sugerido_por_regra,
)

AGORA = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


class TestEstados(unittest.TestCase):
    def test_ordem_inclui_os_estados_da_versao_final(self):
        self.assertLess(estados.posicao(StatusAnalise.PREPARANDO_FOTOS), estados.posicao(StatusAnalise.TRATANDO_FOTOS))
        self.assertLess(estados.posicao(StatusAnalise.VERIFICANDO_FOTOS), estados.posicao(StatusAnalise.LENDO_PRODUTO))

    def test_aguardando_confirmacao_nao_conta_como_em_andamento(self):
        self.assertFalse(estados.esta_em_processamento(StatusAnalise.AGUARDANDO_CONFIRMACAO))
        self.assertTrue(estados.esta_em_processamento(StatusAnalise.LENDO_PRODUTO))

    def test_retomada(self):
        self.assertTrue(estados.pode_retomar(StatusAnalise.INTERROMPIDA))
        self.assertFalse(estados.pode_retomar(StatusAnalise.PRONTA))
        self.assertTrue(estados.retomada_precisa_de_fotos(StatusAnalise.LENDO_PRODUTO, tem_leitura=False))
        self.assertFalse(estados.retomada_precisa_de_fotos(StatusAnalise.ESCREVENDO, tem_leitura=True))
        self.assertEqual(estados.etapa_de_retomada(StatusAnalise.ESCREVENDO, True, True), StatusAnalise.ESCREVENDO)
        self.assertEqual(estados.etapa_de_retomada(StatusAnalise.LENDO_PRODUTO, True, False),
                         StatusAnalise.AGUARDANDO_CONFIRMACAO)
        self.assertEqual(estados.etapa_de_retomada(None, False, False), StatusAnalise.PREPARANDO_FOTOS)

    def test_parada_ha_mais_de_10_minutos(self):
        self.assertTrue(estados.esta_parada(StatusAnalise.ESCREVENDO, AGORA - timedelta(minutes=11), AGORA))
        self.assertFalse(estados.esta_parada(StatusAnalise.ESCREVENDO, AGORA - timedelta(minutes=9), AGORA))
        self.assertFalse(estados.esta_parada(StatusAnalise.AGUARDANDO_CONFIRMACAO, AGORA - timedelta(days=1), AGORA))


class TestCapacidade(unittest.TestCase):
    def test_numeros_por_plano(self):
        self.assertEqual([capacidade_do_plano(p).analises_por_mes for p in ("gratis", "essencial", "pro", "business")],
                         [5, 40, 120, 400])
        self.assertIs(capacidade_do_plano("gratis").nivel, Nivel.GRATIS)
        self.assertIs(capacidade_do_plano("pro").nivel, Nivel.PAGO)
        self.assertFalse(capacidade_do_plano("gratis").pesquisa_de_mercado)
        self.assertTrue(capacidade_do_plano("essencial").preco_com_analise)

    def test_plano_desconhecido_vale_como_gratis(self):
        self.assertIs(capacidade_do_plano("vip").nivel, Nivel.GRATIS)

    def test_restantes_nunca_negativo(self):
        self.assertEqual(restantes(capacidade_do_plano("gratis"), 7), 0)

    def test_limites(self):
        gratis = capacidade_do_plano("gratis")
        garantir_pode_comecar(gratis, usadas_no_mes=4, em_andamento=0, na_ultima_hora=9)
        with self.assertRaises(CotaEsgotada):
            garantir_pode_comecar(gratis, usadas_no_mes=5, em_andamento=0, na_ultima_hora=0)
        with self.assertRaises(AnaliseEmAndamento):
            garantir_pode_comecar(gratis, usadas_no_mes=0, em_andamento=1, na_ultima_hora=0)
        with self.assertRaises(LimitePorHora):
            garantir_pode_comecar(capacidade_do_plano("pro"), usadas_no_mes=0, em_andamento=0, na_ultima_hora=10)

    def test_orcamento_do_dia_estourado_cai_no_gratis(self):
        self.assertEqual(nivel_efetivo(Nivel.PAGO, Decimal("0.31"), Decimal("0.30")), (Nivel.GRATIS, True))
        self.assertEqual(nivel_efetivo(Nivel.PAGO, Decimal("0.10"), Decimal("0.30")), (Nivel.PAGO, False))
        self.assertEqual(nivel_efetivo(Nivel.GRATIS, Decimal("9"), Decimal("0.30")), (Nivel.GRATIS, False))


class TestFotos(unittest.TestCase):
    def test_qualidade(self):
        self.assertIs(classificar_qualidade(400, 900, 120, 200), QualidadeFoto.PEQUENA)
        self.assertIs(classificar_qualidade(1200, 900, 30, 200), QualidadeFoto.ESCURA)
        self.assertIs(classificar_qualidade(1200, 900, 120, 5, borda_forte=10), QualidadeFoto.TREMIDA)
        self.assertIs(classificar_qualidade(1200, 900, 120, 5, borda_forte=200), QualidadeFoto.OK)  # fundo liso, contorno nítido
        self.assertIs(classificar_qualidade(1200, 900, 120, 200), QualidadeFoto.OK)

    def test_redimensionar_nunca_aumenta(self):
        self.assertEqual(tamanho_para_lado_maior(4000, 3000, 1568), (1568, 1176))
        self.assertEqual(tamanho_para_lado_maior(800, 600, 1568), (800, 600))

    def test_caixa_em_pixels_com_folga_e_dentro_da_foto(self):
        x0, y0, x1, y1 = caixa_em_pixels((0, 100, 500, 1000), 2000, 1000)
        self.assertEqual((x0, y0), (0, 64))  # 100 menos 4% de 900
        self.assertLessEqual(x1, 2000)
        self.assertEqual(y1, 1000)


LEITURA_BRUTA = {
    "reconhecido": True,
    "motivo_nao_reconhecido": "",
    "produto": "  Tênis   de corrida ",
    "categoria": "calcados",
    "termos_busca": ["tenis corrida", "tenis corrida", "tenis esportivo", "a", "b", "c"],
    "atributos": [
        {"chave": "Marca", "valor": "Nike", "origem": "foto", "evidencia": "logo na lateral", "confianca": "alta"},
        {"chave": "tamanho", "valor": "42", "origem": "deducao", "evidencia": "parece grande", "confianca": "alta"},
        {"chave": "cor", "valor": "azul", "origem": "deducao", "evidencia": "cor do cabedal", "confianca": "alta"},
        {"chave": "voltagem", "valor": "", "origem": "foto", "evidencia": "", "confianca": "alta"},
        {"chave": "modelo", "valor": "Pegasus 40", "origem": "etiqueta", "evidencia": "etiqueta interna",
         "confianca": "media"},
    ],
    "condicao": {"valor": "usado", "sinais": ["sola gasta"], "confianca": "alta"},
    "defeitos_visiveis": ["risco no bico"],
    "texto_legivel": ["NIKE"],
    "etiqueta_ilegivel": [{"foto": 0, "caixa": [100, 100, 300, 250]}, {"foto": 0, "caixa": [10, 10, 2000, 50]},
                          {"foto": 9, "caixa": [1, 1, 2, 2]}],
    "perguntas": [{"chave": "tamanho", "pergunta": "Qual é a numeração?", "sugerir_foto": "etiqueta"}],
}


class TestLeitura(unittest.TestCase):
    def setUp(self):
        self.leitura = normalizar_leitura(LEITURA_BRUTA, quantidade_fotos=3)

    def test_textos_limpos_e_termos_sem_repetir(self):
        self.assertEqual(self.leitura.produto, "Tênis de corrida")
        self.assertEqual(self.leitura.termos_busca, ("tenis corrida", "tenis esportivo", "a", "b"))

    def test_marca_com_logo_vale_e_vira_a_ia_viu(self):
        marca = self.leitura.atributo("marca")
        self.assertEqual((marca.valor, marca.cartao), ("Nike", Cartao.VIU))

    def test_tamanho_por_deducao_nao_vale_e_vira_pergunta(self):
        tamanho = self.leitura.atributo("tamanho")
        self.assertEqual((tamanho.valor, tamanho.origem, tamanho.cartao), ("", OrigemAtributo.DESCONHECIDO, Cartao.PERGUNTA))
        self.assertIn("tamanho", [p.chave for p in self.leitura.perguntas])
        self.assertEqual(next(p for p in self.leitura.perguntas if p.chave == "tamanho").pergunta, "Qual é a numeração?")

    def test_deducao_nunca_sai_com_confianca_alta(self):
        cor = self.leitura.atributo("cor")
        self.assertEqual((cor.confianca, cor.cartao), (Confianca.MEDIA, Cartao.CONFERE))

    def test_valor_vazio_vira_desconhecido_com_pergunta_padrao(self):
        self.assertEqual(self.leitura.atributo("voltagem").cartao, Cartao.PERGUNTA)
        pergunta = next(p for p in self.leitura.perguntas if p.chave == "voltagem")
        self.assertEqual(pergunta.pergunta, "Qual é a voltagem do produto?")

    def test_etiqueta_com_confianca_media_e_confere(self):
        self.assertEqual(self.leitura.atributo("modelo").cartao, Cartao.CONFERE)

    def test_caixas_fora_do_intervalo_ou_de_foto_inexistente_saem(self):
        self.assertEqual([e.caixa for e in self.leitura.etiqueta_ilegivel], [(100, 100, 300, 250)])

    def test_produto_nao_reconhecido_sem_atributos(self):
        leitura = normalizar_leitura({**LEITURA_BRUTA, "reconhecido": False, "motivo_nao_reconhecido": "paisagem"}, 3)
        self.assertEqual((leitura.atributos, leitura.motivo_nao_reconhecido), ((), "paisagem"))

    def test_condicao_tem_campo_proprio_e_nao_vira_atributo_nem_pergunta(self):
        bruto = {**LEITURA_BRUTA,
                 "atributos": [*LEITURA_BRUTA["atributos"], {"chave": "condicao", "valor": "usado", "origem": "foto",
                                                             "evidencia": "", "confianca": "alta"}],
                 "perguntas": [{"chave": "condicao", "pergunta": "Está novo?", "sugerir_foto": "nenhuma"}]}
        leitura = normalizar_leitura(bruto, 3)
        self.assertIsNone(leitura.atributo("condicao"))
        self.assertNotIn("condicao", [p.chave for p in leitura.perguntas])

    def test_categoria_fora_da_lista_vira_outros(self):
        self.assertEqual(normalizar_leitura({**LEITURA_BRUTA, "categoria": "carros"}, 1).categoria, "outros")

    def test_dict_tem_o_cartao_de_cada_atributo(self):
        dados = self.leitura.para_dict()
        self.assertEqual(dados["atributos"][0]["cartao"], "a_ia_viu")
        self.assertEqual(normalizar_leitura(dados, 3), self.leitura)  # volta igual do banco

    def test_releitura_da_etiqueta_preenche_o_que_faltava(self):
        etiqueta = {"texto_legivel": ["TAM 42 BR"], "atributos": [
            {"chave": "tamanho", "valor": "42", "origem": "etiqueta", "evidencia": "TAM 42 BR", "confianca": "alta"},
            {"chave": "marca", "valor": "Outra", "origem": "etiqueta", "evidencia": "", "confianca": "media"},
        ]}
        junta = juntar_leitura_parcial(self.leitura, etiqueta, OrigemAtributo.ETIQUETA)
        self.assertEqual(junta.atributo("tamanho").valor, "42")
        self.assertEqual(junta.atributo("tamanho").cartao, Cartao.VIU)
        self.assertEqual(junta.atributo("marca").valor, "Nike")  # o que a IA já viu com certeza fica
        self.assertNotIn("tamanho", [p.chave for p in junta.perguntas])
        self.assertIn("TAM 42 BR", junta.texto_legivel)


class TestConfirmacao(unittest.TestCase):
    def test_so_entra_o_que_tem_valor_e_categoria_cai_na_lida(self):
        leitura = normalizar_leitura(LEITURA_BRUTA, 3)
        confirmacao = normalizar_confirmacao({
            "atributos": [{"chave": "Marca", "valor": "Nike"}, {"chave": "cor", "valor": ""}],
            "condicao": "usado", "categoria": "carros", "defeitos": ["risco no bico"],
        }, leitura)
        self.assertEqual([(a.chave, a.valor) for a in confirmacao.atributos], [("marca", "Nike")])
        self.assertEqual((confirmacao.categoria, confirmacao.condicao), ("calcados", CondicaoProduto.USADO))
        self.assertEqual(confirmacao.produto, "Tênis de corrida")


class TestEscrita(unittest.TestCase):
    def test_texto_bom_passa(self):
        texto = "Tênis de corrida usado, com USB-C não.\n\nMarca: Nike\nTamanho: 42\nCor: Azul"
        self.assertEqual(problemas_de_escrita(texto), [])

    def test_acha_cada_tipo_de_problema(self):
        texto = "Ótimo 😀 produto — bivolt 110/220V - leve\n- item com marcador\n1. outro"
        tipos = {p.tipo for p in problemas_de_escrita(texto)}
        self.assertEqual(tipos, {"emoji", "travessao", "barra", "hifen", "marcador"})

    def test_meia_risca(self):
        self.assertEqual([p.tipo for p in problemas_de_escrita("de 10 – 20")], ["travessao"])

    def test_mais_de_5_especificacoes(self):
        texto = "\n".join(f"Item {i}: valor" for i in range(6))
        self.assertIn("especificacoes", {p.tipo for p in problemas_de_escrita(texto)})

    def test_limpeza_deterministica_resolve_tudo(self):
        texto = "Ótimo 😀 produto — bivolt 110/220V - leve\n- item com marcador\n1. outro"
        limpo = limpar_escrita(texto)
        self.assertEqual(problemas_de_escrita(limpo), [], limpo)
        self.assertIn("110 ou 220V", limpo)
        self.assertNotIn("😀", limpo)

    def test_titulo_cortado_na_ultima_palavra(self):
        titulo = "Tênis de corrida masculino azul tamanho quarenta e dois original"
        cortado = cortar_titulo(titulo)
        self.assertLessEqual(len(cortado), 60)
        self.assertTrue(titulo.startswith(cortado))
        self.assertFalse(cortado.endswith(" "))
        self.assertEqual(titulo_valido("Fone 😀 Bluetooth / sem fio"), "Fone Bluetooth ou sem fio")


class TestCanais(unittest.TestCase):
    def test_conectados_primeiro_e_depois_os_que_combinam(self):
        canais = canais_candidatos(["mercado-livre"], "moda", 9000, "novo")
        self.assertEqual(canais[0].slug, "mercado-livre")
        self.assertTrue(canais[0].conectado)
        sugeridos = [c.slug for c in canais[1:]]
        self.assertIn("shopee", sugeridos)
        self.assertIn("shein", sugeridos)
        self.assertNotIn("casas-bahia", sugeridos)
        self.assertLessEqual(len(sugeridos), 4)

    def test_usado_nao_vai_para_quem_nao_aceita_usado(self):
        sugeridos = [c.slug for c in canais_candidatos([], "eletronicos", 50000, "usado")]
        self.assertIn("mercado-livre", sugeridos)
        self.assertNotIn("amazon", sugeridos)

    def test_preco_fora_da_faixa(self):
        self.assertNotIn("shein", [c.slug for c in canais_candidatos([], "moda", 90000, "novo")])

    def test_motivo_da_ia_so_nos_canais_da_lista(self):
        canais = aplicar_motivos(canais_candidatos(["mercado-livre"], "moda", 9000, "novo"),
                                 {"mercado-livre": "Maior público.", "inventado": "x"})
        self.assertEqual(canais[0].motivo, "Maior público.")
        self.assertNotIn("inventado", [c.slug for c in canais])


class TestPreco(unittest.TestCase):
    def test_percentil_linear(self):
        self.assertEqual(percentil([10, 20, 30, 40], 0.5), 25)

    def test_tira_fora_da_curva_e_calcula(self):
        concorrentes = [Concorrente(p, p > 10000) for p in (9000, 9500, 10000, 10500, 11000, 12000, 99000)]
        est = estatistica(concorrentes)
        self.assertEqual(est.descartados, 1)
        self.assertEqual(est.quantidade, 6)
        self.assertEqual(est.mediana, 10250)
        self.assertEqual(est.com_frete_gratis, 3)
        self.assertEqual(est.maximo, 12000)

    def test_poucos_itens_sem_estatistica(self):
        self.assertIsNone(estatistica([Concorrente(1000, False), Concorrente(1100, False)]))

    def test_sugerido_por_condicao(self):
        est = estatistica([Concorrente(p, False) for p in (8000, 9000, 10000, 11000, 12000)])
        self.assertEqual(preco_sugerido_por_regra(est, "novo"), 10090)
        self.assertEqual(preco_sugerido_por_regra(est, "usado"), 9590)

    def test_vitrine_e_preco_da_ia(self):
        self.assertEqual(arredondar_para_vitrine(18734), 18790)
        self.assertEqual(arredondar_para_vitrine(534), 530)
        est = estatistica([Concorrente(p, False) for p in (8000, 9000, 10000, 11000, 12000)])
        self.assertTrue(preco_da_ia_aceitavel(10500, est))
        self.assertFalse(preco_da_ia_aceitavel(50000, est))


class TestPesquisa(unittest.TestCase):
    def test_chave_por_categoria_ou_produto(self):
        self.assertEqual(chave_da_pesquisa("pago", "MLB1276", "Tênis", "usado"), "pago:MLB1276:usado")
        self.assertEqual(chave_da_pesquisa("gratis", None, "Tênis de Corrida!", "novo"), "gratis:tenis_de_corrida:novo")

    def test_perfil_so_aceita_fontes_http(self):
        perfil = normalizar_perfil({"perfil_comprador": "Corredor amador.", "fontes": ["https://a.com", "javascript:x"],
                                    "o_que_valoriza": ["leveza"] * 3})
        self.assertEqual(perfil.fontes, ("https://a.com",))
        self.assertEqual(perfil.o_que_valoriza, ("leveza",))


class TestAtributosML(unittest.TestCase):
    CATEGORIA = [
        AtributoML("BRAND", "Marca", True),
        AtributoML("MODEL", "Modelo", True),
        AtributoML("COLOR", "Cor", False, (("52049", "Azul"), ("52005", "Preto"))),
        AtributoML("SIZE", "Tamanho", True),
        AtributoML("SOLE_MATERIAL", "Material da sola", False),
    ]

    def test_liga_por_sinonimo_e_nome_e_acha_o_id_do_valor(self):
        ligados, sobras = ligar_por_regra([("marca", "Nike"), ("cor", "azul"), ("material_da_sola", "Borracha"),
                                           ("estilo", "casual")], self.CATEGORIA)
        self.assertEqual({l.id: (l.valor, l.valor_id) for l in ligados},
                         {"BRAND": ("Nike", None), "COLOR": ("azul", "52049"), "SOLE_MATERIAL": ("Borracha", None)})
        self.assertEqual(sobras, [("estilo", "casual")])
        self.assertEqual(ligados[1].para_api(), {"id": "COLOR", "value_id": "52049"})

    def test_ia_so_liga_ids_que_existem_e_estao_livres(self):
        ligados, sobras = ligar_por_regra([("marca", "Nike")], self.CATEGORIA)
        extras = ligar_sugestoes_da_ia([{"chave": "linha", "id_ml": "MODEL"}, {"chave": "linha", "id_ml": "BRAND"},
                                        {"chave": "x", "id_ml": "INVENTADO"}],
                                       [("linha", "Pegasus")], self.CATEGORIA, ligados)
        self.assertEqual([(e.id, e.valor) for e in extras], [("MODEL", "Pegasus")])

    def test_obrigatorios_que_faltam(self):
        ligados, _ = ligar_por_regra([("marca", "Nike")], self.CATEGORIA)
        self.assertEqual([a.id for a in obrigatorios_faltando(self.CATEGORIA, ligados)], ["MODEL", "SIZE"])

    def test_de_api(self):
        bruto = {"id": "BRAND", "name": "Marca", "tags": {"required": True}, "values": [{"id": "1", "name": "Nike"}]}
        self.assertEqual(AtributoML.de_api(bruto), AtributoML("BRAND", "Marca", True, (("1", "Nike"),)))


if __name__ == "__main__":
    unittest.main()
