import { Fragment } from 'react';
import Blob from '@/presentation/components/Blob/Blob.jsx';
import Brand from '@/presentation/components/Brand/Brand.jsx';
import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { BRAND_PANEL } from '@/domain/content/loginContent.js';
import './BrandPanel.css';

/** Lado esquerdo do login: marca, "Voltar ao site" e as boas-vindas. */
export default function BrandPanel() {
  const { back, eyebrow, titleLines, lead } = BRAND_PANEL;

  return (
    <aside className="brand-panel">
      <Blob tone="coral" className="brand-panel__blob brand-panel__blob--top" />
      <Blob tone="honey" className="brand-panel__blob brand-panel__blob--bottom" />

      <div className="brand-panel__top">
        <Brand href="#/" size="md" tone="dark" />
        <a href={back.href} className="brand-panel__back">
          <Icon name="chevron-left" size={17} />
          {back.label}
        </a>
      </div>

      <div className="brand-panel__headline">
        <Eyebrow data-enter="1" className="brand-panel__eyebrow">
          {eyebrow}
        </Eyebrow>
        <h1 data-enter="2" className="heading brand-panel__title">
          {titleLines.map((line, index) => (
            <Fragment key={line}>
              {index > 0 && <br />}
              {line}
            </Fragment>
          ))}
        </h1>
        <p data-enter="3" className="brand-panel__lead">
          {lead}
        </p>
      </div>
    </aside>
  );
}
