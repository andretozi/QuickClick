import Section from '@/presentation/components/Section/Section.jsx';
import SectionHeader from '@/presentation/components/Section/SectionHeader.jsx';
import Blob from '@/presentation/components/Blob/Blob.jsx';
import BenefitCard from './BenefitCard.jsx';
import { BENEFITS } from '@/domain/content/landingContent.js';
import './Benefits.css';

const CARD_STAGGER_MS = 110;

const backdrop = (
  <>
    <Blob tone="coral" className="benefits__blob benefits__blob--a" />
    <Blob tone="honey" className="benefits__blob benefits__blob--b" />
  </>
);

export default function Benefits() {
  const { eyebrow, title, items } = BENEFITS;

  return (
    <Section dotted className="benefits" backdrop={backdrop}>
      <SectionHeader eyebrow={eyebrow} eyebrowTone="coral" title={title} className="benefits__header" />
      <div className="benefits__grid">
        {items.map((item, index) => (
          <BenefitCard key={item.title} {...item} data-reveal="up" data-delay={index * CARD_STAGGER_MS} />
        ))}
      </div>
    </Section>
  );
}
