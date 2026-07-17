import { parseNblaContent } from "cgv-bible";
import type { BibleVerse } from "cgv-bible";
import titusNbla from "../../../cgv-data/bibles/NBLA/tito.nbla.md?raw";
import titusMorph from "../../../cgv-data/morphology/MorphGNT/77-Tit-morphgnt.txt?raw";
import titusAlignment from "../../MNA/datasets/interlinear/NT/tito.tokens.jsonl?raw";

export interface GreekToken {
  id: string;
  chapter: number;
  verse: number;
  token: number;
  surface: string;
  sourceMorph: string;
  rmac: string;
  lemma: string;
}

export interface GreekVerse {
  chapter: number;
  verse: number;
  label: string;
  tokens: GreekToken[];
}

export interface AlignmentToken {
  id: string;
  chapter: number;
  verse: number;
  token: number;
  surface: string;
  lemma: string;
  morph: string;
  es: string;
}

export interface TitusData {
  alignment: AlignmentToken[];
  greek: Array<[number, GreekVerse[]]>;
  spanish: BibleVerse[];
}

function parseMorphLine(line: string, index: number): GreekToken | null {
  const match = line.match(/^(\d{6})\s+(\S+)\s+(\S+)\s+(\S+)\s+\S+\s+\S+\s+(.+)$/);
  if (!match) return null;

  const [, reference, partOfSpeech, morph, surface, lemma] = match;
  const chapter = Number(reference.slice(2, 4));
  const verse = Number(reference.slice(4, 6));
  const sourceMorph = `${partOfSpeech}${morph}`;

  return {
    id: `${reference}-${index}`,
    chapter,
    verse,
    token: 0,
    surface,
    sourceMorph,
    rmac: morphGntToRmac(sourceMorph, lemma),
    lemma
  };
}

function parseAlignmentLine(line: string): AlignmentToken | null {
  try {
    const parsed = JSON.parse(line);
    if (!parsed || parsed.book !== "tito") return null;
    if (
      typeof parsed.ch !== "number" ||
      typeof parsed.vs !== "number" ||
      typeof parsed.tok !== "number" ||
      typeof parsed.surface !== "string" ||
      typeof parsed.lemma !== "string" ||
      typeof parsed.morph !== "string" ||
      typeof parsed.es !== "string"
    ) {
      return null;
    }

    return {
      id: `${parsed.ch}:${parsed.vs}:${parsed.tok}`,
      chapter: parsed.ch,
      verse: parsed.vs,
      token: parsed.tok,
      surface: parsed.surface,
      lemma: parsed.lemma,
      morph: parsed.morph,
      es: parsed.es.replace(/·/g, " ")
    };
  } catch {
    return null;
  }
}

function ch(value: string, index: number): string {
  return value[index] ?? "-";
}

function declensionSuffix(morph: string, allowNoGender = false): string {
  const grammaticalCase = ch(morph, 6);
  const number = ch(morph, 7);
  const gender = ch(morph, 8);
  if (grammaticalCase === "-" || grammaticalCase === "?" || number === "-" || number === "?") {
    return "";
  }
  if (gender === "-" || gender === "?") {
    return allowNoGender ? `${grammaticalCase}${number}` : "";
  }
  return `${grammaticalCase}${number}${gender}`;
}

function degreeSuffix(morph: string): string {
  const degree = ch(morph, 9);
  if (degree === "C") return "-C";
  if (degree === "S") return "-S";
  return "";
}

function verbRmac(morph: string): string {
  const code = morph.startsWith("V-") ? morph.slice(2) : morph.slice(1);
  if (code.length < 4) return morph;

  const tenseMap: Record<string, string> = { P: "P", I: "I", F: "F", A: "A", R: "X", L: "Y", X: "X" };
  const voiceMap: Record<string, string> = { A: "A", M: "M", P: "P", E: "E", D: "M", O: "P", N: "E" };
  const moodMap: Record<string, string> = { I: "I", S: "S", O: "O", D: "M", M: "M", N: "N", P: "P" };
  const numberMap: Record<string, string> = { S: "S", P: "P" };
  const person = code[0];
  const tense = tenseMap[code[1]] ?? code[1];
  const voice = voiceMap[code[2]] ?? code[2];
  const mood = moodMap[code[3]] ?? code[3];
  const number = numberMap[code[5]] ?? code[5] ?? "";

  if (["1", "2", "3"].includes(person) && number) {
    return `V-${tense}${voice}${mood}-${person}${number}`;
  }
  return `V-${tense}${voice}${mood}`;
}

function declinedRmac(prefix: string, morph: string, lemma = ""): string {
  const pronounPerson: Record<string, string> = {
    "ἐγώ": "1",
    "σύ": "2",
    "ἡμεῖς": "1",
    "ὑμεῖς": "2",
    "αὐτός": "3",
    "ἑαυτοῦ": "3",
    "ἑαυτός": "3"
  };

  if (prefix === "P" && pronounPerson[lemma]) {
    const suffix = declensionSuffix(morph, true);
    return suffix ? `P-${pronounPerson[lemma]}${suffix}${degreeSuffix(morph)}` : prefix;
  }

  const suffix = declensionSuffix(morph);
  return suffix ? `${prefix}-${suffix}${degreeSuffix(morph)}` : prefix;
}

function morphGntToRmac(morph: string, lemma = ""): string {
  if (!morph || morph === "-") return morph;
  if (morph.startsWith("V-")) return verbRmac(morph);

  const twoLetterPrefixes: Record<string, string> = {
    RA: "T",
    RD: "D",
    RI: "I",
    RR: "R",
    RP: "P"
  };
  const twoLetter = morph.slice(0, 2);
  if (twoLetterPrefixes[twoLetter]) {
    return declinedRmac(twoLetterPrefixes[twoLetter], morph, lemma);
  }

  const posPrefixes: Record<string, string> = {
    N: "N",
    A: "A",
    C: "CONJ",
    D: "ADV",
    I: "INJ",
    P: "PREP",
    X: "PRT"
  };
  const pos = morph[0];
  if (pos === "N" || pos === "A") return declinedRmac(posPrefixes[pos], morph, lemma);
  return posPrefixes[pos] ?? morph;
}

export function loadTitusData(): TitusData {
  const verses = new Map<string, GreekVerse>();

  titusMorph
    .replace(/\r\n/g, "\n")
    .split("\n")
    .forEach((line, index) => {
      const token = parseMorphLine(line.trim(), index);
      if (!token) return;

      const key = `${token.chapter}:${token.verse}`;
      const verse =
        verses.get(key) ??
        {
          chapter: token.chapter,
          verse: token.verse,
          label: `Tito ${token.chapter}:${token.verse}`,
          tokens: []
        };

      token.token = verse.tokens.length + 1;
      verse.tokens.push(token);
      verses.set(key, verse);
    });

  const byChapter = new Map<number, GreekVerse[]>();
  for (const verse of verses.values()) {
    const chapter = byChapter.get(verse.chapter) ?? [];
    chapter.push(verse);
    byChapter.set(verse.chapter, chapter);
  }

  return {
    alignment: titusAlignment
      .replace(/\r\n/g, "\n")
      .split("\n")
      .map(line => parseAlignmentLine(line.trim()))
      .filter((token): token is AlignmentToken => Boolean(token)),
    greek: Array.from(byChapter.entries()),
    spanish: parseNblaContent(titusNbla)
  };
}
