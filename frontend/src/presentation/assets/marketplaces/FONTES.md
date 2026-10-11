# Logos dos marketplaces: fontes

Logos oficiais usados pela Quick Click na vitrine da landing, na área logada e nos anúncios.
Oito foram baixados do Wikimedia Commons em 08/10/2026. O do TikTok Shop veio do site oficial da TikTok em 11/10/2026. Todos estão aqui **sem nenhuma alteração** de cor, forma ou proporção.

No Commons, os oito aparecem como **domínio público** (logo feito só de texto e formas simples, sem originalidade para direito autoral). Todos continuam sendo **marcas registradas** dos seus donos. A Quick Click usa os logos só para indicar com quais marketplaces o produto trabalha, sem sugerir parceria ou patrocínio.

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
| TikTok Shop | `tiktok-shop.svg` | Site oficial da TikTok: é o logo do cabeçalho da Central do Vendedor do Brasil (https://seller-br.tiktok.com), servido pelo CDN da TikTok em https://lf16-scmcdn.oecstatic.com/obj/oec-magellan-sg/i18n/ecom/TTS/normal/main/static/media/logo.1e4a311e.svg (baixado em 11/10/2026; SHA-256 `28275e4d…bf68dce`). | Versão empilhada ("TikTok" sobre "Shop"), escrita **branca** com o ciano #25F4EE e o vermelho #FE2C55: feita para fundo escuro. Nas cenas da marca o palco é escuro (`stage: 'dark'` na paleta); nos tamanhos pequenos o `MarketplaceLogo` põe um fundo escuro atrás (`marketplace-logo--light-art`). Não existe no Commons. A TikTok também usa uma versão horizontal, igual em cores, no login da Central dos EUA (`tts_logo.316b4170.svg`). |

## Como usar

- Sempre pelo componente `MarketplaceLogo` (`presentation/components/MarketplaceLogo`), que desenha um `<img>` com texto alternativo. O monograma (`MarketplaceMark`) é só a reserva para um marketplace novo, ainda sem logo.
- Use sobre fundo claro (placas de vidro claras, cartões areia) ou na cena da marca (`BrandBackdrop`). O azul do Mercado Livre e o preto da Amazon e da Shein desaparecem em fundo escuro. O TikTok Shop é o contrário: a escrita é branca e pede fundo escuro.
- Para "em breve", o componente apaga o logo com filtro de CSS. O arquivo em si nunca é editado.

## Checagens feitas no download

- Cada arquivo abre no navegador e mostra a marca certa (conferido lado a lado em fundo claro e escuro).
- Nenhum arquivo tem `<script>`, eventos (`onload`, `onclick`), `foreignObject` ou links para fora.
- TikTok Shop: o arquivo é byte a byte o mesmo servido pela TikTok (o mesmo SVG também vem embutido no JavaScript da Central do Vendedor, como `src/assets/images/logo.svg`).
