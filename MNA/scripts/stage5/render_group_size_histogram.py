#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_groups(path: Path):
    rows = []
    with path.open('r', encoding='utf-8') as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get('record_type') == 'stage5_candidate_group':
                rows.append(obj)
    return rows


def bucket(size: int) -> str:
    if size <= 2:
        return '01-02'
    if size <= 5:
        return '03-05'
    if size <= 10:
        return '06-10'
    if size <= 20:
        return '11-20'
    if size <= 40:
        return '21-40'
    return '41+'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('book')
    args = parser.parse_args()

    mna = root()
    path = mna / 'datasets' / 'stage5-test' / args.book / 'candidate-groups.jsonl'
    groups = load_groups(path)

    sizes = [g.get('anchor_count', 0) for g in groups]

    buckets = {
        '01-02': 0,
        '03-05': 0,
        '06-10': 0,
        '11-20': 0,
        '21-40': 0,
        '41+': 0,
    }

    for size in sizes:
        buckets[bucket(size)] += 1

    lines = []
    lines.append(f'# Stage 5 Group Histogram - {args.book}')
    lines.append('')
    lines.append(f'Total Groups: {len(groups)}')
    lines.append(f'Average Size: {round(mean(sizes), 2) if sizes else 0}')
    lines.append('')

    for key, value in buckets.items():
        bar = '#' * value
        lines.append(f'{key:>5} | {bar} {value}')

    out = mna / 'datasets' / 'stage5-test' / args.book / 'group-size-histogram.md'
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(f'WROTE: {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())