"""Textos de tela que precisam ficar do jeito certo (lidos de frontend/src/domain/content, sem rodar o front)."""

import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FRONT = RAIZ / "frontend" / "src"
CONTEUDO = FRONT / "domain" / "content"

# Só o Mercado Livre está integrado: promessa que não existe não aparece, nem como promessa
PROIBIDOS_EM_QUALQUER_TELA = ("Zona de risco", "Poucos anúncios", "Baixa automática", "Emissão automática",
                              "Monitor de preços", "Automação completa", "R$ __", "Preço em breve")
PROIBIDOS_NA_LANDING = ("melhor canal", "indica o melhor", "baixa sozinho", "baixa automática", "multicanal",
                        "recommended: true", "você escolhe o canal")


def arquivos_do_front():
    return [p for p in FRONT.rglob("*") if p.suffix in (".js", ".jsx")]


class TestTextosDaTela(unittest.TestCase):
    def test_excluir_conta_no_menu_e_na_secao_das_configuracoes(self):
        conteudo = (CONTEUDO / "settingsContent.js").read_text(encoding="utf-8")
        self.assertIn("danger: { label: 'Excluir conta', icon: 'alert' }", conteudo)
        self.assertRegex(conteudo, r"export const DANGER_SECTION = \{\s*title: 'Excluir conta',")

    def test_a_secao_das_configuracoes_mostra_o_texto_do_conteudo(self):
        secao = FRONT / "presentation" / "pages" / "settings" / "components" / "DangerSection" / "DangerSection.jsx"
        self.assertIn("DANGER_SECTION.title", secao.read_text(encoding="utf-8"))
        pagina = (FRONT / "presentation" / "pages" / "settings" / "SettingsPage.jsx").read_text(encoding="utf-8")
        self.assertIn("SETTINGS.sections[id]", pagina)

    def test_nenhum_texto_proibido_em_qualquer_arquivo_do_front(self):
        for arquivo in arquivos_do_front():
            texto = arquivo.read_text(encoding="utf-8")
            for proibido in PROIBIDOS_EM_QUALQUER_TELA:
                self.assertNotIn(proibido, texto, f"{arquivo.relative_to(RAIZ)}: {proibido}")

    def test_landing_sem_promessa_de_estoque_sincronizado_nem_de_melhor_canal(self):
        landing = (CONTEUDO / "landingContent.js").read_text(encoding="utf-8").lower()
        for proibido in PROIBIDOS_NA_LANDING:
            self.assertNotIn(proibido, landing)

    def test_so_o_mercado_livre_e_citado_como_onde_publica_na_landing(self):
        landing = (CONTEUDO / "landingContent.js").read_text(encoding="utf-8")
        self.assertIn("publica no Mercado Livre. Outros marketplaces em breve.", landing)
        self.assertIn("Vários marketplaces (em breve)", landing)

    def test_aviso_do_plano_nao_promete_multicanal_que_nao_existe(self):
        marketplaces = (CONTEUDO / "marketplacesContent.js").read_text(encoding="utf-8")
        self.assertNotIn("Multicanal", marketplaces)
        self.assertIn("Vários marketplaces a partir do Pro (em breve).", marketplaces)


if __name__ == "__main__":
    unittest.main()
