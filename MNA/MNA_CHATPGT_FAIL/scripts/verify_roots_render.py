#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_DATASETS = {
    'predications': 'data/predications/{book}-predications.jsonl',
    'connectors': 'data/connectors/{book}-connectors.jsonl',
    'paso8': 'data/paso8-trunk/{book}-paso8-trunk.jsonl',
    'paso9': 'data/paso9-support/{book}-paso9-support.jsonl',
    'movement': 'data/movement/{book}-movement.jsonl',
}


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict]:
    rows = []

    if not path.exists():
        return rows

    with path.open('r', encoding='utf-8') as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except Exception:
                print(f'FAIL {path}:{lineno}: invalid json')

    return rows


def index(rows: list[dict]) -> set[str]:
    out = set()

    for row in rows:
        key = str(
            row.get('predication_id')
            or row.get('stream_index')
            or row.get('id')
            or ''
        )

        if key:
            out.add(key)

    return out


def main() -> None:
    if len(sys.argv) != 2:
        print('Usage: python3 MNA/scripts/verify_roots_render.py <book>')
        sys.exit(2)

    book = sys.argv[1].lower()

    loaded = {}

    for name, template in REQUIRED_DATASETS.items():
        path = root() / template.format(book=book)

        if not path.exists():
            print(f'FAIL missing dataset: {path}')
            continue

        rows = read_jsonl(path)
        loaded[name] = rows

        print(f'PASS {name}: {len(rows)} rows')

    if 'predications' not in loaded:
        print('FAIL no predications dataset')
        sys.exit(1)

    predication_keys = index(loaded['predications'])

    for name, rows in loaded.items():
        if name == 'predications':
            continue

        keys = index(rows)
        missing = sorted(predication_keys - keys)

        if missing:
            print(f'WARN {name}: missing mappings = {len(missing)}')
            print('FIRST 10:')
            for value in missing[:10]:
                print(f'  - {value}')
        else:
            print(f'PASS {name}: full coverage')

    print('DONE')


if __name__ == '__main__':
    main()
