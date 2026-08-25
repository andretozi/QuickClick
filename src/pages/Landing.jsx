import { useRef } from 'react';
import useLandingAnimations from '../hooks/useLandingAnimations.js';
import Nav from '../sections/Nav.jsx';
import Hero from '../sections/Hero.jsx';
import HowItWorks from '../sections/HowItWorks.jsx';
import WhyUs from '../sections/WhyUs.jsx';
import Compare from '../sections/Compare.jsx';
import Price from '../sections/Price.jsx';
import FinalCTA from '../sections/FinalCTA.jsx';
import Footer from '../sections/Footer.jsx';
import '../styles/landing.css';

export default function Landing() {
  const rootRef = useRef(null);
  useLandingAnimations(rootRef);

  return (
    <div ref={rootRef} className="qc-page">
      <Nav />
      <Hero />
      <HowItWorks />
      <WhyUs />
      <Compare />
      <Price />
      <FinalCTA />
      <Footer />
    </div>
  );
}
