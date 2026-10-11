# Progresso · prompt v5

Arquivo de retomada. Se a sessão cair, a próxima começa por aqui. Atualizado ao fim de cada etapa.
Regra: o Claude Code não faz commit nem push; quem commita é o André.

## Status das etapas (v5)

| Etapa | Status |
|---|---|
| Passo 1 · Onde estamos | feito |
| A · Ambiente | feito |
| B · Run 'main' com um clique | feito (falta só o clique do André, na Etapa I) |
| C · Revisar o que foi feito | feito no Chrome headless; falta repetir na aba visível quando a extensão conectar |
| D · Título da aba | feito (conferir a aba no Chrome na Etapa I) |
| E · Logo do TikTok Shop | feito |
| F · Marketplaces no estilo da vitrine | falta |
| G · Telas no padrão da landing | falta |
| H · Docs | falta |
| I · Conferência final | falta |

## Passo 1 · Onde estamos (11/10/2026)

- Pasta `C:\Users\Marcus\PycharmProjects\QuickClick`, branch `area-logada` em `997006a`, em dia com `origin/area-logada`. Remote já era `andretozi/QuickClick`.
- Identidade só neste repositório: `user.name` "André Tozi Magalhães", `user.email` andretozi95@gmail.com. No `%USERPROFILE%\.claude\settings.json`: `"attribution": { "commit": "", "pr": "" }`.
- Atenção: existe uma pasta `QuickClick/` dentro do projeto, um segundo clone idêntico (com `.git` próprio, também na `area-logada`). Não está no Git e não foi mexida. Pode confundir o PyCharm (dois `main.py`); o André decide se apaga.

## Ambiente · DESKTOP-OCA9G1O (computador do Marcus)

| Item | Antes | Agora |
|---|---|---|
| Git | 2.45.1.windows.1 | igual |
| Python | 3.14.0 (`AppData\Local\Programs\Python\Python314`) e 3.13 da Microsoft Store; o `python` do PATH é o 3.13 da Store | igual; o projeto usa a `.venv` com o 3.14.0 |
| Node e npm | não instalados | Node 24.20.0 LTS e npm 11.19.0, pelo winget (`OpenJS.NodeJS.LTS`, MSI oficial do nodejs.org, hash conferido) em `C:\Program Files\nodejs` |
| Chrome | 154.0.8037.98 | igual |
| Extensão do Claude no Chrome | não instalada em nenhum perfil | falta o André instalar (claude.ai/chrome) |
| Plugin frontend-design | não instalado | instalado (`frontend-design@claude-plugins-official`, escopo do usuário) |

- `.venv` na raiz com `py -3.14 -m venv .venv`: pip atualizado, `backend/requirements.txt` instalado (fastapi 0.143.0, uvicorn 0.54.0, httpx 0.28.1), import ok.
- `npm ci` em `frontend` ok. O npm 11.19 avisa que não rodou o `postinstall` do esbuild (scripts de instalação agora pedem aprovação); o build funciona assim mesmo, porque o binário vem no pacote `@esbuild/win32-x64`.
- `npm run build`: ok. Testes do back com a `.venv`: 55 ok.
- O terminal que já estava aberto não enxerga o Node novo no PATH. Nesta sessão uso `C:\Program Files\nodejs` direto. O PyCharm precisa ser reaberto para enxergar o Node.

## Etapa B · Run 'main' com um clique (feito)

Diagnóstico:
- O PyCharm já tinha um interpretador "Python 3.14 (QuickClick)" (no `jdk.table.xml`) apontando para `QuickClick\.venv\Scripts\python.exe`, mas a `.venv` não existia: era isso que quebrava o Run 'main'. Agora ela existe.
- Faltavam o `.idea/misc.xml` (interpretador do projeto) e qualquer configuração "main" (o `workspace.xml` não tinha `RunManager`). O `vcs.xml` registra a pasta duplicada `QuickClick/` como segundo repositório.
- O PyCharm foi aberto antes do Node existir, então o PATH dele não tem o npm.

Feito:
- `.run/main.run.xml` (para commitar): nome "main", script `$PROJECT_DIR$/main.py`, pasta `$PROJECT_DIR$`, interpretador `$PROJECT_DIR$/.venv/Scripts/python.exe` (não depende do interpretador do projeto), `PYTHONUNBUFFERED=1`, uma instância só.
- `.idea/misc.xml` criado com o interpretador "Python 3.14 (QuickClick)" e a pasta duplicada `QuickClick/` excluída no `QuickClick.iml` (a `.idea` é local, fora do Git).
- `main.py`: mostra Python, Node e npm; relança com a `.venv` quando roda com outro Python (com trava contra laço); acha o npm fora do PATH (PATH do processo, link do nvm, Arquivos de Programas, AppData e o PATH atual do registro do Windows); exige Node 18 ou mais novo; `npm ci` quando falta o `node_modules` ou o `package-lock.json` é mais novo (cai para `npm install` se o `ci` falhar); se a 8080 já é do Quick Click (o `/api/health` responde), avisa e só abre o navegador; porta, rotas e o resto continuam iguais. Docstring atualizada.
- README: seção "Primeira vez num computador novo" e o passo a passo do `main.py`.

Testado pelo terminal (com o Node fora do PATH do shell):
- `.venv` com `NO_BROWSER=1 REBUILD=1`: achou o npm em `C:\Program Files\nodejs`, buildou e serviu; `/api/health`, a página inicial e `/docs` responderam.
- Segunda execução com o servidor no ar: "O Quick Click já está rodando", saída 0.
- `py -3.14` (Python do sistema) e `python` (3.13 da Store): relançaram com a `.venv`.
- Porta ocupada por outro programa: a mensagem antiga, saída 1.
- `package-lock.json` mais novo: rodou `npm ci` e voltou a ficar em dia.

Falta: o clique do André no Run 'main' (Etapa I). Se o PyCharm não mostrar a configuração "main", fechar e reabrir o PyCharm.

## Etapa C · Revisão (feito; RETOMAR DAQUI: depois vêm F, G, H e I)

- Auditoria do diário contra o código: tudo o que o diário cita existe, nenhum import quebrado, rotas certas. Diário v4 desatualizado em dois pontos: o `SettingsPage` não é mais stub e o `ConnectDialog` foi reescrito (não removido).
- `/code-review high` de `main...area-logada` e correções:
  - corrida no localStorage: os repositórios de anúncios e contas leem e gravam sem `await` no meio (latência e senha antes);
  - violação de camada: o `connectionsRepository` não importa mais o domínio (a regra `canConnectMore` chega pela aplicação);
  - criar anúncio: a comemoração só depois de gravar; o rascunho sai antes de gravar (fotos não ocupam o espaço duas vezes) e volta se der erro; autosave cancelado ao publicar; IA com tratamento de erro (texto novo `ai.error`);
  - rascunho: fotos numa chave própria (`usuario:<id>:rascunho_fotos`), regravadas só quando mudam;
  - reativar anúncio pausado exige o ML conectado (texto `resumeBlocked`);
  - cor do avatar escolhida sem salvar volta ao sair das configurações;
  - foco: tirada a cópia de restauração do `useMarketplaces` (o `useModal` já faz);
  - mantido de propósito: o título "QuickClick" (pedido do André).
- Auditoria, extras: textos fixos foram para o content (`BRAND.name`, separadores dos insights), Termos e Privacidade viraram botões com aviso "em breve", `#000` do `AiScene.css` virou token, botão final do criar anúncio diz "Salvar anúncio" quando não vai publicar.
- Achado no roteiro: os toasts (canto inferior direito) cobriam os botões das linhas do painel. Agora ficam no canto inferior esquerdo.
- `main.py`: folga de 5 s na comparação do `package-lock.json`. `.git/info/exclude` ganhou `/QuickClick/` (o clone duplicado não entra num `git add .`).
- Roteiro completo no Chrome headless (scripts no scratchpad, pelo DevTools Protocol), sem erros no console: cadastro, navbar com nome e avatar, menu, sair e entrar; criar anúncio com foto, IA, preço, canais e salvar; conectar, sincronizar, desconectar e conectar de novo o ML; publicar, pausar, reativar, duplicar, excluir e editar; insights com "Simulação"; perfil, cor, senha (errada e certa) e preferências; segunda conta isolada; excluir a segunda (senha errada e certa); a primeira intacta. Vitrine: as 9 cenas com os logos certos (`.screens/etapaC-vitrine-1440-folha.jpg`). Screens em `.screens/etapaC-*`.
- Build ok, 55 testes ok.

Próximos passos: F (MarketplaceScene e placas), G (telas no padrão da landing), H (docs: CLAUDE.md, README, area-logada.md com a chave `rascunho_fotos`, toasts à esquerda, TikTok Shop) e I (Run 'main' do André, roteiro em 1440 e 390 na aba visível, grep da regra de escrita, /code-review, git status).

## Etapa D · Título da aba (feito)

- `frontend/index.html`: `<title>QuickClick</title>`. Nenhum código troca o `document.title` (procurado em `frontend/src`), então a aba fica "QuickClick" em todas as telas. Build ok; o `dist/index.html` já sai com o título novo.
- Feita antes do roteiro da Etapa C porque a extensão do Chrome ainda não estava conectada.

## Etapa E · Logo do TikTok Shop (feito)

- Busca: o Commons não tem nenhum arquivo do TikTok Shop (busca por título e a categoria "TikTok logos"). As páginas oficiais (`seller-br.tiktok.com`, `seller-us.tiktok.com`) montam o cabeçalho por JavaScript; o logo estava nos pacotes JS oficiais.
- Escolhido: `logo.1e4a311e.svg`, o logo do cabeçalho da Central do Vendedor do Brasil, servido pelo CDN da TikTok (`lf16-scmcdn.oecstatic.com/.../TTS/normal/main/static/media/logo.1e4a311e.svg`). SVG 80×32, versão empilhada ("TikTok" sobre "Shop"), escrita branca com o ciano #25F4EE e o vermelho #FE2C55. Byte a byte igual ao `src/assets/images/logo.svg` embutido no JS da Central. Sem script, eventos, `foreignObject` ou links.
- Alternativa oficial vista (não usada): `tts_logo.316b4170.svg`, versão horizontal do login da Central dos EUA (`lf16-cdn-tos.tiktokcdn-us.com/.../account/static/media/`).
- Ligado: `assets/marketplaces/tiktok-shop.svg` (cópia idêntica), `LOGOS` do `MarketplaceLogo`, linha nova no `FONTES.md` (origem, data, hash), comentários "TikTok Shop não tem logo" tirados do `MarketplaceLogo`, `MarketplaceMark` e `marketplacesContent.js`.
- A escrita do logo é branca: na paleta, `deep` e `glow` pretos e `stage: 'dark'`; o `BrandBackdrop` ganhou o modificador `--dark-stage` (a luz do centro escurece; variável `--brand-glow-edge`). Fora das cenas, o `MarketplaceLogo` dá um fundo escuro ao logo (`marketplace-logo--light-art`, usado na lista "em breve" do criar anúncio, que é clara).
- Conferido (Chrome headless pelo DevTools Protocol, porque a extensão ainda não conectou): cena do TikTok Shop na vitrine em 1440 e 390, logo grande e legível, sem erros no console. `.screens/etapaE-tiktok-vitrine-1440.jpg` e `-390.jpg`.

# Histórico · prompt v4

## Etapa 0 · Diagnóstico (08/10/2026)

- Pasta: `C:\Users\PC\PycharmProjects\QuickClick`, branch `main`, remoto `andretozi/FrontendQuickClick`. Mudanças da sessão anterior sem commit (38 alterados, cerca de 90 novos).
- PyCharm: SDK "Python 3.14" (`AppData\Local\Programs\Python\Python314\python.exe`), script `$PROJECT_DIR$/main.py`, pasta de trabalho `$PROJECT_DIR$`. Tudo certo.
- Python 3.14: fastapi, uvicorn e httpx instalados. No Git Bash o `python` é o alias da Microsoft Store; use `py` ou o caminho completo.
- Node 24.15, npm 11.12.
- `npm run build`: ok. Testes do back: 55 ok. `main.py` com `NO_BROWSER=1`: `/api/health` ok, página inicial ok, console sem erros.
- Logos: 8 SVGs em `frontend/src/presentation/assets/marketplaces` com `FONTES.md`, todos carregando. TikTok Shop sem SVG livre: monograma.

## Status das etapas

| Etapa | Status |
|---|---|
| 0 · Diagnóstico | feito |
| 1 · Navbar de vidro | feito |
| 2 · Vitrine tela cheia | feito |
| 3 · Conta no navegador | feito |
| 4 · Navbar logada e menu | feito |
| 5 · Painel e insights | feito |
| 6 · Criar anúncio | feito |
| 7 · Marketplaces | feito |
| 8 · Configurações | feito |
| Docs finais | feito |

## Diário

### Etapa 1 · Navbar (feito)
- Vidro sempre ligado (blur 12px, saturate 1.2, fundo creme a 4%, linha clara embaixo). Textos todos em coral, hover coral glow. Entrar e Criar anúncio: contorno coral (classe `site-nav__outline`). Começar grátis segue coral com texto branco.
- Decisão do André: o "Quick" do logo acompanha o fundo. `Section` agora expõe `data-surface` (light ou dark); a vitrine também. `animation/landing/navigation.js` marca `site-nav--over-dark` e o `site-nav__brand` fica creme.
- Menu do usuário: primeiro nome em coral ao lado do avatar, botão em vidro neutro.
- Arquivos: SiteNav.jsx e .css, UserMenu.jsx e .css, Section.jsx, Marketplaces.jsx (data-surface), navigation.js.
- Screens: .screens/etapa1-*.jpg
- Atenção: vários arquivos têm CRLF; edições por script precisam normalizar as quebras de linha.

### Etapa 2 · Vitrine em tela cheia (feito)
- Os logos não estavam quebrados nesta sessão (todos carregam pelo import do Vite); o problema era a vitrine antiga. Ela foi refeita do zero.
- Seção `#marketplaces` com 100% de largura e 100svh, uma cena por marketplace (`data-part="slide"`), título coral em Fraunces com sombra difusa, que vira creme onde o coral some (`titleTone` da paleta).
- Paletas tiradas dos SVGs (fill e stop-color) em `MARKETPLACE_PALETTES` (`domain/content/marketplacesContent.js`). Palavras em `SHOWCASE_WORDS` ("Já integrado" e "Em breve").
- Novo `BrandBackdrop` (presentation/components): malha de degradês, manchas desfocadas, faixas de luz, luz central atrás do logo, vinheta e grão. Imagem opcional em `assets/marketplaces/fundos/<slug>.webp` (ver LEIAME.md da pasta).
- Novo motor `infrastructure/animation/core/particleField.js`: um canvas com DPR, explosão (gravidade, arrasto e giro), molas até pontos sorteados da palavra em Fraunces, a palavra acende nítida e depois se desfaz. O laço para quando não há nada e pausa fora da tela.
- `ParticleBurst` agora é um `<canvas>` que usa esse motor (a vitrine e as boas vindas já usam; publicar e conectar vão usar). O `burst` antigo de DOM e o `ballisticKeyframes` foram removidos.
- Cena reescrita em `landing/scenes/marketplaces.js`: a próxima entra pela esquerda e a atual sai pela direita, numa mola com parallax (o fundo a 58%, o logo a 128%); cursor 2,5 vezes maior, com mola no clique, logo amassando, anel grande, 80 partículas (40 no celular) e a palavra. `MARKETPLACE_SHOWCASE_SCENE_MS = 5000` e `SHOWCASE_PARTICLES` em `core/config.js`.
- Acessibilidade: lista escondida com "Mercado Livre, já integrado" e os outros.
- Screens: `.screens/etapa2-*` (1440, 390 e GIF).

### Etapa 3 · Conta no navegador (feito; as páginas das rotas privadas entram nas Etapas 5 a 8)
- Saíram a conta de demonstração e o botão dela: `demoSeed.js`, `DEMO_CREDENTIALS`, `signInWithDemo`, `DemoBadge` e os textos. O selo virou `SIMULATION_BADGE` ("Simulação"), usado nos insights.
- Chaves por conta: `quickclick:v1:usuario:<id>:anuncios`, `:conexoes`, `:preferencias` e `:rascunho` (`userKey` e `USER_KEYS` em `localStore.js`). `contas` e `sessao` continuam globais. `clearUser(id)` apaga tudo de uma conta.
- Limpeza única do formato antigo: se existir `quickclick:v1:semente`, somem as coleções globais, a conta demo e a sessão dela (`dropLegacyData`).
- `deleteAccount(id, senha)` em `accountsRepository.js`, para a Zona de risco.
- Login: email ou senha errados mostram a mensagem embaixo da senha (`invalid-credentials`, com aria-describedby). Os botões sociais já mostravam o toast de "em breve"; o texto foi ajustado.
- `#/cadastro` ligado no `App.jsx`. Testado no Chrome: validação por campo e criação da conta com hash e sal, levando ao `#/painel`.
- Conta de teste usada nas verificações: "Marina Teste", marina@teste.dev, senha Marina2026 (só existe no navegador de teste).

### Etapa 4 · Navbar logada e menu (feito)
- Já existia (`UserMenu`, `Avatar`, `useMenu`, `useRovingKeys`). Conferido no Chrome: abre com mola, setas andam pelos itens, Esc fecha e devolve o foco, clique fora fecha. Mostra nome, email e o selo do plano; itens Marketplaces, Configurações, Ver site e Sair.
- Ajustes: primeiro nome em coral, botão em vidro neutro e fundo do menu quase opaco (dentro da navbar o backdrop-filter não alcança a página).
- `App.jsx`: as páginas privadas moram dentro de um `AppShell` que fica montado entre uma página e outra (transição suave pelas entradas `data-enter`).

### Etapa 5 · Painel e insights (feito; conferir de novo com anúncios depois da Etapa 6)
- Nova `DashboardPage` com saudação pelo horário, loja (eyebrow), selos de plano e conexões, 4 `StatCard` com contagem, `SegmentedControl` Anúncios e Insights e modal próprio para excluir.
- `ListingsPanel` (busca, filtro, ordenação, estados de carregando, erro, vazio e sem resultados) e `ListingRow` (foto, título, preço, estoque, atualização, canais e ações).
- `ListingChannels`: logo real do ML com a situação e os outros apagados como "em breve", com brilho passando.
- Gráficos em SVG próprio (`presentation/components/charts`): `AreaChart` (faturamento, tooltip por mouse e teclado, tabela escondida para leitor de tela), `BarChart`, `DumbbellChart`, `DonutChart`, `ChartTooltip` e `ChartLegend`. A entrada animada fica em `infrastructure/animation/charts/charts.js` (data-chart-*).
- `insightsService`: sem anúncios devolve null (estado vazio); o volume simulado cresce com os anúncios publicados. Selo `SimulationBadge`.
- Novo `core/loops.js` (data-shimmer e data-spin) ligado pela casca; nada de @keyframes novos no CSS.
- Correção: `entrances.js` também observa o atributo data-enter (o React reaproveitava o elemento do "carregando" e a entrada não disparava).

### Etapa 6 · Criar anúncio (feito)
- `ListingEditorPage` (`pages/listing`), usada em `#/anuncios/novo` e `#/anuncios/:id`, com os passos `PhotosStep`, `DetailsStep`, `PriceStep`, `ChannelsStep`, `PublishStep` e a tela `PublishSuccess`.
- Caso de uso `application/listings/useListingEditor.js`: passos com validação (`validateListingStep`), rascunho salvo sozinho por conta (só no criar, nunca vazio), IA simulada, faixa de preço, publicar ou salvar fora do ar, edição.
- Infraestrutura nova: `media/imageResizer.js` (canvas, 800 px, JPEG) e `ai/suggestionService.js` (SIMULADO: cor média da capa e modelos por categoria; faixa de preço por categoria e condição).
- Componentes novos: `Stepper` (trilho com mola), `FileDrop` (+ `useFileDrop`), `PriceRuler`, `ListingPreview` (prévia no ML) e `Toggle`.
- Comemoração reutilizável: `infrastructure/animation/app/celebrate.js` + `useCelebration` (cursor, clique com mola, explosão e a palavra "Publicado" ou "Salvo"). Também vai servir para o conectar.
- Testado no Chrome: foto (gerada em canvas), IA, régua, canais sem ML conectado, salvar, sucesso, painel e abertura da edição.
- Correções no motor de partículas: as que caem um pouco abaixo da tela não somem mais antes de formar a palavra, e a palavra aparece mesmo sem partículas.
- Atenção: na sessão de teste, a janela do Chrome ficou "hidden" (visibilityState), o que congela rAF e WAAPI. Para os GIFs, a janela precisa estar visível.

### Etapa 7 · Marketplaces (quase pronta; retomar daqui)
Feito:
- Removidos a página antiga (MarketplaceGrid, MarketplaceCard, ConnectDialog, PlanPanel) e as animações dela (`animation/marketplaces`, `useMarketplacesAnimations`, `useConnectedEffect`, `useDialogAnimations`, `useCardsEntrance`). O `marketplacesService` e o `httpClient` continuam no projeto, sem uso, para quando o back voltar.
- `application/marketplaces/useMarketplaces.js` reescrito sobre o `connectionsRepository` (localStorage, por conta): passos `CONNECT_STEPS` (confirmar, "Indo para o Mercado Livre", autorizando, conectado, limite e erro), sincronizar com progresso simulado e desconectar com modal. O limite vem de `planRules`.
- Componentes compartilhados (as Configurações também usam): `MarketplaceBoard` (aviso do plano com link para #planos, a grade e os dois diálogos), `MarketplacePlate` (placa grande com `BrandBackdrop` nas cores da marca; em breve: apagado e com brilho) e `ConnectDialog` (amarelo da marca no redirecionamento; "Conectado" com cursor, check se desenhando e a palavra em partículas).
- `Modal` ganhou o espaço `media` (acima do título). O modal liga `observeLoops` (spinners e brilhos funcionam no portal).
- `celebrate.js` desenha o check (`data-part="celebrate-check"`) e põe a palavra sempre acima do alvo.
- Nova `MarketplacesPage`, com topo cinematográfico no amarelo do ML, título "Suas lojas, conectadas." e o quadro.
- Testado no Chrome: abrir, confirmar, redirecionar, autorizar e conectar (a palavra "Conectado" aparece).
Falta nesta etapa:
- Conferir no Chrome: fechar o diálogo, placa conectada (apelido, conectado desde), "Sincronizar agora" com a barra e "Desconectar" com modal.
- Exportar o GIF da conexão para `.screens` (a gravação foi interrompida pelo limite de uso).

## Próximos passos (para a próxima sessão)
1. Terminar a verificação da Etapa 7 (acima).
2. Etapa 8 · Configurações: `pages/settings/SettingsPage.jsx` hoje é um STUB TEMPORÁRIO (devolve null). Fazer: navegação lateral com indicador (`useIndicator` e `SegmentedControl` vertical já existem), que vira abas no celular. Seções: Perfil (nome, email, telefone, loja e cor do avatar; usar `updateAccount` e `setSessionAccount`), Segurança (`changePassword`), Plano (comparação dos 4 planos, sem pagamento, "R$ __ por mês"), Conexões (`<MarketplaceBoard compact />` com `useMarketplaces`), Preferências (`Toggle` com `getPreferences` e `savePreferences`), Zona de risco (`deleteAccount(id, senha)` com modal e depois `forgetSession`). Salvar mostra toast.
3. Docs: atualizar o CLAUDE.md (logos oficiais permitidos com FONTES.md, monograma como reserva; só o ML disponível no front, com o catálogo do back como pendência; navbar de vidro com textos em coral; fundos das marcas em código com a imagem opcional; telas e rotas novas; login no navegador sem banco e sem conta pré-criada; "O Claude Code não faz commit nem push; quem commita é o André"), o README e criar o `docs/area-logada.md` (telas, chaves do localStorage, o que é simulado e como trocar pela API).
4. Conferência final: `npm run build`, testes do back, grep da regra de escrita (sem travessão, meia risca, hífen ou barra em texto de tela, exceto NF-e), roteiro completo no Chrome (com a janela VISÍVEL) e GIFs do cadastro, login e criar anúncio. Depois `/code-review` e `git status`.
- (09/10) Etapa 7 conferida: placa conectada com apelido e "conectado desde", "Sincronizar agora" com barra e toast, "Desconectar" com modal (a chave de conexões fica vazia). GIF em `.screens/etapa7-conectar-ml.gif`.

### Etapa 8 · Configurações (feito)
- `SettingsPage` com navegação lateral (`SegmentedControl` vertical com indicador de mola) que vira uma fileira de abas no celular.
- Seções em `pages/settings/components`: `ProfileSection` (nome, email, telefone, loja e cor do avatar; a navbar muda na hora), `SecuritySection` (troca de senha, confere a atual), `PlanSection` (os 4 planos com o atual em destaque, "R$ __ por mês", troca em breve), Conexões (`MarketplaceBoard compact`), `PreferencesSection` (`Toggle` que salva na hora) e `DangerSection` (excluir a conta com modal que pede a senha; apaga tudo da conta e encerra a sessão).
- Caso de uso `application/settings/useSettings.js`. Textos em `domain/content/settingsContent.js`. Novo erro `password-incorrect`.
- Testado no Chrome: perfil (a conta de teste virou "Marina Souza", avatar verde), senha errada, preferência gravada em `usuario:<id>:preferencias`, 390 px.

### Docs (feito)
- CLAUDE.md: logos oficiais com FONTES.md (o monograma é só reserva), navbar de vidro em coral, fundos das marcas em código com imagem opcional, partículas e laços, telas e rotas novas, área logada sem banco e sem conta pré criada, só o ML no front (pendência do catálogo do back) e "O Claude Code não faz commit nem push; quem commita é o André".
- README: tabela de telas nova e a seção da tela de marketplaces.
- Novo `docs/area-logada.md`: telas, chaves do localStorage, o que é simulado e como trocar pela API.

### Conferência final (09/10)
- `npm run build` sem erros nem avisos; 55 testes do back passando; `main.py` servindo em 127.0.0.1:8080.
- Regra de escrita: script varreu `domain/content` e `index.html`, sem travessão, meia risca, hífen ou barra em texto de tela (fora a NF-e). O "R$" e o "0,00" do preço saíram do componente e foram para o content.
- Camadas do front: a presentation não importa infrastructure (só comentários citam), domain e infrastructure não importam outras camadas, `fetch` só no httpClient.
- Roteiro no Chrome: cadastro com validação, sair, segunda conta (Rafael) com painel vazio e boas vindas, exclusão da segunda conta (senha errada, depois certa; chaves apagadas), login de volta com a Marina e o anúncio dela intacto, insights com o selo Simulação, conectar, sincronizar e desconectar o ML, editar perfil, senha e preferências.
- Correção: ao sair numa página privada, a guarda mandava para o login (corrida ao zerar o "acabou de sair"); agora vai para a landing.
- Pendente: GIF do fluxo de cadastro, login e criar anúncio (a janela do Chrome precisa estar visível; com ela oculta, o navegador congela rAF e WAAPI).

### Revisão de código (/code-review medium)
Corrigido:
- Desconectar e sincronizar agora têm tratamento de erro, com toast. Sincronizar uma conexão que sumiu não mostra mais "sincronizado".
- `openConnect` ignora marketplace já conectado.
- O limite do plano e o "em breve" também são conferidos no `connectionsRepository` (o "servidor"), com `ConnectionError`; o diálogo mostra o passo de limite.
- O redirecionamento para o login guarda a query da página privada.
Mantido de propósito (pedido do prompt v4): área logada no localStorage em vez da API, logos oficiais (o CLAUDE.md já foi atualizado) e o catálogo do back desalinhado, registrado como pendência.
Não corrigido (fora do escopo, pequeno): na landing, ir de `#planos` para `#/` não rola até o topo (o logo usa `#top`, que funciona).
