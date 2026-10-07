import SceneCard from '../SceneCard/SceneCard.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { SCENES } from '@/domain/content/landingContent.js';
import './RegisterScene.css';

/** Passo 1: formulário de cadastro se preenchendo sozinho. */
export default function RegisterScene() {
  const { title, fields, button, done } = SCENES.register;

  return (
    <div className="register-scene" data-scene="register" aria-hidden="true">
      <SceneCard tone="warm" data-part="card">
        <div className="register-scene__topbar">
          <span className="register-scene__dot register-scene__dot--coral" />
          <span className="register-scene__dot register-scene__dot--honey" />
          <span className="register-scene__dot register-scene__dot--muted" />
          <span className="register-scene__title">{title}</span>
        </div>

        <div className="register-scene__fields">
          {fields.map((label) => (
            <div key={label}>
              <div className="register-scene__label">{label}</div>
              <div className="register-scene__row">
                <div className="register-scene__input">
                  <div data-part="fill" className="register-scene__fill" />
                </div>
                <span data-part="check" className="register-scene__check">
                  <Icon name="check-circle" />
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="register-scene__footer">
          <span data-part="button" className="register-scene__button">
            {button}
          </span>
          <span data-part="done" className="register-scene__done">
            {done}
            <Icon name="check" size={16} />
          </span>
        </div>
      </SceneCard>
    </div>
  );
}
