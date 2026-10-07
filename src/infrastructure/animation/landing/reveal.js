import { EASE_OUT_EXPO } from '../core/motion.js';

const DISTANCE_PX = 46;
const BLUR_PX = 6;
const DURATION_MS = 900;

/** De onde cada elemento vem: [x, y] multiplicados pela distância. */
const DIRECTIONS = {
  up: [0, 1],
  down: [0, -1],
  left: [-1, 0],
  right: [1, 0]
};

/** Devolve o elemento ao controle do CSS (assim o :hover volta a funcionar). */
function settle(element, animation) {
  element.style.opacity = '1';
  element.style.transform = '';
  element.style.filter = '';
  element.style.willChange = '';
  animation.cancel();
}

/**
 * Elementos [data-reveal="up|down|left|right"] entram quando aparecem na tela.
 * [data-delay="ms"] atrasa a entrada para criar uma sequência.
 */
export function setupReveals(animator, { amplitude, blur }) {
  const elements = animator.queryAll('[data-reveal]');
  const blurFilter = blur ? `blur(${BLUR_PX}px)` : 'none';
  const startTransform = new Map();

  elements.forEach((element) => {
    const [x, y] = DIRECTIONS[element.dataset.reveal] ?? DIRECTIONS.up;
    const transform = `translate(${x * DISTANCE_PX * amplitude}px,${y * DISTANCE_PX * amplitude}px)`;
    startTransform.set(element, transform);
    Object.assign(element.style, { opacity: '0', transform, filter: blurFilter, willChange: 'transform,opacity' });
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const element = entry.target;
        observer.unobserve(element);

        const animation = animator.animate(
          element,
          [
            { opacity: 0, transform: startTransform.get(element), filter: blurFilter },
            { opacity: 1, transform: 'translate(0,0)', filter: 'blur(0)' }
          ],
          {
            duration: DURATION_MS,
            delay: Number(element.dataset.delay) || 0,
            easing: EASE_OUT_EXPO,
            fill: 'forwards'
          }
        );
        animation?.addEventListener('finish', () => settle(element, animation));
      });
    },
    { threshold: 0.16, rootMargin: '0px 0px -6% 0px' }
  );

  elements.forEach((element) => observer.observe(element));
  animator.onDispose(() => observer.disconnect());
}
