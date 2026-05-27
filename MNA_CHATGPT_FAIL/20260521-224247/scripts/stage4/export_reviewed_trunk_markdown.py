#!/usr/bin/env python3
"""
MNA Etapa 4 — Exportar Tronco Revisado a Markdown

PROPÓSITO
- Exportar las filas revisadas de suggested-trunk a un archivo Markdown legible en español.
- Útil para preparación de manuales y revisión rápida de enseñanza.
- No modifica los datos fuente.

REGLA DE ARQUITECTURA
- La capa canónica permanece intacta: griego, JSON, RMAC, referencias, enums internos.
- La capa de presentación se localiza al español para lectores/estudiantes.

Salida:
  MNA/exports/reviewed-trunk/<book>.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional


STATUS_ES = {
    "AI_REVIEWED": "REVISADO_POR_IA",
    "NEEDS_EXTERNAL_GREEK_REVIEW": "REQUIERE_REVISIÓN_GRIEGA_EXTERNA",
    "REVIEWED_FOR_MANUAL_USE": "REVISADO_PARA_USO_EN_MANUAL",
}

CONFIDENCE_ES = {
    "HIGH": "ALTA",
    "MEDIUM-HIGH": "MEDIA-ALTA",
    "MEDIUM": "MEDIA",
    "MEDIUM-LOW": "MEDIA-BAJA",
    "LOW": "BAJA",
}

# Presentation-only translation map.
# These strings are intentionally NOT written back into the JSONL dataset.
NOTE_SENTENCE_ES = {
    "Main thanksgiving force preserved": "Se preserva la fuerza principal de acción de gracias",
    "Main thanksgiving predicate preserved": "Se preserva el predicado principal de acción de gracias",
    "Main exhortational force preserved": "Se preserva la fuerza exhortativa principal",
    "Main statement preserved": "Se preserva la declaración principal",
    "Main reporting assertion preserved": "Se preserva la afirmación principal de reporte",
    "Main report assertion preserved": "Se preserva la afirmación principal de reporte",
    "Opening rhetorical question preserved as trunk": "Se preserva la pregunta retórica inicial como tronco",
    "Primary baptism assertion preserved": "Se preserva la afirmación principal sobre el bautismo",
    "Main sending contrast preserved": "Se preserva el contraste principal del envío",
    "Dual-predicate contrast preserved": "Se preserva el contraste de doble predicado",
    "Quotation introduction preserved as governing assertion": "Se preserva la introducción de la cita como afirmación gobernante",
    "Primary rhetorical assertion preserved": "Se preserva la afirmación retórica principal",
    "Primary force placed on God's saving action": "La fuerza principal se coloca en la acción salvadora de Dios",
    "Coordinated setup predicates preserved": "Se preservan los predicados coordinados de preparación",
    "Main contrastive proclamation preserved": "Se preserva la proclamación contrastiva principal",
    "Comparative explanatory assertion preserved": "Se preserva la afirmación explicativa comparativa",
    "Main imperative preserved": "Se preserva el imperativo principal",
    "Main divine choosing predicate preserved": "Se preserva el predicado principal de elección divina",
    "Repeated divine choosing predicate preserved": "Se preserva el predicado repetido de elección divina",
    "Main identity/location statement preserved": "Se preserva la declaración principal de identidad/ubicación",
    "Quoted imperative preserved for manual flow": "Se preserva el imperativo citado para el flujo del manual",
    "Main arrival predicate preserved": "Se preserva el predicado principal de llegada",
    "Main decision predicate preserved": "Se preserva el predicado principal de decisión",
    "Main presence/condition assertion preserved": "Se preserva la afirmación principal de presencia/condición",
    "Dependent purpose/result clause preserved for manual flow": "Se preserva la cláusula dependiente de propósito/resultado para el flujo del manual",
    "Main speaking assertion preserved": "Se preserva la afirmación principal de habla",
    "Main contrastive speaking assertion preserved": "Se preserva la afirmación principal contrastiva de habla",
    "Main ignorance assertion preserved": "Se preserva la afirmación principal de ignorancia",
    "Draft revised from unstable connector-only span": "Borrador revisado desde un tramo inestable basado solo en conector",
    "Main revelation assertion preserved": "Se preserva la afirmación principal de revelación",
    "Main rhetorical knowledge question preserved": "Se preserva la pregunta retórica principal de conocimiento",
    "Main reception contrast preserved": "Se preserva el contraste principal de recepción",
    "Main speaking predicate preserved": "Se preserva el predicado principal de habla",
    "Main contrastive reception assertion preserved": "Se preserva la afirmación principal contrastiva de recepción",
    "Primary assertion about the spiritual person preserved": "Se preserva la afirmación principal sobre la persona espiritual",
    "Final contrastive assertion preserved": "Se preserva la afirmación contrastiva final",
    "Main inability predicate preserved": "Se preserva el predicado principal de incapacidad",
    "Main feeding metaphor preserved": "Se preserva la metáfora principal de alimentación",
    "Main diagnosis preserved": "Se preserva el diagnóstico principal",
    "Final diagnostic assertion/question preserved": "Se preserva la afirmación/pregunta diagnóstica final",
    "Identity questions and servant identification preserved": "Se preservan las preguntas de identidad y la identificación como servidores",
    "Full contrastive planting-watering-growth chain preserved": "Se preserva completa la cadena contrastiva plantar-regar-crecimiento",
    "Conclusion from planting/watering contrast preserved": "Se preserva la conclusión del contraste plantar/regar",
    "Main unity assertion preserved": "Se preserva la afirmación principal de unidad",
    "Main identity assertion preserved": "Se preserva la afirmación principal de identidad",
    "Main foundation-laying assertion preserved": "Se preserva la afirmación principal de colocación del fundamento",
    "Main inability assertion preserved": "Se preserva la afirmación principal de incapacidad",
    "Conditional building clause preserved for manual flow": "Se preserva la cláusula condicional de edificación para el flujo del manual",
    "Main manifestation assertion preserved": "Se preserva la afirmación principal de manifestación",
    "Conditional-result structure preserved": "Se preserva la estructura condición-resultado",
    "Knowledge-question preserved": "Se preserva la pregunta de conocimiento",
    "Conditional-result warning preserved": "Se preserva la advertencia condición-resultado",
    "Opening prohibition preserved as primary exhortational force": "Se preserva la prohibición inicial como fuerza exhortativa principal",
    "Main assertion about worldly wisdom preserved": "Se preserva la afirmación principal sobre la sabiduría del mundo",
    "Main divine knowledge assertion preserved": "Se preserva la afirmación principal de conocimiento divino",
    "Main prohibition preserved": "Se preserva la prohibición principal",
    "Main requirement predicate preserved": "Se preserva el predicado principal de requisito",
    "Main evaluative assertion preserved": "Se preserva la afirmación evaluativa principal",
    "Coordinated self-awareness and non-justification assertions preserved": "Se preservan las afirmaciones coordinadas de conciencia propia y no justificación",
    "Main explanatory action preserved": "Se preserva la acción explicativa principal",
    "Opening diagnostic rhetorical questions preserved": "Se preservan las preguntas retóricas diagnósticas iniciales",
    "Three-part corrective chain preserved": "Se preserva la cadena correctiva de tres partes",
    "Paul's judgment and embedded divine-display assertion preserved": "Se preservan el juicio de Pablo y la afirmación incrustada de exhibición divina",
    "Coordinated apostolic suffering chain preserved": "Se preserva la cadena coordinada de sufrimiento apostólico",
    "Main labor assertion preserved": "Se preserva la afirmación principal de trabajo",
    "Main response predicate preserved": "Se preserva el predicado principal de respuesta",
    "Main writing predicate preserved": "Se preserva el predicado principal de escritura",
    "Main fathering/begetting assertion preserved": "Se preserva la afirmación principal de engendrar/paternidad",
    "Main exhortation predicate preserved": "Se preserva el predicado principal de exhortación",
    "Main sending predicate preserved": "Se preserva el predicado principal de envío",
    "Main arrogance assertion preserved": "Se preserva la afirmación principal de arrogancia",
    "Main promised coming preserved": "Se preserva la venida prometida principal",
    "Governing question preserved": "Se preserva la pregunta gobernante",
    "Main rebuke of their inflated posture preserved": "Se preserva el reproche principal contra su postura inflada",
    "Main judgment assertion preserved": "Se preserva la afirmación principal de juicio",
    "Core disciplinary action preserved": "Se preserva la acción disciplinaria central",
    "Main evaluation of their boasting preserved": "Se preserva la evaluación principal de su jactancia",
    "Main cleansing command preserved": "Se preserva el mandato principal de limpieza",
    "Main feast-exhortation preserved": "Se preserva la exhortación principal de celebrar la fiesta",
    "Main previous-writing instruction preserved": "Se preserva la instrucción principal de la carta anterior",
    "Clarifying limitation preserved": "Se preserva la limitación aclaratoria",
    "Main present-writing instruction preserved": "Se preserva la instrucción principal de la escritura presente",
    "Inside/outside judgment questions preserved together": "Se preservan juntas las preguntas sobre juzgar a los de adentro/afuera",
    "God-judges-outsiders assertion and removal command preserved as closing conclusion": "Se preservan la afirmación de que Dios juzga a los de afuera y el mandato de quitar al malo como conclusión final",
    "Main rebuking question preserved": "Se preserva la pregunta principal de reprensión",
    "False-witness consequence assertion preserved": "Se preserva la afirmación consecuente sobre falso testimonio",
    "Past identity and threefold contrastive transformation preserved": "Se preserva la identidad pasada y la transformación contrastiva triple",
    "Liberty slogan and corrective limitations preserved together": "Se preservan juntos el lema de libertad y las limitaciones correctivas",
    "Food/body slogan and divine abolition assertion preserved": "Se preservan el lema comida/cuerpo y la afirmación de abolición divina",
    "God’s raising of the Lord and future raising of believers preserved": "Se preserva que Dios levantó al Señor y levantará a los creyentes",
    "Union-with-the-Lord assertion preserved as contrast": "Se preserva la afirmación de unión con el Señor como contraste",
    "Purchase assertion and glorify-God command preserved together": "Se preservan juntos la afirmación de compra y el mandato de glorificar a Dios",
    "Opening statement preserved": "Se preserva la declaración inicial",
    "Main marriage instruction preserved": "Se preserva la instrucción principal sobre el matrimonio",
    "Mutual marital obligation command preserved": "Se preserva el mandato de obligación marital mutua",
    "Mutual bodily authority contrast preserved": "Se preserva el contraste de autoridad corporal mutua",
    "Permission/not-command distinction preserved": "Se preserva la distinción entre permiso y mandato",
    "Paul’s wish statement preserved": "Se preserva la declaración de deseo de Pablo",
    "Main unmarried/widow statement preserved": "Se preserva la declaración principal sobre solteros/viudas",
    "Conditional marriage instruction preserved": "Se preserva la instrucción condicional de casarse",
    "Parallel unbelieving-spouse instruction preserved": "Se preserva la instrucción paralela sobre el cónyuge incrédulo",
    "Sanctification assertion preserved": "Se preserva la afirmación de santificación",
    "Salvation-outcome question preserved": "Se preserva la pregunta sobre el resultado de salvación",
    "Main remain/walk principle preserved": "Se preserva el principio principal de permanecer/andar",
    "Circumcision-state instruction preserved": "Se preserva la instrucción sobre el estado de circuncisión",
    "Circumcision insignificance assertion preserved": "Se preserva la afirmación de insignificancia de la circuncisión",
    "Remain-in-calling principle preserved": "Se preserva el principio de permanecer en el llamamiento",
    "Slave-calling instruction preserved": "Se preserva la instrucción sobre el llamamiento siendo esclavo",
    "Slave/free paradox assertions preserved": "Se preservan las afirmaciones paradójicas esclavo/libre",
    "Purchase assertion and anti-human-slavery exhortation preserved together": "Se preservan juntas la afirmación de compra y la exhortación a no hacerse esclavos de hombres",
    "Closing remain-with-God principle preserved": "Se preserva el principio final de permanecer con Dios",
    "Topic shift and command/opinion distinction preserved": "Se preserva el cambio de tema y la distinción mandato/opinión",
    "Main judgment statement preserved": "Se preserva la declaración principal de juicio/opinión",
    "Paired state-maintenance instructions preserved": "Se preservan las instrucciones pareadas de mantener el estado",
    "Conditional marriage-not-sin assertion preserved": "Se preserva la afirmación condicional de que casarse no es pecado",
    "Main compressed-time assertion preserved": "Se preserva la afirmación principal del tiempo reducido",
    "World-use reorientation preserved": "Se preserva la reorientación del uso del mundo",
    "Main desire for undistractedness preserved": "Se preserva el deseo principal de estar sin distracción",
    "Married-man concern assertion preserved": "Se preserva la afirmación sobre la preocupación del casado",
    "Divided-concern statement preserved": "Se preserva la declaración de preocupación dividida",
    "Main benefit-oriented statement preserved": "Se preserva la declaración principal orientada al beneficio",
    "Conditional permission structure preserved": "Se preserva la estructura condicional de permiso",
    "Firm-decision good-action statement preserved": "Se preserva la declaración de buena acción basada en decisión firme",
    "Marriage and non-marriage comparative conclusion preserved": "Se preserva la conclusión comparativa entre casar y no casar",
    "Marriage-bound statement preserved": "Se preserva la declaración de vínculo matrimonial",
    "Main happier-if-remains statement preserved": "Se preserva la declaración principal de que será más feliz si permanece así",
    "Topic shift and knowledge statement preserved": "Se preserva el cambio de tema y la declaración de conocimiento",
    "Conditional knowledge-warning preserved": "Se preserva la advertencia condicional sobre el conocimiento",
    "Knowledge assertion about idols/God preserved": "Se preserva la afirmación de conocimiento sobre ídolos/Dios",
    "One-God/one-Lord confession preserved": "Se preserva la confesión de un Dios/un Señor",
    "Not-all-have-knowledge assertion preserved": "Se preserva la afirmación de que no todos tienen conocimiento",
    "Food-not-commend-us assertion preserved": "Se preserva la afirmación de que la comida no nos presentará ante Dios",
    "Main warning preserved": "Se preserva la advertencia principal",
    "Conditional temple-meal scenario preserved": "Se preserva el escenario condicional de comida en templo",
    "Weak-brother destruction assertion preserved": "Se preserva la afirmación sobre la destrucción del hermano débil",
    "Sinning-against-brothers/Christ assertion preserved": "Se preserva la afirmación de pecado contra los hermanos/Cristo",
    "Conditional self-limitation conclusion preserved": "Se preserva la conclusión condicional de autolimitación",
    "Four rhetorical questions preserved together": "Se preservan juntas las cuatro preguntas retóricas",
    "Formal defense-introduction assertion preserved": "Se preserva la afirmación formal que introduce la defensa",
    "Rhetorical rights question preserved": "Se preserva la pregunta retórica sobre derechos",
    "Three rhetorical labor-benefit examples preserved together": "Se preservan juntos los tres ejemplos retóricos de trabajo/beneficio",
    "Two rhetorical questions preserved": "Se preservan dos preguntas retóricas",
    "Written-law introduction preserved": "Se preserva la introducción de la ley escrita",
    "Main application assertion preserved": "Se preserva la afirmación principal de aplicación",
    "Conditional rhetorical rights argument preserved": "Se preserva el argumento retórico condicional sobre derechos",
    "Conditional comparison preserved": "Se preserva la comparación condicional",
    "Main Lord-command assertion preserved": "Se preserva la afirmación principal del mandato del Señor",
    "Main non-use-of-rights assertion preserved": "Se preserva la afirmación principal del no uso de derechos",
    "Conditional non-boasting assertion preserved": "Se preserva la afirmación condicional de no jactancia",
    "Both conditional halves preserved": "Se preservan ambas mitades condicionales",
    "Main voluntary enslavement assertion preserved": "Se preserva la afirmación principal de esclavitud voluntaria",
    "Adaptive ministry statements preserved": "Se preservan las declaraciones de adaptación ministerial",
    "Adaptive ministry continuation preserved": "Se preserva la continuación de adaptación ministerial",
    "Adaptive weak-to-weak clause and summary statement preserved": "Se preserva la cláusula débil-a-débil y la declaración resumida",
    "Main gospel-motivation assertion preserved": "Se preserva la afirmación principal de motivación por el evangelio",
    "Race illustration and imperative application preserved together": "Se preservan juntas la ilustración de la carrera y la aplicación imperativa",
    "Main athletic self-control assertion preserved": "Se preserva la afirmación principal de dominio propio atlético",
    "Paul's two personal discipline assertions preserved": "Se preservan las dos afirmaciones personales de disciplina de Pablo",
    "Main bodily discipline chain preserved": "Se preserva la cadena principal de disciplina corporal",
    "Main disclosure-prevention assertion preserved": "Se preserva la afirmación principal para evitar ignorancia",
    "Main Israel-identification assertion preserved": "Se preserva la afirmación principal de identificación con Israel",
    "Main shared spiritual-food assertion preserved": "Se preserva la afirmación principal de alimento espiritual compartido",
    "Main shared spiritual-drink assertion preserved": "Se preserva la afirmación principal de bebida espiritual compartida",
    "Main divine-displeasure assertion preserved": "Se preserva la afirmación principal de desagrado divino",
    "Main example-pattern assertion preserved": "Se preserva la afirmación principal de ejemplo/patrón",
    "Main typological-occurrence assertion preserved": "Se preserva la afirmación principal de ocurrencia tipológica",
    "Main warning exhortation preserved": "Se preserva la exhortación principal de advertencia",
    "Main temptation assurance preserved": "Se preserva la afirmación principal sobre la tentación",
    "Main inferential command preserved": "Se preserva el mandato inferencial principal",
    "Main appeal to discernment preserved": "Se preserva la apelación principal al discernimiento",
    "Two participation questions preserved together": "Se preservan juntas las dos preguntas de participación",
    "Main one-body assertion preserved": "Se preserva la afirmación principal de un solo cuerpo",
    "Main sacrificial-participation assertion preserved": "Se preserva la afirmación principal de participación sacrificial",
    "Two impossibility assertions preserved together": "Se preservan juntas las dos afirmaciones de imposibilidad",
    "Repeated liberty slogan and corrective limitations preserved together": "Se preservan juntos el lema repetido de libertad y las limitaciones correctivas",
    "Main marketplace eating command preserved": "Se preserva el mandato principal de comer lo vendido en el mercado",
    "Conditional invitation and eating instruction preserved together": "Se preservan juntos la invitación condicional y la instrucción de comer",
    "Conditional disclosure and resulting prohibition preserved together": "Se preservan juntos la declaración condicional y la prohibición resultante",
    "Clarifying conscience assertion preserved": "Se preserva la afirmación aclaratoria sobre la conciencia",
    "Comprehensive summary imperative preserved": "Se preserva el imperativo resumidor general",
    "Main command to become without offense preserved": "Se preserva el mandato principal de ser sin tropiezo",
    "Paul’s imitative example preserved": "Se preserva el ejemplo imitativo de Pablo",
    "Main imitation command preserved": "Se preserva el mandato principal de imitación",
    "Main praise assertion preserved": "Se preserva la afirmación principal de alabanza",
    "Main disclosure statement preserved": "Se preserva la declaración principal de revelación/instrucción",
    "Main shame assertion preserved": "Se preserva la afirmación principal de vergüenza",
    "Conditional shame-logic preserved": "Se preserva la lógica condicional de vergüenza",
    "Main obligation assertion preserved": "Se preserva la afirmación principal de obligación",
    "Creation-order contrast preserved": "Se preserva el contraste del orden de creación",
    "Creation-purpose contrast preserved": "Se preserva el contraste del propósito de creación",
    "Mutuality assertion preserved": "Se preserva la afirmación de mutualidad",
    "Reciprocal origin comparison preserved": "Se preserva la comparación recíproca de origen",
    "Main discernment imperative preserved": "Se preserva el imperativo principal de discernimiento",
    "Main rhetorical question preserved": "Se preserva la pregunta retórica principal",
    "Conditional glory assertion preserved": "Se preserva la afirmación condicional de gloria",
    "Conditional contentiousness statement preserved": "Se preserva la declaración condicional sobre contención",
    "Main corrective non-praise assertion preserved": "Se preserva la afirmación correctiva principal de no alabanza",
    "Main necessity assertion preserved": "Se preserva la afirmación principal de necesidad",
    "Main negative gathered-meal assertion preserved": "Se preserva la afirmación principal negativa sobre la comida reunida",
    "Main self-prioritizing meal assertion preserved": "Se preserva la afirmación principal de comida individualista",
    "Rebuking rhetorical questions preserved together": "Se preservan juntas las preguntas retóricas de reprensión",
    "Main received-and-delivered tradition assertion preserved": "Se preserva la afirmación principal de tradición recibida y entregada",
    "Central bread-identification saying preserved": "Se preserva la declaración central de identificación del pan",
    "Central cup-identification saying preserved": "Se preserva la declaración central de identificación de la copa",
    "Main proclamation assertion preserved": "Se preserva la afirmación principal de proclamación",
    "Conditional warning and result preserved together": "Se preservan juntos la advertencia condicional y el resultado",
    "Main self-examination command preserved": "Se preserva el mandato principal de autoexamen",
    "Main judgment-eating/drinking assertion preserved": "Se preserva la afirmación principal de comer/beber juicio",
    "Main consequence assertion preserved": "Se preserva la afirmación principal de consecuencia",
    "Conditional counterfactual judgment statement preserved": "Se preserva la declaración condicional contrafactual de juicio",
    "Main Lord-discipline assertion preserved": "Se preserva la afirmación principal de disciplina del Señor",
    "Inferential command preserved": "Se preserva el mandato inferencial",
    "Conditional practical instruction preserved": "Se preserva la instrucción práctica condicional",
    "Spirit-confession criteria": "criterios de confesión por el Espíritu",
    "Main diversity/same-Spirit assertion preserved": "Se preserva la afirmación principal de diversidad/mismo Espíritu",
    "Ministry diversity/same-Lord assertion preserved": "Se preserva la afirmación de diversidad de ministerios/mismo Señor",
    "Activity diversity/same-God assertion preserved": "Se preserva la afirmación de diversidad de operaciones/mismo Dios",
    "Main manifestation-given assertion preserved": "Se preserva la afirmación principal de manifestación dada",
    "First distribution examples preserved": "Se preservan los primeros ejemplos de distribución",
    "Gift-distribution list preserved": "Se preserva la lista de distribución de dones",
    "Main summary assertion preserved": "Se preserva la afirmación resumidora principal",
    "Body analogy preserved": "Se preserva la analogía del cuerpo",
    "Conditional member-speech and corrective conclusion preserved": "Se preserva el habla condicional del miembro y la conclusión correctiva",
    "Parallel conditional member-speech and corrective conclusion preserved": "Se preserva el habla condicional paralela del miembro y la conclusión correctiva",
    "Main divine-placement assertion preserved": "Se preserva la afirmación principal de colocación divina",
    "Summary contrast preserved": "Se preserva el contraste resumidor",
    "Main impossibility assertion preserved": "Se preserva la afirmación principal de imposibilidad",
    "Main necessity assertion preserved": "Se preserva la afirmación principal de necesidad",
    "Main honor-giving assertion preserved": "Se preserva la afirmación principal de otorgar honra",
    "Main divine-composition assertion preserved": "Se preserva la afirmación principal de composición divina",
    "Purpose/result clause preserved for manual flow": "Se preserva la cláusula de propósito/resultado para el flujo del manual",
    "Main one-Spirit/one-body baptism assertion preserved": "Se preserva la afirmación principal de un Espíritu/un cuerpo en el bautismo",
    "Main topic frame preserved": "Se preserva el marco principal del tema",
}

PHRASE_ES = [
    ("treated as explanatory expansion", "tratado como expansión explicativa"),
    ("treated as expansion", "tratado como expansión"),
    ("treated as supporting expansion", "tratado como expansión de apoyo"),
    ("treated as supporting detail", "tratado como detalle de apoyo"),
    ("treated as supporting reason", "tratado como razón de apoyo"),
    ("treated as supporting proof", "tratado como prueba de apoyo"),
    ("treated as explanatory support", "tratado como apoyo explicativo"),
    ("treated as explanatory reason", "tratado como razón explicativa"),
    ("treated as explanatory content", "tratado como contenido explicativo"),
    ("treated as explanatory qualification", "tratado como aclaración explicativa"),
    ("treated as qualification", "tratado como aclaración"),
    ("treated as continuation", "tratado como continuación"),
    ("treated as coordinated continuation", "tratado como continuación coordinada"),
    ("treated as coordinated expansion", "tratado como expansión coordinada"),
    ("treated as contrastive setup", "tratado como preparación contrastiva"),
    ("treated as setup", "tratado como preparación"),
    ("treated as content expansion", "tratado como expansión del contenido"),
    ("treated as citation content", "tratado como contenido citado"),
    ("treated as support", "tratado como apoyo"),
    ("treated as result expansion", "tratado como expansión de resultado"),
    ("treated as purpose/result", "tratado como propósito/resultado"),
    ("treated as purpose", "tratado como propósito"),
    ("treated as practical result", "tratado como resultado práctico"),
    ("treated as pastoral qualification", "tratado como aclaración pastoral"),
    ("treated as grounding reason", "tratado como razón fundamentadora"),
    ("treated as balancing qualification", "tratado como aclaración de equilibrio"),
    ("treated as balancing continuation", "tratado como continuación de equilibrio"),
    ("treated as descriptive expansion", "tratado como expansión descriptiva"),
    ("treated as manner expansion", "tratado como expansión de manera"),
    ("treated as manner/qualification", "tratado como manera/aclaración"),
    ("treated as temporal boundary", "tratado como límite temporal"),
    ("treated as intensifying qualification", "tratado como aclaración intensificadora"),
    ("treated as warning support", "tratado como apoyo de la advertencia"),
    ("treated as qualifying frame", "tratado como marco calificativo"),
    ("treated as grounding frame", "tratado como marco fundamentador"),
    ("treated as the object for judgment", "tratado como objeto del juicio/discernimiento"),
    ("retained as governing pattern", "retenido como patrón gobernante"),
    ("retained as circumstance", "retenido como circunstancia"),
    ("retained as the content", "retenido como el contenido"),
    ("retained as complement", "retenido como complemento"),
    ("retained as participatory basis", "retenido como base participativa"),
    ("retained because", "retenido porque"),
    ("retained together", "retenido junto"),
    ("retained", "retenido"),
    ("preserved together", "preservados juntos"),
    ("preserved", "preservado"),
    ("semantic ambiguity remains", "permanece ambigüedad semántica"),
    ("Semantic implications remain debated", "Las implicaciones semánticas siguen siendo debatidas"),
    ("Semantic/application questions remain complex", "Las preguntas semánticas/de aplicación siguen siendo complejas"),
    ("interpretive uncertainty remains high", "la incertidumbre interpretativa sigue siendo alta"),
    ("following", "lo siguiente"),
    ("preceding", "lo anterior"),
    ("clause", "cláusula"),
    ("clauses", "cláusulas"),
    ("question", "pregunta"),
    ("questions", "preguntas"),
    ("assertion", "afirmación"),
    ("assertions", "afirmaciones"),
    ("predicate", "predicado"),
    ("predicates", "predicados"),
    ("contrast", "contraste"),
    ("contrasts", "contrastes"),
    ("rhetorical", "retórico"),
    ("warning", "advertencia"),
    ("command", "mandato"),
    ("imperative", "imperativo"),
    ("purpose", "propósito"),
    ("result", "resultado"),
    ("explanatory", "explicativo"),
    ("supporting", "de apoyo"),
    ("manual flow", "flujo del manual"),
    ("main", "principal"),
    ("Main", "Principal"),
]


def translate_note_sentence(sentence: str) -> str:
    text = sentence.strip()
    if not text:
        return text

    if text in NOTE_SENTENCE_ES:
        return NOTE_SENTENCE_ES[text]

    # Translate leading known sentence fragments while preserving any unmatched tail.
    for source, target in sorted(NOTE_SENTENCE_ES.items(), key=lambda item: len(item[0]), reverse=True):
        if text.startswith(source):
            return target + text[len(source):]

    translated = text
    for source, target in PHRASE_ES:
        translated = translated.replace(source, target)
    return translated


def translate_note_to_spanish(note: str) -> str:
    """Translate presentation notes to Spanish without touching canonical dataset values."""
    if not note:
        return ""

    normalized = note.strip()
    # Split on sentence boundaries and semicolon boundaries, preserving punctuation.
    parts = re.split(r"(?<=[.;])\s+", normalized)
    translated_parts = [translate_note_sentence(part) for part in parts]
    return " ".join(part for part in translated_parts if part).strip()


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    metadata = None
    rows = []

    if not path.is_file():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido en {path}:{line_number}: {exc}") from exc

            if obj.get("record_type") == "metadata":
                metadata = obj
            else:
                rows.append(obj)

    return metadata, rows


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (int(r.get("chapter", 0)), int(r.get("verse", 0))))


def should_include(row: dict, include_unreviewed: bool) -> bool:
    if include_unreviewed:
        return True
    return row.get("reviewed_for_manual_use") is True


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Exportar filas revisadas del tronco sugerido a Markdown.")
    parser.add_argument("book", help="Slug del libro, por ejemplo: 1corintios")
    parser.add_argument("--from", dest="from_ref", help="Inicio CAPÍTULO:VERSÍCULO, por ejemplo: 9:1")
    parser.add_argument("--to", dest="to_ref", help="Final CAPÍTULO:VERSÍCULO, por ejemplo: 10:33")
    parser.add_argument("--include-unreviewed", action="store_true", help="Incluir filas no marcadas como reviewed_for_manual_use=true")
    parser.add_argument(
        "--raw-notes",
        action="store_true",
        help="Exportar notas canónicas sin traducción de presentación al español",
    )
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()
        dataset_path = root / "datasets" / "suggested-trunk" / f"{book}.jsonl"
        output_path = root / "exports" / "reviewed-trunk" / f"{book}.md"

        _metadata, rows = load_jsonl(dataset_path)
        rows = sort_rows(rows)

        def parse_bound(value: Optional[str]) -> Optional[tuple[int, int]]:
            if not value:
                return None
            chapter, verse = value.split(":", 1)
            return int(chapter), int(verse)

        start = parse_bound(args.from_ref)
        end = parse_bound(args.to_ref)

        filtered = []
        for row in rows:
            key = (int(row.get("chapter", 0)), int(row.get("verse", 0)))
            if start and key < start:
                continue
            if end and key > end:
                continue
            if should_include(row, args.include_unreviewed):
                filtered.append(row)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        title_range = ""
        if args.from_ref or args.to_ref:
            title_range = f" ({args.from_ref or 'inicio'}–{args.to_ref or 'fin'})"

        lines = []
        lines.append(f"# Tronco Revisado — {book}{title_range}")
        lines.append("")
        lines.append(f"Filas exportadas: {len(filtered)}")
        lines.append("")

        current_chapter = None
        for row in filtered:
            chapter = int(row.get("chapter", 0))
            if chapter != current_chapter:
                current_chapter = chapter
                lines.append(f"## Capítulo {chapter}")
                lines.append("")

            reference = row.get("reference")
            confidence = CONFIDENCE_ES.get(str(row.get("confidence")), row.get("confidence"))
            status = STATUS_ES.get(str(row.get("status")), row.get("status"))
            trunk = row.get("trunk_greek") or ""
            notes = row.get("review_notes") or row.get("notes") or ""
            display_notes = notes if args.raw_notes else translate_note_to_spanish(notes)

            lines.append(f"### {reference}")
            lines.append(f"#### Estado: {status} | Confianza: {confidence}")
            lines.append("##### Tronco griego")
            lines.append("```text")
            lines.append(trunk)
            lines.append("```")
            if display_notes:
                lines.append("##### Notas de revisión")
                lines.append(display_notes)
            lines.append("")

        output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

        print("MNA Etapa 4 — Exportar Tronco Revisado a Markdown")
        print(f"LIBRO: {book}")
        print(f"DATASET CANÓNICO: {dataset_path}")
        print(f"SALIDA EN ESPAÑOL: {output_path}")
        print(f"FILAS EXPORTADAS: {len(filtered)}")
        print("NOTAS: español de presentación" if not args.raw_notes else "NOTAS: canónicas sin traducir")
        print("STATUS: PASS")
        return 0

    except Exception as exc:
        print("Falló la exportación del tronco revisado de MNA Etapa 4", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
