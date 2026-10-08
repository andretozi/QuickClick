# Quick Click

**Clicou, vendeu.** Automação de vendas multicanal com inteligência artificial, para pequenos e grandes vendedores. A Quick Click se conecta às contas que o vendedor já tem no Mercado Livre, na Shopee, na Amazon e em outros marketplaces e assume a operação de venda.

Projeto acadêmico de Projetos de Engenharia da Computação, Mackenzie, 2026.
André Tozi Magalhaes (PO e dev) e Guilherme Diego Sanches (SM e dev).

**Stack**

- Front: React 18 + Vite 5, CSS puro no padrão BEM e animações com a Web Animations API.
- Back: Python 3.14 com FastAPI + Uvicorn e banco SQLite.

## Como rodar

Pré-requisitos:

- **Node.js 18 ou mais novo.** Confira com `node -v`.
- **Python 3.10 ou mais novo.** O projeto usa o 3.14.

| Jeito | Comando | Endereço |
|---|---|---|
| PyCharm | botão **Run ▶ 'main'** | abre sozinho em http://127.0.0.1:8080 |
| Terminal | `python main.py` (no Windows também `py main.py`) | http://127.0.0.1:8080 |

O `main.py` faz tudo em ordem:

1. Roda `npm install` e `npm run build` dentro de `frontend/` quando precisa.
2. Instala com pip o que faltar de `backend/requirements.txt`, no mesmo Python que roda o `main.py`.
3. Sobe um único servidor em `127.0.0.1:8080`, com a API em `/api` e o front buildado no resto.
4. Abre o navegador.

A documentação automática da API fica em http://127.0.0.1:8080/docs.

Variáveis úteis (no PowerShell, `$env:REBUILD=1; python main.py`):

| Variável | Efeito |
|---|---|
| `REBUILD=1` | força um build novo do front |
| `NO_BROWSER=1` | não abre o navegador |

### Modo de desenvolvimento (recarrega ao salvar)

1. Deixe o back rodando com `python main.py`, na porta 8080.
2. Em outro terminal, entre em `frontend/` e rode `npm run dev`. O site fica em http://localhost:5173.
3. O Vite repassa toda chamada `/api` para `127.0.0.1:8080`, então o front de desenvolvimento conversa com o back de verdade.

Para o back recarregar sozinho ao salvar, troque o passo 1 por:

```
python -m uvicorn backend.app.bootstrap:criar_app --factory --reload --port 8080
```

### Telas

| Endereço | Tela |
|---|---|
| `#/` | landing |
| `#/login` | login (simulado: "Entrar" leva para a tela de marketplaces) |
| `#/marketplaces` | conectar as contas que o vendedor já tem nos marketplaces |

Hashes sem barra (`#como`, `#marketplaces`, `#planos`) são seções da landing. De outra tela, um link `#planos` abre a landing já na seção de planos.

### Testes do back

Da raiz do projeto:

```
python -m unittest discover -s backend/tests -t .
```

No PyCharm, clique com o botão direito em `backend/tests` e escolha **Run 'Python tests in tests'**. Rode o `main.py` uma vez antes, para instalar as dependências.

## Arquitetura: monolito em camadas

O sistema é **uma aplicação só**, com um deploy e um processo (o `main.py`). O front é a camada de apresentação do sistema. O back repete as mesmas camadas do front.

```
┌────────────────────────────────────────────────────────────────────┐
│ frontend/  (apresentação do sistema: React, roda no navegador)     │
│   app → presentation → application → domain | infrastructure      │
└───────────────────────────────┬────────────────────────────────────┘
                                │ HTTP /api (mesmo endereço 127.0.0.1:8080)
┌───────────────────────────────▼────────────────────────────────────┐
│ backend/  (Python)                                                 │
│   app             liga as camadas e cria o FastAPI                 │
│   presentation    rotas HTTP /api e entrega do front buildado      │
│   application     casos de uso + portas (interfaces)               │
│   domain          entidades e regras de negócio, Python puro       │
│   infrastructure  configuração, SQLite, integrações com marketplaces│
└────────────────────────────────────────────────────────────────────┘
```

### Regras de dependência

**Front** (`frontend/src`). Cada camada só usa as de baixo:

```
app/             Raiz: liga as camadas e escolhe a página pela rota
   │
presentation/    Componentes React + CSS (BEM). Só desenha.
   │
application/     Hooks com os casos de uso das telas
   ├────────────────────────┐
domain/                infrastructure/
Textos e dados do      Tudo que fala com o navegador ou com
produto. Sem React,    serviços externos (animações, URL,
sem DOM.               chamadas à API)
```

- `presentation` usa `application` e lê dados do `domain`. Ela **nunca** importa `infrastructure` (e nunca chama `fetch`).
- `application` usa `domain` e `infrastructure`.
- `domain` e `infrastructure` não importam nenhuma outra camada.

**Back** (`backend/`). As setas apontam para quem é importado:

```
app ──► presentation ──► application ──► domain
 │                            ▲             ▲
 └──► infrastructure ─────────┴─────────────┘
      (implementa as portas declaradas na application)
```

- `domain` é Python puro: não importa nenhuma outra camada nem framework (nada de FastAPI, pydantic ou sqlite3).
- `application` importa só o `domain`. O que ela precisa de fora (banco, marketplaces) chega por **portas**, que são interfaces (`Protocol`).
- `infrastructure` implementa as portas e pode importar `domain` e `application`.
- `presentation` usa `application` e `domain`. Ela **nunca** importa `infrastructure`.
- Só `app` conhece todas as camadas e liga uma na outra.

O teste `backend/tests/test_arquitetura.py` confere essas regras lendo os imports de cada arquivo.

## Pastas

```
FrontendQuickClick/
├── main.py                 # Run 'main': build do front, dependências do back e servidor único
├── .env.example            # modelo de configuração local e de segredos futuros (copie para .env)
├── frontend/               # React + Vite
│   ├── index.html  package.json  vite.config.js
│   └── src/
│       ├── main.jsx        # ponto de entrada (estilos globais + <App />)
│       ├── app/            # App.jsx: rota → página
│       ├── presentation/   # styles/, utils/, components/ (Button, Icon, Brand, Section, Blob,
│       │                   # MarketplaceMark...), pages/ (landing, login, marketplaces)
│       ├── application/    # navigation/, animation/, auth/, marketplaces/ (useMarketplaces)
│       ├── domain/         # content/: todo o texto do site e o catálogo de marketplaces
│       └── infrastructure/ # browser/, auth/, http/ (o único fetch), marketplaces/ (serviço da API),
│                           # animation/ (core, landing, login, marketplaces)
└── backend/                # FastAPI
    ├── requirements.txt
    ├── app/                # bootstrap.py: criar_app() liga tudo e cria o vendedor de demonstração
    ├── presentation/http/  # api.py, rotas.py (/api), esquemas.py (JSON), erros.py, front.py
    ├── application/        # portas.py (interfaces) e casos_de_uso/ (um por arquivo)
    ├── domain/             # marketplace.py (catálogo), plano.py (regra do limite),
    │                       # vendedor.py, conta_vinculada.py, erros.py
    ├── infrastructure/     # config.py (.env), banco/ (SQLite), marketplaces/ (gateways OAuth)
    ├── data/               # quickclick.sqlite3, criado na execução (fora do Git)
    └── tests/              # unittest
```

## API

Documentação interativa em http://127.0.0.1:8080/docs.

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/health` | confere se a API está no ar |
| GET | `/api/plans` | planos de assinatura, do Grátis ao Business |
| GET | `/api/me` | vendedor atual: plano, marketplaces conectados e se cabe mais um |
| GET | `/api/marketplaces` | catálogo completo, com status (`disponivel` ou `em_breve`) e se está conectado |
| POST | `/api/marketplaces/{slug}/connection` | conecta a conta que o vendedor já tem no marketplace |
| DELETE | `/api/marketplaces/{slug}/connection` | desconecta e libera a vaga do plano |

Erros vêm sempre no mesmo formato, com uma mensagem pronta para a tela:

```json
{"erro": {"codigo": "limite_do_plano", "mensagem": "No plano Grátis você conecta 1 marketplace. Pra conectar mais, mude para o plano Pro.", "plano_sugerido": "pro"}}
```

| Status | Código | Quando |
|---|---|---|
| 404 | `marketplace_nao_encontrado` | o slug não existe no catálogo |
| 409 | `marketplace_em_breve` | o marketplace ainda está chegando |
| 403 | `limite_do_plano` | o plano já conectou o máximo de marketplaces |

Conectar o que já está conectado, ou desconectar o que não está, não dá erro.

### Regras de negócio

- **Planos:** Grátis (R$ 0 pra sempre), Essencial, Pro e Business, todos sem comissão sobre as vendas. Os preços dos pagos ainda não foram definidos (`preco_mensal_centavos: null`).
- **Limite de marketplaces:** Grátis e Essencial conectam 1. Pro e Business conectam vários, porque o multicanal começa no Pro (`backend/domain/plano.py`).
- **Catálogo:** Mercado Livre, Shopee e Amazon estão disponíveis. Magalu, Americanas, Casas Bahia, Shein, TikTok Shop e AliExpress vêm em breve (`backend/domain/marketplace.py`).

### Vendedor de demonstração e configuração

Ainda não existe login de verdade: a API sempre atende o vendedor de demonstração. O plano dele vem do `.env` (copie o `.env.example`):

```
QUICKCLICK_PLANO_DEMO=gratis   # gratis, essencial, pro ou business
QUICKCLICK_BANCO=backend/data/quickclick.sqlite3
```

Mudou o `.env`? Reinicie o `main.py`.

### Integração com os marketplaces: simulada

Cada marketplace tem um gateway OAuth 2.0 em `backend/infrastructure/marketplaces/`, com três operações: gerar a URL de autorização, trocar o código pelo token e renovar o token. Nesta versão os gateways são **simulados**: não acessam a rede e não usam credenciais, e os tokens são falsos (mas têm a validade real de cada canal).

O comentário de cada gateway descreve a integração real:

- **Mercado Livre:** API REST direta, sem os SDKs oficiais, que foram arquivados em 2022. O token vale 6 horas e é renovado por refresh token.
- **Amazon:** autorização pelo Seller Central e tokens pelo Login with Amazon.
- **Shopee:** Open Platform.

Com credenciais reais, a conexão vira duas etapas. O POST devolve a URL de autorização, o vendedor autoriza no marketplace e volta por um callback com o código.

### Tela de marketplaces

Em `#/marketplaces` o vendedor vê o plano (com o uso e o aviso do limite) e todos os marketplaces do catálogo. Ao clicar em **Conectar**:

1. uma confirmação explica que ele vai autorizar direto no marketplace e que a gente nunca vê a senha;
2. uma tela curta de "Autorizando…" aparece enquanto o back faz a conexão simulada;
3. o card vira **Conectado**, com o check se desenhando e uma onda saindo do monograma.

Erros do back, como o limite do plano, aparecem no próprio diálogo, com a mensagem dele e o caminho para os planos. Os monogramas são as iniciais de cada marketplace numa cor que lembra a marca dele; nenhum logo oficial é usado.

## Convenções do front

**Textos.** Todo texto de tela fica em `frontend/src/domain/content/`, inclusive os aria-labels. Os componentes não têm texto fixo.

**Regra de escrita.** Nenhum texto de tela usa traço (—, – ou -) nem barra (/). As frases são escritas com vírgula, ponto ou dois pontos, e palavras com hífen são evitadas ("Email", "Que bom te ver de novo"). A única exceção é a sigla NF-e.

**CSS com BEM.** Cada componente tem o próprio `.css` na mesma pasta.

- Bloco: `.hero`
- Elemento: `.hero__title`
- Modificador: `.button--dark`

Para posicionar um bloco dentro de outro usamos *mix*, por exemplo `class="blob blob--coral hero__blob hero__blob--a"`. O `blob` define a aparência e o `hero__blob` define a posição.

**Tokens.** Nenhuma cor é escrita direto nos componentes:

- cor sólida: `var(--color-coral)`;
- com transparência: `rgb(var(--rgb-ink) / 0.6)`.

**React.**

- Componentes funcionais e pequenos.
- Estado só nos hooks da camada `application`.
- Inputs controlados.
- Efeitos sempre com limpeza.
- O `StrictMode` fica ligado.

**Ganchos de animação.** O JavaScript nunca procura classes CSS. Ele usa atributos `data-*`:

| Atributo | Para que serve |
|---|---|
| `data-reveal="up\|down\|left\|right"` + `data-delay` | Entrada ao rolar até o elemento |
| `data-scene="nome"` | Toca a coreografia com esse nome quando a cena aparece |
| `data-part="nome"` | Parte animada dentro de uma cena |
| `data-blob` | Mancha de luz flutuando |
| `data-parallax` | Camada com parallax |
| `data-nav` | Menu que some e volta |
| `data-enter` | Entrada em sequência no login e na tela de marketplaces (topo, plano e cards) |

**Configuração das animações.** Fica em `frontend/src/infrastructure/animation/core/config.js`.

- Intensidade, repetição das cenas e parallax se ajustam ali.
- As animações rodam **sempre**, mesmo com "efeitos de animação" desligados no Windows (`respectReducedMotion: false`). Essa é uma decisão do projeto.

## Convenções do back

- Nomes do domínio em português, os mesmos da conversa com o negócio: `Marketplace`, `ContaVinculada`, `Plano`, `Vendedor`.
- Configuração local e segredos ficam no `.env`, que está fora do Git. O modelo é o `.env.example`. Segredo nunca vai para o código nem para o front.
- O banco SQLite fica em `backend/data/` e também está fora do Git.
