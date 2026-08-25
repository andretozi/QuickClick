const SPARK_SIZE = { nav: 21, 'brand-panel': 20, footer: 19 };

export default function LogoMark({ variant = 'nav' }) {
  const size = SPARK_SIZE[variant] ?? SPARK_SIZE.nav;
  return (
    <span className={`qc-logo qc-logo--${variant}`}>
      <span className="qc-logo__pulse" data-logo-pulse />
      <span className="qc-logo__box">
        <span className="qc-logo__ring" />
        <svg
          width={size}
          height={size}
          viewBox="0 0 24 24"
          fill="none"
          className="qc-logo__spark"
        >
          <path
            d="M4 3l6.9 16.6 2.45-7.25 7.25-2.45L4 3z"
            fill="#fff"
            stroke="#fff"
            strokeWidth="1"
            strokeLinejoin="round"
          />
        </svg>
      </span>
    </span>
  );
}
