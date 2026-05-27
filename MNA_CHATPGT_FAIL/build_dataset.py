import os
import re
import unicodedata
from collections import Counter
from core.loader import load_sblgnt, load_nbla
from core.morph_loader import load_morphgnt
from core.ref_converter import convert_ref
from core.aligner_v2 import align_tokens

BOOK = "filipenses"

SBL_PATH = f"data/SBLGNT/{BOOK}.md"
NBLA_PATH = f"data/NBLA/{BOOK}.nbla.md"
MORPH_PATH = f"data/MorphGNT/{BOOK}-morphgnt.txt"
OUT_DIR = "data/ROOTS"
OUT_PATH = f"{OUT_DIR}/{BOOK}-dataset.md"

os.makedirs(OUT_DIR, exist_ok=True)

sbl = load_sblgnt(SBL_PATH)
nbla = load_nbla(NBLA_PATH)
morph = load_morphgnt(MORPH_PATH)


def normalize(token):
    token = re.sub(r"[·.,;:!?¿¡⸀⸂⸃()\[\]«»“”\"']", "", token).lower()
    token = unicodedata.normalize("NFD", token)
    token = "".join(ch for ch in token if unicodedata.category(ch) != "Mn")
    return token.strip()

def normalize_greek(token):
    token = re.sub(r"[·.,;:!?¿¡⸀⸂⸃()\[\]«»“”\"']", "", token).lower()
    token = unicodedata.normalize("NFD", token)
    token = "".join(ch for ch in token if unicodedata.category(ch) != "Mn")
    return token


def tokenize_nbla(text):
    tokens = []

    for raw in text.split():
        cleaned = normalize(raw)

        if cleaned:
            tokens.append(cleaned)

        # Only closing punctuation ends a clause span
        if any(p in raw for p in ["?", "!"]):
            tokens.append("<PUNCT>")

    return tokens


CONNECTOR_MAP = {
    "γαρ": ("γάρ", "porque"),
    "ινα": ("ἵνα", "que"),
    "και": ("καὶ", "y"),
    "δε": ("δὲ", "pero/sino"),
    "αλλα": ("ἀλλά", "pero"),
    "οτι": ("ὅτι", "que"),
    "ωστε": ("ὥστε", "de manera que"),
    "ει": ("εἰ", "si"),
}

COORDINATING = {"και", "δε", "αλλα"}
CLAUSE_STARTERS = {"ινα", "και", "αλλα", "οτι", "ωστε", "ει"}

VERB_EQUIVALENTS = {
    "βαπτιζω": "bautizar",
    "λεγω": "decir",
    "ειμι": "ser/estar",
    "σταυροω": "crucificar",
    "γραφω": "escribir",
    "εχω": "tener",
    "γινωσκω": "conocer",
    "οραω": "ver",
    "ποιεω": "hacer",
    "λαμβανω": "recibir",
    "διδωμι": "dar",
    "ερχομαι": "venir",
    "ακουω": "oír",
    "πιστευω": "creer",
    "αγαπαω": "amar",
    "καλεω": "llamar",
    "σωζω": "salvar",
    "γινομαι": "llegar a ser",
    "θελω": "querer",
    "δυναμαι": "poder",
    "αποκρινομαι": "responder",
    "κρινω": "juzgar",
    "μενω": "permanecer",
    "ακολουθεω": "seguir",
    "κηρυσσω": "predicar",
    "ευαγγελιζω": "anunciar buenas nuevas",
    "λαλεω": "hablar",
    "εσθιω": "comer",
    "οιδα": "saber",
    "εγειρω": "resucitar/levantar",
    "πινω": "beber",
    "προφητευω": "profetizar",
    "ανακρινω": "juzgar/discernir",
    "καταργεω": "anular/destruir",
    "δοκεω": "parecer/creer",
    "γαμεω": "casarse",
    "υποτασσω": "someter",
    "ζητεω": "buscar",
    "σπειρω": "sembrar",
    "προσευχομαι": "orar",
    "βλεπω": "ver/cuidarse",
    "τιθημι": "poner",
    "παραδιδωμι": "entregar",
    "αμαρτανω": "pecar",
    "αποθνησκω": "morir",
    "συνερχομαι": "reunirse",
    "ευχαριστεω": "dar gracias",
    "παρακαλεω": "rogar/exhortar",
    "απολλυμι": "perder/destruir",
    "φυσιοω": "envanecerse",
    "κοιμαομαι": "dormir",
    "οικοδομεω": "edificar",
    "καταισχυνω": "avergonzar",
    "καυχαομαι": "gloriarse",
    "ποτιζω": "dar de beber",
    "διακρινω": "discernir/distinguir",
    "οφειλω": "deber",
    "φημι": "decir",
    "υπαρχω": "ser/existir",
    "μεριμναω": "preocuparse",
    "μετεχω": "participar",
    "κερδαινω": "ganar",
    "αγιαζω": "santificar",
    "φυτευω": "plantar",
    "εποικοδομεω": "edificar encima",
    "εργαζομαι": "trabajar",
    "κληρονομεω": "heredar",
    "εξεστιν": "ser lícito",
    "χωριζω": "separar",
    "διατασσω": "ordenar",
    "χραομαι": "usar",
    "χαιρω": "regocijarse",
    "αρεσκω": "agradar",
    "τρεχω": "correr",
    "αγνοεω": "ignorar",
    "πιπτω": "caer",
    "πορευομαι": "ir",
    "επαινεω": "alabar",
    "διερμηνευω": "interpretar",
    "ζηλοω": "celar/anhelar",
    "επιγινωσκω": "reconocer",
    "ασπαζομαι": "saludar",
    "υστερεω": "carecer",
    "μεριζω": "dividir",
    "εκλεγομαι": "escoger",
    "εξουθενεω": "menospreciar",
    "καταγγελλω": "proclamar",
    "αποκαλυπτω": "revelar",
    "δοκιμαζω": "probar",
    "οικεω": "habitar",
    "φθειρω": "corromper",
    "λογιζομαι": "considerar",
    "μανθανω": "aprender",
    "βασιλευω": "reinar",
    "πειναω": "tener hambre",
    "κοπιαω": "trabajar",
    "ευλογεω": "bendecir",
    "διωκω": "perseguir",
    "θυω": "sacrificar",
    "αποστερεω": "privar",
    "συμφερω": "convenir",
    "εξουσιαζω": "ejercer autoridad",
    "πορνευω": "fornicar",
    "αγοραζω": "comprar",
    "πειραζω": "probar/tentar",
    "αφιημι": "perdonar/dejar",
    "κατεχω": "retener",
    "ιστημι": "estar/poner",
    "ζαω": "vivir",
    "περισσευω": "abundar",
    "διερχομαι": "pasar",
    "παραλαμβανω": "recibir",
    "ελπιζω": "esperar",
    "σιγαω": "callar",
    "ζωοποιεω": "dar vida",
    "δηλοω": "manifestar",
    "κενοω": "vaciar",
    "ευδοκεω": "agradarse",
    "περιπατεω": "andar",
    "αυξανω": "crecer",
    "ευρισκω": "hallar",
    "πεμπω": "enviar",
    "διδασκω": "enseñar",
    "δοξαζω": "glorificar",
    "φευγω": "huir",
    "πλαναω": "desviar/engañar",
    "αδικεω": "hacer injusticia",
    "νομιζω": "pensar",
    "δεω": "deber/ser necesario",
    "κλαιω": "llorar",
    "ασθενεω": "ser débil",
    "σκανδαλιζω": "hacer tropezar",
    "στεγω": "soportar",
    "γνωριζω": "dar a conocer",
    "ωφελεω": "aprovechar",
    "ψαλλω": "cantar",
    "επιτρεπω": "permitir",
    "αλλασσω": "cambiar",
    "ενδυω": "vestir",
    "δηλοω": "manifestar/informar",
    "υπερυψοω": "exaltar",
    "χαριζομαι": "conceder/dar",
    "καμπτω": "doblar",
    "εξομολογεω": "confesar",
    "εγγιζω": "acercar",
    "υπερυψοω": "exaltar",
    "χαριζομαι": "conceder",
    "καμπτω": "doblar",
    "εξομολογεω": "confesar",
    "επιτελεω": "perfeccionar",
    "επιποθεω": "añorar",
    "φρονεω": "sentir/pensar",
    "πληροω": "llenar",
    "προκοπτω": "redundar/progresar",
    "τολμαω": "atreverse",
    "ηγουμαι": "estimar/considerar",
    "αποβαινω": "resultar",
    "μεγαλυνω": "magnificar",
    "αξιοω": "considerar digno",
    "αγωνιζομαι": "luchar",
    "πασχω": "padecer",
    "παρακαλεω": "consolar/exhortar",
    "πληροφορεω": "cumplir/convencer",
    "σπενδω": "derramar",
    "χαιρω": "gozar",
    "συγχαιρω": "gozarse juntamente",
    "πεμπω": "enviar",
    "ισοψυχεω": "tener igual ánimo",
    "μεριμναω": "interesarse/preocuparse",
    "γνησιως": "genuinamente",
    "δοκιμαζω": "probar/aprobar",
    "αναγκαιος": "necesario",
    "αδημονεω": "angustiarse",
    "ελεεω": "tener misericordia",
    "παραπλησιον": "cerca",
    "ατιμαζω": "deshonrar",
    "προσδεχομαι": "recibir",
    "σπουδαιως": "diligentemente",
    "βλεπω": "cuidar/mirar",
    "κατανταω": "llegar",
    "διωκω": "proseguir/perseguir",
    "επεκτεινομαι": "extenderse",
    "σκοπεω": "poner la mira/observar",
    "μετασχηματιζω": "transformar",
    "στηκω": "estar firmes",
    "συλλαμβανω": "ayudar",
    "συναιρω": "combatir juntos",
    "χαιρω": "regocijarse",
    "επιεικες": "amabilidad",
    "γνωριζω": "dar a conocer",
    "υπερεχω": "sobrepasar",
    "φρουρεω": "guardar",
    "μανθανω": "aprender",
    "μεμυημαι": "aprender el secreto",
    "ισχυω": "poder",
    "κοινωνεω": "participar",
    "απεχω": "tener/recibir",
    "περισσευω": "abundar",
    "πληροω": "suplir/llenar",
}


def morph_code(item):
    if isinstance(item, tuple) and len(item) >= 2:
        return item[1]
    return item or ""


def morph_greek(item):
    return item[0] if isinstance(item, tuple) and len(item) >= 1 else ""


def morph_lemma(item):
    return item[2] if isinstance(item, tuple) and len(item) >= 3 else ""


def analysis_words_from_morph(morph_tokens):
    return [morph_greek(token) for token in morph_tokens]


def to_rmac(code):
    code = code.strip()

    if not code.startswith("V"):
        return code

    code = code.replace("--", "-").strip("-")
    parts = [p for p in code.split("-") if p]

    if len(parts) == 2 and parts[0] == "V":
        body = parts[1]
        if len(body) == 6:
            return f"V-{body[:3]}-{body[3:]}"
        if len(body) == 3:
            return f"V-{body}"
        return code

    if len(parts) == 3 and parts[0] == "V":
        middle = parts[1]
        last = parts[2]
        if len(middle) == 4 and middle[0].isdigit():
            return f"V-{middle[1:]}-{middle[0]}{last}"
        return f"V-{middle}-{last}"

    return code


def is_verb(code):
    return code.startswith("V")


def is_finite(code):
    if not code or not code.startswith("V"):
        return False

    rmac = to_rmac(code)
    parts = [p for p in rmac.split("-") if p]
    if len(parts) < 2:
        return False

    tvm = parts[1]
    return len(tvm) == 3 and tvm[2] in {"I", "S", "M", "O"}


def finite_indexes(morph_tokens):
    return [
        i for i, token in enumerate(morph_tokens)
        if is_finite(morph_code(token))
    ]


def greek_clause_bounds(greek_words, finite, idx):
    verb_index = finite[idx]

    if idx == 0:
        start = 0
    else:
        prev_finite = finite[idx - 1]
        start = verb_index
        for j in range(prev_finite + 1, verb_index):
            if normalize_greek(greek_words[j]) in CLAUSE_STARTERS:
                start = j
                break

    if idx + 1 < len(finite):
        next_finite = finite[idx + 1]
        end = next_finite - 1
        for j in range(verb_index + 1, next_finite):
            if normalize_greek(greek_words[j]) in CLAUSE_STARTERS:
                end = j - 1
                break
    else:
        end = len(greek_words) - 1

    return start, end


def spans_in_range(alignment, start, end):
    spans = []
    trusted_verb_labels = {
        "verb-direct",
        "verb-expanded",
        "periphrastic-finite",
        "periphrastic-participle",
    }

    for i in range(start, end + 1):
        if i < len(alignment):
            label = alignment[i][2]
            span = alignment[i][3]
            if span and label in trusted_verb_labels:
                spans.append(span)

    return spans


def first_span_start(alignment, start, end):
    spans = spans_in_range(alignment, start, end)
    if not spans:
        return None
    return min(s[0] for s in spans)


def connector_spans_in_range(alignment, start, end):
    spans = []
    for i in range(start, end + 1):
        if i < len(alignment):
            label = alignment[i][2]
            span = alignment[i][3]
            if span and label == "function":
                spans.append(span)
    return spans


def first_connector_start(alignment, start, end):
    spans = connector_spans_in_range(alignment, start, end)
    if not spans:
        return None
    return min(s[0] for s in spans)


def clause_span(alignment, bounds, idx, nbla_tokens):
    g_start, g_end = bounds[idx]
    start = first_span_start(alignment, g_start, g_end)

    if start is None:
        return None

    current_spans = spans_in_range(alignment, g_start, g_end)

    if idx + 1 < len(bounds):
        next_g_start, next_g_end = bounds[idx + 1]

        next_verb_start = first_span_start(alignment, next_g_start, next_g_end)
        next_connector_start = first_connector_start(alignment, next_g_start, next_g_end)

        candidates = [
            x for x in [next_verb_start, next_connector_start]
            if x is not None and x > start
        ]

        if candidates:
            end = min(candidates) - 1
        elif current_spans:
            end = max(s[1] for s in current_spans)
        else:
            end = start
    else:
        end = len(nbla_tokens) - 1

    # Hard stop at punctuation marker BEFORE the next clause material.
    for j in range(start, end + 1):
        if nbla_tokens[j] == "<PUNCT>":
            end = j - 1
            break

    if end < start:
        end = start

    return start, end


def fallback_verb_surface(token):
    surface = normalize_greek(morph_greek(token))
    lemma = normalize_greek(morph_lemma(token)) or surface
    return VERB_EQUIVALENTS.get(lemma) or VERB_EQUIVALENTS.get(surface)


def highlight_surface(tokens, surface_text):
    if not surface_text or surface_text == "[missing]":
        return " ".join(tokens)

    surface_tokens = surface_text.split()
    n = len(surface_tokens)

    for i in range(0, len(tokens) - n + 1):
        if tokens[i:i + n] == surface_tokens:
            tokens[i:i + n] = [f"=={' '.join(surface_tokens)}=="]
            break

    return " ".join(tokens)


def mark_span(tokens, surface_text, left, right):
    if not surface_text or surface_text == "[missing]":
        return tokens

    surface_tokens = surface_text.split()
    n = len(surface_tokens)

    for i in range(0, len(tokens) - n + 1):
        if tokens[i:i + n] == surface_tokens:
            tokens[i:i + n] = [f"{left}{' '.join(surface_tokens)}{right}"]
            break

    return tokens


def mark_greek_connectors(text):
    words = text.split()
    marked = []

    for w in words:
        key = normalize_greek(w)
        if key in CONNECTOR_MAP:
            marked.append(f"({w})")
        else:
            marked.append(w)

    return " ".join(marked)


def connector_surface(alignment, greek_index):
    if greek_index >= len(alignment):
        return None, False

    surface = alignment[greek_index][1]
    label = alignment[greek_index][2]
    span = alignment[greek_index][3]

    if span and surface != "[missing]" and label == "function":
        return surface, True

    key = normalize_greek(alignment[greek_index][0])
    if key in CONNECTOR_MAP:
        return CONNECTOR_MAP[key][1], False

    return None, False



def connector_markers_for_clause(greek_words, alignment, g_start, g_end):
    markers = []

    for i in range(g_start, g_end + 1):
        key = normalize_greek(greek_words[i])
        if key not in CONNECTOR_MAP:
            continue

        surface, present = connector_surface(alignment, i)
        if not surface:
            continue

        marker = f"({surface})" if present else f"[{surface}]"
        if marker not in markers:
            markers.append(marker)

    return markers


def finite_fallback_surface(morph_tokens, verb_index):
    fallback = fallback_verb_surface(morph_tokens[verb_index])
    if fallback:
        return fallback

    lemma = normalize_greek(morph_lemma(morph_tokens[verb_index]))
    if lemma:
        suggestion = VERB_EQUIVALENTS.get(lemma)
        return suggestion if suggestion else lemma

    return "sin sugerencia"


def roots_unaligned_clause(greek_words, morph_tokens, alignment, g_start, g_end, verb_index):
    markers = connector_markers_for_clause(greek_words, alignment, g_start, g_end)
    suggestion = finite_fallback_surface(morph_tokens, verb_index)

    prefix = " ".join(markers)
    body = f"[sin alineación: {suggestion}]"

    return f"{prefix} {body}".strip()

def build_clauses(greek_words, morph_tokens, alignment, nbla_tokens):
    clauses = []
    finite = finite_indexes(morph_tokens)

    bounds = [
        greek_clause_bounds(greek_words, finite, idx)
        for idx in range(len(finite))
    ]

    for idx, verb_index in enumerate(finite):
        g_start, g_end = bounds[idx]

        greek_clause = " ".join(greek_words[g_start:g_end + 1])
        greek_clause = mark_greek_connectors(greek_clause)

        span = clause_span(alignment, bounds, idx, nbla_tokens)

        if not span:
            nbla_clause = roots_unaligned_clause(
                greek_words,
                morph_tokens,
                alignment,
                g_start,
                g_end,
                verb_index,
            )
        else:
            start, end = span
            clause_tokens = nbla_tokens[start:end + 1]
            clause_tokens = [t for t in clause_tokens if t != "<PUNCT>"]
            for i in range(g_start, g_end + 1):
                key = normalize_greek(greek_words[i])
                if key in CONNECTOR_MAP:
                    surface, present = connector_surface(alignment, i)

                    # If found in NBLA → mark it
                    if present:
                        clause_tokens = mark_span(clause_tokens, surface, "(", ")")

                    # If NOT found → FORCE it at clause start
                    elif surface:
                        clause_tokens.insert(0, f"({surface})")

            verb_surface = alignment[verb_index][1]
            label = alignment[verb_index][2]

            if label not in {
                "verb-direct",
                "verb-expanded",
                "periphrastic-finite",
                "periphrastic-participle",
            } or verb_surface == "[missing]":
                verb_surface = fallback_verb_surface(morph_tokens[verb_index])

            nbla_clause = highlight_surface(clause_tokens, verb_surface)

        clauses.append((greek_clause, nbla_clause))

    return clauses, finite, bounds



def find_connectors(greek_words, clauses_bounds, alignment, previous_anchor=None):
    connectors = []

    for idx, (g_start, g_end) in enumerate(clauses_bounds):
        for i in range(g_start, g_end + 1):
            key = normalize_greek(greek_words[i])

            if key not in CONNECTOR_MAP:
                continue

            gr, default_es = CONNECTOR_MAP[key]
            surface, present = connector_surface(alignment, i)
            es = surface if surface else default_es

            tipo = "coordinante" if key in COORDINATING else "subordinante"

            if idx == 0:
                A = previous_anchor if previous_anchor else "CONTEXTO_ANTERIOR"
                B = "C1"
                scope = "interverso"
            else:
                A = f"C{idx}"
                B = f"C{idx + 1}"
                scope = "intraverso"

            connectors.append({
                "gr": gr,
                "es": es,
                "es_present": present,
                "A": A,
                "B": B,
                "tipo": tipo,
                "estado": "confirmado",
                "scope": scope,
            })

            break

    return connectors



def build_structure(clauses, connectors):
    parent_map = {}

    for c in connectors:
        if c.get("scope") != "intraverso":
            continue

        if c["tipo"] == "subordinante":
            if not (c["A"].startswith("C") and c["B"].startswith("C")):
                continue

            parent = int(c["A"][1:])
            child = int(c["B"][1:])
            parent_map[child] = parent

    structure = []
    for i in range(1, len(clauses) + 1):
        level = 0
        current = i
        while current in parent_map:
            current = parent_map[current]
            level += 1
        structure.append((i, level))

    return structure


def format_book_ref(ref):
    parts = ref.split()
    book = parts[0]
    rest = parts[1]

    m = re.match(r"(\d+)([a-záéíóúñ]+)", book, re.IGNORECASE)
    if m:
        num, name = m.groups()
        return f"{num} {name.capitalize()} {rest}"

    return ref.capitalize()


def connector_display(c):
    es = f"({c['es']})" if c["es_present"] else f"[{c['es']}]"
    return f"({c['gr']}) → {es}"


lines = []
lines.append("> Fuente: SBLGNT (griego) + NBLA (español)\n\n")

missing_lemmas = Counter()
previous_anchor = None

for ref in sorted(sbl.keys(), key=lambda r: tuple(map(int, r.split()[1].split(":")))):
    if ref not in nbla:
        continue

    sbl_words = sbl[ref]
    nbla_text = nbla[ref]
    nbla_tokens = tokenize_nbla(nbla_text)

    morph_ref = convert_ref(ref)
    if morph_ref not in morph:
        continue

    morph_tokens = morph[morph_ref]

    analysis_words = analysis_words_from_morph(morph_tokens)
    alignment = align_tokens(analysis_words, morph_tokens, nbla_tokens)

    clauses, finite, bounds = build_clauses(
        analysis_words,
        morph_tokens,
        alignment,
        nbla_tokens
    )

    connectors = find_connectors(analysis_words, bounds, alignment, previous_anchor)
    structure = build_structure(clauses, connectors)

    lines.append(f"### {format_book_ref(ref)}\n\n")
    lines.append(" ".join(sbl_words) + "\n\n")
    lines.append(f"[{nbla_text}]\n\n")

    lines.append("#### Verbos\n\n")

    has_verbs = False

    for i, token in enumerate(morph_tokens):
        g = morph_greek(token)
        code = morph_code(token)

        if not is_verb(code):
            continue

        tag = "[F]" if is_finite(code) else "[NF]"

        span = alignment[i][3]
        surface = alignment[i][1]
        label = alignment[i][2]
        fallback = fallback_verb_surface(token)

        if (
            span
            and surface != "[missing]"
            and label in {
                "verb-direct",
                "verb-expanded",
                "periphrastic-finite",
                "periphrastic-participle",
            }
        ):
            if tag == "[F]":
                surface = f"=={surface}=="
        else:
            if fallback:
                surface = f"-{fallback}-"
            else:
                lemma = normalize_greek(morph_lemma(token))
                suggestion = VERB_EQUIVALENTS.get(lemma)

                if suggestion:
                    surface = f"[sin equivalente - {suggestion}]"
                elif lemma:
                    surface = f"[sin equivalente - {lemma}]"
                else:
                    surface = "[sin equivalente]"

                missing_lemmas[lemma] += 1

        lines.append(f"- {g} ({to_rmac(code)}) {tag} → {surface}\n")
        has_verbs = True

    if not has_verbs:
        lines.append("- (sin verbos)\n")

    lines.append("\n#### Cláusulas\n\n")

    if clauses:
        for i, (gr, es) in enumerate(clauses):
            lines.append(f"- C{i + 1}\n")
            lines.append(f"  {gr}\n")
            lines.append(f"  {es}\n")
    else:
        lines.append("- (sin cláusulas)\n")

    lines.append("\n#### Conectores\n\n")

    if connectors:
        for c in connectors:
            lines.append(f"- {connector_display(c)}\n")
            lines.append(f"  A: {c['A']}\n")
            lines.append(f"  B: {c['B']}\n")
            lines.append(f"  CONEXIÓN: {c['A']} + {c['gr']} + {c['B']}\n")
            lines.append(f"  TIPO: {c['tipo']}\n")
            lines.append(f"  ESTADO: {c['estado']}\n")
            lines.append(f"  ALCANCE: {c.get('scope', 'intraverso')}\n\n")
    else:
        lines.append("- (sin conectores)\n")

    lines.append("\n#### Estructura\n\n")

    for idx, level in structure:
        indent = "  " * level
        lines.append(f"{indent}- C{idx}\n")

    if clauses:
        previous_anchor = f"{format_book_ref(ref)} C{len(clauses)}"

    lines.append("\n---\n\n")


with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("\n=== TOP MISSING LEMMAS ===\n")
for lemma, count in missing_lemmas.most_common(50):
    print(f"{lemma}: {count}")

print("DONE")