import { animateRegister } from './register.js';
import { animatePhoto } from './photo.js';
import { animateAi } from './ai.js';
import { animateSale } from './sale.js';
import { animateComparison } from './comparison.js';
import { animatePricing } from './pricing.js';

/** Cada [data-scene="nome"] da página aponta para a sua coreografia. */
const SCENES = {
  register: animateRegister,
  photo: animatePhoto,
  ai: animateAi,
  sale: animateSale,
  comparison: animateComparison,
  pricing: animatePricing
};

/** Toca cada cena uma única vez, quando 30% dela aparece na tela. */
export function setupScenes(animator, motion) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        SCENES[entry.target.dataset.scene]?.(animator, entry.target, motion);
      });
    },
    { threshold: 0.3 }
  );

  animator.queryAll('[data-scene]').forEach((scene) => observer.observe(scene));
  animator.onDispose(() => observer.disconnect());
}
