from .io import ref
from .morph import is_imperative, parse_verb


def run(tokens):
    rows=[]
    for t in tokens:
        if is_imperative(t):
            p=parse_verb(t.get('morph',''))
            rows.append({
                'ref': ref(t), 'tok': t.get('tok'), 'surface': t.get('surface'),
                'lemma': t.get('lemma'), 'morph': t.get('morph'), 'tense': p.get('tense'),
                'voice': p.get('voice'), 'person': p.get('person'), 'number': p.get('number'),
                'es': t.get('es')
            })
    return rows
