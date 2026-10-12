# Arquitetura e convenções

Regras que valem para todo o código da Quick Click. Se algo aqui não bate com o código, o código está errado (ou este arquivo ficou velho: atualize os dois juntos).

## Produto: o que nunca contradizer

- Modelo de negócio: assinatura **sem comissão sobre as vendas**, em nenhum plano.
- Planos: Grátis (R$ 0 pra sempre, sem prazo), Essencial, Pro (o recomendado) e Business. Os preços dos pagos ainda não foram definidos: escreva "R$ __ por mês".
- Nunca escreva "comissão quando vende" nem "sem mensalidade".
- **Não existe chat nem assistente virtual** no produto, e não deve ser criado.
- **Não invente** depoimentos, números de clientes, selos ou parcerias.
- Lemas da marca, exatamente assim: "Clicou, vendeu.", "Clicou… vendeu.", "Clicou aqui, vendeu ali", "Vendeu em um canal, sai de todos.", "Da foto ao anúncio pronto."

## Monólito em camadas

Uma aplicação só, com um processo (o `main.py`). O front e o back têm as mesmas cinco camadas no primeiro nível. Dentro de cada camada, o código é organizado por página ou por funcionalidade.

### Front (`frontend/src`)

```
app → presentation → application → domain
                                 → infrastructure
```

- `presentation` usa `application` e lê `domain`. Nunca importa `infrastructure` e nunca chama `fetch`.
- `application` usa `domain` e `infrastructure`. O estado das telas mora aqui, nos hooks.
- `domain` e `infrastructure` não importam nenhuma outra camada.
- O único `fetch` do front fica no cliente HTTP da `infrastructure`.

### Back (`backend/`)

- `domain`: Python puro, sem framework (nada de fastapi, pydantic ou sqlite3) e sem outras camadas.
- `application`: casos de uso. Importa só o `domain`. O que vem de fora (banco, marketplaces) entra por portas (`Protocol`).
- `infrastructure`: implementa as portas (SQLite, marketplaces, configuração). Importa `domain` e `application`.
- `presentation`: rotas HTTP, todas começando com `/api`. Importa `application` e `domain`, nunca `infrastructure`.
- `app`: raiz de composição, o único lugar que importa todas as camadas.

## Convenções do front

- **CSS puro em BEM** (`bloco__elemento--modificador`), um `.css` por componente, na mesma pasta. Posicionamento por mix de classes.
- **Cores só por tokens**: `var(--color-*)` e `rgb(var(--rgb-*) / alfa)`, definidos em `presentation/styles/tokens.css`.
- **Textos só na `domain`**, inclusive os aria-labels. Componente não tem texto fixo.
- **Animações sempre ligadas.** Ficam na `infrastructure` (Web Animations API) e acham os elementos por atributos `data-*`, nunca por classe. A opção `respectReducedMotion: false` é decisão do projeto.
- O `StrictMode` fica ligado. Componentes funcionais, inputs controlados e efeitos sempre com limpeza.
- Reaproveite os componentes e os efeitos que já existem antes de criar outros.
- Identidade visual: fundos areia e cacau, destaque coral, títulos em Fraunces e texto em Nunito.
- Marketplaces aparecem com o **logo oficial** (fontes e licenças em `presentation/assets/marketplaces/FONTES.md`; nunca altere os arquivos), sempre pelo `MarketplaceLogo`.
- **Navbar de vidro** (`SiteNav`): sem cor própria, blur de 12 px, todos os textos em coral. Sobre seção escura (`data-surface="dark"`), o "Quick" da marca fica creme.
- **Fundos das marcas** são gerados em código (`BrandBackdrop`, com as paletas de cada marca). Imagem opcional em `assets/marketplaces/fundos/<slug>.webp`.
- Partículas, explosões e palavras: um canvas só, pelo motor de partículas (`ParticleBurst`). Laços (spinner, brilho) por `data-spin` e `data-shimmer`; nada de `@keyframes` novo no CSS.
- Telas: `#/` (landing), `#/login`, `#/cadastro`, `#/painel`, `#/anuncios/novo`, `#/anuncios/:id`, `#/marketplaces`, `#/configuracoes` e a 404. As privadas mandam para `#/login?volta=...`. Hashes sem barra (`#planos`) são seções da landing.
- **Área logada sem banco:** contas, sessão, anúncios, conexões, preferências e rascunho ficam no localStorage (chaves `quickclick:v1:usuario:<id>:...`). Não existe conta pré criada nem conta de demonstração: cada vendedor cria a sua.
- No front, só o **Mercado Livre** está disponível para conectar e publicar; os outros aparecem "em breve".

## Regra de escrita (todo texto que aparece na tela)

- Não use traço de nenhum tipo: travessão (—), meia risca (–) nem hífen (-).
- Não use barra (/).
- Reescreva com vírgula, ponto ou dois pontos.
- Evite palavras com hífen, reescrevendo a frase: "Email" (não "E-mail"), "Que bom te ver de novo" (não "Bem-vindo de volta").
- Única exceção: a sigla oficial NF-e.
- Vale para os textos da `domain`, o `index.html`, os aria-labels e as mensagens de erro da API que aparecem na tela.
- Caminhos de código (hrefs, slugs, nomes de arquivo) não são texto de tela. O separador "·" é permitido.

## Convenções do back

- Nomes do domínio em português: `Marketplace`, `ContaVinculada`, `Plano`, `Vendedor`. O JSON da API também: `nome`, `conectado`, `status`.
- Regras de negócio moram no `domain`: o limite de marketplaces por plano (Grátis e Essencial: 1; Pro e Business: vários) e o catálogo de marketplaces.
- **Catálogo sincronizado:** a lista de marketplaces do front acompanha o catálogo do back. Mudou um, mude o outro. Pendência: o back ainda marca Shopee e Amazon como disponíveis; o front só libera o Mercado Livre.
- Erros de negócio têm `codigo` estável e `mensagem` amigável (com a regra de escrita). A API devolve tudo como `{"erro": {...}}`.
- Integrações com os marketplaces são **simuladas**. O comentário de cada adaptador descreve a integração real. Mercado Livre usa REST direto, sem os SDKs oficiais, que foram arquivados em 2022.
- Sem login ainda: a API atende o vendedor de demonstração, com o plano em `QUICKCLICK_PLANO_DEMO` no `.env`.
- Configuração local e segredos ficam no `.env`, fora do Git. O modelo é o `.env.example`. Segredo nunca vai para o código, para o front nem para o Git.
- O banco SQLite fica em `backend/data/`, também fora do Git.

## Comandos

| O que | Comando | Onde |
|---|---|---|
| Rodar tudo (front buildado, API e navegador) | `python main.py` ou Run 'main' no PyCharm | raiz |
| Front com recarga ao salvar | `npm run dev` | `frontend/` |
| Build do front | `npm run build` | `frontend/` |
| Testes do back | `python -m unittest discover -s backend/tests -t .` | raiz |

## Antes de commitar

- `npm run build` sem erros.
- Testes do back passando.
- Mensagens de commit em português.
