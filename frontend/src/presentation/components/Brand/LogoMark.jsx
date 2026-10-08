import Icon from '@/presentation/components/Icon/Icon.jsx';
import './LogoMark.css';

const SPARK_SIZE = { sm: 19, md: 20, lg: 21 };

/** Ícone da marca (quadrado laranja com o "clique"). size: 'sm' | 'md' | 'lg' */
export default function LogoMark({ size = 'lg' }) {
  return (
    <span className={`logo-mark logo-mark--${size}`} aria-hidden="true">
      <span className="logo-mark__pulse" data-logo-pulse />
      <span className="logo-mark__box">
        <span className="logo-mark__ring" />
        <Icon name="logo-spark" size={SPARK_SIZE[size]} className="logo-mark__spark" />
      </span>
    </span>
  );
}
