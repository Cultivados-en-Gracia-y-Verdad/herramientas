# CGV Data Contract v0.1

This is the first minimal bridge from cgv-translator to cgv-data for Greek NT occurrence gathering.

## Translator Query

Given a Greek Strong's number:

```text
G1401
```

cgv-translator needs cgv-data to return occurrence records for that Strong's number.

## Minimal Occurrence Record

Each occurrence record must provide:

- `reference`: readable verse reference, for example `Matthew 8:9`
- `surfaceForm`: Greek form in the verse, for example `δούλῳ`
- `lemma`: Greek lemma, for example `δοῦλος`
- `strongs`: Strong's number, for example `G1401`
- `morphology`: morphology/parsing code when available
- `greekText`: Greek verse text or clause context when available

## Current cgv-data Findings

cgv-data currently has:

- TR1894 Greek NT verse text at `bibles/TR1894/tr1894.txt`
- MorphGNT SBLGNT Greek NT morphology and token text files at `morphology/MorphGNT/*-morphgnt.txt`
- verse references inside MorphGNT rows as six-digit book/chapter/verse IDs
- lemma and morphology columns inside MorphGNT rows
- Spanish USFX text with Strong's tags at `bibles/SPNBES/spa-bes.usfx.xml`

cgv-data does not currently expose a general Greek NT Strong's-to-lemma occurrence index for MorphGNT. The first translator bridge supports `G1401` by using the known prototype mapping `G1401 -> δοῦλος`, then reads the real MorphGNT SBLGNT files.

For occurrence evidence, cgv-translator should treat SBLGNT via MorphGNT as the NT source basis because the lemma and morphology are tied to those token rows. TR1894 can remain available in cgv-data, but mixing TR1894 verse text with SBLGNT morphology would make the evidence source ambiguous.

## Required Published Shape

For general use beyond `G1401`, cgv-data should publish one stable file or folder that lets consumers resolve a Greek Strong's number to occurrence records without app-specific hardcoding. A future version could be:

```text
greek/nt/occurrences-by-strongs/G1401.json
```

with records shaped like:

```json
{
  "reference": "Matthew 8:9",
  "surfaceForm": "δούλῳ",
  "lemma": "δοῦλος",
  "strongs": "G1401",
  "morphology": "N- ----DSM-",
  "greekText": "..."
}
```
