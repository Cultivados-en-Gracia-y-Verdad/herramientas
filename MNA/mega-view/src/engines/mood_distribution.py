from collections import Counter
from .morph import is_verb, parse_verb


def run(tokens):
    moods=Counter()
    tenses=Counter()
    voices=Counter()
    for t in tokens:
        if not is_verb(t):
            continue
        p=parse_verb(t.get('morph',''))
        if p.get('mood'): moods[p['mood']] += 1
        if p.get('tense'): tenses[p['tense']] += 1
        if p.get('voice'): voices[p['voice']] += 1
    return {
        'moods': dict(moods.most_common()),
        'tenses': dict(tenses.most_common()),
        'voices': dict(voices.most_common())
    }
