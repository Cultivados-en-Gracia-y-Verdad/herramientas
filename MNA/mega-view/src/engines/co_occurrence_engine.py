from itertools import combinations

MIN_COUNT = 3
WINDOW = 3


def ref_key(ref):
    ch, vs = ref.split(":")
    return int(ch), int(vs)


def chapter(ref):
    return ref_key(ref)[0]


def near_refs(refs_a, refs_b):
    pairs = []

    for a in refs_a:
        ch_a, vs_a = ref_key(a)

        for b in refs_b:
            ch_b, vs_b = ref_key(b)

            if ch_a != ch_b:
                continue

            distance = abs(vs_a - vs_b)

            if distance <= WINDOW:
                pairs.append({
                    "a": a,
                    "b": b,
                    "distance": distance
                })

    return pairs


def run(results, stop_lemmas):
    repeated = results["repeated_lemmas"]

    lemma_refs = {}

    for row in repeated:
        lemma = row["lemma"]

        if lemma in stop_lemmas:
            continue

        refs = row["refs"]

        if len(refs) < MIN_COUNT:
            continue

        lemma_refs[lemma] = refs

    output = []

    for lemma_a, lemma_b in combinations(sorted(lemma_refs), 2):

        refs_a = lemma_refs[lemma_a]
        refs_b = lemma_refs[lemma_b]

        shared_chapters = sorted(
            set(chapter(r) for r in refs_a)
            &
            set(chapter(r) for r in refs_b)
        )

        nearby = near_refs(refs_a, refs_b)

        score = (
            len(shared_chapters) * 2
            +
            len(nearby)
        )

        if score < 4:
            continue

        output.append({
            "lemma_a": lemma_a,
            "lemma_b": lemma_b,
            "score": score,
            "shared_chapters": shared_chapters,
            "near_refs": nearby[:10]
        })

    output.sort(
        key=lambda x: (-x["score"], x["lemma_a"], x["lemma_b"])
    )

    return output