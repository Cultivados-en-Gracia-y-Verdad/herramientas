from collections import defaultdict


def run(results):
    scores = defaultdict(lambda: {
        "score": 0,
        "signals": []
    })

    # Boundary signals
    for r in results.get("boundary_signals", []):
        ref = r["ref"]
        scores[ref]["score"] += r["score"]
        scores[ref]["signals"].append("boundary")

    # Imperatives
    for r in results.get("imperatives", []):
        ref = r["ref"]
        scores[ref]["score"] += 1
        scores[ref]["signals"].append("imperative")

    # Discourse markers
    strong_markers = {
        "οὖν",
        "διό",
        "γάρ",
        "ἀλλά",
        "ἵνα",
        "ὅτι",
        "ἄρα",
        "πλήν"
    }

    for r in results.get("discourse_markers", []):
        if r["lemma"] in strong_markers:
            ref = r["ref"]
            scores[ref]["score"] += 1
            scores[ref]["signals"].append(r["lemma"])

    # Contrast markers
    for r in results.get("contrast_markers", []):
        ref = r["from_ref"]
        scores[ref]["score"] += 2
        scores[ref]["signals"].append("contrast")

    rows = []

    for ref, data in scores.items():
        rows.append({
            "ref": ref,
            "score": data["score"],
            "signals": sorted(set(data["signals"]))
        })

    rows.sort(
        key=lambda r: (
            -r["score"],
            int(r["ref"].split(":")[0]),
            int(r["ref"].split(":")[1])
        )
    )

    return rows