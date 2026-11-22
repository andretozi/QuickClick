import { useEffect, useMemo, useState } from 'react';
import QRCode from 'qrcode';
import Button from '@/presentation/components/Button/Button.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import Modal from '@/presentation/components/Modal/Modal.jsx';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { LISTING_DETAIL } from '@/domain/content/listingContent.js';
import './QrCodeModal.css';

export default function QrCodeModal({ open, onClose, channelSlug, channelName, listingTitle, url }) {
  const [copied, setCopied] = useState(false);

  const safeUrl = typeof url === 'string' && url.trim().startsWith('https://') ? url.trim() : null;

  useEffect(() => {
    setCopied(false);
  }, [open, safeUrl]);

  const qrData = useMemo(() => {
    if (!safeUrl) return null;
    try {
      const qr = QRCode.create(safeUrl, { errorCorrectionLevel: 'M' });
      const size = qr.modules.size;
      const data = qr.modules.data;
      const margin = 4;
      const total = size + margin * 2;
      const segments = [];

      for (let row = 0; row < size; row += 1) {
        for (let col = 0; col < size; col += 1) {
          if (data[row * size + col]) {
            segments.push(`M${col + margin} ${row + margin}h1v1h-1z`);
          }
        }
      }

      return {
        total,
        viewBox: `0 0 ${total} ${total}`,
        path: segments.join('')
      };
    } catch {
      return null;
    }
  }, [safeUrl]);

  const handleCopy = async () => {
    if (!safeUrl) return;
    try {
      await navigator.clipboard.writeText(safeUrl);
      setCopied(true);
      showToast({
        tone: TOAST_TONES.SUCCESS,
        title: LISTING_DETAIL.toasts.qrCopied.title,
        text: LISTING_DETAIL.toasts.qrCopied.text
      });
    } catch {
      showToast({
        tone: TOAST_TONES.ERROR,
        title: LISTING_DETAIL.toasts.qrCopyError.title,
        text: LISTING_DETAIL.toasts.qrCopyError.text
      });
    }
  };

  return (
    <Modal
      open={Boolean(open && safeUrl && qrData)}
      onClose={onClose}
      size="md"
      className="qr-code-modal"
      media={
        channelSlug ? (
          <span className="qr-code-modal__brand">
            <MarketplaceLogo slug={channelSlug} size="md" decorative />
          </span>
        ) : null
      }
      title={channelName ? LISTING_DETAIL.channels.qrModal.title(channelName) : ''}
      description={LISTING_DETAIL.channels.qrModal.description}
      actions={
        safeUrl ? (
          <div className="qr-code-modal__actions">
            <Button
              variant="outline"
              size="sm"
              icon={copied ? 'check' : 'copy'}
              iconPosition="start"
              iconSize={15}
              onClick={handleCopy}
              className="qr-code-modal__action-btn"
              data-autofocus
            >
              {copied ? LISTING_DETAIL.channels.qrModal.copied : LISTING_DETAIL.channels.qrModal.copyLink}
            </Button>
            <Button
              href={safeUrl}
              target="_blank"
              rel="noopener noreferrer"
              size="sm"
              icon="external"
              iconPosition="start"
              iconSize={15}
              className="qr-code-modal__action-btn"
            >
              {LISTING_DETAIL.channels.qrModal.openListing}
            </Button>
          </div>
        ) : null
      }
    >
      {qrData && (
        <div className="qr-code-modal__frame">
          <svg
            className="qr-code-modal__svg"
            viewBox={qrData.viewBox}
            role="img"
            aria-label={LISTING_DETAIL.channels.qrModal.qrAlt(channelName ?? '')}
            shapeRendering="crispEdges"
          >
            <rect width={qrData.total} height={qrData.total} fill="#ffffff" />
            <path d={qrData.path} fill="#12100e" />
          </svg>
        </div>
      )}
      {listingTitle && <p className="qr-code-modal__listing-title">{listingTitle}</p>}
      {safeUrl && <p className="qr-code-modal__url">{safeUrl}</p>}
    </Modal>
  );
}
