import Button from '@/presentation/components/Button/Button.jsx';
import Panel from '@/presentation/components/Panel/Panel.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './StatusPanel.css';

/**
 * Painel de vidro para "carregando" e "não deu certo" (painel, insights, marketplaces e editor).
 * - status 'loading': o spinner gira (data-spin) ao lado do texto
 * - status 'error': o texto e o botão de tentar de novo
 * - size: a altura mínima de cada tela, 'sm' (180 px) | 'md' (200 px) | 'lg' (220 px)
 */
export default function StatusPanel({ status = 'loading', text, retryLabel, onRetry, size = 'lg', className }) {
  const loading = status === 'loading';
  return (
    <Panel tone="glass" className={cx('status-panel', `status-panel--${size}`, className)} role={loading ? 'status' : 'alert'}>
      {loading ? (
        <>
          <span data-spin className="status-panel__spinner" aria-hidden="true" />
          {text}
        </>
      ) : (
        <>
          <p className="status-panel__title">{text}</p>
          <Button size="sm" variant="light" onClick={onRetry}>
            {retryLabel}
          </Button>
        </>
      )}
    </Panel>
  );
}
