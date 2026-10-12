# Quick Click

**Clicou, vendeu.** Automação de vendas multicanal com inteligência artificial, para pequenos e grandes vendedores. A Quick Click se conecta às contas que o vendedor já tem no Mercado Livre, na Shopee, na Amazon e em outros marketplaces e assume a operação de venda.

Este repositório é o **MVP**: a landing, o cadastro e o login, o painel com anúncios e insights, o criar anúncio em 5 passos, a conexão com o Mercado Livre e as configurações da conta. A área logada funciona no próprio navegador (localStorage, separado por conta), com a IA, a conexão e as vendas simuladas. O back em FastAPI já serve a API de planos e marketplaces.

Projeto acadêmico de Projetos de Engenharia da Computação, Mackenzie, 2026.
André Tozi Magalhaes (PO e dev) e Guilherme Diego Sanches (SM e dev).

## Como rodar

Precisa do **Python 3.11 ou mais novo** (o projeto usa o 3.14) e do **Node.js 18 ou mais novo**.

1. Na raiz do projeto, crie a `.venv`: `py -3.14 -m venv .venv` (com outra versão a partir da 3.11, troque o número, por exemplo `py -3.12`).
2. No PyCharm, escolha a configuração **main** e clique em **Run 'main'**. Pelo terminal: `.venv\Scripts\python main.py`.

O `main.py` instala o que falta (`npm ci` no front e o `backend/requirements.txt` no Python da `.venv`), builda o front quando ele mudou e sobe tudo num servidor só, em http://127.0.0.1:8080: o site, a API em `/api` e a documentação da API em `/docs`. Com `NO_BROWSER=1` ele não abre o navegador; com `REBUILD=1` ele força um build novo.

**Modo de desenvolvimento (recarrega ao salvar):** com o `main.py` rodando, entre em `frontend/` e rode `npm run dev`. O site fica em http://localhost:5173 e as chamadas `/api` vão para o back da porta 8080.

**Conferências:** em `frontend/`, `npm run check` (imports e camadas) e `npm run build`; na raiz, os testes do back com `.venv\Scripts\python -m unittest discover -s backend/tests -t .`.

## Pastas

```
QuickClick/
├── .run/          configuração "main" do PyCharm: roda o main.py com o Python da .venv
├── backend/       API em Python (FastAPI e SQLite), em camadas: app, presentation, application, domain, infrastructure e tests
├── frontend/      site em React e Vite; o código fica em src/, nas mesmas camadas: app, presentation, application, domain e infrastructure
├── main.py        Run 'main': dependências, build do front e servidor único em 127.0.0.1:8080
└── .env.example   modelo do .env (configuração local e segredos, que ficam fora do Git)
```
