import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './AiProgress.css';

/**
 * Progresso real da análise, etapa por etapa (vem do back): feita, em andamento ou a seguir.
 * - stages: [{ id, label, state: 'done' | 'active' | 'todo' }]
 * - photo: capa do anúncio (opcional), com o feixe de luz passando enquanto a IA trabalha
 */
export default function AiProgress({ stages, photo, title, className, ...rest }) {
  const working = stages.some((stage) => stage.state === 'active');

  return (
    <div className={cx('ai-progress', className)} role="status" aria-live="polite" {...rest}>
      {photo && (
        <span className="ai-progress__photo" aria-hidden="true">
          <img src={photo} alt="" />
          {working && <span data-shimmer className="ai-progress__beam" />}
        </span>
      )}
      <div className="ai-progress__body">
        {title && <p className="ai-progress__title">{title}</p>}
        <ol className="ai-progress__list">
          {stages.map((stage) => (
            <li key={stage.id} className={cx('ai-progress__item', `ai-progress__item--${stage.state}`)}>
              <span className="ai-progress__mark" aria-hidden="true">
                {stage.state === 'done' ? (
                  <Icon name="check" size={14} />
                ) : stage.state === 'active' ? (
                  <span data-spin className="ai-progress__spinner" />
                ) : (
                  <Icon name="sparkle" size={13} />
                )}
              </span>
              {stage.label}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
