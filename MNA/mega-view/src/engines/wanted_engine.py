from collections import defaultdict


PURPOSE_MARKERS = {"ἵνα", "εἰς", "πρός"}


def add_family(families, family, ref, source, lemma):
    families[family]["count"] += 1
    families[family]["refs"].add(ref)
    families[family]["sources"].add(source)
    families[family]["lemmas"].add(lemma)


def run(tokens, results, family_map):

    reverse = {}

    for family, lemmas in family_map.items():
        for lemma in lemmas:
            reverse[lemma] = family

    families = defaultdict(
        lambda: {
            "count": 0,
            "refs": set(),
            "sources": set(),
            "lemmas": set()
        }
    )

    # Imperatives
    for row in results["imperatives"]:
        lemma = row["lemma"]

        if lemma in reverse:
            add_family(
                families,
                reverse[lemma],
                row["ref"],
                "imperative",
                lemma
            )

    # Repeated lemmas
    for row in results["repeated_lemmas"]:

        lemma = row["lemma"]

        if lemma not in reverse:
            continue

        family = reverse[lemma]

        for ref in row["refs"]:
            add_family(
                families,
                family,
                ref,
                "repeated",
                lemma
            )

    rows = []

    for family, data in families.items():

        rows.append({
            "family": family,
            "count": data["count"],
            "lemmas": sorted(data["lemmas"]),
            "sources": sorted(data["sources"]),
            "refs": sorted(data["refs"])
        })

    rows.sort(
        key=lambda x: (-x["count"], x["family"])
    )

    return rows