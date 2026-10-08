/**
 * Cria um "animador" ligado a um elemento raiz.
 *
 * Centraliza o que toda animação precisa: buscar elementos, agendar passos,
 * disparar animações (Web Animations API) e limpar tudo ao desmontar.
 * Assim cada efeito só descreve O QUE anima, sem repetir infraestrutura.
 */
export function createAnimator(root) {
  const timers = new Set();
  const animations = new Set();
  const disposers = [];
  let alive = true;

  const query = (selector, scope = root) => scope.querySelector(selector);
  const queryAll = (selector, scope = root) => Array.from(scope.querySelectorAll(selector));

  /** Partes animáveis são marcadas com data-part="nome" dentro de um componente. */
  const part = (name, scope = root) => query(`[data-part="${name}"]`, scope);
  const parts = (name, scope = root) => queryAll(`[data-part="${name}"]`, scope);

  /** Executa `fn` depois de `ms` milissegundos (cancelado automaticamente no dispose). */
  const after = (ms, fn) => {
    const id = setTimeout(() => {
      timers.delete(id);
      if (alive) fn();
    }, ms);
    timers.add(id);
    return id;
  };

  /** element.animate() com registro para cancelamento. Ignora elementos ausentes. */
  const animate = (element, keyframes, options) => {
    if (!element || !alive) return null;
    const animation = element.animate(keyframes, options);
    const forget = () => animations.delete(animation);
    animations.add(animation);
    // O navegador descarta animações "fill: forwards" substituídas por outras mais novas.
    animation.addEventListener('remove', forget);
    if (options?.iterations !== Infinity && options?.fill !== 'forwards') {
      animation.addEventListener('finish', forget);
    }
    return animation;
  };

  /** Registra uma limpeza extra (listeners, observers...). */
  const onDispose = (fn) => disposers.push(fn);

  const dispose = () => {
    alive = false;
    timers.forEach(clearTimeout);
    timers.clear();
    animations.forEach((animation) => animation.cancel());
    animations.clear();
    disposers.forEach((fn) => fn());
  };

  return {
    root,
    query,
    queryAll,
    part,
    parts,
    after,
    animate,
    onDispose,
    dispose,
    get alive() {
      return alive;
    }
  };
}
