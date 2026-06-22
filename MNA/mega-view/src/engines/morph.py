"""Helpers for MorphGNT-style morphology tags used in CGV interlinear files."""

TENSE = {
    'P': 'present', 'I': 'imperfect', 'F': 'future', 'A': 'aorist',
    'X': 'perfect', 'Y': 'pluperfect'
}
VOICE = {'A': 'active', 'M': 'middle', 'P': 'passive'}
MOOD = {
    'I': 'indicative', 'D': 'imperative', 'S': 'subjunctive', 'O': 'optative',
    'N': 'infinitive', 'P': 'participle'
}
PERSON = {'1': '1st', '2': '2nd', '3': '3rd'}
NUMBER = {'S': 'singular', 'P': 'plural'}
CASE = {'N': 'nominative', 'G': 'genitive', 'D': 'dative', 'A': 'accusative', 'V': 'vocative'}
GENDER = {'M': 'masculine', 'F': 'feminine', 'N': 'neuter'}


def is_verb(tok):
    return tok.get('morph', '').startswith('V')


def parse_verb(morph):
    """Parse common MorphGNT verb positions: V-3AAI-S-- / V--AAPNSM-."""
    if not morph or not morph.startswith('V'):
        return {}
    def ch(i):
        return morph[i] if len(morph) > i else '-'
    return {
        'person': PERSON.get(ch(2), None),
        'tense': TENSE.get(ch(3), None),
        'voice': VOICE.get(ch(4), None),
        'mood': MOOD.get(ch(5), None),
        'case': CASE.get(ch(6), None),
        'number': NUMBER.get(ch(7), None),
        'gender': GENDER.get(ch(8), None),
    }


def is_imperative(tok):
    return is_verb(tok) and parse_verb(tok.get('morph', '')).get('mood') == 'imperative'
