# Quick Click

## Configuração em um PC novo (faça uma vez, antes do Run 'main')

Só o código vem no Git. A configuração do PyCharm **não vem**, porque a pasta `.idea/` está no `.gitignore`. Então, em cada computador novo, repita estes quatro passos antes de clicar em **Run 'main'**:

**1. Instale o Python e o Node.** Python **3.11 ou mais novo** (o projeto usa o 3.14) e Node.js **18 ou mais novo** (LTS). Se instalar algum dos dois com o PyCharm já aberto, **feche e reabra o PyCharm**: programa instalado com a IDE aberta só entra no PATH dela quando ela é reaberta.

**2. Crie a `.venv` na raiz do projeto**, pelo terminal:

```powershell
py -3.14 -m venv .venv
```

(com outra versão a partir da 3.11, troque o número: `py -3.12`)

**3. Instale as dependências Python, todas de uma vez:**

```powershell
.venv\Scripts\python -m pip install -r requirements.txt
```

Esse passo é opcional: o `main.py` instala sozinho, na primeira execução, o que faltar aqui e também as dependências do front (`npm ci`). E se na hora de subir o servidor ainda faltar alguma peça, ele roda o `requirements` de novo por conta própria e tenta mais uma vez antes de desistir.

**4. Aponte o interpretador do PyCharm para a `.venv`.** É o passo que mais trava o Run 'main':

> **Settings → Project: QuickClick → Python Interpreter → Add Interpreter → Add Local Interpreter → Select existing →** `.venv\Scripts\python.exe`

Sem isso o PyCharm usa outro Python, que não tem as dependências do projeto: o editor marca `import fastapi` e `import uvicorn` como não resolvidos, o painel de pacotes não funciona e o Run 'main' pode falhar antes mesmo de começar.

Feito isso, escolha a configuração **main** e clique em **Run 'main'**.

### Se o Run 'main' não funcionar

Rode pelo terminal. Não depende do PyCharm e funciona sempre:

```powershell
.venv\Scripts\python main.py
```

### Outros detalhes

- **No Mac e no Linux** os caminhos mudam: crie a `.venv` com `python3 -m venv .venv` e troque `.venv\Scripts\python.exe` por `.venv/bin/python`.
- **O `.env` é opcional.** Sem ele o projeto roda com os padrões. Crie um, copiando o `.env.example`, só se quiser trocar o plano do vendedor de demonstração ou o caminho do banco.
- **O banco não precisa de nada:** o arquivo SQLite e a pasta `backend/data/` são criados na primeira execução.

---

**Clicou, vendeu.** Automação de vendas multicanal com inteligência artificial, para pequenos e grandes vendedores. A Quick Click se conecta às contas que o vendedor já tem no Mercado Livre, na Shopee, na Amazon e em outros marketplaces e assume a operação de venda.

Este repositório é o **MVP**: a landing, o cadastro e o login, o painel com anúncios e insights, o criar anúncio em 5 passos, a conexão com o Mercado Livre e as configurações da conta. A área logada funciona no próprio navegador (localStorage, separado por conta), com a IA, a conexão e as vendas simuladas. O back em FastAPI já serve a API de planos e marketplaces.

Projeto acadêmico de Projetos de Engenharia da Computação, Mackenzie, 2026.
André Tozi Magalhaes (PO e dev) e Guilherme Diego Sanches (SM e dev).

## Como rodar

Com a `.venv` criada e o interpretador apontado (veja **Configuração em um PC novo**, no começo): no PyCharm, escolha a configuração **main** e clique em **Run 'main'**. Pelo terminal: `.venv\Scripts\python main.py`.

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
├── requirements.txt  instala as dependências Python de uma vez (aponta para backend/requirements.txt)
└── .env.example   modelo do .env (configuração local e segredos, que ficam fora do Git)
```
