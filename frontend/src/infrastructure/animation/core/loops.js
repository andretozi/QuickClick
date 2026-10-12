/**
 * Animações em laço que a casca da área logada liga sozinha, achando os elementos por data-*:
 *   [data-shimmer]  faixa de luz passando (marketplaces "em breve");
 *   [data-spin]     indicador de carregando girando.
 * Como as entradas, pega também o que aparece depois (MutationObserver na raiz).
 */
const LOOPS = [
  {
    selector: '[data-shimmer]',
    keyframes: [
      { transform: 'translateX(-120%)', offset: 0 },
      { transform: 'translateX(120%)', offset: 0.6 },
      { transform: 'translateX(120%)', offset: 1 }
    ],
    options: (i) => ({ duration: 3600, delay: (i % 5) * 240, iterations: Infinity, easing: 'ease-in-out' })
  },
  {
    selector: '[data-spin]',
    keyframes: [{ transform: 'rotate(0deg)' }, { transform: 'rotate(360deg)' }],
    options: () => ({ duration: 800, iterations: Infinity, easing: 'linear' })
  }
];

export function observeLoops(animator, root) {
  const started = new WeakSet();

  const play = (elements) =>
    elements.forEach((element) => {
      if (started.has(element)) return;
      const loop = LOOPS.find((item) => element.matches(item.selector));
      if (!loop) return;
      started.add(element);
      element.animate(loop.keyframes, loop.options(Math.floor(Math.random() * 5)));
    });

  const selector = LOOPS.map((item) => item.selector).join(',');
  play(animator.queryAll(selector, root));

  const observer = new MutationObserver((mutations) => {
    const found = [];
    mutations.forEach((mutation) =>
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof HTMLElement)) return;
        if (node.matches(selector)) found.push(node);
        found.push(...node.querySelectorAll(selector));
      })
    );
    if (found.length) play(found);
  });
  observer.observe(root, { childList: true, subtree: true });
  animator.onDispose(() => observer.disconnect());
}
