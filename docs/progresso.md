# Progresso · prompt v4

Arquivo de retomada. Se a sessão cair, a próxima começa por aqui. Atualizado ao fim de cada etapa.
Regra: o Claude Code não faz commit nem push; quem commita é o André.

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
