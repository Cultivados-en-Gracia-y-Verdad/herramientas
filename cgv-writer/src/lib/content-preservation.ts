function stripCommentWrapper(text: string): string {
  const trimmed = String(text || "").trim();
  const match = trimmed.match(/^<!--\s*([\s\S]*?)\s*-->$/);
  return match ? match[1].trim() : trimmed;
}

/** Normalize a markdown line to a comparable content fingerprint (format-agnostic). */
export function normalizeContentFingerprint(line: string): string {
  return stripCommentWrapper(line)
    .replace(/^>\s?-?\s*/, "")
    .replace(/^#{1,6}\s+/, "")
    .replace(/^-\s+/, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function fingerprintMultiset(md: string): Map<string, number> {
  const map = new Map<string, number>();
  for (const line of String(md || "").split("\n")) {
    const fp = normalizeContentFingerprint(line);
    if (!fp) continue;
    map.set(fp, (map.get(fp) ?? 0) + 1);
  }
  return map;
}

function exampleLineForFingerprint(md: string, fingerprint: string): string {
  for (const line of String(md || "").split("\n")) {
    if (normalizeContentFingerprint(line) === fingerprint) {
      return line.trim();
    }
  }
  return fingerprint;
}

export interface ContentLossCheck {
  missing: string[];
  missingCount: number;
}

/** Every substantive line in `before` must still appear in `after` (multiset). */
export function checkContentPreserved(before: string, after: string): ContentLossCheck {
  const beforeMap = fingerprintMultiset(before);
  const afterMap = fingerprintMultiset(after);
  const missing: string[] = [];
  let missingCount = 0;

  for (const [fp, count] of beforeMap) {
    const afterCount = afterMap.get(fp) ?? 0;
    if (afterCount >= count) continue;

    const deficit = count - afterCount;
    missingCount += deficit;
    missing.push(exampleLineForFingerprint(before, fp));
  }

  return { missing, missingCount };
}

export interface SafeTransformResult {
  output: string;
  changed: boolean;
  blocked: boolean;
  loss: ContentLossCheck;
}

/** Run `transform` only when it preserves every content line; otherwise return source unchanged. */
export function safeMarkdownTransform(
  source: string,
  transform: (md: string) => string
): SafeTransformResult {
  const input = String(source || "");
  if (!input.trim()) {
    const output = transform(input);
    return {
      output,
      changed: output !== input,
      blocked: false,
      loss: { missing: [], missingCount: 0 }
    };
  }

  const candidate = transform(input);
  const loss = checkContentPreserved(input, candidate);
  if (loss.missingCount > 0) {
    return {
      output: input,
      changed: false,
      blocked: true,
      loss
    };
  }

  return {
    output: candidate,
    changed: candidate !== input,
    blocked: false,
    loss: { missing: [], missingCount: 0 }
  };
}
