/** Junta classes CSS ignorando valores vazios: cx('a', cond && 'b') → 'a b'. */
export function cx(...classes) {
  return classes.filter(Boolean).join(' ');
}
