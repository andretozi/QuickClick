import { useRef } from 'react';
import useLandingAnimations from '@/application/animation/useLandingAnimations.js';
import Nav from './sections/Nav/Nav.jsx';
import Hero from './sections/Hero/Hero.jsx';
import HowItWorks from './sections/HowItWorks/HowItWorks.jsx';
import Marketplaces from './sections/Marketplaces/Marketplaces.jsx';
import Benefits from './sections/Benefits/Benefits.jsx';
import Comparison from './sections/Comparison/Comparison.jsx';
import Plans from './sections/Plans/Plans.jsx';
import FinalCta from './sections/FinalCta/FinalCta.jsx';
import Footer from './sections/Footer/Footer.jsx';
import './LandingPage.css';

/** Página inicial: só monta as seções na ordem e liga as animações. */
export default function LandingPage() {
  const rootRef = useRef(null);
  useLandingAnimations(rootRef);

  return (
    <div ref={rootRef} className="landing">
      <Nav />
      <main>
        <Hero />
        <HowItWorks />
        <Marketplaces />
        <Benefits />
        <Comparison />
        <Plans />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}
