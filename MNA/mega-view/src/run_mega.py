#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from engines.io import load_tokens, write_json, ensure_dir
from engines import repeated_lemmas, discourse_markers, mood_distribution, imperatives, contrast_markers, boundary_signals


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def md_table(rows, columns, limit=None):
    if limit:
        rows = rows[:limit]
    if not rows:
        return '_None found._\n'
    out=[]
    out.append('| ' + ' | '.join(columns) + ' |')
    out.append('| ' + ' | '.join(['---']*len(columns)) + ' |')
    for r in rows:
        vals=[]
        for c in columns:
            v=r.get(c,'')
            if isinstance(v, list):
                v=', '.join(map(str,v))
            if isinstance(v, dict):
                v=json.dumps(v, ensure_ascii=False)
            vals.append(str(v).replace('|','\\|'))
        out.append('| ' + ' | '.join(vals) + ' |')
    return '\n'.join(out)+'\n'


def write_markdown(path, book, results):
    lines=[f'# Mega View: {book}', '', 'Generated from interlinear token data. These are observable signals, not an outline or interpretation.', '']
    lines.append('## Mood Distribution')
    for group, counts in results['mood_distribution'].items():
        lines.append(f'### {group.title()}')
        lines.append(md_table([{'item':k,'count':v} for k,v in counts.items()], ['item','count']))
    lines.append('## Imperatives')
    lines.append(md_table(results['imperatives'], ['ref','surface','lemma','morph','es'], limit=100))
    lines.append('## Discourse Markers')
    lines.append(md_table(results['discourse_markers'], ['ref','surface','lemma','category','es'], limit=200))
    lines.append('## Repeated Lemmas')
    rep=[]
    for r in results['repeated_lemmas'][:100]:
        rep.append({'lemma':r['lemma'], 'count':r['count'], 'refs':', '.join(r['refs'][:12])})
    lines.append(md_table(rep, ['lemma','count','refs']))
    lines.append('## Contrast Markers / Pairs')
    lines.append(md_table(results['contrast_markers'], ['pair','from_ref','from_surface','to_ref','to_surface','distance_tokens'], limit=100))
    lines.append('## Possible Boundary Signals')
    b=[]
    for r in results['boundary_signals']:
        if r['score'] < 2:
        continue
        b.append({'ref':r['ref'], 'score':r['score'], 'signals':'; '.join(f"{s['signal']}: {s['value']}" for s in r['signals'])})
    lines.append(md_table(b, ['ref','score','signals'], limit=150))
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    ap=argparse.ArgumentParser(description='Generate Mega View observable signals from CGV interlinear tokens.')
    ap.add_argument('book', help='Book slug, e.g. efesios')
    ap.add_argument('--data-dir', default=str(ROOT.parent/'datasets'/'interlinear'/'NT'))
    ap.add_argument('--out-dir', default=str(ROOT/'output'))
    args=ap.parse_args()

    data_path=Path(args.data_dir)/f'{args.book}.tokens.jsonl'
    out_dir=Path(args.out_dir)/args.book
    ensure_dir(out_dir)

    tokens=load_tokens(data_path)
    markers=load_json(ROOT/'src'/'config'/'discourse_markers.json')
    contrasts=load_json(ROOT/'src'/'config'/'contrast_pairs.json')
    stops=load_json(ROOT/'src'/'config'/'stop_lemmas.json')

    results={
        'book': args.book,
        'token_count': len(tokens),
        'mood_distribution': mood_distribution.run(tokens),
        'imperatives': imperatives.run(tokens),
        'discourse_markers': discourse_markers.run(tokens, markers),
        'repeated_lemmas': repeated_lemmas.run(tokens, stops),
        'contrast_markers': contrast_markers.run(tokens, contrasts),
        'boundary_signals': boundary_signals.run(tokens, markers),
    }

    for key,value in results.items():
        if key in {'book','token_count'}:
            continue
        write_json(out_dir/f'{key}.json', value)
    write_json(out_dir/'mega_view.json', results)
    write_markdown(out_dir/'mega_view.md', args.book, results)
    print(f'Wrote Mega View for {args.book} to {out_dir}')

if __name__ == '__main__':
    main()
