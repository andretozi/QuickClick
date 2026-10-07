import Section from '@/presentation/components/Section/Section.jsx';
import Brand from '@/presentation/components/Brand/Brand.jsx';
import { FOOTER } from '@/domain/content/landingContent.js';
import './Footer.css';

export default function Footer() {
  return (
    <Section as="footer" tone="dark" className="site-footer" innerClassName="site-footer__inner">
      <Brand size="sm" tone="dark" tagline={FOOTER.tagline} />
      <p className="site-footer__copyright">{FOOTER.copyright}</p>
    </Section>
  );
}
