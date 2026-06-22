from collections import Counter, defaultdict
from .io import ref


def run(tokens, stop_lemmas=None, min_count=2, top=100):
    stop=set(stop_lemmas or [])
    counts=Counter(t.get('lemma') for t in tokens if t.get('lemma') and t.get('lemma') not in stop)
    refs=defaultdict(list)
    seen=set()
    for t in tokens:
        lemma=t.get('lemma')
        if not lemma or lemma in stop:
            continue
        r=ref(t)
        key=(lemma,r)
        if key not in seen:
            refs[lemma].append(r)
            seen.add(key)
    rows=[]
    for lemma,count in counts.most_common(top):
        if count >= min_count:
            rows.append({'lemma': lemma, 'count': count, 'refs': refs[lemma][:25]})
    return rows
