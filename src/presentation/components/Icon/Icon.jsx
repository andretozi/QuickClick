/**
 * Biblioteca única de ícones SVG.
 * Os ícones de traço usam `currentColor`: a cor vem do CSS de quem usa.
 *
 * Uso: <Icon name="arrow-right" size={18} />
 */
const ICONS = {
  'arrow-right': { strokeWidth: 2.4, body: <path d="M5 12h14M13 6l6 6-6 6" /> },
  'arrow-down': { body: <path d="M12 5v14M6 13l6 6 6-6" /> },
  'chevron-left': { strokeWidth: 2.2, body: <path d="M15 6l-6 6 6 6" /> },
  user: {
    body: <path d="M12 12a4 4 0 100-8 4 4 0 000 8zM5 20c0-3.3 3.1-6 7-6s7 2.7 7 6" />
  },
  check: { strokeWidth: 2.6, body: <path d="M5 12.5l4 4L19 7" /> },
  'check-circle': {
    body: (
      <>
        <circle cx="12" cy="12" r="11" fill="currentColor" stroke="none" />
        <path d="M7 12.5l3.2 3.2L17 9" stroke="#fff" strokeWidth="2.2" />
      </>
    )
  },
  eye: {
    body: (
      <>
        <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
        <circle cx="12" cy="12" r="3" />
      </>
    )
  },
  'eye-off': {
    body: (
      <path d="M3 3l18 18M10.6 10.7a3 3 0 004.2 4.2M9.4 5.2A9.4 9.4 0 0112 5c6.5 0 10 7 10 7a17 17 0 01-3.3 4.1M6.1 6.6A17 17 0 002 12s3.5 7 10 7a9.3 9.3 0 003.4-.6" />
    )
  },
  dollar: {
    body: (
      <path d="M12 2v20M17 6.5C17 4.6 14.8 4 12 4S7 4.9 7 7s2.5 2.6 5 3 5 1 5 3.4S14.8 20 12 20s-5-.7-5-2.8" />
    )
  },
  camera: {
    body: (
      <>
        <rect x="3" y="6" width="18" height="14" rx="3" />
        <circle cx="12" cy="13" r="3.4" />
        <path d="M8 6l1.4-2.2h5.2L16 6" />
      </>
    )
  },
  'trend-up': {
    body: (
      <>
        <path d="M4 18l5-5 3 3 7-8" />
        <path d="M17 8h3v3" />
      </>
    )
  },

  /* ---------- Ícones preenchidos ---------- */
  sparkle: {
    filled: true,
    body: <path d="M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6L12 3z" />
  },
  'logo-spark': {
    filled: true,
    body: (
      <path
        d="M4 3l6.9 16.6 2.45-7.25 7.25-2.45L4 3z"
        stroke="currentColor"
        strokeWidth="1"
        strokeLinejoin="round"
      />
    )
  },
  cursor: {
    filled: true,
    body: (
      <path
        d="M6 3l13 8.2-5.3 1.5 3 5.8-3 1.3-2.9-5.7L6 19V3z"
        stroke="#fff"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    )
  },
  apple: {
    filled: true,
    body: (
      <path d="M16.4 12.8c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.1-2.8.8-3.5.8-.7 0-1.9-.8-3-.8-1.6 0-3 .9-3.8 2.3-1.6 2.8-.4 7 1.2 9.3.8 1.1 1.7 2.4 2.9 2.3 1.2 0 1.6-.7 3-.7s1.8.7 3 .7c1.2 0 2-1.1 2.8-2.2.9-1.3 1.2-2.5 1.3-2.6-.1 0-2.5-1-2.5-3.8zM14.2 5.9c.6-.8 1-1.8.9-2.9-.9 0-2 .6-2.6 1.3-.6.6-1.1 1.7-1 2.7 1 .1 2-.5 2.7-1.1z" />
    )
  },
  facebook: {
    filled: true,
    body: (
      <path d="M22 12a10 10 0 10-11.6 9.9v-7H7.9V12h2.5V9.8c0-2.5 1.5-3.9 3.8-3.9 1.1 0 2.2.2 2.2.2v2.5h-1.2c-1.2 0-1.6.8-1.6 1.6V12h2.7l-.4 2.9h-2.3v7A10 10 0 0022 12z" />
    )
  },
  google: {
    filled: true,
    viewBox: '0 0 48 48',
    body: (
      <>
        <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.4 29.3 35 24 35c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.6 6.1 29.6 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.3-.4-3.5z" />
        <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 18.9 13 24 13c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.6 6.1 29.6 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
        <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.5-5.2l-6.2-5.3C29.2 34.9 26.7 36 24 36c-5.3 0-9.7-2.6-11.3-6.9l-6.5 5C9.6 39.6 16.2 44 24 44z" />
        <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4 5.5l6.2 5.3C41 38.4 44 32 44 24c0-1.3-.1-2.3-.4-3.5z" />
      </>
    )
  }
};

export default function Icon({ name, size = 20, width, height, strokeWidth, className, ...rest }) {
  const icon = ICONS[name];
  if (!icon) return null;

  const paint = icon.filled
    ? { fill: 'currentColor' }
    : {
        fill: 'none',
        stroke: 'currentColor',
        strokeWidth: strokeWidth ?? icon.strokeWidth ?? 2,
        strokeLinecap: 'round',
        strokeLinejoin: 'round'
      };

  return (
    <svg
      width={width ?? size}
      height={height ?? size}
      viewBox={icon.viewBox ?? '0 0 24 24'}
      className={className}
      aria-hidden="true"
      focusable="false"
      {...paint}
      {...rest}
    >
      {icon.body}
    </svg>
  );
}
