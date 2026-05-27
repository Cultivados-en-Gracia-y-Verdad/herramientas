# MNA SYSTEM RULES

## 1. Scope

MNA is only a mechanical alignment system.

It does not produce:
- verbs
- clauses
- connectors
- structure
- interpretation
- teaching material

## 2. Inputs

- SBLGNT Greek token stream
- NBLA Spanish verse text

## 3. Output

Each verse produces only:

- Greek text
- NBLA text
- Alignment
- Extra NBLA-supplied material
- Validation

## 4. Greek token rule

Every SBLGNT token must be mapped.

No Greek token may disappear.

## 5. Spanish coverage rule

Every NBLA word must be accounted for.

A Spanish word may be accounted for by:
- direct mapping
- expanded mapping
- merged mapping
- extra

Punctuation is ignored.

## 6. No overlap rule

No Spanish word may be reused by two Greek tokens unless the mapping is explicitly marked as a merge.

## 7. Classification types

direct:
One Greek token maps to one NBLA expression-unit.

expanded:
One Greek token maps to an NBLA expression with added lexical material.

merged-forward:
First Greek token in a multi-token Greek unit mapped to one Spanish expression.

merged-backward:
Second or later Greek token sharing that same Spanish expression.

missing:
Greek token is not represented in NBLA; supply minimal Spanish equivalent in parentheses.

extra:
NBLA word or phrase has no direct SBLGNT token source.

## 8. Supplied language rule

All supplied equivalents must be Spanish.

Correct:
δὲ → (pero) [missing]

Incorrect:
δὲ → (but) [missing]

## 9. Article rule

Greek articles are mapped only if NBLA has an actual Spanish article or article-like expression.

If not represented:

ὁ → (el) [missing]

Do not map articles onto nouns already mapped by another Greek token.

## 10. Proper-name merge rule

When NBLA combines two Greek name tokens into one Spanish name:

Ἰησοῦ → Jesucristo [merged-forward]
Χριστοῦ → Jesucristo [merged-backward]

## 11. Validation rule

A verse may be marked LOCKED only if:

- every Greek token is mapped
- every NBLA word is consumed
- no Spanish word is reused illegally
- all supplied words are Spanish
- no punctuation is counted
- no interpretation is introduced

Otherwise:

Status: INVALID