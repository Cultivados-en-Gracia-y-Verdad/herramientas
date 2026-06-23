def peak_chapters(flow, key):
    if not flow:
        return []

    peak = max(row.get(key, 0) for row in flow)
    if peak == 0:
        return []

    return [
        row["chapter"]
        for row in flow
        if row.get(key, 0) == peak
    ]


def rises(flow, key):
    rows = []

    for i in range(1, len(flow)):
        prev = flow[i - 1]
        cur = flow[i]

        prev_val = prev.get(key, 0)
        cur_val = cur.get(key, 0)

        if cur_val > prev_val:
            rows.append({
                "from": prev["chapter"],
                "to": cur["chapter"],
                "metric": key,
                "from_value": prev_val,
                "to_value": cur_val,
            })

    return rows


def falls(flow, key):
    rows = []

    for i in range(1, len(flow)):
        prev = flow[i - 1]
        cur = flow[i]

        prev_val = prev.get(key, 0)
        cur_val = cur.get(key, 0)

        if cur_val < prev_val:
            rows.append({
                "from": prev["chapter"],
                "to": cur["chapter"],
                "metric": key,
                "from_value": prev_val,
                "to_value": cur_val,
            })

    return rows


def run(results):
    flow = results.get("flow", [])

    metrics = [
        "imperatives",
        "markers",
        "contrasts",
        "boundaries",
        "action_lemmas",
        "indicatives",
        "participles",
        "subjunctives",
        "infinitives",
    ]

    output = {
        "peaks": [],
        "rises": [],
        "falls": [],
    }

    for metric in metrics:
        peaks = peak_chapters(flow, metric)

        if peaks:
            output["peaks"].append({
                "metric": metric,
                "chapters": peaks,
            })

        output["rises"].extend(rises(flow, metric))
        output["falls"].extend(falls(flow, metric))

    return output