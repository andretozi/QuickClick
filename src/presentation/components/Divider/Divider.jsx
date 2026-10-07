import './Divider.css';

/** Linha divisória com um texto no meio ("ou entre com e-mail"). */
export default function Divider({ children }) {
  return (
    <div className="divider">
      <span className="divider__line" />
      <span className="divider__text">{children}</span>
      <span className="divider__line" />
    </div>
  );
}
