import { EASE_OUT_EXPO } from './motion.js';

/**
 * Entrada em sequência que também pega o que aparece depois (dados que chegam da
 * "API", abas que trocam, linhas filtradas).
 *
 * Elementos com [data-enter="1|2|3"] entram na ordem do número (1 = título,
 * 2 = conteúdo, 3 = detalhes) e, dentro do mesmo número, na ordem da página.
 * Um MutationObserver observa a raiz: elementos novos com [data-enter] entram no próximo lote.
 * Cada elemento entra uma vez só; no fim, ele volta para o CSS (o :hover funciona).
 * Com `instant` (movimento reduzido), tudo só aparece, sem animar.
 */
export function observeEntrances(
  animator,
  root,
  { start = 60, step = 70, distance = 22, blur = 7, duration = 760, instant = false } = {}
) {
  const entered = new WeakSet();

  const play = (elements) => {
    const fresh = elements.filter((element) => !entered.has(element));
    fresh
      .sort((a, b) => (Number(a.dataset.enter) || 2) - (Number(b.dataset.enter) || 2))
      .forEach((element, i) => {
        entered.add(element);
        if (instant) {
          element.style.opacity = '1';
          return;
        }
        const animation = animator.animate(
          element,
          [
            { opacity: 0, transform: `translateY(${distance}px)`, filter: `blur(${blur}px)` },
            { opacity: 1, transform: 'translateY(0)', filter: 'blur(0)' }
          ],
          { duration, delay: start + i * step, easing: EASE_OUT_EXPO, fill: 'forwards' }
        );
        animation?.addEventListener('finish', () => {
          element.style.opacity = '1';
          animation.cancel();
        });
      });
  };

  play(animator.queryAll('[data-enter]', root));

  let pending = [];
  let scheduled = false;
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      // o React pode reaproveitar um elemento e só ganhar o data-enter (carregando → pronto)
      if (mutation.type === 'attributes') {
        if (mutation.target instanceof HTMLElement && mutation.target.matches('[data-enter]')) pending.push(mutation.target);
        return;
      }
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof HTMLElement)) return;
        if (node.matches('[data-enter]')) pending.push(node);
        pending.push(...node.querySelectorAll('[data-enter]'));
      });
    });
    if (scheduled || pending.length === 0) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      const batch = pending.filter((element) => element.isConnected);
      pending = [];
      play(batch);
    });
  });
  observer.observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ['data-enter'] });
  animator.onDispose(() => observer.disconnect());
}
