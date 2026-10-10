import { createAnimator } from '../core/createAnimator.js';
import { quadraticPoint } from '../core/physics.js';
import { createParticleField } from '../core/particleField.js';
import { drawCheck } from '../core/effects.js';

/**
 * Comemoração de "publicar" e "conectar": o cursor da marca voa até o alvo, clica com
 * mola, o alvo amassa e as partículas explodem e formam a palavra ("Publicado", "Conectado").
 *
 * Dentro da raiz:
 *   [data-part="celebrate-target"]  o botão ou selo que recebe o clique;
 *   [data-part="celebrate-cursor"]  o cursor (escondido até a hora);
 *   [data-part="particles"]         o canvas de partículas, cobrindo a raiz;
 *   [data-part="celebrate-check"]   (opcional) o traço de um check que se desenha no clique.
 *
 * Devolve { play(word) → Promise que resolve quando a palavra se desfaz, dispose }.
 */
const FLY_MS = 620;
const HOLD_MS = 1100;

export function createCelebration(root) {
  const animator = createAnimator(root);
  const canvas = animator.part('particles');
  const field = canvas ? createParticleField(animator, canvas) : null;

  const wait = (ms) => new Promise((resolve) => animator.after(ms, resolve));

  async function play(word) {
    const target = animator.part('celebrate-target');
    const cursor = animator.part('celebrate-cursor');
    if (!target || !cursor || !field) return;
    await field.ready;

    const rootBox = root.getBoundingClientRect();
    const box = target.getBoundingClientRect();
    const point = { x: box.left - rootBox.left + box.width * 0.62, y: box.top - rootBox.top + box.height * 0.6 };
    const hot = { x: cursor.offsetWidth * (4 / 24), y: cursor.offsetHeight * (3 / 24) };
    const at = (p, scale = 1, rotate = 0) =>
      `translate(${(p.x - hot.x).toFixed(1)}px, ${(p.y - hot.y).toFixed(1)}px) rotate(${rotate}deg) scale(${scale})`;

    // 1. o cursor chega numa curva
    const from = { x: point.x + 260, y: point.y + 220 };
    const control = { x: point.x + 300, y: point.y - 60 };
    const frames = Array.from({ length: 15 }, (_, i) => {
      const t = i / 14;
      return { offset: t, transform: at(quadraticPoint(from, control, point, t), 0.75 + 0.25 * t, (1 - t) * -16), opacity: Math.min(1, t * 2.5) };
    });
    animator.animate(cursor, frames, { duration: FLY_MS, easing: 'cubic-bezier(.22,.9,.32,1)', fill: 'forwards' });
    await wait(FLY_MS);

    // 2. clique com mola: o cursor afunda, o alvo amassa
    animator.animate(
      cursor,
      [
        { transform: at(point), opacity: 1 },
        { transform: at({ x: point.x, y: point.y + 5 }, 0.8), opacity: 1, offset: 0.3 },
        { transform: at(point, 1.06), opacity: 1, offset: 0.65 },
        { transform: at(point), opacity: 1 }
      ],
      { duration: 460, easing: 'ease-out', fill: 'forwards' }
    );
    animator.animate(
      target,
      [
        { transform: 'scale(1)' },
        { transform: 'scale(1.05, .9)', offset: 0.25 },
        { transform: 'scale(.97, 1.04)', offset: 0.55 },
        { transform: 'scale(1)' }
      ],
      { duration: 620, easing: 'ease-out' }
    );

    drawCheck(animator, animator.part('celebrate-check'), { duration: 520 });

    // 3. explosão e palavra por cima
    const narrow = root.clientWidth < 560;
    field.burst(point.x, point.y, { count: narrow ? 40 : 70, power: narrow ? 0.7 : 0.9 });
    await wait(650);
    const size = Math.min(root.clientWidth * (narrow ? 0.14 : 0.08), 96);
    // a palavra fica logo acima do alvo, sem encostar nele
    const wordY = Math.max(size * 0.7, point.y - box.height * 0.6 - size * 0.8);
    field.formWord(word, { x: root.clientWidth / 2, y: wordY, size, maxWidth: root.clientWidth * 0.86 });
    await wait(650 + HOLD_MS);

    // 4. a palavra se desfaz e o cursor sai
    field.scatter();
    animator.animate(cursor, [{ opacity: 1, transform: at(point) }, { opacity: 0, transform: at({ x: point.x + 140, y: point.y - 160 }, 0.8) }], {
      duration: 420,
      easing: 'ease-in',
      fill: 'forwards'
    });
    await wait(500);
  }

  return { play, dispose: animator.dispose };
}
