from .io import ref


def run(tokens, contrast_pairs, window=12):
    rows=[]
    lemmas=[t.get('lemma') for t in tokens]
    for a,b in contrast_pairs:
        for i,lemma in enumerate(lemmas):
            if lemma != a:
                continue
            end=min(len(tokens), i+window+1)
            for j in range(i+1, end):
                if lemmas[j] == b:
                    rows.append({
                        'type': 'pair', 'pair': [a,b],
                        'from_ref': ref(tokens[i]), 'from_surface': tokens[i].get('surface'),
                        'to_ref': ref(tokens[j]), 'to_surface': tokens[j].get('surface'),
                        'distance_tokens': j-i
                    })
                    break
    return rows
