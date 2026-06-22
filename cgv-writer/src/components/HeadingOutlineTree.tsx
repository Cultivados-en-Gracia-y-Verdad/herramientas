import type { HeadingOutlineNode } from "../lib/analyze";
import { dispatchOutlineNavigate } from "../lib/outline-bridge";

interface HeadingOutlineTreeProps {
  nodes: HeadingOutlineNode[];
}

function OutlineItem({ node }: { node: HeadingOutlineNode }) {
  return (
    <li className={`outline-level-${node.level}`}>
      <button
        type="button"
        className="outline-link"
        title={`Ir a ${"#".repeat(node.level)} ${node.title}`}
        onClick={() =>
          dispatchOutlineNavigate({
            level: node.level,
            bodyOffset: node.bodyOffset,
            ordinal: node.ordinal
          })
        }
      >
        {node.title}
      </button>
      {node.children.length > 0 && (
        <ul className="outline-tree">
          {node.children.map(child => (
            <OutlineItem key={child.id} node={child} />
          ))}
        </ul>
      )}
    </li>
  );
}

export function HeadingOutlineTree({ nodes }: HeadingOutlineTreeProps) {
  if (!nodes.length) {
    return <p className="outline-empty">Sin encabezados H1/H2/H3.</p>;
  }

  return (
    <ul className="outline-tree">
      {nodes.map(node => (
        <OutlineItem key={node.id} node={node} />
      ))}
    </ul>
  );
}
