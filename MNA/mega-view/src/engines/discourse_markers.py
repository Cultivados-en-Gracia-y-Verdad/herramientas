from .io import ref


def run(tokens, markers):
    rows=[]
    for t in tokens:
        lemma=t.get('lemma')
        if lemma in markers:
            rows.append({
                'ref': ref(t), 'tok': t.get('tok'), 'surface': t.get('surface'),
                'lemma': lemma, 'category': markers[lemma], 'es': t.get('es')
            })
    return rows
