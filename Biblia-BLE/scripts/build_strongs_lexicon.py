#!/usr/bin/env python3
"""Build a compact Spanish Strong's lexicon JSON for the BLE web reader.

Primary definitions: Spanish Strong's e-Sword dictionary (.dctx)
  (Diccionario Strong en español)

Supplementary metadata:
  - Open Scriptures HebrewStrong.xml + Greek dictionary → xlit / lemma
  - MNA lemma glosses → short Spanish gloss (es)

Output:
  Biblia-BLE/reader/strongs.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MNA = ROOT.parent / "MNA"
HEBREW_XML = MNA / "datasets" / "rules" / "sources" / "HebrewStrong.xml"
HBO_ES = MNA / "datasets" / "rules" / "hbo_lemma_lexicon.json"
GRC_ES = MNA / "datasets" / "rules" / "grc_lemma_lexicon.json"
GRC_STRONGS = MNA / "datasets" / "rules" / "grc_lemma_strongs.json"
DEFAULT_OUT = ROOT / "reader" / "strongs.json"
CACHE_DIR = ROOT / "reader" / ".cache"
SPANISH_DCTX_CACHE = CACHE_DIR / "strong-es.dctx"
GREEK_JS_URL = (
    "https://raw.githubusercontent.com/openscriptures/strongs/"
    "master/greek/strongs-greek-dictionary.js"
)
GREEK_CACHE = CACHE_DIR / "strongs-greek-dictionary.js"

NS = {"os": "http://openscriptures.github.com/morphhb/namespace"}
WS_RE = re.compile(r"\s+")
HEX_ESC_RE = re.compile(r"\\'([0-9a-fA-F]{2})")
UNI_ESC_RE = re.compile(r"\\u(-?\d+)\?")
CTRL_RE = re.compile(
    r"\\([a-zA-Z]+)(-?\d+)?[ ]?"  # \word or \wordN
    r"|\\[^a-zA-Z0-9]"  # \' etc. already handled; leftover single-char
    r"|[{}]"
)
PAR_RE = re.compile(r"\\par[d]?|\\line", re.I)


def clean(text: str | None) -> str:
    if not text:
        return ""
    return WS_RE.sub(" ", text).strip()


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def find_default_spanish_dctx() -> Path | None:
    if SPANISH_DCTX_CACHE.is_file():
        return SPANISH_DCTX_CACHE
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        for p in sorted(downloads.glob("Strong*.dctx")):
            # Prefer the Spanish-titled module over encrypted English Strong.
            try:
                con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
                desc = con.execute("SELECT Description FROM Details").fetchone()
                con.close()
                if desc and "español" in desc[0].lower().replace("espanol", "español"):
                    return p
                if desc and "españ" in desc[0].lower():
                    return p
                if desc and "espanol" in desc[0].lower():
                    return p
            except sqlite3.Error:
                continue
        # Fallback: any Strong*.dctx whose first definition looks like RTF Spanish
        for p in sorted(downloads.glob("Strong*.dctx")):
            try:
                con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
                row = con.execute(
                    "SELECT Definition FROM Dictionary WHERE Topic='H1'"
                ).fetchone()
                con.close()
                if row and isinstance(row[0], str) and "padre" in row[0].lower():
                    return p
            except sqlite3.Error:
                continue
    return None


def rtf_to_text(rtf: str) -> str:
    """Best-effort RTF → plain text for Spanish Strong entries."""
    if not rtf:
        return ""
    text = rtf.replace("\r\n", "\n").replace("\r", "\n")
    text = PAR_RE.sub("\n", text)

    def hex_repl(m: re.Match[str]) -> str:
        try:
            return bytes.fromhex(m.group(1)).decode("cp1252", errors="replace")
        except ValueError:
            return ""

    text = HEX_ESC_RE.sub(hex_repl, text)

    def uni_repl(m: re.Match[str]) -> str:
        code = int(m.group(1))
        if code < 0:
            code = 65536 + code
        try:
            return chr(code)
        except ValueError:
            return ""

    text = UNI_ESC_RE.sub(uni_repl, text)
    text = CTRL_RE.sub("", text)
    text = html.unescape(text)
    text = text.replace("\x00", "")
    # Collapse whitespace but keep paragraph breaks as spaces
    text = WS_RE.sub(" ", text).strip(" \n\t;")
    return text


def split_def_usage(plain: str) -> tuple[str, str, str]:
    """Return (translit_guess, definition, usage) from Spanish Strong plain text."""
    text = plain
    # Usage follows ":-" (Spanish modules) or ":--"
    usage = ""
    m = re.search(r"\s*:--?\s*", text)
    if m:
        usage = clean(text[m.end() :])
        text = clean(text[: m.start()])

    # First token is often Hebrew/Greek glyphs; second often Latin translit.
    # Keep a short Latin-looking headword when present.
    translit = ""
    parts = text.split(" ", 2)
    if len(parts) >= 2 and re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÜüÑñ''`´\-]+", parts[1]):
        translit = parts[1]
        body = parts[2] if len(parts) > 2 else ""
    elif len(parts) >= 1 and re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÜüÑñ''`´\-]+", parts[0]):
        translit = parts[0]
        body = parts[1] if len(parts) > 1 else (parts[2] if len(parts) > 2 else "")
        if len(parts) == 3:
            body = f"{parts[1]} {parts[2]}"
        elif len(parts) == 2:
            body = parts[1]
        else:
            body = ""
    else:
        # Drop leading non-Latin run (original script), keep the rest.
        body = re.sub(r"^[^\x00-\x7FÁÉÍÓÚáéíóúÜüÑñ]+", "", text).strip()
        # If translit still leads body
        m2 = re.match(r"^([A-Za-zÁÉÍÓÚáéíóúÜüÑñ''`´\-]+)\s+(.*)$", body)
        if m2:
            translit = m2.group(1)
            body = m2.group(2)

    return translit, clean(body), usage


def hebrew_es_lookup(hbo: dict[str, str], strongs_id: str) -> str:
    raw = strongs_id.upper()
    if not raw.startswith("H"):
        return ""
    body = raw[1:]
    m = re.fullmatch(r"(\d+)([A-Z]?)", body)
    if not m:
        return hbo.get(body.lower(), "") or hbo.get(body, "")
    num, letter = m.group(1), m.group(2).lower()
    if letter:
        for key in (f"{num} {letter}", f"{num}{letter}", f"{num} {letter.upper()}"):
            if key in hbo:
                return hbo[key]
    if num in hbo:
        return hbo[num]
    for key in (f"{num} a", f"{num} b", f"{num}a", f"{num}b"):
        if key in hbo:
            return hbo[key]
    return ""


def greek_es_by_strongs(grc_es: dict[str, str], lemma_to_s: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for lemma, sid in lemma_to_s.items():
        gloss = grc_es.get(lemma)
        if not gloss:
            continue
        out.setdefault(sid.upper(), gloss)
    return out


def parse_spanish_dctx(dctx: Path) -> dict[str, dict]:
    con = sqlite3.connect(f"file:{dctx}?mode=ro", uri=True)
    rows = con.execute("SELECT Topic, Definition FROM Dictionary").fetchall()
    con.close()
    entries: dict[str, dict] = {}
    for topic, definition in rows:
        if not topic or not isinstance(definition, str):
            continue
        key = str(topic).strip().upper()
        if not re.fullmatch(r"[HG]\d+[A-Z]?", key):
            continue
        plain = rtf_to_text(definition)
        translit, def_text, usage = split_def_usage(plain)
        rec: dict[str, str] = {}
        if translit:
            rec["xlit"] = translit
        if def_text:
            rec["def"] = def_text
        if usage:
            rec["usage"] = usage
        if rec:
            entries[key] = rec
    return entries


def meta_hebrew(xml_path: Path) -> dict[str, dict]:
    if not xml_path.is_file():
        return {}
    tree = ET.parse(xml_path)
    root = tree.getroot()
    out: dict[str, dict] = {}
    for entry in root.findall("os:entry", NS):
        eid = entry.get("id")
        if not eid:
            continue
        w = entry.find("os:w", NS)
        rec: dict[str, str] = {}
        if w is not None:
            if w.get("xlit"):
                rec["xlit"] = w.get("xlit") or ""
            if w.get("pron"):
                rec["pron"] = w.get("pron") or ""
            lemma = clean("".join(w.itertext()))
            if lemma:
                rec["lemma"] = lemma
        if rec:
            out[eid.upper()] = rec
    return out


def fetch_greek_js(cache: Path, url: str) -> str:
    if cache.is_file():
        return cache.read_text(encoding="utf-8")
    cache.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as resp:
        text = resp.read().decode("utf-8")
    cache.write_text(text, encoding="utf-8")
    return text


def meta_greek(text: str) -> dict[str, dict]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        return {}
    data = json.loads(text[start : end + 1])
    out: dict[str, dict] = {}
    for sid, raw in data.items():
        if not isinstance(raw, dict):
            continue
        rec: dict[str, str] = {}
        lemma = clean(raw.get("lemma"))
        xlit = clean(raw.get("translit"))
        if lemma:
            rec["lemma"] = lemma
        if xlit:
            rec["xlit"] = xlit
        if rec:
            out[sid.upper()] = rec
    return out


def merge_entry(
    spanish: dict[str, str] | None,
    meta: dict[str, str] | None,
    gloss_es: str,
) -> dict[str, str]:
    rec: dict[str, str] = {}
    spanish = spanish or {}
    meta = meta or {}
    # Prefer Open Scriptures transliteration when available; else Spanish module.
    if meta.get("xlit"):
        rec["xlit"] = meta["xlit"]
    elif spanish.get("xlit"):
        rec["xlit"] = spanish["xlit"]
    if meta.get("pron"):
        rec["pron"] = meta["pron"]
    if meta.get("lemma"):
        rec["lemma"] = meta["lemma"]
    if gloss_es:
        rec["es"] = gloss_es
    if spanish.get("def"):
        rec["def"] = spanish["def"]
    if spanish.get("usage"):
        rec["usage"] = spanish["usage"]
    return rec


def build(
    out: Path,
    *,
    spanish_dctx: Path | None = None,
    refresh_greek: bool = False,
) -> dict[str, int]:
    dctx = spanish_dctx or find_default_spanish_dctx()
    if dctx is None or not dctx.is_file():
        raise SystemExit(
            "Spanish Strong's .dctx not found. Pass --spanish-dctx PATH "
            "(e.g. Downloads/Strong (Esp) Diccionario Strong en Español.dctx)"
        )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if dctx.resolve() != SPANISH_DCTX_CACHE.resolve():
        shutil.copy2(dctx, SPANISH_DCTX_CACHE)
        dctx = SPANISH_DCTX_CACHE

    hbo_es = load_json(HBO_ES)
    grc_es = load_json(GRC_ES)
    lemma_to_s = load_json(GRC_STRONGS)
    grc_es_map = greek_es_by_strongs(grc_es, lemma_to_s)

    spanish = parse_spanish_dctx(dctx)
    heb_meta = meta_hebrew(HEBREW_XML)

    if refresh_greek and GREEK_CACHE.is_file():
        GREEK_CACHE.unlink()
    try:
        greek_text = fetch_greek_js(GREEK_CACHE, GREEK_JS_URL)
        grc_meta = meta_greek(greek_text)
    except Exception:
        grc_meta = {}

    lex: dict[str, dict] = {}
    all_keys = set(spanish) | set(heb_meta) | set(grc_meta)
    for key in sorted(all_keys):
        gloss = ""
        if key.startswith("H"):
            gloss = hebrew_es_lookup(hbo_es, key)
            meta = heb_meta.get(key)
        else:
            gloss = grc_es_map.get(key, "")
            meta = grc_meta.get(key)
        rec = merge_entry(spanish.get(key), meta, gloss)
        if rec.get("def") or rec.get("es"):
            lex[key] = rec

    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "Diccionario Strong en español; xlit/lemma Open Scriptures; glosas MNA",
        "lang": "es",
        "entries": lex,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    he = sum(1 for k in lex if k.startswith("H"))
    ge = sum(1 for k in lex if k.startswith("G"))
    return {"hebrew": he, "greek": ge, "total": len(lex), "bytes": out.stat().st_size, "dctx": str(dctx)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Spanish reader/strongs.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--spanish-dctx", type=Path, default=None)
    parser.add_argument("--refresh-greek", action="store_true")
    args = parser.parse_args()
    stats = build(args.out, spanish_dctx=args.spanish_dctx, refresh_greek=args.refresh_greek)
    print(f"wrote {args.out}")
    print(f"  source: {stats['dctx']}")
    print(f"  Hebrew: {stats['hebrew']}")
    print(f"  Greek:  {stats['greek']}")
    print(f"  total:  {stats['total']}")
    print(f"  size:   {stats['bytes'] / 1024:.0f} KB")
    # sanity samples
    data = json.loads(args.out.read_text(encoding="utf-8"))["entries"]
    for k in ("H430", "G26"):
        print(f"  sample {k}: {data.get(k)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
