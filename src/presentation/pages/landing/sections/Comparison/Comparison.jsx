import Section from '@/presentation/components/Section/Section.jsx';
import SectionHeader from '@/presentation/components/Section/SectionHeader.jsx';
import Blob from '@/presentation/components/Blob/Blob.jsx';
import ComparisonCard from './ComparisonCard.jsx';
import { COMPARISON } from '@/domain/content/landingContent.js';
import './Comparison.css';

const backdrop = (
  <>
    <Blob tone="coral" className="comparison__blob comparison__blob--a" />
    <Blob tone="honey" className="comparison__blob comparison__blob--b" />
  </>
);

export default function Comparison() {
  const { title, lead, others, ours } = COMPARISON;

  return (
    <Section className="comparison" backdrop={backdrop}>
      <SectionHeader title={title} lead={lead} size="md" />
      <div className="comparison__grid">
        <div data-reveal="right">
          <ComparisonCard label={others.label} items={others.items} />
        </div>
        <div data-reveal="left">
          <ComparisonCard highlight ribbon={ours.ribbon} title={ours.title} items={ours.items} data-scene="comparison" />
        </div>
      </div>
    </Section>
  );
}
