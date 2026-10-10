/**
 * Física simples para as animações: mola amortecida e curvas. A gravidade e o arrasto
 * das partículas ficam em particleField.js.
 * Tudo puro (sem DOM): quem anima usa os números para montar keyframes ou mover elementos.
 */

const STEP_S = 1 / 240; // passo fixo da simulação (estável em qualquer taxa de quadros)

/**
 * Mola amortecida (massa 1). `step(dtMs)` avança a simulação; `position` e
 * `velocity` dizem onde ela está. Rigidez alta = rápida; amortecimento alto = sem balançar.
 */
export function createSpring({ stiffness = 170, damping = 26, position = 0, velocity = 0 } = {}) {
  let x = position;
  let v = velocity;
  let target = position;

  return {
    get position() {
      return x;
    },
    get velocity() {
      return v;
    },
    get target() {
      return target;
    },
    setTarget(value) {
      target = value;
    },
    /** Pula direto para um valor, parado. */
    jump(value) {
      x = value;
      v = 0;
      target = value;
    },
    /** Desloca posição e alvo juntos (para o laço infinito "dar a volta" sem tranco). */
    shift(delta) {
      x += delta;
      target += delta;
    },
    step(dtMs) {
      let remaining = Math.min(dtMs, 64) / 1000;
      while (remaining > 0) {
        const dt = Math.min(STEP_S, remaining);
        const force = -stiffness * (x - target) - damping * v;
        v += force * dt;
        x += v * dt;
        remaining -= dt;
      }
      return x;
    },
    isResting(epsilon = 0.4) {
      return Math.abs(x - target) < epsilon && Math.abs(v) < epsilon;
    }
  };
}

/** Ponto de uma curva de Bézier quadrática (o cursor voando numa curva suave). */
export function quadraticPoint(p0, control, p1, t) {
  const u = 1 - t;
  return {
    x: u * u * p0.x + 2 * u * t * control.x + t * t * p1.x,
    y: u * u * p0.y + 2 * u * t * control.y + t * t * p1.y
  };
}

/** Número aleatório entre min e max. */
export function between(min, max) {
  return min + Math.random() * (max - min);
}
