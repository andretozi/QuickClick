import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './Stepper.css';

/**
 * Trilho dos passos ("da foto ao anúncio pronto"): o trilho enche com mola até o passo
 * atual e os passos já visitados viram atalho.
 * - steps: [{ id, label, hint }]; current: índice; visited: maior índice já aberto
 * - onSelect(index); label: nome da lista para o leitor de tela
 */
export default function Stepper({ steps, current, visited, onSelect, label, className, ...rest }) {
  const progress = steps.length > 1 ? current / (steps.length - 1) : 0;

  return (
    <nav className={cx('stepper', className)} aria-label={label} {...rest}>
      <span className="stepper__rail" aria-hidden="true">
        <span className="stepper__fill" style={{ transform: `scaleX(${progress})` }} />
      </span>
      <ol className="stepper__list">
        {steps.map((step, index) => {
          const done = index < current;
          const active = index === current;
          const reachable = index <= visited && !active;
          return (
            <li
              key={step.id}
              className={cx('stepper__item', done && 'stepper__item--done', active && 'stepper__item--active')}
            >
              <button
                type="button"
                className="stepper__button"
                onClick={() => onSelect(index)}
                disabled={!reachable}
                aria-current={active ? 'step' : undefined}
              >
                <span className="stepper__dot" aria-hidden="true">
                  {done ? <Icon name="check" size={16} /> : index + 1}
                </span>
                <span className="stepper__text">
                  <span className="stepper__label">{step.label}</span>
                  <span className="stepper__hint">{step.hint}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
