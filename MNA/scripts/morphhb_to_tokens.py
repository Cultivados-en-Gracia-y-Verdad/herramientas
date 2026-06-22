#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path
import xml.etree.ElementTree as ET

OSIS_NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag

def parse_osis_id(osis_id: str):
    # e.g. "Gen.1.3"
    parts = osis_id.split(".")
    if len(parts) < 3:
        return None
    book = parts[0]
    ch = int(parts[1])
    vs = int(parts[2])
    return book, ch, vs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--book", required=True)   # output slug, e.g. genesis
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # streaming parse
    current_book = None
    current_ch = None
    current_vs = None
    w_in_verse = 0

    with out.open("w", encoding="utf-8") as f_out:
        context = ET.iterparse(str(src), events=("start", "end"))
        for event, el in context:
            tag = strip_ns(el.tag)

            if event == "start" and tag == "div" and el.get("type") == "book":
                current_book = el.get("osisID")

            elif event == "start" and tag == "chapter":
                # chapter osisID="Gen.1"
                pass

            elif event == "start" and tag == "verse":
                # verse osisID="Gen.1.1"
                parsed = parse_osis_id(el.get("osisID", ""))
                if parsed:
                    current_book, current_ch, current_vs = parsed
                    w_in_verse = 0

            elif event == "end" and tag == "w":
                if current_book is None or current_ch is None or current_vs is None:
                    el.clear()
                    continue

                w_in_verse += 1
                surface = (el.text or "").strip()
                lemma = (el.get("lemma") or "").strip()
                morph = (el.get("morph") or "").strip()
                wid = (el.get("id") or "").strip()

                # Output shape mirrors your NT tokens: keep it simple.
                row = {
                    "book": args.book,          # spanish/slug you control
                    "ref_book": current_book,   # OSIS book code (Gen, Exod…)
                    "ch": current_ch,
                    "vs": current_vs,
                    "w": w_in_verse,
                    "surface": surface,
                    "lemma": lemma,
                    "morph": morph,
                    "id": wid,
                    "es": "?",                  # to be filled by rules
                }
                f_out.write(json.dumps(row, ensure_ascii=False) + "\n")

                el.clear()

            # clear other tags to keep memory low
            if event == "end":
                el.clear()

if __name__ == "__main__":
    main()