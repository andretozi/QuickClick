import { cx } from '@/presentation/utils/cx.js';
import './ParticleBurst.css';

/**
 * A explosão de partículas que vira palavra: um único <canvas> que cobre o bloco pai
 * (que precisa ter position relativa). Quem desenha é o campo de partículas da
 * infraestrutura (animation/core/particleField.js), achando o canvas pelo data-part.
 * Usado na vitrine da landing, nas boas vindas, no publicar e no conectar.
 * Props extras (como data-part) vão para o canvas.
 */
export default function ParticleBurst({ className, ...rest }) {
  return <canvas aria-hidden="true" className={cx('particle-burst', className)} {...rest} />;
}
