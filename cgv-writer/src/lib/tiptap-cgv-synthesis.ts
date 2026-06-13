import Blockquote from "@tiptap/extension-blockquote";

/** En Síntesis review — one blockquote unit for round-trip with Presenter. */
export const CgvSynthesisBlockquote = Blockquote.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      class: {
        default: "cgv-synthesis synthesis-box",
        parseHTML: element =>
          element.getAttribute("class") || "cgv-synthesis synthesis-box",
        renderHTML: attributes => ({
          class: attributes.class || "cgv-synthesis synthesis-box"
        })
      }
    };
  }
});
