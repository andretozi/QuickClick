"""Modelo genérico dos canais: esquema do Mercado Livre, ficha do produto (leitura e confirmação) e GTIN."""

import unittest

from backend.domain.canais.esquema import TipoDeCampo
from backend.domain.canais.ficha import Embalagem, Identificacao, gtin_valido, montar_ficha, normalizar_gtin
from backend.domain.ia.atributos_ml import AtributoML, esquema_do_ml
from backend.domain.ia.leitura import (
    Confianca,
    CondicaoProduto,
    OrigemAtributo,
    normalizar_confirmacao,
    normalizar_leitura,
)

ATRIBUTOS_DA_API = [
    {"id": "BRAND", "name": "Marca", "tags": {"required": True}},
    {"id": "GTIN", "name": "Código universal de produto", "tags": {"catalog_required": True}},
    {"id": "COLOR", "name": "Cor", "values": [{"id": "52049", "name": "Preto"}, {"id": "52055", "name": "Branco"}]},
    {"id": "MAIN_COLOR", "name": "Cor principal", "values": [{"id": "2450295", "name": "Azul"}]},
    {"id": "VOLUME_CAPACITY", "name": "Capacidade em volume", "default_unit": "mL"},
]

LEITURA_BRUTA = {
    "reconhecido": True,
    "produto": "Tênis de corrida",
    "categoria": "calcados",
    "condicao": {"valor": "usado", "confianca": "media"},
    "atributos": [
        {"chave": "marca", "valor": "Nike", "origem": "foto", "evidencia": "logo na lateral", "confianca": "alta"},
        {"chave": "cor", "valor": "Azul marinho", "origem": "foto", "evidencia": "cabedal", "confianca": "media"},
        {"chave": "material", "valor": "Couro", "origem": "deducao", "evidencia": "textura", "confianca": "baixa"},
        {"chave": "tamanho", "valor": "", "origem": "desconhecido", "evidencia": "", "confianca": "baixa"},
        {"chave": "modelo", "valor": "Pegasus", "origem": "etiqueta", "evidencia": "lingueta", "confianca": "alta"},
    ],
}

CONFIRMACAO_BRUTA = {
    "produto": "Tênis Nike Pegasus",
    "categoria": "esporte",
    "condicao": "novo",
    "atributos": [
        {"chave": "cor", "valor": "AZUL   marinho"},  # mesmo valor da leitura, outra caixa e espaços
        {"chave": "marca", "valor": "Adidas"},  # o vendedor mudou
        {"chave": "genero", "valor": "Masculino"},  # o vendedor acrescentou
    ],
}


class TestEsquemaDoML(unittest.TestCase):
    def setUp(self):
        atributos = [AtributoML.de_api(a) for a in ATRIBUTOS_DA_API]
        self.esquema = esquema_do_ml("MLB23262", "Tênis", atributos)
        self.campos = {c.id: c for c in self.esquema.campos}

    def test_campos_na_ordem_com_canal_e_categoria(self):
        self.assertEqual([c.id for c in self.esquema.campos],
                         ["BRAND", "GTIN", "COLOR", "MAIN_COLOR", "VOLUME_CAPACITY"])
        self.assertEqual((self.esquema.canal, self.esquema.categoria_id, self.esquema.categoria_nome),
                         ("mercado-livre", "MLB23262", "Tênis"))
        self.assertTrue(all(c.canal == "mercado-livre" for c in self.esquema.campos))

    def test_tipo_obrigatorio_valores_unidade_e_chave(self):
        marca = self.campos["BRAND"]
        self.assertEqual((marca.obrigatorio, marca.tipo, marca.chave, marca.nome), (True, TipoDeCampo.TEXTO, "marca", "Marca"))
        self.assertTrue(self.campos["GTIN"].obrigatorio)  # só catalog_required
        cor = self.campos["COLOR"]
        self.assertEqual((cor.obrigatorio, cor.tipo, cor.chave), (False, TipoDeCampo.LISTA, "cor"))
        self.assertEqual(cor.valores, (("52049", "Preto"), ("52055", "Branco")))
        self.assertEqual((self.campos["MAIN_COLOR"].tipo, self.campos["MAIN_COLOR"].chave), (TipoDeCampo.LISTA, "cor"))
        volume = self.campos["VOLUME_CAPACITY"]
        self.assertEqual((volume.tipo, volume.unidade, volume.chave), (TipoDeCampo.NUMERO, "mL", "capacidade"))

    def test_obrigatorios_e_por_chave(self):
        self.assertEqual([c.id for c in self.esquema.obrigatorios()], ["BRAND", "GTIN"])
        self.assertEqual([c.id for c in self.esquema.por_chave()["cor"]], ["COLOR", "MAIN_COLOR"])

    def test_sem_atributos(self):
        esquema = esquema_do_ml("MLB1", "", [])
        self.assertEqual((esquema.campos, esquema.obrigatorios(), esquema.por_chave()), ((), (), {}))

    def test_value_type_do_ml_define_o_tipo_e_os_valores_ficam(self):
        sim_nao = [{"id": "242085", "name": "Sim"}, {"id": "242084", "name": "Não"}]
        brutos = [
            {"id": "IS_KIT", "name": "É kit", "value_type": "boolean", "values": sim_nao},
            {"id": "WEIGHT", "name": "Peso", "value_type": "number_unit", "default_unit": "g"},
            {"id": "UNITS", "name": "Unidades", "value_type": "number"},
            {"id": "GENDER", "name": "Gênero", "value_type": "list", "values": [{"id": "1", "name": "Masculino"}]},
            {"id": "BRAND", "name": "Marca", "value_type": "string", "values": [{"id": "9", "name": "Nike"}]},
            {"id": "OLD", "name": "Antigo", "values": [{"id": "1", "name": "A"}]},  # cache antigo, sem value_type
            {"id": "GRID", "name": "Grade", "value_type": "grid_id", "default_unit": "cm"},  # tipo desconhecido
        ]
        campos = esquema_do_ml("MLB1", "", [AtributoML.de_api(b) for b in brutos]).campos
        self.assertEqual([(c.id, c.tipo, c.unidade) for c in campos], [
            ("IS_KIT", TipoDeCampo.BOOLEANO, ""), ("WEIGHT", TipoDeCampo.NUMERO, "g"), ("UNITS", TipoDeCampo.NUMERO, ""),
            ("GENDER", TipoDeCampo.LISTA, ""), ("BRAND", TipoDeCampo.TEXTO, ""), ("OLD", TipoDeCampo.LISTA, ""),
            ("GRID", TipoDeCampo.NUMERO, "cm"),
        ])
        self.assertEqual(campos[0].valores, (("242085", "Sim"), ("242084", "Não")))
        self.assertEqual(campos[4].valores, (("9", "Nike"),))


class TestMontarFicha(unittest.TestCase):
    def setUp(self):
        self.leitura = normalizar_leitura(LEITURA_BRUTA, quantidade_fotos=2)

    def _resumo(self, ficha):
        return [(v.chave, v.valor, v.origem, v.confianca, v.confirmado) for v in ficha.valores]

    def test_so_leitura(self):
        ficha = montar_ficha(self.leitura)
        self.assertEqual(self._resumo(ficha), [
            ("marca", "Nike", OrigemAtributo.FOTO, Confianca.ALTA, False),
            ("cor", "Azul marinho", OrigemAtributo.FOTO, Confianca.MEDIA, False),
            ("material", "Couro", OrigemAtributo.DEDUCAO, Confianca.BAIXA, False),
            ("modelo", "Pegasus", OrigemAtributo.ETIQUETA, Confianca.ALTA, False),
        ])
        self.assertEqual((ficha.produto, ficha.categoria, ficha.condicao),
                         ("Tênis de corrida", "calcados", CondicaoProduto.USADO))
        self.assertEqual((ficha.identificacao, ficha.embalagem), (Identificacao(), Embalagem()))

    def test_com_confirmacao(self):
        confirmacao = normalizar_confirmacao(CONFIRMACAO_BRUTA, self.leitura)
        ficha = montar_ficha(self.leitura, confirmacao)
        self.assertEqual(self._resumo(ficha), [
            ("cor", "AZUL marinho", OrigemAtributo.FOTO, Confianca.MEDIA, True),
            ("marca", "Adidas", OrigemAtributo.DESCONHECIDO, Confianca.BAIXA, True),
            ("genero", "Masculino", OrigemAtributo.DESCONHECIDO, Confianca.BAIXA, True),
            ("material", "Couro", OrigemAtributo.DEDUCAO, Confianca.BAIXA, False),
            ("modelo", "Pegasus", OrigemAtributo.ETIQUETA, Confianca.ALTA, False),
        ])
        self.assertEqual((ficha.produto, ficha.categoria, ficha.condicao),
                         ("Tênis Nike Pegasus", "esporte", CondicaoProduto.NOVO))
        chaves = [v.chave for v in ficha.valores]
        self.assertEqual(len(chaves), len(set(chaves)))

    def test_identificacao_e_embalagem_so_com_o_confirmado(self):
        leitura = normalizar_leitura({**LEITURA_BRUTA, "atributos": [
            {"chave": "gtin", "valor": "4006381333931", "origem": "etiqueta", "evidencia": "x", "confianca": "alta"},
            {"chave": "peso_g", "valor": "300", "origem": "deducao", "evidencia": "x", "confianca": "media"}]}, 1)
        self.assertEqual((montar_ficha(leitura).identificacao, montar_ficha(leitura).embalagem),
                         (Identificacao(), Embalagem()))  # só lido não entra
        confirmacao = normalizar_confirmacao({"atributos": [
            {"chave": "gtin", "valor": "400-6381 333931"}, {"chave": "sku", "valor": "TEN-42"},
            {"chave": "peso_g", "valor": "350,6 g"}, {"chave": "comprimento_cm", "valor": "30"},
            {"chave": "largura_cm", "valor": "12.5cm"}, {"chave": "altura_cm", "valor": "1,2 m"}]}, leitura)
        ficha = montar_ficha(leitura, confirmacao)
        self.assertEqual(ficha.identificacao, Identificacao(gtin="4006381333931", sku="TEN-42"))
        self.assertEqual(ficha.embalagem, Embalagem(peso_g=351, comprimento_cm=30.0, largura_cm=12.5, altura_cm=None))
        invalidos = normalizar_confirmacao({"atributos": [{"chave": "gtin", "valor": "4006381333932"},
                                                          {"chave": "peso_g", "valor": "0"}]}, leitura)
        ficha = montar_ficha(leitura, invalidos)
        self.assertEqual((ficha.identificacao.gtin, ficha.embalagem.peso_g), (None, None))


class TestGtin(unittest.TestCase):
    def test_validos(self):
        for codigo in ("73513537", "036000291452", "4006381333931", "00012345600012", " 4006381333931 "):
            with self.subTest(codigo=codigo):
                self.assertTrue(gtin_valido(codigo))

    def test_invalidos(self):
        for codigo in ("73513538", "036000291453", "4006381333932", "00012345600013",  # verificador errado
                       "1234567", "400638133393a", "", "00000000", "4006 3813 33931",
                       "４００６３８１３３３９３１", None):
            with self.subTest(codigo=codigo):
                self.assertFalse(gtin_valido(codigo))

    def test_normalizar_gtin(self):
        for texto in ("４００６３８１３３３９３１", "400-6381-333931", " 4006381 333931 ", "4006381\u2010333931"):
            with self.subTest(texto=texto):
                self.assertEqual(normalizar_gtin(texto), "4006381333931")
        for texto in ("4006381333932", "400-6381-33393", "", None, "abc"):
            with self.subTest(texto=texto):
                self.assertIsNone(normalizar_gtin(texto))


if __name__ == "__main__":
    unittest.main()
