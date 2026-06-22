import { Node } from "@tiptap/core";
import { decodeTableMarkdown, encodeTableMarkdown, renderTableHtml } from "./table-block";

export const CgvTable = Node.create({
  name: "cgvTable",
  group: "block",
  atom: true,
  selectable: true,
  draggable: false,

  addAttributes() {
    return {
      markdown: {
        default: "",
        parseHTML: element => {
          const encoded = element.getAttribute("data-markdown");
          if (encoded) return decodeTableMarkdown(encoded);
          return element.textContent?.trim() ?? "";
        },
        renderHTML: attributes => ({
          "data-markdown": encodeTableMarkdown(String(attributes.markdown || ""))
        })
      }
    };
  },

  parseHTML() {
    return [{ tag: 'div[class="cgv-table"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ["div", { class: "cgv-table", ...HTMLAttributes }];
  },

  addNodeView() {
    return ({ node }) => {
      const dom = document.createElement("div");
      dom.className = "cgv-table";
      dom.dataset.markdown = encodeTableMarkdown(String(node.attrs.markdown || ""));

      const inner = document.createElement("div");
      inner.className = "cgv-table-inner";
      inner.innerHTML = renderTableHtml(String(node.attrs.markdown || ""));

      dom.appendChild(inner);
      return { dom };
    };
  }
});
