def ref_key(ref):
    ch, vs = ref.split(":")
    return int(ch), int(vs)


def make_range(refs):
    refs = sorted(refs, key=ref_key)

    if len(refs) == 1:
        return refs[0]

    return f"{refs[0]}–{refs[-1]}"


def expand_refs(refs, max_gap=3):
    refs = sorted(set(refs), key=ref_key)

    clusters = []
    current = []

    last_ch = None
    last_vs = None

    for ref in refs:
        ch, vs = ref_key(ref)

        if not current:
            current = [ref]

        elif ch == last_ch and vs <= last_vs + max_gap:
            current.append(ref)

        else:
            clusters.append(current)
            current = [ref]

        last_ch = ch
        last_vs = vs

    if current:
        clusters.append(current)

    return clusters


def collect_refs(results):

    refs = set()

    #
    # Concentration
    #

    for r in results.get("concentration", []):
        if r.get("score", 0) >= 6:
            refs.add(r["ref"])

    #
    # Strong boundaries
    #

    summary = results.get("signal_summary", {})

    for r in summary.get("strong_boundary_signals", []):
        refs.add(r["ref"])

    #
    # Imperative clusters
    #

    for cluster in summary.get("imperative_clusters", []):
        refs.update(cluster.get("refs", []))

    #
    # Marker clusters
    #

    for cluster in summary.get("marker_clusters", []):
        refs.update(cluster.get("refs", []))

    return refs


def run(results, max_gap=3):

    refs = collect_refs(results)

    clusters = expand_refs(refs, max_gap=max_gap)

    by_ref = {
        r["ref"]: r
        for r in results.get("concentration", [])
    }

    regions = []

    for cluster in clusters:

        total_score = 0
        peak = 0

        signals = set()

        for ref in cluster:

            row = by_ref.get(ref)

            if row:

                total_score += row.get("score", 0)
                peak = max(peak, row.get("score", 0))

                for s in row.get("signals", []):
                    signals.add(s)

        regions.append({
            "range": make_range(cluster),
            "count": len(cluster),
            "peak": peak,
            "total_score": total_score,
            "refs": cluster,
            "signals": sorted(signals),
        })

    regions.sort(
        key=lambda r: (-r["total_score"], -r["peak"])
    )

    return regions