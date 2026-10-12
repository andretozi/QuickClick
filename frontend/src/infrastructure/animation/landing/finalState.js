/**
 * Mostra a landing já "pronta", sem animar.
 * Usado apenas quando MOTION_CONFIG.respectReducedMotion = true e o sistema pede menos movimento.
 */
export function showFinalState(animator) {
  const show = (selector, styles) =>
    animator.queryAll(selector).forEach((element) => Object.assign(element.style, styles));

  show('[data-reveal]', { opacity: '1', transform: 'none', filter: 'none' });
  show('[data-part="word"]', { opacity: '1', transform: 'none' });
  show('[data-part="check"], [data-part="done"], [data-part="tag"], [data-part="toast"], [data-part="amount"]', {
    opacity: '1',
    strokeDashoffset: '0'
  });
  show('[data-part="listing"]', { opacity: '1', transform: 'none' });
  show('[data-part="viewport"]', { opacity: '1' });
  show('[data-part="fill"]', { width: '100%' });
  animator.queryAll('[data-part="bar"]').forEach((bar) => {
    bar.style.height = bar.style.getPropertyValue('--bar-height') || '60%';
  });
}
