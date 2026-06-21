import Paragraph from "@tiptap/extension-paragraph";

/** Preserves paragraph `class` (e.g. cgv-scripture) through TipTap parse/render. */
export const CgvParagraph = Paragraph.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      class: {
        default: null,
        parseHTML: element => element.getAttribute("class"),
        renderHTML: attributes => {
          if (!attributes.class) return {};
          return { class: attributes.class };
        }
      },
      dataQuizId: {
        default: null,
        parseHTML: element => element.getAttribute("data-quiz-id"),
        renderHTML: attributes => {
          if (!attributes.dataQuizId) return {};
          return { "data-quiz-id": attributes.dataQuizId };
        }
      }
    };
  }
});
