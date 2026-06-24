# BLE verse file format

Compatible with `cgv-bible` `parseNblaContent()` and CGV library layout.

## File naming

```text
{book_slug}.ble.md
```

Examples: `mateo.ble.md`, `1corintios.ble.md`, `filemon.ble.md`

## Line format

```text
{BookLabel} {chapter}:{verse} {literal_spanish_text}
```

- **BookLabel** — display name (`Mateo`, `1corintios`, …). Numbered epistles keep the slug prefix.
- **chapter**, **verse** — integers, no leading zeros required.
- **literal_spanish_text** — space-joined token glosses; mid-dots expanded to spaces.

## Assembly rules

1. Tokens grouped by `(book, ch, vs)`, ordered by `tok`.
2. Each `es` gloss: replace `·` with a single space.
3. Join glosses with a single space (punctuation stays on the gloss that carries it).
4. Skip tokens with missing or `?` gloss (should not occur in export-ready builds).

## Example

Tokens (Mateo 1:1, abbreviated):

| tok | es |
|----:|-----|
| 1 | libro |
| 2 | de·genealogía |
| 3 | de·Jesús |
| 8 | de·Abraham. |

Verse line:

```text
Mateo 1:1 libro de genealogía de Jesús … de Abraham.
```

## Library install

```text
{CGV_LIBRARY_ROOT}/bibles/BLE/mateo.ble.md
```

CGV Writer lists `BLE` as a version when `*.ble.md` files are present.
