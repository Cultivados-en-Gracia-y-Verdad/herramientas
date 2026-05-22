#!/usr/bin/env python3

CONNECTOR_NORMALIZATION_MAP = {
    "Εἰ": "εἰ",
    "εἴ": "εἰ",
    "Εἴ": "εἰ",
    "⸀εἴ": "εἰ",
    "⸂εἴ": "εἰ",
    "⸀Εἰ": "εἰ",
    "Ἐὰν": "ἐὰν",
    "ἐάν": "ἐὰν",
    "⸀ἐὰν": "ἐὰν",
    "ἐὰν⸃": "ἐὰν",
    "ἐὰν⸅": "ἐὰν",
    "Ὅτι": "ὅτι",
    "Ὥστε": "ὥστε",
    "Ὥστε,": "ὥστε",
    "ὥστε,": "ὥστε",
    "Εἴτε": "εἴτε",
    "⸀εἴτε": "εἴτε",
    "καθώς": "καθὼς",
    "⸀καθώς": "καθὼς",
    "Καθάπερ": "καθάπερ",
    "⸀καθάπερ": "καθάπερ",
    "Ἐπεὶ": "ἐπεὶ",
    "⸀ὅτε": "ὅτε",
}


def normalize_connector(connector):
    if connector is None:
        return None
    connector = str(connector).strip()
    return CONNECTOR_NORMALIZATION_MAP.get(connector, connector)
