# Paleo-Hebrew overview

Investigative work toward OT translation. See [sources/ahrc.md](sources/ahrc.md) for the [Ancient Hebrew Research Center](https://www.ancient-hebrew.org) reference set.

## Script

Paleo-Hebrew (also called Old Hebrew) is the alphabet used for Hebrew before the adoption of the Aramaic (square) script. For digital text, this project uses the Unicode **Phoenician** block because it encodes the same 22 letterforms.

## Workflow

1. Start from square Hebrew — OSHB, MNA OT tokens, or LBF source files.
2. Optionally strip niqqud and cantillation for consonantal display.
3. Map each consonant through `data/letter-map.json`.
4. Publish Paleo output to `output/` or downstream CGV apps.

## Not in scope (yet)

- Semantic translation or spelling changes
- Dividing words differently than the Hebrew source
- Custom font binaries (Unicode text is the interchange format)

## References

- OSHB / MNA Hebrew morphology
- Unicode Phoenician block: U+10900–U+1091F
