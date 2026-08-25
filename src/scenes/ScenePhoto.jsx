export default function ScenePhoto() {
  return (
    <div
      data-reveal="left"
      data-scene="foto"
      style={{ order: 1, display: 'flex', justifyContent: 'center' }}
    >
      <div className="qc-f-stage">
        <div className="qc-f-phone">
          <div className="qc-f-screen">
            <div data-f-bracket className="qc-f-bracket qc-f-bracket--tl" />
            <div data-f-bracket className="qc-f-bracket qc-f-bracket--tr" />
            <div data-f-bracket className="qc-f-bracket qc-f-bracket--bl" />
            <div data-f-bracket className="qc-f-bracket qc-f-bracket--br" />
            <div data-f-prod className="qc-f-prod">
              <div className="qc-f-prod__body" />
              <div className="qc-f-prod__shade" />
              <div className="qc-f-prod__dot" />
            </div>
            <div data-f-flash className="qc-f-flash" />
          </div>
          <div className="qc-f-shutter-wrap">
            <div data-f-shutter className="qc-f-shutter" />
          </div>
        </div>
        <div data-f-listing className="qc-f-listing">
          <div className="qc-f-listing__head">
            <div className="qc-f-listing__thumb" />
            <div className="qc-f-listing__lines">
              <div className="qc-f-listing__line qc-f-listing__line--a" />
              <div className="qc-f-listing__line qc-f-listing__line--b" />
            </div>
          </div>
          <div className="qc-f-listing__foot">
            <span className="qc-f-listing__price">R$ 189</span>
            <span className="qc-f-listing__ok">
              Anúncio criado
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                <path
                  d="M5 12.5l4 4L19 7"
                  stroke="#37A06A"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
