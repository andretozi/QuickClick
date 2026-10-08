import Section from '@/presentation/components/Section/Section.jsx';
import SectionHeader from '@/presentation/components/Section/SectionHeader.jsx';
import Blob from '@/presentation/components/Blob/Blob.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import MarketplaceMark from '@/presentation/components/MarketplaceMark/MarketplaceMark.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { MARKETPLACES } from '@/domain/content/landingContent.js';
import { MARKETPLACE_CATALOG } from '@/domain/content/marketplacesContent.js';
import './Marketplaces.css';

const CHIP_STAGGER_MS = 60;
const AVAILABLE = MARKETPLACE_CATALOG.filter((marketplace) => marketplace.available);
const SOON = MARKETPLACE_CATALOG.filter((marketplace) => !marketplace.available);

const backdrop = (
  <>
    <Blob tone="honey" className="marketplaces__blob marketplaces__blob--a" />
    <Blob tone="coral" className="marketplaces__blob marketplaces__blob--b" />
  </>
);

/** Nome do marketplace com o monograma. Os disponíveis têm um ponto verde "no ar" (cena "marketplaces"). */
function Chip({ marketplace, soon = false, delay }) {
  return (
    <li data-reveal="up" data-delay={delay} className={cx('marketplaces__chip', soon && 'marketplaces__chip--soon')}>
      <MarketplaceMark
        slug={marketplace.slug}
        monogram={marketplace.monogram}
        size="sm"
        className="marketplaces__mark"
      />
      {marketplace.name}
      {!soon && <span data-part="live" className="marketplaces__live" aria-hidden="true" />}
    </li>
  );
}

/** Seção "Marketplaces": onde a Quick Click já funciona e o que está chegando. */
export default function Marketplaces() {
  const { eyebrow, title, lead, availableLabel, soonLabel, cta } = MARKETPLACES;

  return (
    <Section id="marketplaces" className="marketplaces" backdrop={backdrop}>
      <SectionHeader eyebrow={eyebrow} eyebrowTone="coral" title={title} lead={lead} size="md" className="marketplaces__header" />

      <div data-scene="marketplaces" className="marketplaces__catalog">
        <p data-reveal="up" className="marketplaces__label">
          {availableLabel}
        </p>
        <ul className="marketplaces__list" aria-label={availableLabel}>
          {AVAILABLE.map((marketplace, index) => (
            <Chip key={marketplace.slug} marketplace={marketplace} delay={index * CHIP_STAGGER_MS} />
          ))}
        </ul>

        <p data-reveal="up" className="marketplaces__label">
          {soonLabel}
        </p>
        <ul className="marketplaces__list" aria-label={soonLabel}>
          {SOON.map((marketplace, index) => (
            <Chip
              key={marketplace.slug}
              marketplace={marketplace}
              soon
              delay={(index + AVAILABLE.length) * CHIP_STAGGER_MS}
            />
          ))}
        </ul>
      </div>

      <div data-reveal="up" className="marketplaces__action">
        <Button href={cta.href} size="lg" icon="arrow-right" iconSize={19}>
          {cta.label}
        </Button>
      </div>
    </Section>
  );
}
