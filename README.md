# Quick Click — Front-end

Landing page animada da Quick Click ("Clicou, vendeu.") + tela de login.
Feita em HTML com animações reais (Web Animations API), textura, parallax e cenas dinâmicas.

## Arquivos

| Arquivo | O que é |
|---|---|
| `Quick Click.dc.html` | **Página principal** — hero animado, "Como funciona", comparativo, preço e CTA. |
| `Login.dc.html` | Tela de login (Google / Apple / Facebook + e-mail). Abre pelo botão **Entrar**. |
| `support.js` | Runtime que faz as páginas rodarem. **Precisa ficar na mesma pasta.** |
| `index.html` | Redireciona para a página principal (bom para GitHub Pages). |
| `Quick Click (standalone).html` | Versão **um-arquivo-só**, funciona offline (só a landing, sem o login). |

## Como rodar

**Mais simples:** abra `Quick Click (standalone).html` no navegador — funciona offline, com tudo (animações, textura, cores).

**Projeto completo (com login):** mantenha `Quick Click.dc.html`, `Login.dc.html` e `support.js` juntos na mesma pasta e abra `index.html` (ou o `Quick Click.dc.html`).
Precisa de internet só para carregar as fontes (Google Fonts).

> Dica: para servir localmente sem restrições de `file://`, rode na pasta:
> `python -m http.server` e acesse `http://localhost:8000`.

## Publicar no GitHub

```bash
git init
git add .
git commit -m "Quick Click front-end — landing animada + login"
git branch -M main
git remote add origin https://github.com/andretozi/FrontendQuickClick.git
git push -u origin main
```

### GitHub Pages
Em **Settings → Pages**, selecione a branch `main` e a pasta `/root`.
O `index.html` abre a landing automaticamente.
