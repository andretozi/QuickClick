import { useRef, useState } from 'react';
import useLoginAnimations, { pressAnimation } from '../hooks/useLoginAnimations.js';
import LogoMark from '../components/LogoMark.jsx';
import '../styles/login.css';

export default function Login({ brandPanel = true }) {
  const rootRef = useRef(null);
  const pwRef = useRef(null);
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);

  useLoginAnimations(rootRef);

  const togglePw = () => {
    setShowPw((v) => {
      const next = !v;
      if (pwRef.current) pwRef.current.type = next ? 'text' : 'password';
      return next;
    });
  };

  const onSubmit = (e) => {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setTimeout(() => setLoading(false), 1600);
  };

  const onSocial = (e) => pressAnimation(e.currentTarget);

  return (
    <div ref={rootRef} className="lg-page">
      {brandPanel && (
        <div className="lg-brand-panel">
          <div data-blob className="lg-brand-panel__blob-a" />
          <div data-blob className="lg-brand-panel__blob-b" />

          <div className="lg-top">
            <a href="#/" className="lg-top__logo">
              <LogoMark variant="brand-panel" />
              <span className="qc-brand" style={{ fontSize: 22 }}>
                Quick <span className="qc-brand__accent" style={{ color: '#FF8A5C' }}>Click</span>
              </span>
            </a>
            <a href="#/" className="lg-top__back">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                <path
                  d="M15 6l-6 6 6 6"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Voltar ao site
            </a>
          </div>

          <div className="lg-headline">
            <p data-in="1" className="lg-eyebrow">ÁREA DO VENDEDOR</p>
            <h1 data-in="2" className="lg-h1">
              Bem-vindo
              <br />
              de volta.
            </h1>
            <p data-in="3" className="lg-headline__lead">
              Entre e continue transformando estoque parado em dinheiro. É só uma foto —
              a IA cuida do resto.
            </p>
          </div>

          <div className="lg-proof-wrap">
            <div data-proof data-in="4" className="lg-proof">
              <span className="lg-proof__badge-wrap">
                <span data-proof-ring className="lg-proof__ring" />
                <span className="lg-proof__badge">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M5 12.5l4 4L19 7"
                      stroke="#fff"
                      strokeWidth="2.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </span>
              <div>
                <div className="lg-proof__title">Nova venda no Bazar da Ana</div>
                <div className="lg-proof__amount">+ R$ 189,00</div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="lg-form-panel">
        <div data-in="3" className="lg-form-wrap">
          <div className="lg-form-head">
            <h2 className="lg-h2">Entrar na sua conta</h2>
            <p className="lg-form-head__lead">
              Escolha como quer entrar — leva alguns segundos.
            </p>
          </div>

          <div className="lg-socials">
            <button onClick={onSocial} className="lg-btn-social lg-btn-social--google">
              <svg width="21" height="21" viewBox="0 0 48 48">
                <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.4 29.3 35 24 35c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.6 6.1 29.6 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.3-.4-3.5z" />
                <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 18.9 13 24 13c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.6 6.1 29.6 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
                <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.5-5.2l-6.2-5.3C29.2 34.9 26.7 36 24 36c-5.3 0-9.7-2.6-11.3-6.9l-6.5 5C9.6 39.6 16.2 44 24 44z" />
                <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4 5.5l6.2 5.3C41 38.4 44 32 44 24c0-1.3-.1-2.3-.4-3.5z" />
              </svg>
              Continuar com Google
            </button>
            <button onClick={onSocial} className="lg-btn-social lg-btn-social--apple">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff">
                <path d="M16.4 12.8c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.1-2.8.8-3.5.8-.7 0-1.9-.8-3-.8-1.6 0-3 .9-3.8 2.3-1.6 2.8-.4 7 1.2 9.3.8 1.1 1.7 2.4 2.9 2.3 1.2 0 1.6-.7 3-.7s1.8.7 3 .7c1.2 0 2-1.1 2.8-2.2.9-1.3 1.2-2.5 1.3-2.6-.1 0-2.5-1-2.5-3.8zM14.2 5.9c.6-.8 1-1.8.9-2.9-.9 0-2 .6-2.6 1.3-.6.6-1.1 1.7-1 2.7 1 .1 2-.5 2.7-1.1z" />
              </svg>
              Continuar com Apple
            </button>
            <button onClick={onSocial} className="lg-btn-social lg-btn-social--facebook">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff">
                <path d="M22 12a10 10 0 10-11.6 9.9v-7H7.9V12h2.5V9.8c0-2.5 1.5-3.9 3.8-3.9 1.1 0 2.2.2 2.2.2v2.5h-1.2c-1.2 0-1.6.8-1.6 1.6V12h2.7l-.4 2.9h-2.3v7A10 10 0 0022 12z" />
              </svg>
              Continuar com Facebook
            </button>
          </div>

          <div className="lg-divider">
            <span className="lg-divider__line" />
            <span className="lg-divider__text">ou entre com e-mail</span>
            <span className="lg-divider__line" />
          </div>

          <form onSubmit={onSubmit} className="lg-form">
            <div>
              <label className="lg-field__label">E-mail</label>
              <input
                type="email"
                autoComplete="email"
                placeholder="voce@sualoja.com.br"
                className="lg-input"
              />
            </div>
            <div>
              <div className="lg-field__label-row">
                <label className="lg-field__label" style={{ marginBottom: 0 }}>Senha</label>
                <a href="#">Esqueci a senha</a>
              </div>
              <div className="lg-pw-wrap">
                <input
                  ref={pwRef}
                  type="password"
                  autoComplete="current-password"
                  placeholder="Sua senha"
                  className="lg-input lg-input--pw"
                />
                <button
                  type="button"
                  onClick={togglePw}
                  aria-label={showPw ? 'Ocultar senha' : 'Mostrar senha'}
                  className="lg-pw-toggle"
                >
                  {!showPw ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path
                        d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path
                        d="M3 3l18 18M10.6 10.7a3 3 0 004.2 4.2M9.4 5.2A9.4 9.4 0 0112 5c6.5 0 10 7 10 7a17 17 0 01-3.3 4.1M6.1 6.6A17 17 0 002 12s3.5 7 10 7a9.3 9.3 0 003.4-.6"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </button>
              </div>
            </div>
            <button type="submit" className="lg-btn-submit">
              {!loading ? (
                <span>Entrar</span>
              ) : (
                <span className="lg-btn-submit__loading">
                  <span className="lg-spinner" />
                  Entrando…
                </span>
              )}
            </button>
          </form>

          <p className="lg-signup">
            Novo por aqui? <a href="#/">Criar conta grátis</a>
          </p>
          <p className="lg-terms">
            Ao continuar, você concorda com os <a href="#">Termos</a> e a{' '}
            <a href="#">Política de Privacidade</a>.
          </p>
        </div>
      </div>
    </div>
  );
}