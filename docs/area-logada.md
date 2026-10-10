# Área logada (sem banco)

A área do vendedor funciona inteira no navegador, sem o back e sem banco, tanto no `npm run dev` quanto pelo `main.py`. Tudo fica no `localStorage`, atrás de repositórios em `frontend/src/infrastructure/storage`, que imitam a API futura (nomes em português, Promises e latência simulada). Para ligar o back, só o corpo desses repositórios muda: os hooks e as telas continuam iguais.

Não existe conta pré-criada nem conta de demonstração. Cada vendedor cria a sua em `#/cadastro`, e várias contas podem conviver no mesmo navegador sem misturar dados.

## Telas

| Rota | Tela | O que faz |
|---|---|---|
| `#/cadastro` | `SignupPage` | Nome, email, nome da loja, senha e confirmação, com a mensagem de erro embaixo de cada campo. Entra direto e mostra as boas vindas no painel. |
| `#/login` | `LoginPage` | Email e senha. Erro de credencial embaixo da senha. Google, Apple e Facebook mostram "em breve". |
| `#/painel` | `DashboardPage` | Saudação, números da loja e as abas Anúncios (busca, filtro, ordenação, editar, pausar, duplicar e excluir) e Insights (gráficos com o selo "Simulação"). |
| `#/anuncios/novo` | `ListingEditorPage` | Assistente em 5 passos: fotos, detalhes (com a IA simulada), preço (régua), canais e publicar. O rascunho é salvo sozinho. |
| `#/anuncios/:id` | `ListingEditorPage` | O mesmo formulário, para ver e editar. |
| `#/marketplaces` | `MarketplacesPage` | Conectar o Mercado Livre (fluxo OAuth simulado), sincronizar e desconectar. Os outros aparecem "em breve". |
| `#/configuracoes` | `SettingsPage` | Perfil, segurança, plano, conexões, preferências e zona de risco (excluir a conta). |
| outra | `NotFoundPage` | A 404. |

As rotas privadas sem sessão vão para `#/login?volta=<rota>` e voltam ao destino depois de entrar. A sessão continua depois de recarregar a página e "Sair" encerra a sessão.

## Chaves do localStorage

Todas começam com `quickclick:v1:`.

| Chave | Conteúdo | Repositório |
|---|---|---|
| `contas` | Lista de contas: id, nome, email, telefone, loja, plano, cor do avatar e a senha como `{ algoritmo, sal, hash }` | `accountsRepository.js` |
| `sessao` | `{ conta_id, iniciada_em }` da conta logada | `sessionRepository.js` |
| `usuario:<id>:anuncios` | Anúncios da conta, com as fotos já reduzidas (data URL em JPEG) | `listingsRepository.js` |
| `usuario:<id>:conexoes` | Marketplaces conectados: apelido, conectado em, sincronizado em | `connectionsRepository.js` |
| `usuario:<id>:preferencias` | Avisos de venda, estoque baixo e dicas de preço | `preferencesRepository.js` |
| `usuario:<id>:rascunho` | O rascunho do "criar anúncio" (passo e campos) | `draftsRepository.js` |

Excluir a conta apaga a entrada em `contas` e todas as chaves `usuario:<id>:...` (`clearUser`). Se o navegador bloquear o localStorage, os dados ficam só na memória até a página fechar. Se o espaço acabar (fotos), a tela mostra um aviso (`StorageFullError`).

Na primeira abertura depois desta versão, uma limpeza única tira o formato antigo: as coleções globais e a conta de demonstração da versão anterior (`dropLegacyData` em `localStore.js`).

## O que é simulado

- **Senha:** SHA-256 com sal, via `crypto.subtle` (`infrastructure/security/passwordHasher.js`). Não é segurança de verdade: com o back, a senha vai por HTTPS e é guardada com um algoritmo lento (Argon2, scrypt ou bcrypt).
- **IA do anúncio:** `infrastructure/ai/suggestionService.js` lê a cor média da capa e escolhe um modelo de anúncio por categoria. Nenhuma foto sai do navegador.
- **Faixa de preço:** o mesmo serviço monta mínimo, sugerido e máximo a partir da categoria e da condição.
- **Conexão com o Mercado Livre:** o fluxo de autorização (confirmar, ir ao Mercado Livre, autorizar) é só visual. O apelido da conta sai do nome da loja e a sincronização só espera e atualiza a hora.
- **Publicar:** o anúncio fica marcado como publicado no Mercado Livre, mas nada é enviado.
- **Insights:** `infrastructure/insights/insightsService.js` simula 30 dias de vendas a partir dos anúncios da conta (sempre iguais para a mesma conta). Sem anúncios, a aba mostra o estado vazio.

## Como trocar pela API

1. Em cada repositório de `infrastructure/storage`, troque o corpo das funções por chamadas ao `httpClient` (`infrastructure/http/httpClient.js`), mantendo os nomes e o formato devolvido. Rotas sugeridas: `POST /api/contas`, `POST /api/sessao`, `DELETE /api/sessao`, `GET /api/me`, `GET|POST|PATCH|DELETE /api/anuncios`, `GET|POST|DELETE /api/marketplaces/:slug/conexao`, `POST /api/marketplaces/:slug/sincronizar`, `GET|PUT /api/preferencias`, `GET /api/insights`.
2. `infrastructure/auth/authService.js` passa a usar o cookie de sessão do back; o `sessionRepository` deixa de existir.
3. `passwordHasher.js` e `imageResizer.js` (a foto original vai para o armazenamento de arquivos) deixam de ser usados.
4. `marketplacesService.js` já fala com a API atual do back (`/api/marketplaces`). Antes de ligar, alinhe o catálogo: o back ainda marca Shopee e Amazon como disponíveis (pendência registrada no `CLAUDE.md`).
5. Os casos de uso em `application/` e as telas não mudam.
