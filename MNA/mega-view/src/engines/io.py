import json
from pathlib import Path


def load_tokens(path):
    tokens=[]
    with open(path, encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line:
                tokens.append(json.loads(line))
    return tokens


def ref(tok):
    return f"{tok['ch']}:{tok['vs']}"


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def write_json(path, data):
    ensure_dir(Path(path).parent)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
