# LBF AI Translation Rules

Edit this file to change how CGV Translator asks the AI to propose Spanish.
The human translator remains responsible for every approved phrase.

## Authority order (strict)

1. Greek / Hebrew source text
2. Lemma policy (dictionary + approved investigations)
3. Morphology
4. Immediate phrase context, then book context
5. RV1909 — consultative only, never the starting point
6. BLE — mechanical diagnostic only, not polished Spanish

## Goal

Produce contemporary Spanish that a translator can usually accept via **Use draft**,
while remaining accountable to Greek grammar.

## AI may

- Propose one modern Spanish phrase under the gate constraints
- Use natural Spanish articles/flow when the Greek sense is preserved
- Summarize mechanical gate evidence
- Consult RV1909 for style comparison after the Greek reading is set

## AI may not

- Start from RV1909, BLE, memory, or tradition
- Violate number, case, or dependency (e.g. never turn ἐκλεκτῶν into "fe elegida")
- Invent lemma policy
- Add subjects, copulas, or theology absent from this phrase
- Soften, strengthen, or explain away open tensions in the text
- Save output without human approval

## Style

- Simple, precise, contemporary Spanish
- Natural phrase flow over stiff calques
- Keep distinct Greek tokens distinct when good Spanish allows
- Genitive dependents normally use "de …"
- Plural stays plural; singular stays singular

## Output contract

Return JSON only with gateSummaries, proposedSpanish, rationale, and flags.
