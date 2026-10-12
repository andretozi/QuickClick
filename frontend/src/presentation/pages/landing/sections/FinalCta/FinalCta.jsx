import Section from '@/presentation/components/Section/Section.jsx';
import SectionLights from '@/presentation/pages/landing/components/SectionLights/SectionLights.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import { FINAL_CTA } from '@/domain/content/landingContent.js';
import './FinalCta.css';

export default function FinalCta() {
  const { title, lead, cta, finePrint } = FINAL_CTA;

  return (
    <Section id="final" tone="dark" dotted className="final-cta" backdrop={<SectionLights block="final-cta" />}>
      <h2 data-reveal="up" className="heading final-cta__title">
        {title}
      </h2>
      <p data-reveal="up" data-delay="90" className="final-cta__lead">
        {lead}
      </p>
      <div data-reveal="up" data-delay="180" className="final-cta__action">
        <Button href={cta.href} size="lg" icon="arrow-right" iconSize={19}>
          {cta.label}
        </Button>
      </div>
      <p data-reveal="up" data-delay="260" className="final-cta__fine-print">
        {finePrint}
      </p>
    </Section>
  );
}
