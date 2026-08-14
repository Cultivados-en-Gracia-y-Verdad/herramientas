# Daniel — G0A Evidence Chain

`promote-g0a-approvals.py` always archives the queue it promoted to the fixed name
`daniel-g0a-final-review.yaml`. That file therefore reflects the **most recent**
promotion, not the whole book. The complete G0A evidence for Daniel is the chain below.

| # | Archive | Items | Artifact reviewed (phrases sha256) | Reviewer | Date |
|---|---------|-------|------------------------------------|----------|------|
| 1 | `daniel-g0a-final-review-20260809T220008Z-full-book.yaml` | 356 | `66c85967a916c007fb8c36a5c825bd2f457b1d2503b7d046f096ba7113ae14a1` | chatgpt-g0a, then esp-hebreo-arameo specialist pass on 7 escalations | 2026-08-09 |
| 2 | `daniel-g0a-rereview-2-39-20260813.yaml` | 1 (Daniel 2:39) | `b338d84ac2cbb74ffee1b5d01cfbc3e8da8c463fffd6d3125890ce8e99658198` | claude-g0a (cowork / claude-opus-5) | 2026-08-13 |

Archive 1 covers 356 of 357 phrase records. The 357th (Daniel 2:39) was already
`lbf-approved` before that queue was generated, was subsequently re-approved inside
archive 1, and was then reopened on 2026-08-13 when its Spanish changed
(«tercer reino de metal» → «tercer reino de bronce», נְחָשָׁא / H5174).
Archive 2 closes that reopening under targeted invalidation
(TRANSLATOR_GATE0_CONTRACT.md, "Translator edit compatibility").

Union of archives 1 and 2 = all 357 phrase records reviewed and APPROVED.

## Artifact lineage

```
66c85967…  phrase map as reviewed in archive 1
    ↓ promotion 2026-08-09T22:00:08Z (356 records → lbf-approved)
f5c7ce0d…
    ↓ translator edit 2026-08-13T13:49:58Z (Daniel 2:39 Spanish; 2:39 → lbf-preliminary)
b338d84a…  phrase map as reviewed in archive 2
    ↓ promotion 2026-08-13T20:35:07Z (Daniel 2:39 → lbf-approved)
1e3b0db7fd0d9d3aa6cf17377762ba334089dc914a467a1ce5a68b791e18ef43   ← current
```

Backups: `daniel-phrases.pre-g0a-promotion-20260809T220008Z.json`,
`daniel-phrases.pre-g0a-promotion-20260813T203507Z.json`.

## Open finding carried to the book-level final check

Daniel 2:39 is now the only place in the book where H5174 is rendered «bronce».
The same lemma still reads «metal» in **2:32, 2:35, 2:45, 5:4, 5:23, 7:19** —
and 2:32 / 2:35 / 2:45 describe the same statue as 2:39. This is a WORKFLOW.md §17
consistency decision, not a defect in 2:39. Revising any of those six verses
returns each of them to G0A.
