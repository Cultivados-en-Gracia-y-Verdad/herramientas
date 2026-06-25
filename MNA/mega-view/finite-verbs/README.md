# Mega View — Finite Verbs v3

Targets your actual MorphGNT file format:

```text
100101 V- -PAPDPM- οὖσιν οὖσιν οὖσι(ν) εἰμί
```

Run from repo root:

```bash
python3 MNA/mega-view/finite-verbs/scripts/extract_finite_verbs.py
```

Spanish verb glosses come from:

```text
MNA/datasets/interlinear/NT/efesios.tokens.jsonl
```

The Assertions view starts with blank `subject`, `object`, `notes`, and `confidence`
fields. Browser edits are stored locally. Use **Save JSON** to write
`assertions.json` and **Load JSON** to restore it.

The current Assertions observation scope is Ephesians 1:4–14. Later records
remain in the data but are not presented in the working view yet.

Los códigos RMAC muestran una explicación breve en español al pasar el cursor
o recibir enfoque. Al pulsar un código se abre su desglose de tiempo, voz,
modo, persona y número. La línea de pronombre es una ayuda de memoria
morfológica, no una identificación automática del sujeto.

Las referencias abren el versículo correspondiente del interlineal local en
una ventana dentro del visor.

The Observation Session checklist and notes are also stored locally in the
browser. They remain human-controlled and do not infer completion.

Outputs:

- `MNA/mega-view/finite-verbs/output/finite_verbs.json`
- `MNA/mega-view/finite-verbs/output/finite_verbs_data.js`
- `MNA/mega-view/finite-verbs/output/assertions.json`
- `MNA/mega-view/finite-verbs/output/assertions_data.js`
- `MNA/mega-view/finite-verbs/output/interlinear_data.js`
- `MNA/mega-view/finite-verbs/output/finite_verbs.csv`
- `MNA/mega-view/finite-verbs/output/finite_verbs.md`
- `MNA/mega-view/finite-verbs/output/summary.json`

Finite rule:

```text
POS = V-
morph mood slot = I/S/O/D
```

Excluded:

```text
P = participle
N = infinitive
```
