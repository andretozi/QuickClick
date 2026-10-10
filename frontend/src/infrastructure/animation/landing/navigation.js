import { onScrollFrame } from '../core/onScrollFrame.js';

const SCROLLED_CLASS = 'site-nav--scrolled';
const HIDDEN_CLASS = 'site-nav--hidden';
const OVER_DARK_CLASS = 'site-nav--over-dark';

const SCROLLED_AFTER_PX = 24; // a partir daqui o menu ganha fundo desfocado
const ALWAYS_VISIBLE_UNTIL_PX = 90; // perto do topo o menu nunca some
const DIRECTION_THRESHOLD_PX = 10; // quanto rolar na mesma direção para esconder/mostrar

/**
 * Menu: desfoca o fundo ao sair do topo, some ao descer e volta ao subir.
 * Com `hideOnScroll: false` (área logada), o menu só ganha o vidro e nunca some.
 */
export function setupNavigation(animator, { hideOnScroll = true } = {}) {
  const nav = animator.query('[data-nav]');
  if (!nav) return;

  let lastY = window.scrollY;
  let accumulated = 0;
  let hidden = false;
  const surfaces = animator.queryAll('[data-surface]');

  /** A seção que está atrás da linha de baixo do menu é escura? */
  const isOverDark = () => {
    const line = nav.offsetHeight;
    const behind = surfaces.find((surface) => {
      const { top, bottom } = surface.getBoundingClientRect();
      return top <= line && bottom > line;
    });
    return behind?.dataset.surface === 'dark';
  };

  onScrollFrame(animator, (y) => {
    const delta = y - lastY;
    const changedDirection = (delta > 0 && accumulated < 0) || (delta < 0 && accumulated > 0);
    if (changedDirection) accumulated = 0;
    accumulated += delta;

    if (y < ALWAYS_VISIBLE_UNTIL_PX) {
      hidden = false;
      accumulated = 0;
    } else if (accumulated > DIRECTION_THRESHOLD_PX) {
      hidden = true;
      accumulated = 0;
    } else if (accumulated < -DIRECTION_THRESHOLD_PX) {
      hidden = false;
      accumulated = 0;
    }

    nav.classList.toggle(SCROLLED_CLASS, y > SCROLLED_AFTER_PX);
    nav.classList.toggle(HIDDEN_CLASS, hideOnScroll && hidden);
    nav.classList.toggle(OVER_DARK_CLASS, isOverDark());
    lastY = y;
  });
}
