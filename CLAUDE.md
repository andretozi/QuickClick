# Quick Click · regras do projeto

Quick Click ("Clicou, vendeu.") é uma automação de vendas multicanal com IA que se conecta às contas que o vendedor já tem nos marketplaces. Projeto acadêmico (Projetos de Engenharia da Computação, Mackenzie, 2026) de André Tozi Magalhaes (PO e dev) e Guilherme Diego Sanches (SM e dev). A arquitetura completa está no `README.md`.

## Produto: não contradizer

- Modelo de negócio: assinatura **sem comissão sobre as vendas**, em nenhum plano. Planos: Grátis (R$ 0 pra sempre, sem prazo), Essencial, Pro (o recomendado) e Business. Os preços dos pagos ainda não foram definidos: escreva "R$ __ por mês".
- Nunca escreva "comissão quando vende" nem "sem mensalidade".
- **Não existe chat nem assistente virtual** no produto, e não deve ser criado.
- **Não invente** depoimentos, números de clientes, selos ou parcerias.
- Lemas da marca, exatamente assim: "Clicou, vendeu.", "Clicou… vendeu.", "Clicou aqui, vendeu ali", "Vendeu em um canal, sai de todos.", "Da foto ao anúncio pronto."

## Como rodar

- O `main.py` da raiz é a forma de rodar tudo com um clique (Run 'main' no PyCharm, Python 3.14). Ele builda o front, instala o que faltar do back e serve tudo em `127.0.0.1:8080`: a API em `/api` (documentação em `/docs`) e o front no resto. Mantenha esse comportamento.
- Build do front: `npm run build` dentro de `frontend/`.
- Testes do back: `python -m unittest discover -s backend/tests -t .` (na raiz).

## Camadas e quem pode importar quem

**Front** (`frontend/src`): `app` → `presentation` → `application` → `domain` e `infrastructure`.

- `presentation` usa `application` e lê `domain`. Nunca importa `infrastructure` e nunca chama `fetch` (o único `fetch` do front fica em `infrastructure/http/httpClient.js`; cada serviço, como `infrastructure/marketplaces/marketplacesService.js`, traduz o JSON da API).
- `application` usa `domain` e `infrastructure`. O estado das telas mora aqui, nos hooks.
- `domain` e `infrastructure` não importam outras camadas.

**Back** (`backend/`):

- `domain`: Python puro, sem framework (nada de fastapi, pydantic, sqlite3) e sem outras camadas.
- `application`: casos de uso; importa só `domain`. Dependências externas entram por portas (`Protocol`).
- `infrastructure`: implementa as portas (SQLite, marketplaces, configuração); importa `domain` e `application`.
- `presentation`: rotas HTTP, todas começando com `/api`; importa `application` e `domain`, nunca `infrastructure`.
- `app`: raiz de composição, o único lugar que importa todas as camadas.
- `backend/tests/test_arquitetura.py` confere essas regras. Mantenha esse teste passando.

## Front

- **CSS puro em BEM** (`bloco__elemento--modificador`), um `.css` por componente, na mesma pasta. Posicionamento por mix de classes. Cores só por tokens (`var(--color-*)` e `rgb(var(--rgb-*) / alfa)`) de `presentation/styles/tokens.css`.
- **Textos só em `frontend/src/domain/content/`**, inclusive aria-labels. Componente não tem texto fixo.
- **Animações sempre ligadas.** Ficam em `infrastructure/animation` (Web Animations API, elementos achados por `data-*`). Em `core/config.js`, `respectReducedMotion: false` é decisão do projeto: **não mude**.
- Reaproveite os componentes que existem (`Button`, `Icon`, `Brand`, `Section`, `Blob`, `MarketplaceMark`...) e os efeitos de `infrastructure/animation/core/effects.js` (`driftBlobs`, `pulseLogo`, `ripple`, `drawCheck`, `enterInSequence`...).
- Identidade visual: fundos areia e cacau, destaque coral, títulos em Fraunces e texto em Nunito.
- Marketplaces aparecem com o **logo oficial** (`presentation/assets/marketplaces`, fontes em `FONTES.md`; nunca altere os arquivos), sempre pelo `MarketplaceLogo`. O monograma (`MarketplaceMark`) é só a reserva de quem não tem logo livre (TikTok Shop).
- **Navbar de vidro** (`SiteNav`): sem cor própria, blur de 12 px, todos os textos em coral. Sobre seção escura (`data-surface="dark"`), o "Quick" da marca fica creme.
- **Fundos das marcas** são gerados em código (`BrandBackdrop`, paletas em `MARKETPLACE_PALETTES`). Imagem opcional em `assets/marketplaces/fundos/<slug>.webp`.
- Partículas, explosões e palavras: um canvas só, pelo `infrastructure/animation/core/particleField.js` (componente `ParticleBurst`). Laços (spinner, brilho) por `data-spin` e `data-shimmer` (`core/loops.js`); nada de `@keyframes` novo no CSS.
- Telas: `#/` (landing), `#/login`, `#/cadastro`, `#/painel`, `#/anuncios/novo`, `#/anuncios/:id`, `#/marketplaces`, `#/configuracoes` e a 404. As privadas mandam para `#/login?volta=...`. Hashes sem barra (`#planos`) são seções da landing.
- **Área logada sem banco:** contas, sessão, anúncios, conexões, preferências e rascunho ficam no localStorage, por repositórios em `infrastructure/storage` (chaves `quickclick:v1:usuario:<id>:...`). Não existe conta pré criada nem conta de demonstração: cada vendedor cria a sua. Detalhes em `docs/area-logada.md`.
- No front, só o **Mercado Livre** está disponível para conectar e publicar; os outros aparecem "em breve".

## Regra de escrita (todo texto que aparece na tela)

- Não use traço de nenhum tipo: travessão (—), meia risca (–) nem hífen (-).
- Não use barra (/).
- Reescreva com vírgula, ponto ou dois pontos.
- Evite palavras com hífen, reescrevendo a frase: "Email" (não "E-mail"), "Que bom te ver de novo" (não "Bem-vindo de volta").
- Única exceção: a sigla oficial NF-e.
- Vale para `domain/content`, `index.html`, aria-labels, textos fixos e as mensagens de erro da API que aparecem na tela.
- Caminhos de código (hrefs, slugs, nomes de arquivo) não são texto de tela. O separador "·" é permitido.

## Back

- Nomes do domínio em português: `Marketplace`, `ContaVinculada`, `Plano`, `Vendedor`. JSON da API também em português (`nome`, `conectado`, `status`).
- Regras de negócio moram no `domain`: o limite de marketplaces por plano fica em `domain/plano.py` (Grátis e Essencial: 1; Pro e Business: vários) e o catálogo em `domain/marketplace.py`.
- **Catálogo sincronizado:** a lista de marketplaces da landing (`frontend/src/domain/content/marketplacesContent.js`) acompanha `backend/domain/marketplace.py`. Mudou um, mude o outro. **Pendência:** o back ainda marca Shopee e Amazon como disponíveis; o front só libera o Mercado Livre. Alinhar quando a área logada voltar a usar a API.
- Erros de negócio têm `codigo` estável e `mensagem` amigável (com a regra de escrita), e a API devolve tudo como `{"erro": {...}}`.
- Integrações com os marketplaces são **simuladas** (`infrastructure/marketplaces/`). O comentário de cada gateway descreve a integração real. Mercado Livre usa REST direto, sem os SDKs oficiais, que foram arquivados em 2022.
- Sem login ainda: a API atende o vendedor de demonstração, com o plano em `QUICKCLICK_PLANO_DEMO` no `.env`.
- Configuração local e segredos ficam no `.env`, fora do Git. O modelo é o `.env.example`. Segredo nunca vai para o código, para o front nem para o Git.
- O banco SQLite fica em `backend/data/`, também fora do Git.

## Fluxo de trabalho

- O Claude Code não faz commit nem push; quem commita é o André.
- Mensagens de commit em português.
- O andamento das tarefas longas fica em `docs/progresso.md` (retomada se a sessão cair).
- Antes de commitar: `npm run build` sem erros e testes do back passando.
