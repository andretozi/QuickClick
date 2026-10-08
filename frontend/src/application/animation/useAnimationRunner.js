import { useEffect } from 'react';

/**
 * Aplicação · Liga um "runner" de animação (infraestrutura) ao ciclo de vida do React.
 * O runner recebe o elemento raiz e devolve a função de limpeza, chamada ao sair da página.
 *
 * @param {React.RefObject<HTMLElement>} rootRef
 * @param {(root: HTMLElement) => () => void} run
 */
export default function useAnimationRunner(rootRef, run) {
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    return run(root);
  }, [rootRef, run]);
}
