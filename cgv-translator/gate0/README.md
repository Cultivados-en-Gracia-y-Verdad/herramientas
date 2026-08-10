# CGV Gate 0 Review Runner

The review runner processes G0A and G0B queues without modifying Translator artifacts.

## What it does

1. Extracts the next pending batch into a reviewer packet.
2. Records reviewer decisions from a completed result packet.
3. Validates allowed decisions.
4. Requires evidence for `APPROVED` / `VERIFIED`.
5. Requires notes for revision/relink/rejection/escalation decisions.
6. Updates queue summary and queue status.
7. Preserves review history.

It does **not**:
- modify `daniel-phrases.json`;
- modify `daniel-reverse-links.json`;
- mark Translator records approved;
- decide whether an AI review is sufficient for human approval.

## G0A decisions

```text
APPROVED
NEEDS_REVISION
REJECTED
ESCALATE
```

## G0B decisions

```text
VERIFIED
NEEDS_RELINK
REJECTED
ESCALATE
```

## Create a batch

```bash
python3 gate0/review-runner.py packet   --queue gate0/queues/daniel-g0a-translation-review.yaml   --batch-size 10   --out gate0/review-packets/daniel-g0a-batch-001.yaml
```

For G0B:

```bash
python3 gate0/review-runner.py packet   --queue gate0/queues/daniel-g0b-alignment-review.yaml   --batch-size 20   --out gate0/review-packets/daniel-g0b-batch-001.yaml
```

## Reviewer output

The reviewer fills a result file with the same item IDs:

```yaml
packet:
  queue_id: daniel-G0A
  gate: G0A_TRANSLATION_APPROVAL
  book: daniel

items:
  - id: G0A-0001
    decision: APPROVED
    confidence: high
    evidence: "Spanish accounts for the supplied source span without omission."
    notes: ""
```

## Apply results

```bash
python3 gate0/review-runner.py apply   --queue gate0/queues/daniel-g0a-translation-review.yaml   --results gate0/review-results/daniel-g0a-batch-001-results.yaml   --reviewer esp-traduccion   --runtime claude-code   --model sonnet
```

## Check progress

```bash
python3 gate0/review-runner.py status   --queue gate0/queues/daniel-g0a-translation-review.yaml
```

A queue reaches `PASS` only when every item has the positive decision required by that gate and there are no pending/revision/relink/rejected/escalated items.
