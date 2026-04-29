import sys

from core.loader import load_sblgnt, load_nbla
from core.morph_loader import load_morphgnt
from core.ref_converter import convert_ref
from core.aligner import (
    build_verse,
    apply_alignment,
    print_alignment,
    suggest_alignment,
)

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
sbl_path = f"data/SBLGNT/{book}.md"
nbla_path = f"data/NBLA/{book}.nbla.md"
morph_path = f"data/MorphGNT/{book}-morphgnt.txt"

sbl = load_sblgnt(sbl_path)
nbla = load_nbla(nbla_path)
morph = load_morphgnt(morph_path)

# ----------------------------
# TARGET VERSE
# ----------------------------
target_ref = "1corintios 1:5"

# ----------------------------
# GET TOKENS
# ----------------------------
full_tokens = sbl[target_ref]

print("\nTARGET REF:", target_ref)

print("\nALL TOKENS:")
for t in full_tokens:
    print(t)

# ----------------------------
# LIMIT TOKENS
# ----------------------------
N = 12
greek_words = full_tokens[:N]

print("\nUSING FIRST", N, "TOKENS:")
for t in greek_words:
    print(t)

# ----------------------------
# BUILD VERSE
# ----------------------------
verse = build_verse(target_ref, greek_words)

# ----------------------------
# CONVERT REF → MORPH KEY
# ----------------------------
morph_ref = convert_ref(target_ref)
morph_tokens = morph[morph_ref][:N]

# ----------------------------
# NORMALIZATION
# ----------------------------
def normalize(g):
    g = g.replace("⸀", "").replace("⸂", "").replace("⸃", "")
    g = g.replace(",", "").replace(".", "").replace("·", "").replace(";", "")
    return g

# ----------------------------
# ATTACH MORPHOLOGY
# ----------------------------
for token, (g, m) in zip(verse.tokens, morph_tokens):
    g_clean = normalize(g)

    if token.greek != g_clean:
        raise ValueError(f"Morph mismatch: {token.greek} != {g_clean}")

    token.morph = m

# ----------------------------
# NBLA TOKENIZATION
# ----------------------------
def tokenize_nbla(text):
    return text.replace(",", "").replace(".", "").split()

nbla_tokens = tokenize_nbla(nbla[target_ref])
print("\nNBLA KEYS SAMPLE:")
for k in list(nbla.keys())[:10]:
    print(k)
# ----------------------------
# SUGGESTIONS (UPGRADED)
# ----------------------------
print("\nSUGGESTIONS:")
for i, t in enumerate(verse.tokens):
    morph_suggestion = suggest_alignment(t)

    nbla_guess = nbla_tokens[i] if i < len(nbla_tokens) else ""

    print(f"{t.greek} → morph: {morph_suggestion} | nbla: {nbla_guess}")

# ----------------------------
# ALIGNMENT (MUST MATCH N)
# ----------------------------
alignment = [
    ("ὅτι", "porque", "expanded"),
    ("ἐν", "en", "direct"),
    ("παντὶ", "todo", "expanded"),
    ("ἐπλουτίσθητε", "fueron enriquecidos", "expanded"),
    ("ἐν", "en", "direct"),
    ("αὐτῷ", "Él", "expanded"),
    ("ἐν", "en", "direct"),
    ("παντὶ", "todo", "expanded"),
    ("λόγῳ", "palabra", "direct"),
    ("καὶ", "y", "direct"),
    ("πάσῃ", "toda", "expanded"),
    ("γνώσει", "conocimiento", "direct"),
]

# ----------------------------
# VALIDATION
# ----------------------------
if len(greek_words) != len(alignment):
    print("\n❌ LENGTH MISMATCH")
    print("TOKENS:", len(greek_words))
    print("ALIGNMENT:", len(alignment))
    sys.exit(1)

# ----------------------------
# APPLY + PRINT
# ----------------------------
apply_alignment(verse, alignment)
print_alignment(verse)