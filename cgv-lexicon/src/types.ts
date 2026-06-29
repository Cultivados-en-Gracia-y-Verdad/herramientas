export type LexiconLang = "grc" | "hbo";

export interface LexiconEntry {
  lang: LexiconLang;
  lemma: string;
  gloss_es?: string;
  strongs?: string;
  sources: string[];
}

export interface LexiconManifest {
  built_at: string;
  producer: string;
  grc: { entries: number; with_gloss: number; with_strongs: number };
  hbo: { entries: number; with_gloss: number; with_strongs: number };
}
