import re
import unicodedata


def normalize(token):
    token = re.sub(r"[·.,;:!?¿¡⸀⸂⸃()\[\]«»“”\"']", "", token).lower()
    token = unicodedata.normalize("NFD", token)
    token = "".join(ch for ch in token if unicodedata.category(ch) != "Mn")
    return token.strip()


def morph_code(morph_item):
    if isinstance(morph_item, tuple):
        if len(morph_item) >= 2:
            return morph_item[1]
        return ""
    return morph_item or ""


def morph_lemma(morph_item):
    if isinstance(morph_item, tuple) and len(morph_item) >= 3:
        return morph_item[2]
    return ""


def is_verb(morph_item):
    return morph_code(morph_item).startswith("V")


FUNCTION_MAP = {
    "γαρ": [["porque"], ["pues"]],
    "οτι": [["que"], ["porque"]],
    "ινα": [["que"], ["para", "que"], ["a", "fin", "de", "que"]],
    "και": [["y"]],
    "αλλα": [["sino"], ["pero"], ["antes", "bien"]],
    "ει": [["si"]],
    "ωστε": [["de", "manera", "que"], ["asi", "que"], ["por", "tanto"]],
    "δε": [["sino", "que"], ["pero"], ["sino"], ["sin", "embargo"], ["ahora", "bien"], ["en", "cambio"]],
}


# Surface-form overrides for forms that NBLA regularly renders with a fixed phrase.
SURFACE_VERB_MAP = {
    "η": [["haya"], ["sea"], ["es"]],
    "ητε": [["esten"], ["sean"], ["esten", "enteramente", "unidos"]],
    "λεγητε": [["se", "pongan", "de", "acuerdo"], ["digan"], ["hablen"], ["decir"]],
    "εδηλωθη": [["he", "sido", "informado"], ["fui", "informado"], ["informado"]],
    "εστιν": [["es"], ["esta"]],
    "εστι": [["es"], ["esta"]],
    "εισιν": [["son"], ["hay"]],
    "εισι": [["son"], ["hay"]],
    "εστε": [["son"], ["son"]],
    "ειμι": [["soy"], ["estoy"]],
    "εσμεν": [["somos"]],
    "εκληθητε": [["fueron", "llamados"]],
    "εβαπτισθητε": [["fueron", "bautizados"]],
    "κατηρτισμενοι": [["enteramente", "unidos"], ["unidos"]],
    "επλουτισθητε": [["fueron", "enriquecidos"]],
    "εβεβαιωθη": [["fue", "confirmado"], ["confirmado"]],
    "βεβαιωσει": [["confirmara"]],
    "λεγω": [["me", "refiero"], ["digo"], ["dice"]],
    "λεγει": [["dice"]],
    "μεμερισται": [["esta", "dividido"], ["dividido"]],
    "εσταυρωθη": [["fue", "crucificado"], ["crucificado"]],
    "εβαπτισθητε": [["fueron", "bautizados"]],
}


# Lemma-based surface phrases.
# These should be NBLA-style surfaces, not dictionary glosses with slashes.
LEMMA_VERB_MAP = {
    "αγαπαω": [["amar"], ["aman"], ["amo"], ["ame"], ["amen"]],
    "αγιαζω": [["santificados"], ["santificar"]],
    "αγνοεω": [["ignorar"], ["ignoren"]],
    "αδικεω": [["hacer", "injusticia"], ["hace", "injusticia"]],
    "αιτεω": [["piden"], ["pedir"]],
    "ακουω": [["oir"], ["oyen"], ["oigan"], ["he", "oido"], ["han", "oido"]],
    "αμαρτανω": [["pecar"], ["peca"], ["pecan"]],
    "ανακρινω": [["disciernen"], ["discernir"], ["juzga"], ["juzgado"]],
    "αποκαλυπτω": [["revelar"], ["revelada"], ["revelo"]],
    "απολλυμι": [["pierden"], ["perder"], ["destruir"]],
    "αποστελλω": [["enviar"], ["envio"], ["envió"]],
    "αρεσκω": [["agradar"], ["agrada"]],
    "ασθενεω": [["ser", "debil"], ["debil"]],
    "ασπαζομαι": [["saludar"], ["saluden"], ["saludan"]],
    "αυξανω": [["crecer"], ["crecimiento"]],
    "βαπτιζω": [["bautice"], ["bautizo"], ["bautizar"], ["bautizados"], ["fueron", "bautizados"]],
    "βασιλευω": [["reinar"], ["reinaron"], ["reinamos"]],
    "βεβαιοω": [["confirmar"], ["confirmado"], ["confirmara"]],
    "βλεπω": [["vean"], ["ver"], ["consideren"], ["cuidense"]],
    "γαμεω": [["casarse"], ["casan"], ["case"]],
    "γινομαι": [["se", "hizo"], ["se", "hace"], ["llegar", "a", "ser"], ["llegado", "a", "ser"], ["ser"], ["fue"]],
    "γινωσκω": [["conocer"], ["conocen"], ["conozcan"], ["sepan"], ["saben"]],
    "γραφω": [["escrito"], ["escribir"], ["escribo"], ["escribi"]],
    "διδασκω": [["ensenar"], ["enseña"], ["enseñan"], ["enseño"]],
    "διδωμι": [["dar"], ["dio"], ["dado"], ["da"], ["den"]],
    "δοκεω": [["parece"], ["cree"], ["creen"], ["creer"]],
    "δοκιμαζω": [["probar"], ["probara"], ["examinar"]],
    "δοξαζω": [["glorificar"], ["glorificado"]],
    "δυναμαι": [["puede"], ["pueden"], ["podia"], ["podian"], ["pude"], ["poder"]],
    "εγειρω": [["resucitar"], ["resucitado"], ["levantar"], ["levantado"]],
    "ειμι": [["soy"], ["es"], ["son"], ["somos"], ["esta"], ["estan"], ["estoy"], ["ser"]],
    "ερχομαι": [["venir"], ["vino"], ["viene"], ["vendrá"], ["fui"], ["ir"]],
    "εσθιω": [["comer"], ["come"], ["comen"]],
    "ευαγγελιζω": [["predicar", "el", "evangelio"], ["predicar"], ["anunciar"]],
    "ευδοκεω": [["agrado"], ["agradó"], ["agradarse"]],
    "ευρισκω": [["hallar"], ["hallado"], ["encontrar"]],
    "ευχαριστεω": [["doy", "gracias"], ["dar", "gracias"], ["damos", "gracias"]],
    "εχω": [["tener"], ["tiene"], ["tienen"], ["tengo"], ["tenemos"], ["tengan"], ["tenia"]],
    "ζητεω": [["buscar"], ["buscan"], ["busque"]],
    "ζαω": [["vivir"], ["vive"], ["vivo"], ["viven"]],
    "θελω": [["querer"], ["quiero"], ["quiere"]],
    "καλεω": [["llamar"], ["llamados"], ["llamo"]],
    "καταγγελλω": [["proclamar"], ["proclaman"]],
    "καταργεω": [["anular"], ["destruir"], ["desapareciendo"]],
    "καταισχυνω": [["avergonzar"], ["avergüence"]],
    "καυχαομαι": [["gloriarse"], ["se", "gloria"], ["jacte"]],
    "κενοω": [["vaciar"], ["haga", "vana"], ["hacer", "vana"]],
    "κερδαινω": [["ganar"]],
    "κηρυσσω": [["predicar"], ["predicamos"], ["proclamar"]],
    "κοιμαομαι": [["dormir"], ["duermen"]],
    "κοπιαω": [["trabajar"], ["trabajamos"]],
    "κραζω": [["clamar"], ["clama"]],
    "κρινω": [["juzgar"], ["juzguen"], ["juzgo"]],
    "λαμβανω": [["recibir"], ["reciben"], ["recibio"], ["recibimos"], ["recibiste"]],
    "λαλεω": [["hablar"], ["hablamos"], ["habla"], ["hablan"]],
    "λεγω": [["decir"], ["dice"], ["digo"], ["digan"], ["dijo"]],
    "λογιζομαι": [["considerar"], ["considero"], ["consideren"]],
    "μανθανω": [["aprender"], ["aprendan"]],
    "μενω": [["permanecer"], ["permanece"]],
    "μεριζω": [["dividir"], ["dividido"]],
    "μεριμναω": [["preocuparse"], ["preocupan"]],
    "μετεχω": [["participar"], ["participan"]],
    "οιδα": [["saber"], ["se"], ["saben"], ["sabemos"]],
    "οικοδομεω": [["edificar"], ["edifica"]],
    "οραω": [["ver"], ["vieron"], ["vean"], ["vio"]],
    "οφειλω": [["deber"], ["debe"], ["debemos"]],
    "παραδιδωμι": [["entregar"], ["entregado"]],
    "παρακαλεω": [["rogar"], ["exhortar"], ["ruego"]],
    "παραλαμβανω": [["recibir"], ["recibido"]],
    "πεμπω": [["enviar"], ["envio"], ["enviare"]],
    "περιπατεω": [["andar"], ["andan"]],
    "περισσευω": [["abundar"], ["abunde"]],
    "πιστευω": [["creer"], ["creen"], ["creyeron"], ["creido"]],
    "πινω": [["beber"], ["bebe"], ["beban"]],
    "πιπτω": [["caer"], ["caiga"]],
    "πλαναω": [["enganar"], ["engañar"], ["desviar"]],
    "ποιεω": [["hacer"], ["hace"], ["hagan"], ["hizo"], ["hecho"]],
    "πορευομαι": [["ir"], ["va"], ["vayan"]],
    "πορνευω": [["fornicar"]],
    "ποτιζω": [["dar", "de", "beber"], ["beber"]],
    "προσευχομαι": [["orar"], ["oro"], ["oren"]],
    "προφητευω": [["profetizar"], ["profetiza"]],
    "σκανδαλιζω": [["hacer", "tropezar"], ["tropieza"]],
    "σπειρω": [["sembrar"], ["siembra"]],
    "σταυροω": [["crucificar"], ["crucificado"], ["fue", "crucificado"]],
    "στεγω": [["soportar"], ["soporta"]],
    "σωζω": [["salvar"], ["salvos"], ["salvo"]],
    "τιθημι": [["poner"], ["puesto"], ["puso"]],
    "τρεχω": [["correr"], ["corran"]],
    "υπαρχω": [["ser"], ["existir"]],
    "υποτασσω": [["someter"], ["sujeto"], ["sujeten"]],
    "χαιρω": [["regocijarse"], ["regocijo"], ["gozo"]],
    "χραομαι": [["usar"], ["uso"]],
    "δηλοω": [["he", "sido", "informado"], ["informado"], ["manifestar"]],
    "βεβαιοω": [["confirmar"], ["confirmado"], ["confirmara"]],
    "απεκδεχομαι": [["esperando", "ansiosamente"], ["esperando"]],
    "υστερεω": [["les", "falta"], ["falta"], ["carecer"]],
}




# Periphrastic constructions where a finite form of ειμι + participle
# is rendered as one Spanish verbal phrase.
# The finite verb receives the auxiliary span; the participle receives the predicate span.
PERIPHRASTIC_MAP = {
    ("ητε", "κατηρτισμενοι"): {
        "full": [["esten", "enteramente", "unidos"]],
        "finite_len": 1,
    },
}

LEXICAL_MAP = {
    "αδελφ": [["hermanos"]],
    "κυρι": [["senor"]],
    "ιησου": [["jesucristo"], ["jesus"]],
    "χριστ": [["cristo"], ["jesucristo"]],
    "σχισμα": [["divisiones"]],
    "εριδ": [["discusiones"]],
    "υμ": [["ustedes"]],
    "χλο": [["cloe"]],
    "νο": [["sentir"]],
    "γνωμ": [["parecer"]],
    "παντ": [["todos"], ["todo"], ["toda"], ["todas"]],
    "πασ": [["todos"], ["todo"], ["toda"], ["todas"]],
}


def sequences_for_verb(greek, morph_item):
    surface = normalize(greek)
    lemma = normalize(morph_lemma(morph_item))

    sequences = []

    if surface in SURFACE_VERB_MAP:
        sequences.extend(SURFACE_VERB_MAP[surface])

    if lemma in LEMMA_VERB_MAP:
        sequences.extend(LEMMA_VERB_MAP[lemma])

    # Passive fallback must run even when lemma is missing
    sequences.extend(passive_sequences(morph_item))

    return sequences


def function_sequences(greek):
    g = normalize(greek)

    for stem, sequences in FUNCTION_MAP.items():
        if g.startswith(stem):
            return sequences

    return []


def lexical_sequences(greek):
    g = normalize(greek)

    for stem, sequences in LEXICAL_MAP.items():
        if g.startswith(stem):
            return sequences

    return []


def find_sequence(tokens, sequence, used):
    n = len(sequence)

    for i in range(0, len(tokens) - n + 1):
        indexes = set(range(i, i + n))

        if indexes & used:
            continue

        if tokens[i:i + n] == sequence:
            return i, i + n - 1

    return None


def find_from_sequences(tokens, sequences, used):
    # Prefer longer phrases first.
    sequences = sorted(sequences, key=len, reverse=True)

    for sequence in sequences:
        found = find_sequence(tokens, sequence, used)
        if found:
            return found

    return None


def surface(tokens, span):
    if not span:
        return "[missing]"
    return " ".join(tokens[span[0]:span[1] + 1])

def passive_sequences(morph_item):
    code = morph_code(morph_item)

    if not code.startswith("V"):
        return []

    rmac = code.replace("--", "-")
    parts = [p for p in rmac.split("-") if p]

    if len(parts) < 2:
        return []

    tvm = parts[1]

    # Passive voice = middle letter P
    if len(tvm) == 3 and tvm[1] == "P":
        return [
            ["fue"],
            ["fueron"],
            ["ha", "sido"],
            ["han", "sido"]
        ]

    return []


def find_periphrastic_partner(greek_tokens, morph_tokens, start_index):
    finite_surface = normalize(greek_tokens[start_index])

    # Look only a short distance ahead. This catches cases like:
    # ἦτε δὲ κατηρτισμένοι without allowing broad guessing.
    for j in range(start_index + 1, min(start_index + 5, len(greek_tokens))):
        partner_surface = normalize(greek_tokens[j])
        key = (finite_surface, partner_surface)

        if key not in PERIPHRASTIC_MAP:
            continue

        partner_morph = morph_tokens[j] if j < len(morph_tokens) else None

        # Require the partner to be a verbal form, normally a participle.
        if not is_verb(partner_morph):
            continue

        return j, PERIPHRASTIC_MAP[key]

    return None

def align_tokens(greek_tokens, morph_tokens, spanish_tokens, spans=None):
    output = [
        (greek, "[missing]", "missing", None)
        for greek in greek_tokens
    ]

    used = set()

    # PASS 0: finite verb + participle periphrastic constructions.
    # This is intentionally narrow: only mapped Greek form pairs are accepted.
    for i, greek in enumerate(greek_tokens):
        if output[i][3]:
            continue

        morph_item = morph_tokens[i] if i < len(morph_tokens) else None

        if not is_verb(morph_item):
            continue

        pair = find_periphrastic_partner(greek_tokens, morph_tokens, i)

        if not pair:
            continue

        partner_index, config = pair
        span = find_from_sequences(spanish_tokens, config["full"], used)

        if not span:
            continue

        finite_len = config.get("finite_len", 1)
        finite_span = (span[0], span[0] + finite_len - 1)
        participle_span = (span[0] + finite_len, span[1])

        used.update(range(span[0], span[1] + 1))
        output[i] = (greek, surface(spanish_tokens, finite_span), "periphrastic-finite", finite_span)
        output[partner_index] = (
            greek_tokens[partner_index],
            surface(spanish_tokens, participle_span),
            "periphrastic-participle",
            participle_span,
        )

    # PASS 1: verbs only.
    # These are the only spans trusted by build_dataset for NBLA clause spans.
    for i, greek in enumerate(greek_tokens):
        if output[i][3]:
            continue

        morph_item = morph_tokens[i] if i < len(morph_tokens) else None

        if not is_verb(morph_item):
            continue

        sequences = sequences_for_verb(greek, morph_item)

        if not sequences:
            continue

        span = find_from_sequences(spanish_tokens, sequences, used)

        if span:
            used.update(range(span[0], span[1] + 1))
            label = "verb-expanded" if span[0] != span[1] else "verb-direct"
            output[i] = (greek, surface(spanish_tokens, span), label, span)

    # PASS 2: connectors/function words.
    for i, greek in enumerate(greek_tokens):
        if output[i][3]:
            continue

        key = normalize(greek)

        # Do not let postpositive δὲ after the first finite verb steal
        # a later Spanish connector span like "sino que".
        if key == "δε" and i > 0:
            prev_key = normalize(greek_tokens[i - 1])
            if prev_key not in {"ητε", "εστιν", "εστι", "εισιν", "εισι", "εστε"}:
                continue

        sequences = function_sequences(greek)

        if not sequences:
            continue

        span = find_from_sequences(spanish_tokens, sequences, used)

        if span:
            used.update(range(span[0], span[1] + 1))
            output[i] = (greek, surface(spanish_tokens, span), "function", span)

    # PASS 3: lexical items.
    # Useful later, but NOT trusted for clause-span creation.
    for i, greek in enumerate(greek_tokens):
        if output[i][3]:
            continue

        sequences = lexical_sequences(greek)

        if not sequences:
            continue

        span = find_from_sequences(spanish_tokens, sequences, used)

        if span:
            used.update(range(span[0], span[1] + 1))
            output[i] = (greek, surface(spanish_tokens, span), "lexical", span)

    return output