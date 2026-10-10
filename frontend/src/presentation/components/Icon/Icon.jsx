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
  x: { strokeWidth: 2.4, body: <path d="M7 7l10 10M17 7L7 17" /> },
  lock: {
    body: (
      <>
        <rect x="5" y="10.5" width="14" height="10" rx="2.5" />
        <path d="M8.5 10.5V8a3.5 3.5 0 017 0v2.5" />
      </>
    )
  },
  sync: {
    body: (
      <>
        <path d="M20 4v5h-5" />
        <path d="M4 20v-5h5" />
        <path d="M5.5 9.5A7 7 0 0118 7l2 2M4 15l2 2a7 7 0 0012.5-2.5" />
      </>
    )
  },
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
  'trend-down': {
    body: (
      <>
        <path d="M4 7l5 5 3-3 7 8" />
        <path d="M17 17h3v-3" />
      </>
    )
  },
  'chevron-down': { strokeWidth: 2.2, body: <path d="M6 9l6 6 6-6" /> },
  'chevron-right': { strokeWidth: 2.2, body: <path d="M9 6l6 6-6 6" /> },
  'arrow-left': { strokeWidth: 2.4, body: <path d="M19 12H5M11 6l-6 6 6 6" /> },
  search: {
    body: (
      <>
        <circle cx="11" cy="11" r="6.5" />
        <path d="M16 16l4.5 4.5" />
      </>
    )
  },
  plus: { strokeWidth: 2.4, body: <path d="M12 5v14M5 12h14" /> },
  trash: {
    body: (
      <>
        <path d="M4 7h16M9.5 7V4.8h5V7" />
        <path d="M6.5 7l1 12.2a1.8 1.8 0 001.8 1.6h5.4a1.8 1.8 0 001.8-1.6L17.5 7" />
        <path d="M10 11v6M14 11v6" />
      </>
    )
  },
  copy: {
    body: (
      <>
        <rect x="8.5" y="8.5" width="11.5" height="11.5" rx="2.5" />
        <path d="M15.5 8.5V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7.5a2 2 0 002 2h2.5" />
      </>
    )
  },
  pause: {
    body: (
      <>
        <rect x="6.5" y="5" width="3.6" height="14" rx="1.2" />
        <rect x="13.9" y="5" width="3.6" height="14" rx="1.2" />
      </>
    )
  },
  play: { body: <path d="M8 5.5v13l10.5-6.5L8 5.5z" /> },
  edit: {
    body: (
      <>
        <path d="M4 20h4.2L19 9.2a2.2 2.2 0 000-3.1l-1.1-1.1a2.2 2.2 0 00-3.1 0L4 15.8V20z" />
        <path d="M13.5 6.5l4 4" />
      </>
    )
  },
  logout: {
    body: (
      <>
        <path d="M14.5 4H18a2 2 0 012 2v12a2 2 0 01-2 2h-3.5" />
        <path d="M10 16l-4-4 4-4M6 12h10" />
      </>
    )
  },
  sliders: {
    body: (
      <>
        <path d="M4 7h9.5M18.5 7H20M4 17h3.5M12.5 17H20" />
        <circle cx="16" cy="7" r="2.5" />
        <circle cx="10" cy="17" r="2.5" />
      </>
    )
  },
  store: {
    body: (
      <>
        <path d="M4.5 10.5V19a1 1 0 001 1h13a1 1 0 001-1v-8.5" />
        <path d="M3 7l2-3h14l2 3v1a2.7 2.7 0 01-5.3.6 2.7 2.7 0 01-5.4 0A2.7 2.7 0 013 8V7z" />
        <path d="M10 20v-4.5h4V20" />
      </>
    )
  },
  upload: {
    body: (
      <>
        <path d="M12 15V4M7.5 8.5L12 4l4.5 4.5" />
        <path d="M5 15v3a2 2 0 002 2h10a2 2 0 002-2v-3" />
      </>
    )
  },
  image: {
    body: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="3" />
        <circle cx="8.5" cy="9.5" r="1.8" />
        <path d="M21 15.5l-5-5L7 19.5" />
      </>
    )
  },
  star: {
    body: <path d="M12 3.6l2.6 5.2 5.7.8-4.1 4 1 5.7-5.2-2.7-5.2 2.7 1-5.7-4.1-4 5.7-.8L12 3.6z" />
  },
  grid: {
    body: (
      <>
        <rect x="4" y="4" width="7" height="7" rx="1.8" />
        <rect x="13" y="4" width="7" height="7" rx="1.8" />
        <rect x="4" y="13" width="7" height="7" rx="1.8" />
        <rect x="13" y="13" width="7" height="7" rx="1.8" />
      </>
    )
  },
  chart: { body: <path d="M4 20V11M10 20V5M16 20v-7M3 20h18" /> },
  info: {
    body: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v5.5M12 7.6v.01" />
      </>
    )
  },
  alert: {
    body: (
      <>
        <path d="M10.3 4.6L2.9 17.5A2 2 0 004.6 20.5h14.8a2 2 0 001.7-3L13.7 4.6a2 2 0 00-3.4 0z" />
        <path d="M12 9.5v4M12 16.8v.01" />
      </>
    )
  },
  external: {
    body: (
      <>
        <path d="M14 4h6v6M20 4l-9 9" />
        <path d="M18 14v4a2 2 0 01-2 2H6a2 2 0 01-2-2V8a2 2 0 012-2h4" />
      </>
    )
  },
  home: {
    body: (
      <>
        <path d="M4 11l8-7 8 7" />
        <path d="M6.5 9.5V20h11V9.5" />
      </>
    )
  },
  package: {
    body: (
      <>
        <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" />
        <path d="M4 7.5l8 4.5 8-4.5M12 12v9" />
      </>
    )
  },
  tag: {
    body: (
      <>
        <path d="M3.5 12.2V4.5a1 1 0 011-1h7.7l8.3 8.3a1.5 1.5 0 010 2.1l-6.2 6.2a1.5 1.5 0 01-2.1 0l-8.7-7.9z" />
        <circle cx="8" cy="8" r="1.4" />
      </>
    )
  },
  shield: { body: <path d="M12 3l7 3v5.5c0 4.3-3 7.8-7 9.5-4-1.7-7-5.2-7-9.5V6l7-3z" /> },
  link: {
    body: (
      <>
        <path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1.2 1.2" />
        <path d="M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1.2-1.2" />
      </>
    )
  },
  bell: {
    body: (
      <>
        <path d="M6 16v-5a6 6 0 0112 0v5l1.5 2h-15L6 16z" />
        <path d="M10 20.5a2.2 2.2 0 004 0" />
      </>
    )
  },
  clock: {
    body: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3.2 2" />
      </>
    )
  },
  cart: {
    body: (
      <>
        <path d="M3.5 5h2.2l2 10.2h10.4L20 8H6.6" />
        <circle cx="10" cy="19" r="1.4" />
        <circle cx="17" cy="19" r="1.4" />
      </>
    )
  },
  menu: { body: <path d="M4 7h16M4 12h16M4 17h16" /> },

  /* ---------- Ícones preenchidos ---------- */
  sparkle: {
    filled: true,
    body: <path d="M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6L12 3z" />
  },
  sparkles: {
    filled: true,
    body: (
      <>
        <path d="M10 2.5l1.7 5L16.6 9.2l-4.9 1.7L10 15.8l-1.7-4.9L3.4 9.2l4.9-1.7L10 2.5z" />
        <path d="M18 13l1 2.8 2.8 1-2.8 1L18 20.6l-1-2.8-2.8-1 2.8-1L18 13z" />
      </>
    )
  },
  more: {
    filled: true,
    body: (
      <>
        <circle cx="5.5" cy="12" r="1.9" />
        <circle cx="12" cy="12" r="1.9" />
        <circle cx="18.5" cy="12" r="1.9" />
      </>
    )
  },
  'star-filled': {
    filled: true,
    body: <path d="M12 3.6l2.6 5.2 5.7.8-4.1 4 1 5.7-5.2-2.7-5.2 2.7 1-5.7-4.1-4 5.7-.8L12 3.6z" />
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
