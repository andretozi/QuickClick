import Section from '@/presentation/components/Section/Section.jsx';
import SectionHeader from '@/presentation/components/Section/SectionHeader.jsx';
import SectionLights from '@/presentation/pages/landing/components/SectionLights/SectionLights.jsx';
import BenefitCard from './BenefitCard.jsx';
import { BENEFITS } from '@/domain/content/landingContent.js';
import './Benefits.css';

const CARD_STAGGER_MS = 110;

export default function Benefits() {
  const { eyebrow, title, items } = BENEFITS;

  return (
    <Section dotted className="benefits" backdrop={<SectionLights block="benefits" />}>
      <SectionHeader eyebrow={eyebrow} eyebrowTone="coral" title={title} className="benefits__header" />
      <div className="benefits__grid">
        {items.map((item, index) => (
          <BenefitCard key={item.title} {...item} data-reveal="up" data-delay={index * CARD_STAGGER_MS} />
        ))}
      </div>
    </Section>
  );
}
