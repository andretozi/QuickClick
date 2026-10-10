import { useRef } from 'react';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import useIndicator from '@/application/animation/useIndicator.js';
import useRovingKeys from '@/application/ui/useRovingKeys.js';
import { cx } from '@/presentation/utils/cx.js';
import './SegmentedControl.css';

/**
 * Seletor segmentado com o indicador andando com mola até a opção escolhida.
 * - mode 'tabs': abas que trocam painéis (role tab; cada painel usa o id `${idPrefix}-painel-${value}`)
 * - mode 'radio': escolha num formulário (role radio)
 * - tone 'glass' (fundo escuro) | 'paper' (fundo claro); orientation 'horizontal' | 'vertical'
 * options: [{ value, label, icon? }]. Setas, Home e End trocam a opção.
 */
export default function SegmentedControl({
  options,
  value,
  onChange,
  label,
  mode = 'tabs',
  idPrefix,
  tone = 'glass',
  orientation = 'horizontal',
  stretch = false,
  className
}) {
  const ref = useRef(null);
  useIndicator(ref, value);
  const onKeyDown = useRovingKeys({ options, value, onChange, containerRef: ref, orientation });
  const tabs = mode === 'tabs';

  return (
    <div
      ref={ref}
      role={tabs ? 'tablist' : 'radiogroup'}
      aria-label={label}
      aria-orientation={tabs ? orientation : undefined}
      className={cx(
        'segmented',
        `segmented--${tone}`,
        `segmented--${orientation}`,
        stretch && 'segmented--stretch',
        className
      )}
      onKeyDown={onKeyDown}
    >
      <span data-part="indicator" className="segmented__indicator" aria-hidden="true" />
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            data-option
            data-active={selected || undefined}
            role={tabs ? 'tab' : 'radio'}
            id={tabs ? `${idPrefix}-aba-${option.value}` : undefined}
            aria-controls={tabs ? `${idPrefix}-painel-${option.value}` : undefined}
            aria-selected={tabs ? selected : undefined}
            aria-checked={tabs ? undefined : selected}
            tabIndex={selected ? 0 : -1}
            className={cx('segmented__option', selected && 'segmented__option--active')}
            onClick={() => onChange(option.value)}
          >
            {option.icon && <Icon name={option.icon} size={17} className="segmented__icon" />}
            <span className="segmented__label">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
