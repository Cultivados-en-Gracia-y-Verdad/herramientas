def load_morphgnt(path):
    data = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) < 5:
                continue

            ref = parts[0]
            pos = parts[1]
            parsing = parts[2]
            greek = parts[3]

            # MorphGNT often has several Greek columns.
            # The lemma is safest as the LAST column.
            lemma = parts[-1]

            code = f"{pos}{parsing}"

            if ref not in data:
                data[ref] = []

            data[ref].append((greek, code, lemma))

    return data