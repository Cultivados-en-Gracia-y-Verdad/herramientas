from collections import Counter, defaultdict


def ref_key(ref):
    ch, vs = ref.split(":")
    return int(ch), int(vs)


def make_range(refs):
    refs = sorted(set(refs), key=ref_key)
    if not refs:
        return ""
    if len(refs) == 1:
        return refs[0]
    return f"{refs[0]}–{refs[-1]}"


def cluster_by_verse(items, min_count=2, max_gap=1):
    by_ref = defaultdict(list)

    for item in items:
        ref = item.get("ref")
        if ref:
            by_ref[ref].append(item)

    refs = sorted(by_ref.keys(), key=ref_key)
    clusters = []
    current = []

    last_ch, last_vs = None, None

    for ref in refs:
        ch, vs = ref_key(ref)

        if not current:
            current = [ref]
        elif ch == last_ch and vs <= last_vs + max_gap:
            current.append(ref)
        else:
            clusters.append(current)
            current = [ref]

        last_ch, last_vs = ch, vs

    if current:
        clusters.append(current)

    results = []
    for cluster in clusters:
        cluster_items = []
        for ref in cluster:
            cluster_items.extend(by_ref[ref])

        if len(cluster_items) >= min_count:
            results.append({
                "range": make_range(cluster),
                "count": len(cluster_items),
                "refs": cluster,
                "lemmas": sorted(set(i.get("lemma", "") for i in cluster_items if i.get("lemma")))
            })

    return results


def action_lemmas(repeated_lemmas, min_count=4):
    """
    This does not know morphology.
    It simply surfaces repeated lemmas that are likely action/movement terms
    by excluding common non-action terms later through config if needed.
    """
    preferred = {
        "περιπατέω",
        "γίνομαι",
        "ἀγαπάω",
        "πληρόω",
        "ποιέω",
        "δίδωμι",
        "γνωρίζω",
        "λέγω",
        "οἰκοδομή",
        "κτίζω",
        "ἔχω",
    }

    rows = []
    for r in repeated_lemmas:
        lemma = r.get("lemma")
        count = r.get("count", 0)

        if lemma in preferred and count >= min_count:
            rows.append({
                "lemma": lemma,
                "count": count,
                "refs": r.get("refs", [])
            })

    return sorted(rows, key=lambda r: (-r["count"], r["lemma"]))


def contrast_patterns(contrast_markers):
    counts = Counter()

    for item in contrast_markers:
        pair = item.get("pair")

        if not pair:
            continue

        if isinstance(pair, list):
            pair_key = " ... ".join(pair)
        else:
            pair_key = str(pair)

        counts[pair_key] += 1

    return [
        {"pattern": pair, "count": count}
        for pair, count in counts.most_common()
    ]


def strong_boundaries(boundary_signals, min_score=3):
    rows = []

    for r in boundary_signals:
        if r.get("score", 0) >= min_score:
            rows.append({
                "ref": r.get("ref"),
                "score": r.get("score"),
                "signals": r.get("signals", [])
            })

    return sorted(rows, key=lambda r: (-r["score"], ref_key(r["ref"])))


def marker_clusters(discourse_markers, min_count=3):
    strong = {
        "οὖν",
        "διό",
        "γάρ",
        "ἀλλά",
        "ἵνα",
        "ὅτι",
        "εἰ",
        "ἄρα",
        "πλήν",
    }

    filtered = [
        m for m in discourse_markers
        if m.get("lemma") in strong
    ]

    return cluster_by_verse(filtered, min_count=min_count, max_gap=1)


def run(results):
    """
    Build a concentrated Mega View summary from existing engine outputs.
    This does not replace the full data tables.
    """

    imperatives = results.get("imperatives", [])
    discourse_markers = results.get("discourse_markers", [])
    repeated_lemmas = results.get("repeated_lemmas", [])
    contrast_markers = results.get("contrast_markers", [])
    boundary_signals = results.get("boundary_signals", [])

    return {
        "strong_boundary_signals": strong_boundaries(boundary_signals, min_score=3),
        "imperative_clusters": cluster_by_verse(imperatives, min_count=3, max_gap=1),
        "marker_clusters": marker_clusters(discourse_markers, min_count=3),
        "repeated_action_lemmas": action_lemmas(repeated_lemmas, min_count=4),
        "contrast_patterns": contrast_patterns(contrast_markers),
    }