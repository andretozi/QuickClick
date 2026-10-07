import { onScrollFrame } from '../core/onScrollFrame.js';

const DEFAULT_SPEED = 0.15;

/** Camadas [data-parallax="velocidade"] andam mais devagar que a rolagem. */
export function setupParallax(animator, { amplitude }) {
  const layers = animator.queryAll('[data-parallax]');
  if (!layers.length) return;

  const speeds = layers.map((layer) => (parseFloat(layer.dataset.parallax) || DEFAULT_SPEED) * amplitude);

  onScrollFrame(animator, (y) => {
    layers.forEach((layer, i) => {
      layer.style.transform = `translate3d(0,${y * speeds[i]}px,0)`;
    });
  });
}
