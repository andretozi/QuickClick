import Blob from '@/presentation/components/Blob/Blob.jsx';

/**
 * As duas luzes do fundo de uma seção da landing: uma coral e uma mel.
 * A posição e o tamanho ficam no CSS da seção: `<bloco>__blob--a` e `<bloco>__blob--b`.
 */
export default function SectionLights({ block }) {
  return (
    <>
      <Blob tone="coral" className={`${block}__blob ${block}__blob--a`} />
      <Blob tone="honey" className={`${block}__blob ${block}__blob--b`} />
    </>
  );
}
