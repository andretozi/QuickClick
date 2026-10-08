import RegisterScene from '../../scenes/RegisterScene/RegisterScene.jsx';
import PhotoScene from '../../scenes/PhotoScene/PhotoScene.jsx';
import AiScene from '../../scenes/AiScene/AiScene.jsx';
import SaleScene from '../../scenes/SaleScene/SaleScene.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './Step.css';

const SCENES = {
  register: RegisterScene,
  photo: PhotoScene,
  ai: AiScene,
  sale: SaleScene
};

/**
 * Um passo do "Como funciona": ilustração animada + texto.
 * `reversed` coloca a ilustração do lado direito (passos pares).
 */
export default function Step({ number, title, description, scene, reversed = false }) {
  const Scene = SCENES[scene];

  return (
    <li className={cx('step', reversed && 'step--reversed')}>
      <div data-reveal={reversed ? 'left' : 'right'} className="step__visual">
        {Scene && <Scene />}
      </div>
      <div className="step__text">
        <div data-reveal="up" className="step__number">
          {number}
        </div>
        <h3 data-reveal="up" data-delay="80" className="heading step__title">
          {title}
        </h3>
        <p data-reveal="up" data-delay="140" className="step__description">
          {description}
        </p>
      </div>
    </li>
  );
}
