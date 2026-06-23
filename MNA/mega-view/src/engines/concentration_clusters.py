def ref_key(ref):
    ch, vs = ref.split(":")
    return int(ch), int(vs)


def make_range(refs):
    refs = sorted(refs, key=ref_key)

    if len(refs) == 1:
        return refs[0]

    return f"{refs[0]}–{refs[-1]}"


def run(concentration, min_score=6, max_gap=1):
    hotspots = [
        r for r in concentration
        if r["score"] >= min_score
    ]

    hotspots = sorted(hotspots, key=lambda r: ref_key(r["ref"]))

    clusters = []
    current = []

    last_ch = None
    last_vs = None

    for r in hotspots:
        ch, vs = ref_key(r["ref"])

        if not current:
            current = [r]

        elif ch == last_ch and vs <= last_vs + max_gap:
            current.append(r)

        else:
            clusters.append(current)
            current = [r]

        last_ch = ch
        last_vs = vs

    if current:
        clusters.append(current)

    rows = []

    for cluster in clusters:

        refs = [x["ref"] for x in cluster]

        rows.append({
            "range": make_range(refs),
            "peak": max(x["score"] for x in cluster),
            "total_score": sum(x["score"] for x in cluster),
            "count": len(cluster),
            "refs": refs
        })

    rows.sort(
        key=lambda r: (-r["total_score"], -r["peak"])
    )

    return rows