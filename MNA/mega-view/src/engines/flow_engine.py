from collections import defaultdict, Counter


ACTION_LEMMAS = {
    "περιπατέω",
    "γίνομαι",
    "ἀγαπάω",
    "πληρόω",
    "ποιέω",
    "δίδωμι",
    "γνωρίζω",
    "λέγω",
    "κτίζω",
    "οἰκοδομή",
    "ἔχω",
}


def chapter_of_ref(ref):
    return int(ref.split(":")[0])


def count_by_chapter(rows, ref_key="ref"):
    counts = defaultdict(int)

    for row in rows:
        ref = row.get(ref_key)
        if ref:
            counts[chapter_of_ref(ref)] += 1

    return counts


def verb_mood(morph):
    # Morph format examples:
    # V-3PAI-S-- = indicative, mood at index 5
    # V-2PAD-P-- = imperative, mood at index 5
    # V--AAPNSM- = participle, mood at index 5
    if morph.startswith("V-") and len(morph) > 5:
        return morph[5]
    return None


def run(tokens, results):
    chapters = sorted(set(t["ch"] for t in tokens))

    imperatives = count_by_chapter(results.get("imperatives", []))
    markers = count_by_chapter(results.get("discourse_markers", []))
    boundaries = count_by_chapter(results.get("boundary_signals", []))
    contrasts = count_by_chapter(results.get("contrast_markers", []), ref_key="from_ref")

    action_counts = defaultdict(int)
    mood_counts = defaultdict(Counter)

    for token in tokens:
        ch = token["ch"]
        lemma = token.get("lemma", "")
        morph = token.get("morph", "")

        if lemma in ACTION_LEMMAS:
            action_counts[ch] += 1

        mood = verb_mood(morph)
        if mood:
            mood_counts[ch][mood] += 1

    rows = []

    for ch in chapters:
        rows.append({
            "chapter": ch,
            "imperatives": imperatives.get(ch, 0),
            "markers": markers.get(ch, 0),
            "contrasts": contrasts.get(ch, 0),
            "boundaries": boundaries.get(ch, 0),
            "action_lemmas": action_counts.get(ch, 0),
            "indicatives": mood_counts[ch].get("I", 0),
            "participles": mood_counts[ch].get("P", 0),
            "subjunctives": mood_counts[ch].get("S", 0),
            "infinitives": mood_counts[ch].get("N", 0),
        })

    return rows