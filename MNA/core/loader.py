def load_sblgnt(path):
    data = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("---"):
                continue

            parts = line.split(maxsplit=2)

            if len(parts) < 3:
                continue

            book = parts[0].lower()
            ref = parts[1]
            text = parts[2].strip()

            key = f"{book} {ref}"
            data[key] = text.split()

    return data


def load_nbla(path):
    data = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("---"):
                continue

            parts = line.split(maxsplit=2)

            if len(parts) < 3:
                continue

            book = parts[0].lower()
            ref = parts[1]
            text = parts[2].strip()

            key = f"{book} {ref}"
            data[key] = text

    return data