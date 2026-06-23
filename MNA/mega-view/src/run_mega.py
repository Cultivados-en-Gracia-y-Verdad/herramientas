#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engines.io import load_tokens, write_json, ensure_dir
from engines import (
    repeated_lemmas,
    discourse_markers,
    mood_distribution,
    imperatives,
    contrast_markers,
    boundary_signals,
    signal_summary,
    concentration_engine,
    concentration_clusters,
    region_engine,
    flow_engine,
    flow_interpreter,
    wanted_engine,
)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def md_table(rows, columns, limit=None):
    if limit:
        rows = rows[:limit]

    if not rows:
        return "_None found._\n"

    out = []
    out.append("| " + " | ".join(columns) + " |")
    out.append("| " + " | ".join(["---"] * len(columns)) + " |")

    for r in rows:
        vals = []
        for c in columns:
            v = r.get(c, "")
            if isinstance(v, list):
                v = ", ".join(map(str, v))
            if isinstance(v, dict):
                v = json.dumps(v, ensure_ascii=False)
            vals.append(str(v).replace("|", "\\|"))
        out.append("| " + " | ".join(vals) + " |")

    return "\n".join(out) + "\n"


def write_markdown(path, book, results):
    lines = [
        f"# Mega View: {book}",
        "",
        "Generated from interlinear token data. These are observable signals, not an outline or interpretation.",
        "",
    ]

    lines.append("## Flow")
    lines.append(md_table(
        results.get("flow", []),
        [
            "chapter",
            "imperatives",
            "markers",
            "contrasts",
            "boundaries",
            "action_lemmas",
            "indicatives",
            "participles",
            "subjunctives",
            "infinitives",
        ],
    ))
    lines.append("")

    flow_view = results.get("flow_interpretation", {})

    lines.append("## Flow Interpretation")
    lines.append("")

    lines.append("### Peaks")
    rows = []
    for r in flow_view.get("peaks", []):
        rows.append({
            "metric": r.get("metric", ""),
            "chapters": ", ".join(map(str, r.get("chapters", []))),
        })
    lines.append(md_table(rows, ["metric", "chapters"]))
    lines.append("")

    lines.append("### Rises")
    rows = []
    for r in flow_view.get("rises", []):
        rows.append({
            "metric": r.get("metric", ""),
            "from": r.get("from", ""),
            "to": r.get("to", ""),
            "from_value": r.get("from_value", ""),
            "to_value": r.get("to_value", ""),
        })
    lines.append(md_table(rows, ["metric", "from", "to", "from_value", "to_value"]))
    lines.append("")

    lines.append("### Falls")
    rows = []
    for r in flow_view.get("falls", []):
        rows.append({
            "metric": r.get("metric", ""),
            "from": r.get("from", ""),
            "to": r.get("to", ""),
            "from_value": r.get("from_value", ""),
            "to_value": r.get("to_value", ""),
        })
    lines.append(md_table(rows, ["metric", "from", "to", "from_value", "to_value"]))
    lines.append("")

    lines.append("## Wanted Families")
    rows = []
    for r in results.get("wanted", []):
        rows.append({
            "family": r.get("family", ""),
            "count": r.get("count", ""),
            "lemmas": ", ".join(r.get("lemmas", [])),
            "sources": ", ".join(r.get("sources", [])),
            "refs": ", ".join(r.get("refs", [])[:12]),
        })
    lines.append(md_table(rows, ["family", "count", "lemmas", "sources", "refs"]))
    lines.append("")

    summary = results.get("signal_summary", {})

    lines.append("## Signal Summary")
    lines.append("")

    lines.append("### Strong Boundary Signals")
    rows = []
    for r in summary.get("strong_boundary_signals", []):
        rows.append({
            "ref": r.get("ref", ""),
            "score": r.get("score", ""),
            "signals": "; ".join(
                f"{s.get('signal')}: {s.get('value')}"
                for s in r.get("signals", [])
            ),
        })
    lines.append(md_table(rows, ["ref", "score", "signals"]))
    lines.append("")

    lines.append("### Imperative Clusters")
    rows = []
    for r in summary.get("imperative_clusters", []):
        rows.append({
            "range": r.get("range", ""),
            "count": r.get("count", ""),
            "lemmas": ", ".join(r.get("lemmas", [])),
        })
    lines.append(md_table(rows, ["range", "count", "lemmas"]))
    lines.append("")

    lines.append("### Marker Clusters")
    rows = []
    for r in summary.get("marker_clusters", []):
        rows.append({
            "range": r.get("range", ""),
            "count": r.get("count", ""),
            "lemmas": ", ".join(r.get("lemmas", [])),
        })
    lines.append(md_table(rows, ["range", "count", "lemmas"]))
    lines.append("")

    lines.append("### Repeated Action Lemmas")
    rows = []
    for r in summary.get("repeated_action_lemmas", []):
        rows.append({
            "lemma": r.get("lemma", ""),
            "count": r.get("count", ""),
            "refs": ", ".join(r.get("refs", [])[:12]),
        })
    lines.append(md_table(rows, ["lemma", "count", "refs"]))
    lines.append("")

    lines.append("### Contrast Patterns")
    rows = []
    for r in summary.get("contrast_patterns", []):
        rows.append({
            "pattern": r.get("pattern", ""),
            "count": r.get("count", ""),
        })
    lines.append(md_table(rows, ["pattern", "count"]))
    lines.append("")

    lines.append("## Concentration")
    rows = []
    for r in results.get("concentration", []):
        if r.get("score", 0) < 6:
            continue
        rows.append({
            "ref": r.get("ref", ""),
            "score": r.get("score", ""),
            "signals": ", ".join(r.get("signals", [])),
        })
    lines.append(md_table(rows, ["ref", "score", "signals"]))
    lines.append("")

    lines.append("## Concentration Clusters")
    rows = []
    for r in results.get("concentration_clusters", []):
        rows.append({
            "range": r.get("range", ""),
            "peak": r.get("peak", ""),
            "total_score": r.get("total_score", ""),
            "count": r.get("count", ""),
            "refs": ", ".join(r.get("refs", [])),
        })
    lines.append(md_table(rows, ["range", "peak", "total_score", "count", "refs"]))
    lines.append("")

    lines.append("## Regions")
    rows = []
    for r in results.get("regions", []):
        rows.append({
            "range": r.get("range", ""),
            "total_score": r.get("total_score", ""),
            "peak": r.get("peak", ""),
            "count": r.get("count", ""),
            "refs": ", ".join(r.get("refs", [])),
            "signals": ", ".join(r.get("signals", [])),
        })
    lines.append(md_table(rows, ["range", "total_score", "peak", "count", "refs", "signals"]))
    lines.append("")

    lines.append("## Mood Distribution")
    for group, counts in results["mood_distribution"].items():
        lines.append(f"### {group.title()}")
        lines.append(md_table(
            [{"item": k, "count": v} for k, v in counts.items()],
            ["item", "count"],
        ))

    lines.append("## Imperatives")
    lines.append(md_table(
        results["imperatives"],
        ["ref", "surface", "lemma", "morph", "es"],
        limit=100,
    ))

    lines.append("## Discourse Markers")
    lines.append(md_table(
        results["discourse_markers"],
        ["ref", "surface", "lemma", "category", "es"],
        limit=200,
    ))

    lines.append("## Repeated Lemmas")
    rows = []
    for r in results["repeated_lemmas"][:100]:
        rows.append({
            "lemma": r["lemma"],
            "count": r["count"],
            "refs": ", ".join(r["refs"][:12]),
        })
    lines.append(md_table(rows, ["lemma", "count", "refs"]))

    lines.append("## Contrast Markers / Pairs")
    lines.append(md_table(
        results["contrast_markers"],
        ["pair", "from_ref", "from_surface", "to_ref", "to_surface", "distance_tokens"],
        limit=100,
    ))

    lines.append("## Possible Boundary Signals")
    rows = []
    for r in results["boundary_signals"]:
        if r.get("score", 0) < 2:
            continue
        rows.append({
            "ref": r["ref"],
            "score": r["score"],
            "signals": "; ".join(
                f"{s['signal']}: {s['value']}"
                for s in r["signals"]
            ),
        })
    lines.append(md_table(rows, ["ref", "score", "signals"], limit=150))

    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(
        description="Generate Mega View observable signals from CGV interlinear tokens."
    )
    ap.add_argument("book", help="Book slug, e.g. efesios")
    ap.add_argument("--data-dir", default=str(ROOT.parent / "datasets" / "interlinear" / "NT"))
    ap.add_argument("--out-dir", default=str(ROOT / "output"))
    args = ap.parse_args()

    data_path = Path(args.data_dir) / f"{args.book}.tokens.jsonl"
    out_dir = Path(args.out_dir) / args.book
    ensure_dir(out_dir)

    tokens = load_tokens(data_path)
    markers = load_json(ROOT / "src" / "config" / "discourse_markers.json")
    contrasts = load_json(ROOT / "src" / "config" / "contrast_pairs.json")
    stops = load_json(ROOT / "src" / "config" / "stop_lemmas.json")
    wanted_families = load_json(ROOT / "src" / "config" / "wanted_families.json")

    results = {
        "book": args.book,
        "token_count": len(tokens),
        "mood_distribution": mood_distribution.run(tokens),
        "imperatives": imperatives.run(tokens),
        "discourse_markers": discourse_markers.run(tokens, markers),
        "repeated_lemmas": repeated_lemmas.run(tokens, stops),
        "contrast_markers": contrast_markers.run(tokens, contrasts),
        "boundary_signals": boundary_signals.run(tokens, markers),
    }

    results["signal_summary"] = signal_summary.run(results)
    results["concentration"] = concentration_engine.run(results)
    results["concentration_clusters"] = concentration_clusters.run(
        results["concentration"]
    )
    results["regions"] = region_engine.run(results)
    results["flow"] = flow_engine.run(tokens, results)
    results["flow_interpretation"] = flow_interpreter.run(results)
    results["wanted"] = wanted_engine.run(tokens, results, wanted_families)

    for key, value in results.items():
        if key in {"book", "token_count"}:
            continue
        write_json(out_dir / f"{key}.json", value)

    write_json(out_dir / "mega_view.json", results)
    write_markdown(out_dir / "mega_view.md", args.book, results)

    print(f"Wrote Mega View for {args.book} to {out_dir}")


if __name__ == "__main__":
    main()