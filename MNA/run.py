import sys
import re

from core.aligner_v2 import align_tokens
from core.loader import load_sblgnt, load_nbla
from core.morph_loader import load_morphgnt
from core.ref_converter import convert_ref
from core.aligner import build_verse, apply_alignment, print_alignment

# ----------------------------
# INPUT
# ----------------------------
if len(sys.argv) < 2:
    print("Usage: python3 run.py <book>")
    sys.exit(1)

book = sys.argv[1]

# ----------------------------
# LOAD DATA
# ----------------------------
sbl = load_sblgnt(f"data/SBLGNT/{book}.md")
nbla = load_nbla(f"data/NBLA/{book}.nbla.md")
morph = load_morphgnt(f"data/MorphGNT/{book}-morphgnt.txt")

# ----------------------------
# TARGET
# ----------------------------
target_ref = "1corintios 1:5"

if target_ref not in nbla:
    print(f"\n❌ NBLA KEY NOT FOUND: {target_ref}")
    sys.exit(1)

# ----------------------------
# HELPERS
# ----------------------------
def normalize(token):
    return re.sub(r"[·.,;⸀⸂⸃]", "", token)

def tokenize_nbla(text):
    return [normalize(w).lower() for w in text.split() if w.strip()]

def find_anchor(greek_word, nbla_tokens, start_index):
    g = normalize(greek_word).lower()

    for i in range(start_index, len(nbla_tokens)):
        n = nbla_tokens[i]

        if g == "ὅτι" and n.startswith("porque"):
            return i
        if g == "ἐν" and n == "en":
            return i
        if g == "καὶ" and n == "y":
            return i
        if g == "λόγῳ" and n.startswith("palabra"):
            return i
        if g == "γνώσει" and n.startswith("conocimiento"):
            return i
        if g.startswith("αὐτ") and n in ["él", "el"]:
            return i

    return None

def surface_from_span(token, start, end, tokens):
    span = tokens[start:end+1]

    g = token.greek

    # --- VERB RULE (form-based, robust) ---
    # Detect common Greek verb endings (aorist/passive/plural etc.)
    if g.endswith("θητε") or g.endswith("ται") or g.endswith("εν") or g.endswith("σαι"):
        if span:
            return span[-1]

    # --- DEFAULT RULE ---
    skip = {"en", "y", "porque", "pero", "de", "del", "la", "el"}

    for w in span:
        if w not in skip:
            return w

    return span[0] if span else ""

# ----------------------------
# BUILD
# ----------------------------
full_tokens = sbl[target_ref]
N = 12
greek_words = full_tokens[:N]

print("\nTARGET REF:", target_ref)

verse = build_verse(target_ref, greek_words)

# ----------------------------
# MORPH
# ----------------------------
morph_tokens = morph[convert_ref(target_ref)][:N]

for token, (g, m) in zip(verse.tokens, morph_tokens):
    if normalize(token.greek) != normalize(g):
        raise ValueError(f"Morph mismatch: {token.greek} != {g}")
    token.morph = m

# ----------------------------
# NBLA TOKENS
# ----------------------------
nbla_tokens = tokenize_nbla(nbla[target_ref])

# ----------------------------
# ANCHORS
# ----------------------------
anchors = []
search_index = 0

for i, t in enumerate(verse.tokens):
    idx = find_anchor(t.greek, nbla_tokens, search_index)
    if idx is not None:
        anchors.append((i, idx))
        search_index = idx + 1

# ----------------------------
# SPANS
# ----------------------------

spans = {}

for i, (g_i, n_i) in enumerate(anchors):

    start_n = n_i

    if i + 1 < len(anchors):
        next_n = anchors[i + 1][1]
        end_n = next_n - 1
    else:
        end_n = len(nbla_tokens) - 1

    # safety
    if end_n < start_n:
        end_n = start_n

    # determine Greek range
    if i + 1 < len(anchors):
        next_g = anchors[i + 1][0]
    else:
        next_g = len(greek_words)

    # assign span to ALL Greek tokens in this range
    for g_index in range(g_i, next_g):
        spans[g_index] = (start_n, end_n)
# ----------------------------
# PRINT SPANS
# ----------------------------
print("\nSPAN DIAGNOSTIC:")

for i, t in enumerate(verse.tokens):
    if i in spans:
        s, e = spans[i]
        print(f"{t.greek} → {' '.join(nbla_tokens[s:e+1])}")
    else:
        print(f"{t.greek} → (no span)")

# ----------------------------
# SURFACE SUGGESTIONS
# ----------------------------
print("\nSURFACE SUGGESTIONS:")

used_spans = set()

for i, t in enumerate(verse.tokens):

    if i in spans:
        s, e = spans[i]
        span_key = (s, e)

        # --- PRIORITY: VERB ALWAYS WINS ---
        g = t.greek
        is_verb = (
            g.endswith("θητε")
            or g.endswith("ται")
            or g.endswith("εν")
            or g.endswith("σαι")
        )

        if is_verb:
            print(f"{t.greek} → {surface_from_span(t, s, e, nbla_tokens)}")

        elif span_key in used_spans:
            print(f"{t.greek} → (shared)")

        else:
            used_spans.add(span_key)
            print(f"{t.greek} → {surface_from_span(t, s, e, nbla_tokens)}")

    else:
        print(f"{t.greek} → (no span)")

# ----------------------------
# ALIGNMENT V2.1 (SPAN-AWARE)
# ----------------------------

alignment = align_tokens(greek_words, morph_tokens, nbla_tokens, spans)

print("\nALIGNMENT V2.1:\n")

for g, s, label, span in alignment:
    if span:
        start, end = span
        span_text = " ".join(nbla_tokens[start:end+1])
    else:
        span_text = "[none]"

    print(f"{g} → {s} [{label}] | span: {span_text}")