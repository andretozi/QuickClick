import { Fragment } from 'react';
import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './SectionHeader.css';

const STAGGER_MS = 80;

/** Título em texto corrido ou em linhas (array): cada linha começa numa linha nova. */
function renderTitle(title) {
  if (!Array.isArray(title)) return title;
  return title.map((line, index) => (
    <Fragment key={line}>
      {index > 0 && <br />}
      {line}
    </Fragment>
  ));
}

/**
 * Cabeçalho centralizado das seções: eyebrow + título + texto de apoio.
 * Cada item entra com um pequeno atraso em relação ao anterior.
 * size: 'lg' (padrão) | 'md' (título um pouco menor)
 */
export default function SectionHeader({ eyebrow, eyebrowTone, title, lead, size = 'lg', className }) {
  const items = [];

  if (eyebrow) {
    items.push((delay) => (
      <Eyebrow key="eyebrow" tone={eyebrowTone} data-reveal="up" data-delay={delay}>
        {eyebrow}
      </Eyebrow>
    ));
  }

  items.push((delay) => (
    <h2
      key="title"
      className={cx('heading', 'section-header__title', size === 'md' && 'section-header__title--md')}
      data-reveal="up"
      data-delay={delay}
    >
      {renderTitle(title)}
    </h2>
  ));

  if (lead) {
    items.push((delay) => (
      <p key="lead" className="section-header__lead" data-reveal="up" data-delay={delay}>
        {lead}
      </p>
    ));
  }

  return (
    <div className={cx('section-header', className)}>
      {items.map((render, index) => render(index * STAGGER_MS))}
    </div>
  );
}
