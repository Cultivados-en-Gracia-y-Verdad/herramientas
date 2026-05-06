import re
import unicodedata


def normalize(token):
    token = re.sub(r"[·.,;:!?⸀⸂⸃()\[\]«»“”\"']", "", token).lower()
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
    "δε": [["pero"], ["sino"], ["sin", "embargo"], ["ahora", "bien"], ["en", "cambio"]],
    "αλλα": [["sino"], ["pero"], ["antes", "bien"]],
    "ει": [["si"]],
    "ωστε": [["de", "manera", "que"], ["asi", "que"], ["por", "tanto"]],
}


# Surface-form overrides for forms that NBLA regularly renders with a fixed phrase.
SURFACE_VERB_MAP = {
    "η": [["haya"], ["sea"], ["es"]],
    "ητε": [["esten"], ["sean"]],
    "εστιν": [["es"], ["esta"]],
    "εστι": [["es"], ["esta"]],
    "εισιν": [["son"], ["hay"]],
    "εισι": [["son"], ["hay"]],
    "εστε": [["son"], ["son"]],
    "ειμι": [["soy"], ["estoy"]],
    "εσμεν": [["somos"]],
    "εκληθητε": [["fueron", "llamados"]],
    "εβαπτισθητε": [["fueron", "bautizados"]],
    "εσταυρωθη": [["fue", "crucificado"]],
    "μεμερισται": [["esta", "dividido"]],
    "κατηρτισμενοι": [["enteramente", "unidos"], ["unidos"]],
    "λεγητε": [["se", "pongan", "de", "acuerdo"], ["digan"], ["hablen"]],
    "εδηλωθη": [["he", "sido", "informado"], ["fui", "informado"], ["informado"]],
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


def align_tokens(greek_tokens, morph_tokens, spanish_tokens, spans=None):
    output = [
        (greek, "[missing]", "missing", None)
        for greek in greek_tokens
    ]

    used = set()

    # PASS 1: verbs only.
    # These are the only spans trusted by build_dataset for NBLA clause spans.
    for i, greek in enumerate(greek_tokens):
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
    # These can mark connectors, but build_dataset will NOT use them for verb clause spans.
    for i, greek in enumerate(greek_tokens):
        if output[i][3]:
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