import { Node } from "@tiptap/core";

/** Wraps ##### (H5) and nested ###### (H6) content for Presenter-compatible structure. */
export const CgvH5Block = Node.create({
  name: "cgvH5Block",
  group: "block",
  content: "block+",
  defining: true,

  parseHTML() {
    return [{ tag: 'div[class="cgv-h5-block"]' }];
  },

  renderHTML() {
    return ["div", { class: "cgv-h5-block" }, 0];
  }
});
