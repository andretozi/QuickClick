import { useRef } from 'react';
import useLoginAnimations from '@/application/animation/useLoginAnimations.js';
import './AuthLayout.css';

/**
 * Casca das telas de entrada (login e cadastro): o painel escuro da marca de um lado
 * e o formulário do outro. Em telas estreitas, o painel vai para cima.
 * Os blocos com [data-enter="ordem"] entram em sequência.
 */
export default function AuthLayout({ panel, children }) {
  const rootRef = useRef(null);
  useLoginAnimations(rootRef);

  return (
    <div ref={rootRef} className="auth-layout">
      {panel}
      <main className="auth-layout__main">{children}</main>
    </div>
  );
}
