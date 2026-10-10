# Logos dos marketplaces: fontes

Logos oficiais usados pela Quick Click na vitrine da landing, na área logada e nos anúncios.
Todos foram baixados do Wikimedia Commons em 08/10/2026 e estão aqui **sem nenhuma alteração** de cor, forma ou proporção.

No Commons, todos aparecem como **domínio público** (logo feito só de texto e formas simples, sem originalidade para direito autoral), mas continuam sendo **marcas registradas** dos seus donos. A Quick Click usa os logos só para indicar com quais marketplaces o produto trabalha, sem sugerir parceria ou patrocínio.

| Marketplace | Arquivo | Origem | Observação |
|---|---|---|---|
| Mercado Livre | `mercado-livre.svg` | https://commons.wikimedia.org/wiki/File:Mercado_Livre_wordmark_(Portuguese_version).svg | Só a escrita oficial ("mercado livre"). O logo completo, com o aperto de mãos no fundo amarelo, não está em domínio público e não encontramos um kit de imprensa público com ele. |
| Shopee | `shopee.svg` | https://commons.wikimedia.org/wiki/File:Shopee.svg | Sacola e escrita. |
| Amazon | `amazon.svg` | https://commons.wikimedia.org/wiki/File:Amazon_2024.svg | Versão de 2024 (escrita e sorriso redesenhados). |
| Magalu | `magalu.svg` | https://commons.wikimedia.org/wiki/File:Magalu_(2019).svg | Versão de 2019. O arquivo traz a faixa colorida embutida como imagem. |
| Americanas | `americanas.svg` | https://commons.wikimedia.org/wiki/File:Lojas_Americanas_(2021).svg | Marca atual, "americanas" (2021). |
| Casas Bahia | `casas-bahia.svg` | https://commons.wikimedia.org/wiki/File:Casas_Bahia_logo_2020.svg | Versão de 2020, a mesma usada hoje na Wikipédia. |
| Shein | `shein.svg` | https://commons.wikimedia.org/wiki/File:Shein_Logo_2017.svg | |
| AliExpress | `aliexpress.svg` | https://commons.wikimedia.org/wiki/File:AliExpress_2024.svg | Versão de 2024. |
| TikTok Shop | (nenhum) | Não existe no Commons nem em kit de imprensa público. | A interface usa o **monograma** "TS" (`MarketplaceMark`) como reserva. Nunca desenhe um logo no lugar. |

## Como usar

- Sempre pelo componente `MarketplaceLogo` (`presentation/components/MarketplaceLogo`), que desenha um `<img>` com texto alternativo e cai no monograma quando o logo não existe.
- Use sobre fundo claro (placas de vidro claras, cartões areia). O azul do Mercado Livre e o preto da Amazon e da Shein desaparecem em fundo escuro.
- Para "em breve", o componente apaga o logo com filtro de CSS. O arquivo em si nunca é editado.

## Checagens feitas no download

- Cada arquivo abre no navegador e mostra a marca certa (conferido lado a lado em fundo claro e escuro).
- Nenhum arquivo tem `<script>`, eventos (`onload`, `onclick`), `foreignObject` ou links para fora.
