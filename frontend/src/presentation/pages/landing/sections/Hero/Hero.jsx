import Section from '@/presentation/components/Section/Section.jsx';
import Blob from '@/presentation/components/Blob/Blob.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { HERO } from '@/domain/content/landingContent.js';
import './Hero.css';

/** Camadas de luz com velocidades diferentes de parallax. */
const LIGHTS = [
  { id: 'a', tone: 'coral', speed: 0.18 },
  { id: 'b', tone: 'honey', speed: 0.1 },
  { id: 'c', tone: 'coral', speed: 0.26 }
];

function HeroBackdrop() {
  return LIGHTS.map((light) => (
    <div key={light.id} className={`hero__parallax hero__parallax--${light.id}`} data-parallax={light.speed}>
      <Blob tone={light.tone} className={`hero__blob hero__blob--${light.id}`} />
    </div>
  ));
}

export default function Hero() {
  return (
    <Section as="header" id="top" dotted className="hero" innerClassName="hero__inner" backdrop={<HeroBackdrop />}>
      <div data-hero>
        <h1 data-part="title" className="heading hero__title">
          {HERO.titleLines.map((line, index) => (
            <span key={line} className={cx('hero__line', index > 0 && 'hero__line--accent')}>
              <span data-part="word" className="hero__word">
                {line}
              </span>
            </span>
          ))}
          <span data-part="cursor" className="hero__cursor" aria-hidden="true">
            <span data-part="ripple" className="hero__ripple" />
            <Icon name="cursor" width={30} height={34} className="hero__cursor-icon" />
          </span>
        </h1>

        <p data-reveal="up" data-delay="1350" className="hero__lead">
          {HERO.lead}
        </p>

        <div data-reveal="up" data-delay="1550" className="hero__actions">
          <Button href={HERO.cta.href} size="lg" icon="arrow-right" iconSize={19}>
            {HERO.cta.label}
          </Button>
          <Button href={HERO.secondary.href} variant="outline" size="lg">
            {HERO.secondary.label}
            <span data-part="scroll-arrow" className="hero__scroll-arrow">
              <Icon name="arrow-down" size={19} />
            </span>
          </Button>
        </div>

        <p data-reveal="up" data-delay="1750" className="hero__fine-print">
          {HERO.finePrint}
        </p>
      </div>
    </Section>
  );
}
