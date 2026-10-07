import Section from '@/presentation/components/Section/Section.jsx';
import Blob from '@/presentation/components/Blob/Blob.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import { PRICING } from '@/domain/content/landingContent.js';
import './Pricing.css';

const backdrop = (
  <>
    <Blob tone="coral" className="pricing__blob pricing__blob--a" />
    <Blob tone="honey" className="pricing__blob pricing__blob--b" />
  </>
);

export default function Pricing() {
  const { eyebrow, title, description, cta } = PRICING;

  return (
    <Section id="preco" className="pricing" backdrop={backdrop}>
      <div data-reveal="up" data-scene="pricing" className="pricing__card">
        <span data-part="shine" className="pricing__shine" aria-hidden="true" />
        <Eyebrow tone="inherit" className="pricing__eyebrow">
          {eyebrow}
        </Eyebrow>
        <h2 className="heading pricing__title">{title}</h2>
        <p className="pricing__description">{description}</p>
        <Button href={cta.href} variant="dark" icon="arrow-right" className="pricing__cta">
          {cta.label}
        </Button>
      </div>
    </Section>
  );
}
