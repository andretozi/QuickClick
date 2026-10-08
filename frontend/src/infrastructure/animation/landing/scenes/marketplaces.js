/** Marketplaces: os disponíveis ganham um ponto verde "no ar", pulsando um depois do outro. */
export function animateMarketplaces(animator, scene) {
  animator.parts('live', scene).forEach((dot, i) =>
    animator.animate(
      dot,
      [{ boxShadow: '0 0 0 0 rgba(55,160,106,.55)' }, { boxShadow: '0 0 0 7px rgba(55,160,106,0)' }],
      { duration: 1800, delay: 400 + i * 300, iterations: Infinity, easing: 'ease-out' }
    )
  );
}
