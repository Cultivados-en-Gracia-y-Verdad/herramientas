import type { EditorState, Extension, Range } from "@codemirror/state";
import {
  Decoration,
  EditorView,
  ViewPlugin,
  WidgetType,
  type DecorationSet,
  type ViewUpdate
} from "@codemirror/view";

interface ManualLineStyle {
  className: string;
  label: string;
  prefixLength: number;
  suffixLength: number;
  legacyComment?: boolean;
  widget?: WidgetType;
}

class ManualLabelWidget extends WidgetType {
  constructor(
    private readonly label: string,
    private readonly className: string
  ) {
    super();
  }

  eq(other: ManualLabelWidget): boolean {
    return other.label === this.label && other.className === this.className;
  }

  toDOM(): HTMLElement {
    const element = document.createElement("span");
    element.className = this.className;
    element.textContent = this.label;
    return element;
  }
}

function previousNonBlankLine(view: EditorView, lineNumber: number): string {
  for (let number = lineNumber - 1; number >= 1; number -= 1) {
    const text = view.state.doc.line(number).text.trim();
    if (text) return text;
  }
  return "";
}

function frontMatterEndLine(state: EditorState): number {
  if (state.doc.lines < 2 || state.doc.line(1).text.trim() !== "---") return 0;
  for (let number = 2; number <= state.doc.lines; number += 1) {
    if (state.doc.line(number).text.trim() === "---") return number;
  }
  return 0;
}

function headingStyle(level: number, prefixLength: number, suffixLength = 0): ManualLineStyle {
  return {
    className: `cm-cgv-manual-h${level}`,
    label: "",
    prefixLength,
    suffixLength
  };
}

function classifyLine(
  view: EditorView,
  lineNumber: number,
  text: string,
  frontMatterEnd: number
): ManualLineStyle {
  if (frontMatterEnd && lineNumber <= frontMatterEnd) {
    return { className: "cm-cgv-manual-yaml", label: "", prefixLength: 0, suffixLength: 0 };
  }

  if (!text.trim()) {
    return { className: "cm-cgv-manual-blank", label: "", prefixLength: 0, suffixLength: 0 };
  }

  const wrappedHeading = text.match(/^<!--\s*(#{1,6}\s+)([\s\S]*?)\s*-->$/);
  if (wrappedHeading) {
    const prefix = text.match(/^<!--\s*#{1,6}\s+/)?.[0] ?? "";
    const suffix = text.match(/\s*-->$/)?.[0] ?? "";
    return {
      ...headingStyle(wrappedHeading[1].trim().length, prefix.length, suffix.length),
      className: `cm-cgv-manual-h${wrappedHeading[1].trim().length} cm-cgv-manual-legacy-comment`,
      legacyComment: true
    };
  }

  const heading = text.match(/^(#{1,6})\s+/);
  if (heading) return headingStyle(heading[1].length, heading[0].length);

  const bullet = text.match(/^-\s+/);
  if (bullet) {
    return {
      className: "cm-cgv-manual-bullet",
      label: "",
      prefixLength: bullet[0].length,
      suffixLength: 0
    };
  }

  if (/^:\s*/.test(text)) {
    return {
      className: "cm-cgv-manual-definition",
      label: "",
      prefixLength: 0,
      suffixLength: 0
    };
  }

  const quiz = text.match(/^<!--\s*@quiz\s+#?([^\s]+)\s*-->$/);
  if (quiz) {
    return {
      className: "cm-cgv-manual-quiz",
      label: "",
      prefixLength: 0,
      suffixLength: 0,
      widget: new ManualLabelWidget(`Quiz: ${quiz[1]}`, "cm-cgv-manual-widget cm-cgv-manual-widget--quiz")
    };
  }

  if (/^---\s*$/.test(text)) {
    return {
      className: "cm-cgv-manual-break",
      label: "",
      prefixLength: 0,
      suffixLength: 0,
      widget: new ManualLabelWidget("Nueva diapositiva", "cm-cgv-manual-widget cm-cgv-manual-widget--break")
    };
  }

  if (text.trim() && /^###\s+/.test(previousNonBlankLine(view, lineNumber))) {
    return {
      className: "cm-cgv-manual-scripture",
      label: "",
      prefixLength: 0,
      suffixLength: 0
    };
  }

  return {
    className: "cm-cgv-manual-paragraph",
    label: "",
    prefixLength: 0,
    suffixLength: 0
  };
}

function addReplacement(
  decorations: Range<Decoration>[],
  atomic: Range<Decoration>[],
  from: number,
  to: number,
  widget?: WidgetType
) {
  if (to <= from) return;
  const replacement = Decoration.replace(widget ? { widget } : {});
  const range = replacement.range(from, to);
  decorations.push(range);
  atomic.push(range);
}

function addInlineDecorations(
  text: string,
  lineFrom: number,
  contentStart: number,
  contentEnd: number,
  decorations: Range<Decoration>[],
  atomic: Range<Decoration>[]
) {
  const patterns = [
    { regex: /__<u>([^<\n]+)<\/u>__/g, open: 5, close: 6, className: "cm-cgv-manual-underline" },
    { regex: /<u>([^<\n]+)<\/u>/g, open: 3, close: 4, className: "cm-cgv-manual-underline" },
    { regex: /\*\*([^*\n]+)\*\*/g, open: 2, close: 2, className: "cm-cgv-manual-bold" },
    { regex: /__([^_\n]+)__/g, open: 2, close: 2, className: "cm-cgv-manual-bold" },
    { regex: /(^|[^*])\*([^*\n]+)\*(?!\*)/g, open: 1, close: 1, className: "cm-cgv-manual-italic", leading: true }
  ];
  const occupied: Array<{ from: number; to: number }> = [];

  for (const pattern of patterns) {
    pattern.regex.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = pattern.regex.exec(text))) {
      const leading = pattern.leading ? match[1]?.length ?? 0 : 0;
      const start = lineFrom + match.index + leading;
      const end = lineFrom + match.index + match[0].length;
      const innerFrom = start + pattern.open;
      const innerTo = end - pattern.close;
      if (start < contentStart || end > contentEnd || innerTo <= innerFrom) continue;
      if (occupied.some(range => start < range.to && end > range.from)) continue;
      occupied.push({ from: start, to: end });

      addReplacement(decorations, atomic, start, innerFrom);
      decorations.push(Decoration.mark({ class: pattern.className }).range(innerFrom, innerTo));
      addReplacement(decorations, atomic, innerTo, end);
    }
  }
}

interface ManualDecorationSets {
  decorations: DecorationSet;
  atomic: DecorationSet;
}

function buildDecorations(view: EditorView): ManualDecorationSets {
  const decorations: Range<Decoration>[] = [];
  const atomic: Range<Decoration>[] = [];
  const seen = new Set<number>();
  const frontMatterEnd = frontMatterEndLine(view.state);

  for (const visible of view.visibleRanges) {
    const first = view.state.doc.lineAt(visible.from).number;
    const last = view.state.doc.lineAt(visible.to).number;

    for (let number = first; number <= last; number += 1) {
      if (seen.has(number)) continue;
      seen.add(number);

      const line = view.state.doc.line(number);
      const style = classifyLine(view, number, line.text, frontMatterEnd);
      const active = view.state.selection.ranges.some(
        range => range.from <= line.to && range.to >= line.from
      );
      const classes = ["cm-cgv-manual-line", style.className, active ? "cm-cgv-manual-line--active" : ""]
        .filter(Boolean)
        .join(" ");

      decorations.push(
        Decoration.line({
          attributes: { class: classes, "data-cgv-label": style.label }
        }).range(line.from)
      );

      if (style.widget) {
        addReplacement(decorations, atomic, line.from, line.to, style.widget);
        continue;
      }

      const contentStart = line.from + style.prefixLength;
      const contentEnd = line.to - style.suffixLength;
      addReplacement(decorations, atomic, line.from, contentStart);
      addReplacement(decorations, atomic, contentEnd, line.to);

      if (style.legacyComment && contentEnd > contentStart) {
        decorations.push(
          Decoration.mark({ class: "cm-cgv-manual-comment-content" }).range(contentStart, contentEnd)
        );
      }

      addInlineDecorations(
        line.text,
        line.from,
        contentStart,
        contentEnd,
        decorations,
        atomic
      );
    }
  }

  return {
    decorations: Decoration.set(decorations, true),
    atomic: Decoration.set(atomic, true)
  };
}

const manualDecorations = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;
    atomic: DecorationSet;

    constructor(view: EditorView) {
      const sets = buildDecorations(view);
      this.decorations = sets.decorations;
      this.atomic = sets.atomic;
    }

    update(update: ViewUpdate) {
      if (update.docChanged || update.selectionSet || update.viewportChanged) {
        const sets = buildDecorations(update.view);
        this.decorations = sets.decorations;
        this.atomic = sets.atomic;
      }
    }
  },
  { decorations: plugin => plugin.decorations }
);

export const codemirrorManualMode: Extension = [
  EditorView.editorAttributes.of({ class: "cm-cgv-manual-mode" }),
  manualDecorations,
  EditorView.atomicRanges.of(view => view.plugin(manualDecorations)?.atomic ?? Decoration.none)
];
