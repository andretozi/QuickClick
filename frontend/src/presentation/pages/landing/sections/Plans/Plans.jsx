import Section from '@/presentation/components/Section/Section.jsx';
import SectionHeader from '@/presentation/components/Section/SectionHeader.jsx';
import Blob from '@/presentation/components/Blob/Blob.jsx';
import PlanCard from './PlanCard.jsx';
import { PLANS } from '@/domain/content/landingContent.js';
import './Plans.css';

const CARD_STAGGER_MS = 110;

const backdrop = (
  <>
    <Blob tone="coral" className="plans__blob plans__blob--a" />
    <Blob tone="honey" className="plans__blob plans__blob--b" />
  </>
);

/** Planos: quatro cartões lado a lado, com o Pro em destaque. */
export default function Plans() {
  const { eyebrow, title, lead, recommendedLabel, items } = PLANS;

  return (
    <Section id="planos" className="plans" backdrop={backdrop}>
      <SectionHeader eyebrow={eyebrow} eyebrowTone="coral" title={title} lead={lead} size="md" className="plans__header" />
      <div className="plans__grid">
        {items.map(({ id, ...plan }, index) => (
          <PlanCard
            key={id}
            {...plan}
            recommendedLabel={recommendedLabel}
            data-reveal="up"
            data-delay={index * CARD_STAGGER_MS}
          />
        ))}
      </div>
    </Section>
  );
}
