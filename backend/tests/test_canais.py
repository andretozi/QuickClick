"""Modelo genérico dos canais: esquema do Mercado Livre, ficha do produto (leitura e confirmação) e GTIN."""

import unittest

from backend.domain.canais.esquema import TipoDeCampo
from backend.domain.canais.ficha import Embalagem, Identificacao, montar_ficha, gtin_valido
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


if __name__ == "__main__":
    unittest.main()
