/**
 * Turn known terms inside a plain-text string (profile.json copy, mostly) into links, without
 * ever touching the underlying data — the PDF builder reads the same strings as plain text, so
 * the linking has to happen at render time, not by baking markup into the content files.
 *
 * Usage in an .astro template:
 *   {linkify(profile.pitch, LINK_TERMS).map((p) =>
 *     typeof p === "string" ? p : <a href={p.href} target={p.external ? "_blank" : undefined} rel={p.external ? "noopener" : undefined}>{p.text}</a>
 *   )}
 */
export interface LinkTerm {
  href: string;
  external?: boolean;
}

export type LinkPart = string | { text: string; href: string; external?: boolean };

/**
 * @param text   the plain-text string to scan
 * @param terms  { "exact phrase to find": { href, external } }, longest phrase wins on overlap
 * @param once   if true (default), only the first match of each term is linked — repeating the
 *               same link in one paragraph reads as noise, not help
 */
export function linkify(text: string, terms: Record<string, LinkTerm>, once = true): LinkPart[] {
  const phrases = Object.keys(terms).sort((a, b) => b.length - a.length);
  if (!phrases.length || !text) return [text];
  const pattern = new RegExp(`(${phrases.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "g");
  const seen = new Set<string>();
  const out: LinkPart[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = pattern.exec(text))) {
    const phrase = m[1];
    const already = once && seen.has(phrase);
    if (m.index > last) out.push(text.slice(last, m.index));
    if (already) {
      out.push(phrase);
    } else {
      const t = terms[phrase];
      out.push({ text: phrase, href: t.href, external: t.external });
      seen.add(phrase);
    }
    last = m.index + phrase.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}
