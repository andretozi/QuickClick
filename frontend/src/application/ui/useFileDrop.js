import { useCallback, useRef, useState } from 'react';

/**
 * Aplicação · Área de soltar arquivos: sabe quando há algo sendo arrastado por cima
 * e entrega os arquivos (soltos ou escolhidos no seletor) para `onFiles`.
 */
export default function useFileDrop(onFiles, { disabled = false } = {}) {
  const [dragging, setDragging] = useState(false);
  const depth = useRef(0); // dragenter e dragleave disparam também nos filhos
  const inputRef = useRef(null);

  const onDragEnter = useCallback(
    (event) => {
      event.preventDefault();
      if (disabled) return;
      depth.current += 1;
      setDragging(true);
    },
    [disabled]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
  }, []);

  const onDragLeave = useCallback((event) => {
    event.preventDefault();
    depth.current = Math.max(0, depth.current - 1);
    if (depth.current === 0) setDragging(false);
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      depth.current = 0;
      setDragging(false);
      if (!disabled) onFiles(event.dataTransfer?.files);
    },
    [disabled, onFiles]
  );

  const openPicker = useCallback(() => {
    if (!disabled) inputRef.current?.click();
  }, [disabled]);

  const onInputChange = useCallback(
    (event) => {
      onFiles(event.target.files);
      event.target.value = ''; // deixa escolher o mesmo arquivo de novo
    },
    [onFiles]
  );

  return { dragging, inputRef, openPicker, onInputChange, dropProps: { onDragEnter, onDragOver, onDragLeave, onDrop } };
}
