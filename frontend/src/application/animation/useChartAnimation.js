import { animateChart } from '@/infrastructure/animation/charts/charts.js';
import useAnimationRunner from './useAnimationRunner.js';

/** Aplicação · Liga a entrada animada de um gráfico ao elemento dele. */
export default function useChartAnimation(rootRef) {
  useAnimationRunner(rootRef, animateChart);
}
