# Quick Click — Front-end

Landing page animada da Quick Click ("Clicou, vendeu.") e tela de login.
Projeto acadêmico — Projetos de Engenharia da Computação, Mackenzie, 2026/2.

**Stack:** React 18 + Vite 5, CSS puro no padrão BEM e animações com a Web Animations API, sem bibliotecas extras.

## Como rodar

Pré-requisitos:

- **Node.js 18 ou mais novo.** Confira com `node -v`.
- **Python 3.8 ou mais novo**, só se for usar o `main.py`.

| Jeito | Comando | Endereço |
|---|---|---|
| PyCharm | botão **Run ▶ 'main'** | abre sozinho em http://127.0.0.1:8080 |
| Terminal (versão final) | `python main.py` | http://127.0.0.1:8080 |
| Terminal (desenvolvimento, recarrega ao salvar) | `npm install` e depois `npm run dev` | http://localhost:5173 |

O `main.py` instala as dependências se faltarem, gera o build quando o código muda e abre o navegador.
Para forçar um build novo no PowerShell, rode `$env:REBUILD=1; python main.py`.

Rotas: `#/` abre a landing e `#/login` abre o login. Hashes sem barra (`#como`, `#preco`) são âncoras dentro da página.

## Arquitetura: monolito em camadas

O front é um único aplicativo (um build, um deploy) organizado em quatro camadas. Cada camada só pode usar as camadas abaixo dela:

```
app/             Raiz: liga as camadas e escolhe a página pela rota
   │
presentation/    Apresentação: componentes React + CSS (BEM). Só desenha.
   │
application/     Aplicação: hooks com os casos de uso das telas
   │             (rota atual, animações da página, formulário de login)
   ├────────────────────────┐
domain/                infrastructure/
Domínio: dados do      Infraestrutura: tudo que fala com o navegador
produto (textos,       ou com serviços externos (animações, URL,
passos, planos).       serviço de login simulado)
Sem React, sem DOM.
```

**Regras**

- `presentation` usa `application` e lê dados do `domain`. Ela **nunca** importa `infrastructure`.
- `application` usa `domain` e `infrastructure`.
- `domain` e `infrastructure` não importam nenhuma outra camada.

## Pastas

```
src/
├── main.jsx                               # ponto de entrada (estilos globais + <App />)
├── app/
│   └── App.jsx                            # rota → página
├── presentation/
│   ├── styles/        tokens.css, base.css  # cores, fontes e medidas | reset
│   ├── utils/         cx.js                 # junta classes CSS
│   ├── components/                          # componentes reutilizáveis, um por pasta
│   │   ├── Blob/  Brand/  Button/  Divider/  Eyebrow/
│   │   ├── Field/  (Field, TextField, PasswordField)
│   │   ├── Icon/
│   │   └── Section/  (Section, SectionHeader)
│   └── pages/
│       ├── landing/
│       │   ├── LandingPage.jsx + .css
│       │   ├── sections/  Nav, Hero, HowItWorks (+Step), Benefits (+BenefitCard),
│       │   │              Comparison (+ComparisonCard), Pricing, FinalCta, Footer
│       │   └── scenes/    SceneCard, RegisterScene, PhotoScene, AiScene, SaleScene
│       └── login/
│           ├── LoginPage.jsx + .css
│           └── components/  BrandPanel, LoginForm, SocialLogin
├── application/
│   ├── navigation/   routes.js, useHashRoute.js
│   ├── animation/    useAnimationRunner.js, useLandingAnimations.js,
│   │                 useLoginAnimations.js, usePressFeedback.js
│   └── auth/         useLoginForm.js
├── domain/
│   └── content/      landingContent.js, loginContent.js   # TODO o texto do site
└── infrastructure/
    ├── browser/      location.js            # window.location e rolagem
    ├── auth/         authService.js         # login simulado (troque pela API real)
    └── animation/
        ├── core/     config.js, createAnimator.js, effects.js, motion.js, onScrollFrame.js
        ├── landing/  index.js, navigation.js, parallax.js, reveal.js, hero.js,
        │             finalState.js, scenes/ (register, photo, ai, sale, comparison, pricing)
        └── login/    index.js
```

## Convenções

**Textos.** Para mudar qualquer frase, edite `src/domain/content/`. Os componentes não têm texto fixo.

**CSS com BEM.** Cada componente tem o próprio `.css` na mesma pasta.

- Bloco: `.pricing`
- Elemento: `.pricing__card`
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
| `data-enter` | Ordem de entrada no login |

**Configuração das animações.** Fica em `src/infrastructure/animation/core/config.js`.

- Intensidade, repetição das cenas e parallax se ajustam ali.
- Por padrão, as animações rodam **sempre**, mesmo com "efeitos de animação" desligados no Windows, como no projeto original.
- `respectReducedMotion: true` liga o modo acessível.

## Publicar

O site final é a pasta `dist/` gerada por `npm run build` (o `main.py` faz isso sozinho). O `vite.config.js` usa `base: './'`, então o build funciona em qualquer subpasta, inclusive no GitHub Pages.
