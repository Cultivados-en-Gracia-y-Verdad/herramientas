/** Internal marker for ###### lines stored inside a commentary bullets array. */
const H6_BULLET_PREFIX = "\u2060h6:";

export function markH6Bullet(text: string): string {
  return `${H6_BULLET_PREFIX}${text.trim()}`;
}

export function isH6Bullet(text: string): boolean {
  return String(text || "").startsWith(H6_BULLET_PREFIX);
}

export function unmarkH6Bullet(text: string): string {
  return isH6Bullet(text) ? text.slice(H6_BULLET_PREFIX.length) : text;
}
