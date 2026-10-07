import Section from '@/presentation/components/Section/Section.jsx';
import SectionHeader from '@/presentation/components/Section/SectionHeader.jsx';
import Blob from '@/presentation/components/Blob/Blob.jsx';
import Step from './Step.jsx';
import { HOW_IT_WORKS } from '@/domain/content/landingContent.js';
import './HowItWorks.css';

const backdrop = (
  <>
    <Blob tone="coral" className="how-it-works__blob how-it-works__blob--a" />
    <Blob tone="honey" className="how-it-works__blob how-it-works__blob--b" />
  </>
);

export default function HowItWorks() {
  const { eyebrow, title, lead, steps } = HOW_IT_WORKS;

  return (
    <Section id="como" tone="dark" dotted className="how-it-works" backdrop={backdrop}>
      <SectionHeader eyebrow={eyebrow} title={title} lead={lead} />
      <ol className="how-it-works__steps">
        {steps.map((step, index) => (
          <Step key={step.number} {...step} reversed={index % 2 === 1} />
        ))}
      </ol>
    </Section>
  );
}
