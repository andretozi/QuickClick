import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import useFileDrop from '@/application/ui/useFileDrop.js';
import './FileDrop.css';

/**
 * Área de arrastar e soltar (ou clicar) para escolher imagens.
 * - onFiles(FileList); busy: preparando os arquivos; disabled: não cabe mais nada
 * - texts: { title, text, button, hint, active, processing }
 * - error: mensagem embaixo, ligada pelo aria-describedby
 */
export default function FileDrop({ id, onFiles, busy = false, disabled = false, texts, error, invalid = false, className }) {
  const drop = useFileDrop(onFiles, { disabled: disabled || busy });
  const hintId = `${id}-dica`;
  const errorId = `${id}-erro`;

  return (
    <div className={cx('file-drop', className)}>
      <div
        {...drop.dropProps}
        className={cx(
          'file-drop__zone',
          drop.dragging && 'file-drop__zone--active',
          busy && 'file-drop__zone--busy',
          disabled && 'file-drop__zone--disabled',
          invalid && 'file-drop__zone--invalid'
        )}
      >
        <span className="file-drop__art" aria-hidden="true">
          <span className="file-drop__halo" />
          <span className="file-drop__icon">
            {busy ? <span data-spin className="file-drop__spinner" /> : <Icon name="camera" size={30} />}
          </span>
        </span>
        <p className="file-drop__title">{busy ? texts.processing : drop.dragging ? texts.active : texts.title}</p>
        <p className="file-drop__text">{texts.text}</p>
        <button
          id={id}
          type="button"
          className="file-drop__button"
          onClick={drop.openPicker}
          disabled={disabled || busy}
          aria-describedby={cx(hintId, error && errorId)}
          aria-invalid={invalid || undefined}
        >
          <Icon name="upload" size={17} />
          {texts.button}
        </button>
        <input
          ref={drop.inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          tabIndex={-1}
          aria-hidden="true"
          className="file-drop__input"
          onChange={drop.onInputChange}
        />
      </div>
      <p id={hintId} className="file-drop__hint">
        {texts.hint}
      </p>
      {error && (
        <p id={errorId} className="file-drop__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
