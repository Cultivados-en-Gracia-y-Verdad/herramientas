from collections import defaultdict, Counter
from .io import ref
from .morph import is_verb, parse_verb

STRONG_MARKERS={'οὖν','διό','διόπερ','ἄρα','ὥστε'}
QUESTION_LEMMAS={'τίς','τί','πῶς','ποῦ','πότε','ποῖος','πόσος'}


def verse_key(t):
    return (t['ch'], t['vs'])


def run(tokens, markers):
    byverse=defaultdict(list)
    for t in tokens:
        byverse[verse_key(t)].append(t)
    rows=[]
    prev_mood_major=None
    for key in sorted(byverse):
        verse=byverse[key]
        signals=[]
        marker_hits=[t.get('lemma') for t in verse if t.get('lemma') in markers]
        strong=[m for m in marker_hits if m in STRONG_MARKERS]
        if strong:
            signals.append({'signal':'strong discourse marker','value':strong})
        if len(marker_hits) >= 3:
            signals.append({'signal':'marker density','value':len(marker_hits)})
        verb_moods=[]
        imperatives=[]
        for t in verse:
            if is_verb(t):
                m=parse_verb(t.get('morph','')).get('mood')
                if m:
                    verb_moods.append(m)
                if m == 'imperative':
                    imperatives.append(t.get('lemma'))
        if imperatives:
            signals.append({'signal':'imperative present','value':imperatives})
        mood_counts=Counter(verb_moods)
        major='imperative' if mood_counts.get('imperative') else ('indicative' if mood_counts.get('indicative') else None)
        if prev_mood_major and major and major != prev_mood_major:
            signals.append({'signal':'mood shift','value':f'{prev_mood_major} → {major}'})
        if major:
            prev_mood_major=major
        vocatives=[t.get('surface') for t in verse if len(t.get('morph',''))>7 and t.get('morph','')[6]=='V']
        if vocatives:
            signals.append({'signal':'vocative present','value':vocatives})
        questions=[t.get('surface') for t in verse if t.get('lemma') in QUESTION_LEMMAS or ';' in t.get('surface','')]
        if questions:
            signals.append({'signal':'question signal','value':questions})
        if signals:
            rows.append({'ref':f'{key[0]}:{key[1]}','signals':signals,'score':len(signals)})
    return rows
