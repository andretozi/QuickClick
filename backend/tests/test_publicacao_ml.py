"""Publicação montada no back: o item do Mercado Livre, as fotos, a descrição, a gestão e os erros."""

import io
import json
import unittest
from datetime import timedelta

from PIL import Image

from backend.application.casos_de_uso import ConectarMarketplace
from backend.application.casos_de_uso.publicar_no_mercado_livre import PublicarNoMercadoLivre
from backend.application.ia.escolha import ProvedoresDeIA
from backend.application.ia.modelos import ArquivoDeFoto
from backend.application.portas import FalhaNoMarketplace
from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.domain.erros import (
    AnuncioNaoEncontrado,
    FotoInvalida,
    MercadoLivreDesconectado,
    PublicacaoRecusada,
)
from backend.domain.ia.atributos_ml import AtributoML, completar_para_publicacao, ligar_confirmados
from backend.domain.plano import GRATIS
from backend.domain.vendedor import Vendedor
from backend.infrastructure.ia.preparador_pillow import PillowPreparador
from backend.tests.test_api_ia import BaseIA, FonteMLFalsa
from backend.tests.test_casos_de_uso import AGORA, GatewayFalso, RepositorioContasEmMemoria, RepositorioVendedoresEmMemoria
from backend.tests.test_provedores_ia import foto_com_detalhes, jpeg

ANUNCIO = {"titulo": "Tênis de corrida Nike azul usado", "descricao": "Tênis usado em bom estado.",
           "preco_centavos": 15990, "estoque": 1, "condicao": "usado", "analise_id": "a1",
           "atributos": [{"chave": "marca", "valor": "Nike"}, {"chave": "numero", "valor": "42"}]}


class PublicadorFalso:
    def __init__(self, erros_ao_publicar=(), erro_na_descricao=None, seller_id="1001", erros_ao_subir_imagem=()):
        self.imagens, self.itens, self.descricoes = [], [], []
        self.conteudos_imagens = []
        self.atualizacoes, self.excluidos = [], []
        self._erros = list(erros_ao_publicar)
        self._erros_imagem = list(erros_ao_subir_imagem)
        self._erro_na_descricao = erro_na_descricao
        self._armazenados = {
            "MLB123456": {
                "id": "MLB123456",
                "title": "Tênis de corrida Nike azul usado",
                "family_name": None,
                "description": "Tênis usado em bom estado.",
                "price": 159.9,
                "status": "active",
                "condition": "used",
                "available_quantity": 1,
                "sold_quantity": 0,
                "category_id": "MLB23262",
                "permalink": "https://produto.mercadolivre.com.br/MLB123456",
                "thumbnail": "https://http2.mlstatic.com/D_1.jpg",
                "pictures": ["https://http2.mlstatic.com/D_1.jpg"],
                "attributes": [{"id": "BRAND", "name": "Marca", "value": "Nike"}],
                "health": 0.85,
                "seller_id": seller_id,
                "tags": ["good_quality_thumbnail"],
                "last_updated": None,
            }
        }

    def subir_imagem(self, token, conteudo, nome="foto.jpg"):
        self.conteudos_imagens.append((nome, conteudo))
        if self._erros_imagem:
            erro = self._erros_imagem.pop(0)
            if erro is not None:
                raise erro
        self.imagens.append(nome)
        return f"IMG{len(self.imagens)}"

    def publicar_anuncio(self, token, dados):
        self.itens.append(dados)
        if self._erros:
            raise self._erros.pop(0)
        return {"id": "MLB123456", "permalink": "https://produto.mercadolivre.com.br/MLB123456", "status": "active"}

    def gravar_descricao(self, token, item_id, texto):
        if self._erro_na_descricao:
            raise self._erro_na_descricao
        self.descricoes.append((item_id, texto))

    def obter_anuncio(self, token, item_id):
        if item_id not in self._armazenados:
            raise FalhaNoMarketplace("404", 404, {"message": "not_found"})
        return dict(self._armazenados[item_id])

    def atualizar_anuncio(self, token, item_id, campos):
        self.atualizacoes.append((item_id, dict(campos)))
        atual = self._armazenados[item_id]
        atual.update(campos)
        return dict(atual)

    def atualizar_descricao(self, token, item_id, texto):
        if self._erro_na_descricao:
            raise self._erro_na_descricao
        self.descricoes.append((item_id, texto))
        self._armazenados[item_id]["description"] = texto

    def excluir_anuncio(self, token, item_id):
        self.excluidos.append(item_id)
        self._armazenados.pop(item_id, None)


class AnalisesFalsas:
    def __init__(self, analises):
        self._analises = analises

    def obter(self, analise_id):
        return self._analises.get(analise_id)


def caso(publicador=None, conectado=True, analises=None, conta_externa="1001"):
    contas = RepositorioContasEmMemoria()
    if conectado:
        contas.salvar(ContaVinculada(
            1, "mercado-livre", AGORA,
            CredenciaisOAuth("tok", "ref", AGORA + timedelta(days=3650), conta_externa_id=conta_externa),
        ))
    conectar = ConectarMarketplace(RepositorioVendedoresEmMemoria(Vendedor(1, "Loja", GRATIS)), contas,
                                   {"mercado-livre": GatewayFalso()})
    analises = analises if analises is not None else {"a1": {"vendedor_id": 1, "leitura": {"ml": {
        "categoria_id": "MLB23262", "mapa": {"numero": "SIZE"}, "obrigatorios": ["SIZE"]}}}}
    publicador = publicador or PublicadorFalso()
    return PublicarNoMercadoLivre(conectar, publicador, FonteMLFalsa(), AnalisesFalsas(analises), PillowPreparador()), publicador


def fotos(quantas=2):
    return [ArquivoDeFoto(f"f{i}.jpg", jpeg(foto_com_detalhes())) for i in range(quantas)]


class TestPublicarNoMercadoLivre(unittest.TestCase):
    def test_monta_o_item_sobe_as_fotos_e_grava_a_descricao(self):
        publicar, publicador = caso()
        resultado = publicar.executar(1, ANUNCIO, fotos())
        self.assertEqual(resultado["id"], "MLB123456")
        item = publicador.itens[0]
        self.assertEqual((item["category_id"], item["currency_id"], item["listing_type_id"], item["condition"]),
                         ("MLB23262", "BRL", "gold_special", "used"))
        self.assertEqual((item["price"], item["available_quantity"], item["buying_mode"]), (159.9, 1, "buy_it_now"))
        self.assertEqual(item["pictures"], [{"id": "IMG1"}, {"id": "IMG2"}])
        self.assertEqual({a["id"]: a["value_name"] for a in item["attributes"]}, {"BRAND": "Nike", "SIZE": "42"})
        self.assertEqual(publicador.descricoes, [("MLB123456", "Tênis usado em bom estado.")])

    def test_reenvia_foto_ampliada_quando_mercado_livre_recusa_por_bordas_brancas(self):
        erro_borda = FalhaNoMarketplace(
            "400",
            400,
            {
                "message": (
                    "Asegúrate de que la imagen tenga como mínimo 500 píxeles en uno de los lados. "
                    "La imagen subida, procesados los bordes blancos, tiene un tamaño de 447px x 447px"
                )
            },
        )
        publicador = PublicadorFalso(erros_ao_subir_imagem=[None, erro_borda, None])
        publicar, _ = caso(publicador)
        resultado = publicar.executar(1, ANUNCIO, fotos(2))
        self.assertEqual(resultado["id"], "MLB123456")
        self.assertEqual(publicador.imagens, ["foto1.jpg", "foto2.jpg"])
        self.assertEqual(len(publicador.conteudos_imagens), 3)
        with Image.open(io.BytesIO(publicador.conteudos_imagens[-1][1])) as reenviada:
            self.assertGreaterEqual(min(reenviada.size), 1200)
            self.assertGreaterEqual(max(reenviada.size), 1600)

    def test_analise_de_outro_vendedor_nao_empresta_a_categoria(self):
        publicar, publicador = caso(analises={"a1": {"vendedor_id": 2, "leitura": {"ml": {"categoria_id": "MLB999"}}}})
        publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual(publicador.itens[0]["category_id"], "MLB23262")  # veio da descoberta pelo título

    def test_sem_mercado_livre_conectado(self):
        publicar, _ = caso(conectado=False)
        with self.assertRaises(MercadoLivreDesconectado):
            publicar.executar(1, ANUNCIO, fotos(1))

    def test_categoria_do_modelo_novo_pede_family_name_sem_title(self):
        erro = FalhaNoMarketplace("400", 400, {"cause": [{"code": "item.family_name.missing"}]})
        publicar, publicador = caso(PublicadorFalso(erros_ao_publicar=[erro]))
        publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual(publicador.itens[1]["family_name"], ANUNCIO["titulo"])
        self.assertNotIn("title", publicador.itens[1])

    def test_completa_atributos_obrigatorios_de_qualidade_e_do_titulo_na_publicacao(self):
        da_categoria = [
            AtributoML("BRAND", "Marca", False),
            AtributoML("MANUFACTURER", "Fabricante", True),
            AtributoML("MODEL", "Modelo", True),
            AtributoML("MATERIAL", "Material", True, (("2282603", "Cerâmica"), ("2431731", "Vidro"))),
            AtributoML("COLOR", "Cor", False, (("52055", "Branco"), ("52049", "Preto"))),
            AtributoML("SALE_FORMAT", "Formato de venda", False, (("1359391", "Unidade"), ("1359392", "Kit"))),
            AtributoML("UNITS_PER_PACK", "Unidades por embalagem", False),
            AtributoML("IS_SET", "É kit", False, (("242084", "Não"), ("242085", "Sim"))),
            AtributoML("VOLUME_CAPACITY", "Capacidade em volume", False, (), "mL"),
            AtributoML("EMPTY_GTIN_REASON", "Motivo de GTIN vazio", False,
                       (("17055160", "O produto não tem código cadastrado"),)),
        ]
        ligados = completar_para_publicacao(
            ligar_confirmados([("quantidade", "1 unidade")], da_categoria, {}),
            da_categoria,
            "Caneca Branca de Cerâmica 250ml Acabamento Brilhante",
        )
        por_id = {l.id: l.para_api() for l in ligados}
        self.assertEqual(por_id["BRAND"], {"id": "BRAND", "value_name": "Genérica"})
        self.assertEqual(por_id["MANUFACTURER"], {"id": "MANUFACTURER", "value_name": "Genérica"})
        self.assertEqual(por_id["MODEL"], {"id": "MODEL", "value_name": "Caneca"})
        self.assertEqual(por_id["MATERIAL"], {"id": "MATERIAL", "value_id": "2282603"})
        self.assertEqual(por_id["COLOR"], {"id": "COLOR", "value_id": "52055"})
        self.assertEqual(por_id["SALE_FORMAT"], {"id": "SALE_FORMAT", "value_id": "1359391"})
        self.assertEqual(por_id["UNITS_PER_PACK"], {"id": "UNITS_PER_PACK", "value_name": "1"})
        self.assertEqual(por_id["IS_SET"], {"id": "IS_SET", "value_id": "242084"})
        self.assertEqual(por_id["VOLUME_CAPACITY"], {"id": "VOLUME_CAPACITY", "value_name": "250 mL"})
        self.assertEqual(por_id["EMPTY_GTIN_REASON"], {"id": "EMPTY_GTIN_REASON", "value_id": "17055160"})

        ligados_kit = completar_para_publicacao(
            ligar_confirmados([("quantidade", "2 unidades")], da_categoria, {}),
            da_categoria,
            "Caneca Branca de Cerâmica 250ml",
        )
        por_id_kit = {l.id: l.para_api() for l in ligados_kit}
        self.assertEqual(por_id_kit["SALE_FORMAT"], {"id": "SALE_FORMAT", "value_id": "1359392"})
        self.assertEqual(por_id_kit["UNITS_PER_PACK"], {"id": "UNITS_PER_PACK", "value_name": "2"})
        self.assertEqual(por_id_kit["IS_SET"], {"id": "IS_SET", "value_id": "242085"})

    def test_pausar_reativar_atualizar_e_excluir_anuncio(self):
        publicar, publicador = caso()
        pausado = publicar.alterar_status(1, "MLB123456", "pausado")
        self.assertEqual(pausado["status"], "paused")
        reativado = publicar.alterar_status(1, "MLB123456", "publicado")
        self.assertEqual(reativado["status"], "active")

        editado = publicar.atualizar(
            1,
            "MLB123456",
            {
                **ANUNCIO,
                "preco_centavos": 19990,
                "estoque": 4,
                "descricao": "Descrição atualizada.",
                "fotos_mantidas": ["https://http2.mlstatic.com/D_1.jpg", "http://malicioso.local/x.jpg"],
            },
            fotos(1),
        )
        self.assertEqual(editado["price"], 199.9)
        self.assertEqual(editado["available_quantity"], 4)
        self.assertEqual(editado["description"], "Descrição atualizada.")
        ultima_atualizacao = publicador.atualizacoes[-1][1]
        self.assertEqual(ultima_atualizacao["pictures"], [
            {"source": "https://http2.mlstatic.com/D_1.jpg"},
            {"id": "IMG1"},
        ])

        excluido = publicar.excluir(1, "MLB123456")
        self.assertTrue(excluido["excluido"])
        self.assertEqual(publicador.excluidos, ["MLB123456"])

    def test_impede_acesso_a_anuncio_de_outro_vendedor_ou_id_invalido(self):
        publicar, _ = caso(PublicadorFalso(seller_id="9999"), conta_externa="1001")
        with self.assertRaises(AnuncioNaoEncontrado):
            publicar.obter(1, "MLB123456")
        with self.assertRaises(AnuncioNaoEncontrado):
            publicar.excluir(1, "MLB123456")
        with self.assertRaises(ValueError):
            publicar.obter(1, "../../etc/passwd")

    def test_recusa_do_mercado_livre_traz_as_causas(self):
        erro = FalhaNoMarketplace("400", 400, {"message": "validation", "cause": [{"message": "Price too low"}]})
        publicar, _ = caso(PublicadorFalso(erros_ao_publicar=[erro]))
        with self.assertRaises(PublicacaoRecusada) as recusa:
            publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual(recusa.exception.detalhes, ["Price too low"])

    def test_descricao_que_nao_entrou_vira_aviso(self):
        publicar, _ = caso(PublicadorFalso(erro_na_descricao=FalhaNoMarketplace("500", 500)))
        resultado = publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual([a["codigo"] for a in resultado["avisos"]], ["descricao_nao_gravada"])

    def test_validacoes(self):
        publicar, _ = caso()
        with self.assertRaises(FotoInvalida):
            publicar.executar(1, ANUNCIO, [])
        with self.assertRaises(ValueError):
            publicar.executar(1, {**ANUNCIO, "preco_centavos": 50}, fotos(1))
        with self.assertRaises(ValueError):
            publicar.executar(1, {**ANUNCIO, "titulo": " "}, fotos(1))

    def test_ignora_atributos_somente_leitura_e_mapeia_unissex_para_sem_genero(self):
        da_categoria = [
            AtributoML.de_api({
                "id": "FILTRABLE_SIZE",
                "name": "Tamanho filtrável",
                "tags": {},  # simula cache antigo de 24h sem a tag read_only
                "values": [{"id": "40", "name": "40"}],
                "value_type": "string",
            }),
            AtributoML.de_api({
                "id": "CUSTOM_READONLY",
                "name": "Campo interno",
                "tags": {"read_only": True, "hidden": True},
                "values": [{"id": "1", "name": "Preto"}],
                "value_type": "list",
            }),
            AtributoML.de_api({
                "id": "GENDER",
                "name": "Gênero",
                "tags": {"required": True, "catalog_required": True},
                "values": [
                    {"id": "339665", "name": "Feminino"},
                    {"id": "339666", "name": "Masculino"},
                    {"id": "110461", "name": "Sem gênero"},
                ],
                "value_type": "list",
            }),
            AtributoML.de_api({
                "id": "COLOR",
                "name": "Cor",
                "tags": {"allow_variations": True},
                "values": [{"id": "52049", "name": "Preto"}],
                "value_type": "string",
            }),
            AtributoML.de_api({
                "id": "SIZE",
                "name": "Tamanho",
                "tags": {"allow_variations": True, "required": True},
                "values": [],
                "value_type": "string",
            }),
            AtributoML.de_api({
                "id": "BRAND",
                "name": "Marca",
                "tags": {"required": True},
                "values": [],
                "value_type": "string",
            }),
        ]

        ligados = completar_para_publicacao(
            ligar_confirmados([("marca", "Havaianas"), ("genero", "Unissex")], da_categoria, {}),
            da_categoria,
            "Chinelo Havaianas Preto Tamanho 40 Unissex Borracha",
        )
        por_id = {l.id: l.para_api() for l in ligados}
        self.assertNotIn("FILTRABLE_SIZE", por_id)
        self.assertNotIn("CUSTOM_READONLY", por_id)
        self.assertEqual(por_id["GENDER"], {"id": "GENDER", "value_id": "110461"})
        self.assertEqual(por_id["COLOR"], {"id": "COLOR", "value_id": "52049"})
        self.assertEqual(por_id["SIZE"], {"id": "SIZE", "value_name": "40"})

        # Também funciona quando o gênero só aparece no título ("Unissex")
        ligados_do_titulo = completar_para_publicacao(
            ligar_confirmados([("marca", "Havaianas")], da_categoria, {}),
            da_categoria,
            "Chinelo Havaianas Preto Tamanho 40 Unissex Borracha",
        )
        por_id_titulo = {l.id: l.para_api() for l in ligados_do_titulo}
        self.assertEqual(por_id_titulo["GENDER"], {"id": "GENDER", "value_id": "110461"})
        self.assertNotIn("FILTRABLE_SIZE", por_id_titulo)

    def test_causas_prioriza_erro_real_sobre_warning_do_mercado_livre(self):
        erro = FalhaNoMarketplace(
            "400",
            400,
            {
                "message": "Validation error",
                "cause": [
                    {
                        "type": "warning",
                        "code": "item.attributes.ignored",
                        "message": "Attribute [FILTRABLE_SIZE] ignored because it is not modifiable.",
                    },
                    {
                        "type": "error",
                        "code": "missing.fashion_grid.grid_id.values",
                        "message": "Attribute [SIZE_GRID_ID] is required.",
                    },
                ],
            },
        )
        publicar, _ = caso(PublicadorFalso(erros_ao_publicar=[erro]))
        with self.assertRaises(PublicacaoRecusada) as recusa:
            publicar.executar(1, ANUNCIO, fotos(1))
        self.assertEqual(recusa.exception.detalhes, ["Attribute [SIZE_GRID_ID] is required."])

        # Se a API só devolver warnings, ainda preserva a mensagem como fallback
        so_warning = FalhaNoMarketplace(
            "400",
            400,
            {"cause": [{"type": "warning", "message": "Only warning"}]},
        )
        publicar_aviso, _ = caso(PublicadorFalso(erros_ao_publicar=[so_warning]))
        with self.assertRaises(PublicacaoRecusada) as recusa_aviso:
            publicar_aviso.executar(1, ANUNCIO, fotos(1))
        self.assertEqual(recusa_aviso.exception.detalhes, ["Only warning"])

    def test_resolve_guia_de_tamanho_e_reenvia_com_variacoes_para_calcados(self):
        atributos_calcado = [
            AtributoML.de_api({"id": "BRAND", "name": "Marca", "tags": {"required": True}, "value_type": "string"}),
            AtributoML.de_api({"id": "MODEL", "name": "Modelo", "tags": {"required": True}, "value_type": "string"}),
            AtributoML.de_api({
                "id": "GENDER",
                "name": "Gênero",
                "tags": {"required": True},
                "values": [{"id": "110461", "name": "Sem gênero"}],
                "value_type": "list",
            }),
            AtributoML.de_api({
                "id": "COLOR",
                "name": "Cor",
                "tags": {"allow_variations": True},
                "values": [{"id": "52049", "name": "Preto"}],
                "value_type": "string",
            }),
            AtributoML.de_api({
                "id": "SIZE",
                "name": "Tamanho",
                "tags": {"allow_variations": True, "required": True},
                "value_type": "string",
            }),
            AtributoML.de_api({
                "id": "FILTRABLE_SIZE",
                "name": "Tamanho filtrável",
                "tags": {"read_only": True, "hidden": True},
                "values": [{"id": "40", "name": "40"}],
                "value_type": "string",
            }),
            AtributoML.de_api({"id": "SIZE_GRID_ID", "name": "Guia de tamanhos", "value_type": "grid_id"}),
            AtributoML.de_api({
                "id": "SIZE_GRID_ROW_ID",
                "name": "Linha da guia",
                "tags": {"variation_attribute": True},
                "value_type": "grid_row_id",
            }),
        ]

        class FonteCalcado(FonteMLFalsa):
            def atributos_da_categoria(self, categoria_id, token):
                return atributos_calcado

        class PublicadorComGuia(PublicadorFalso):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.consultas_guia = []

            def obter_categoria(self, categoria_id, token):
                return {"id": categoria_id, "settings": {"catalog_domain": "MLB-SANDALS_AND_CLOGS"}}

            def buscar_guias_de_tamanho(self, token, domain_id, site_id, atributos, *, seller_id=None, tipo=None):
                self.consultas_guia.append((domain_id, site_id, tipo, seller_id, atributos))
                if tipo == "BRAND":
                    return [
                        {
                            "id": "987654",
                            "rows": [
                                {"id": "987654:1", "attributes": [{"id": "SIZE", "values": [{"name": "37/38"}]}]},
                                {
                                    "id": "987654:2",
                                    "attributes": [
                                        {"id": "SIZE", "values": [{"id": "319001", "name": "39/40"}]},
                                        {"id": "BR_SIZE", "values": [{"name": "40 BR"}]},
                                    ],
                                },
                            ],
                        }
                    ]
                return []

        erro_variacoes = FalhaNoMarketplace(
            "400",
            400,
            {"cause": [{"type": "error", "code": "item.variations.required", "message": "allow_variations must be in variations"}]},
        )
        publicador = PublicadorComGuia(erros_ao_publicar=[erro_variacoes])
        contas = RepositorioContasEmMemoria()
        contas.salvar(ContaVinculada(
            1, "mercado-livre", AGORA,
            CredenciaisOAuth("tok", "ref", AGORA + timedelta(days=3650), conta_externa_id="1001"),
        ))
        conectar = ConectarMarketplace(
            RepositorioVendedoresEmMemoria(Vendedor(1, "Loja", GRATIS)),
            contas,
            {"mercado-livre": GatewayFalso()},
        )
        publicar = PublicarNoMercadoLivre(
            conectar,
            publicador,
            FonteCalcado(),
            AnalisesFalsas({}),
            PillowPreparador(),
        )

        anuncio_chinelo = {
            "titulo": "Chinelo Havaianas Preto Tamanho 40 Unissex Borracha",
            "descricao": "Chinelo original.",
            "preco_centavos": 50000,
            "estoque": 1,
            "condicao": "novo",
            "ml_categoria_id": "MLB273770",
            "atributos": [{"chave": "marca", "valor": "Havaianas"}, {"chave": "genero", "valor": "Unissex"}],
        }
        resultado = publicar.executar(1, anuncio_chinelo, fotos(1))
        self.assertEqual(resultado["id"], "MLB123456")
        self.assertEqual(len(publicador.itens), 2)

        primeiro = {a["id"]: a for a in publicador.itens[0]["attributes"]}
        self.assertNotIn("FILTRABLE_SIZE", primeiro)
        self.assertEqual(primeiro["GENDER"], {"id": "GENDER", "value_id": "110461"})
        self.assertEqual(primeiro["SIZE_GRID_ID"], {"id": "SIZE_GRID_ID", "value_name": "987654"})
        self.assertEqual(primeiro["SIZE_GRID_ROW_ID"], {"id": "SIZE_GRID_ROW_ID", "value_name": "987654:2"})
        self.assertEqual(primeiro["SIZE"], {"id": "SIZE", "value_id": "319001"})

        segundo = publicador.itens[1]
        self.assertNotIn("price", segundo)
        self.assertNotIn("available_quantity", segundo)
        self.assertEqual(len(segundo["variations"]), 1)
        variacao = segundo["variations"][0]
        self.assertEqual(variacao["price"], 500.0)
        self.assertEqual(variacao["available_quantity"], 1)
        self.assertEqual(variacao["picture_ids"], ["IMG1"])
        comb_ids = {a["id"] for a in variacao["attribute_combinations"]}
        self.assertEqual(comb_ids, {"COLOR", "SIZE"})
        var_attr_ids = {a["id"] for a in variacao["attributes"]}
        self.assertIn("SIZE_GRID_ROW_ID", var_attr_ids)
        raiz_ids = {a["id"] for a in segundo["attributes"]}
        self.assertIn("SIZE_GRID_ID", raiz_ids)
        self.assertNotIn("COLOR", raiz_ids)
        self.assertNotIn("SIZE", raiz_ids)

    def test_sobe_foto_local_da_quickstore_direto_para_o_mercado_livre(self):
        foto_id = "a" * 32
        conteudo_jpeg = jpeg(foto_com_detalhes())

        class MidiaEmMemoria:
            def salvar(self, vendedor_id, conteudo, content_type="image/jpeg"):
                return foto_id

            def obter(self, fid):
                return (conteudo_jpeg, "image/jpeg") if fid == foto_id else None

        contas = RepositorioContasEmMemoria()
        contas.salvar(ContaVinculada(
            1, "mercado-livre", AGORA,
            CredenciaisOAuth("tok", "ref", AGORA + timedelta(days=3650), conta_externa_id="1001"),
        ))
        conectar = ConectarMarketplace(
            RepositorioVendedoresEmMemoria(Vendedor(1, "Loja", GRATIS)),
            contas,
            {"mercado-livre": GatewayFalso()},
        )
        publicador = PublicadorFalso()
        publicar = PublicarNoMercadoLivre(
            conectar,
            publicador,
            FonteMLFalsa(),
            AnalisesFalsas({}),
            PillowPreparador(),
            midia=MidiaEmMemoria(),
        )
        anuncio_com_midia_local = {
            **ANUNCIO,
            "fotos_mantidas": [f"https://quickclick.azurewebsites.net/api/quickstore/midia/{foto_id}.jpg"],
        }
        resultado = publicar.executar(1, anuncio_com_midia_local, [])
        self.assertEqual(resultado["id"], "MLB123456")
        self.assertEqual(publicador.imagens, ["foto1.jpg"])
        self.assertEqual(publicador.itens[0]["pictures"], [{"id": "IMG1"}])


class TestRotaDePublicacao(BaseIA):
    def setUp(self):
        self.montar(ProvedoresDeIA())

    def test_sem_mercado_livre_conectado_responde_409(self):
        resposta = self.cliente.post("/api/anuncios/publicar/mercado-livre", data={"anuncio": json.dumps(ANUNCIO)},
                                     files=self.fotos(1))
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (409, "mercado_livre_desconectado"))

    def test_anuncio_que_nao_e_json(self):
        resposta = self.cliente.post("/api/anuncios/publicar/mercado-livre", data={"anuncio": "{"}, files=self.fotos(1))
        self.assertEqual((resposta.status_code, resposta.json()["erro"]["codigo"]), (400, "parametro_invalido"))


if __name__ == "__main__":
    unittest.main()
