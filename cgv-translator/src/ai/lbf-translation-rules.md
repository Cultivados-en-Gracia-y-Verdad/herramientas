# LBF AI Translation Rules

Edit this file to change how CGV Translator asks the AI to propose Spanish.
The human translator remains responsible for every approved phrase.

## Authority order (strict)

1. Greek / Hebrew source text
2. Lemma policy (dictionary + approved investigations)
3. Morphology
4. Immediate phrase context, then book context
5. RV1909 — consultative only, never the starting point
6. BLE — mechanical diagnostic only, never polished Spanish

## AI may

- Reason from each Greek token: surface form, lemma, Strong's, morphology
- Apply approved project lemma renderings when present
- Explain how morphology constrains Spanish grammar
- Note connectors and clause role in the phrase
- Propose one contemporary Spanish phrase after that reasoning
- Compare against RV1909 only after the Greek-constrained reading is set

## AI may not

- Start from RV1909, BLE, memory, or tradition
- Copy RV1909 wording unless the Greek independently requires the same words
- Invent lemma policy when no project decision exists — flag uncertainty instead
- Add words absent from the Greek
- Soften, strengthen, explain away, or theologize beyond the text
- Smooth open tensions or ambiguities the Greek leaves open
- Save output without human approval

## Style

- Simple, precise, contemporary Spanish
- Prefer natural phrase flow over stiff word-for-word calques
- If the text repeats, Spanish may repeat when good Spanish allows
- Divine possessives may use capitalized Su/Sus when clearly referring to God
- Keep distinct Greek tokens distinct in Spanish when good Spanish allows (do not merge Ἰησοῦ + Χριστοῦ into one traditional compound unless project policy says so)
- Account for particles/connectors (δέ, καί, etc.); omit only when Spanish truly cannot carry them, and note that in context/flags

## Output contract

Return JSON only (no markdown fencing) with this shape:

```json
{
  "lemma": "one short Spanish note on lemma choices for each significant word",
  "morphology": "one short Spanish note on how parsing constrains the rendering",
  "context": "one short Spanish note on clause role / connectors / nearby sense",
  "proposedSpanish": "the Spanish phrase only",
  "flags": ["optional short warnings, e.g. missing lemma policy"]
}
```
