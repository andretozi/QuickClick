import Section from '@/presentation/components/Section/Section.jsx';
import SectionHeader from '@/presentation/components/Section/SectionHeader.jsx';
import SectionLights from '@/presentation/pages/landing/components/SectionLights/SectionLights.jsx';
import Step from './Step.jsx';
import { HOW_IT_WORKS } from '@/domain/content/landingContent.js';
import './HowItWorks.css';

export default function HowItWorks() {
  const { eyebrow, title, lead, steps } = HOW_IT_WORKS;

  return (
    <Section id="como" tone="dark" dotted className="how-it-works" backdrop={<SectionLights block="how-it-works" />}>
      <SectionHeader eyebrow={eyebrow} title={title} lead={lead} />
      <ol className="how-it-works__steps">
        {steps.map((step, index) => (
          <Step key={step.number} {...step} reversed={index % 2 === 1} />
        ))}
      </ol>
    </Section>
  );
}
