# 1corintios Metric Threshold Sweep

## Source Boundary

This report is generated only from the collected chapter similarity TSV file.
It does not use Bible text, commentary, headings, semantic labels, or external sources.

## Method

Chapters are connected when similarity is greater than or equal to the tested threshold.
Clusters are connected components at each threshold.
This report observes cluster drift only; it does not assign H0/H1/H2 and does not infer topology.

## Thresholds

- 0.20, 0.25, 0.30, 0.35, 0.40

## Cluster Sweep

### Threshold 0.20

- cluster 1: chapters=1,2,3,4,5,6,8,9,10,11,12,13,16 | size=13 | edges=49 | avg_similarity=0.2477
- cluster 2: chapters=15 | size=1 | edges=0 | avg_similarity=0
- cluster 3: chapters=14 | size=1 | edges=0 | avg_similarity=0
- cluster 4: chapters=7 | size=1 | edges=0 | avg_similarity=0

### Threshold 0.25

- cluster 1: chapters=1,2,3,5,6,8,9,11,12,16 | size=10 | edges=19 | avg_similarity=0.2917
- cluster 2: chapters=15 | size=1 | edges=0 | avg_similarity=0
- cluster 3: chapters=14 | size=1 | edges=0 | avg_similarity=0
- cluster 4: chapters=13 | size=1 | edges=0 | avg_similarity=0
- cluster 5: chapters=10 | size=1 | edges=0 | avg_similarity=0
- cluster 6: chapters=7 | size=1 | edges=0 | avg_similarity=0
- cluster 7: chapters=4 | size=1 | edges=0 | avg_similarity=0

### Threshold 0.30

- cluster 1: chapters=1,2,8,12 | size=4 | edges=4 | avg_similarity=0.3672
- cluster 2: chapters=16 | size=1 | edges=0 | avg_similarity=0
- cluster 3: chapters=15 | size=1 | edges=0 | avg_similarity=0
- cluster 4: chapters=14 | size=1 | edges=0 | avg_similarity=0
- cluster 5: chapters=13 | size=1 | edges=0 | avg_similarity=0
- cluster 6: chapters=11 | size=1 | edges=0 | avg_similarity=0
- cluster 7: chapters=10 | size=1 | edges=0 | avg_similarity=0
- cluster 8: chapters=9 | size=1 | edges=0 | avg_similarity=0
- cluster 9: chapters=7 | size=1 | edges=0 | avg_similarity=0
- cluster 10: chapters=6 | size=1 | edges=0 | avg_similarity=0
- cluster 11: chapters=5 | size=1 | edges=0 | avg_similarity=0
- cluster 12: chapters=4 | size=1 | edges=0 | avg_similarity=0
- cluster 13: chapters=3 | size=1 | edges=0 | avg_similarity=0

### Threshold 0.35

- cluster 1: chapters=2,8 | size=2 | edges=1 | avg_similarity=0.4575
- cluster 2: chapters=1,12 | size=2 | edges=1 | avg_similarity=0.3787
- cluster 3: chapters=16 | size=1 | edges=0 | avg_similarity=0
- cluster 4: chapters=15 | size=1 | edges=0 | avg_similarity=0
- cluster 5: chapters=14 | size=1 | edges=0 | avg_similarity=0
- cluster 6: chapters=13 | size=1 | edges=0 | avg_similarity=0
- cluster 7: chapters=11 | size=1 | edges=0 | avg_similarity=0
- cluster 8: chapters=10 | size=1 | edges=0 | avg_similarity=0
- cluster 9: chapters=9 | size=1 | edges=0 | avg_similarity=0
- cluster 10: chapters=7 | size=1 | edges=0 | avg_similarity=0
- cluster 11: chapters=6 | size=1 | edges=0 | avg_similarity=0
- cluster 12: chapters=5 | size=1 | edges=0 | avg_similarity=0
- cluster 13: chapters=4 | size=1 | edges=0 | avg_similarity=0
- cluster 14: chapters=3 | size=1 | edges=0 | avg_similarity=0

### Threshold 0.40

- cluster 1: chapters=2,8 | size=2 | edges=1 | avg_similarity=0.4575
- cluster 2: chapters=16 | size=1 | edges=0 | avg_similarity=0
- cluster 3: chapters=15 | size=1 | edges=0 | avg_similarity=0
- cluster 4: chapters=14 | size=1 | edges=0 | avg_similarity=0
- cluster 5: chapters=13 | size=1 | edges=0 | avg_similarity=0
- cluster 6: chapters=12 | size=1 | edges=0 | avg_similarity=0
- cluster 7: chapters=11 | size=1 | edges=0 | avg_similarity=0
- cluster 8: chapters=10 | size=1 | edges=0 | avg_similarity=0
- cluster 9: chapters=9 | size=1 | edges=0 | avg_similarity=0
- cluster 10: chapters=7 | size=1 | edges=0 | avg_similarity=0
- cluster 11: chapters=6 | size=1 | edges=0 | avg_similarity=0
- cluster 12: chapters=5 | size=1 | edges=0 | avg_similarity=0
- cluster 13: chapters=4 | size=1 | edges=0 | avg_similarity=0
- cluster 14: chapters=3 | size=1 | edges=0 | avg_similarity=0
- cluster 15: chapters=1 | size=1 | edges=0 | avg_similarity=0

## Most Persistent Chapter Pairs

- 2 ↔ 8: similarity=0.4575 | survives=0.20,0.25,0.30,0.35,0.40
- 1 ↔ 12: similarity=0.3787 | survives=0.20,0.25,0.30,0.35
- 8 ↔ 12: similarity=0.3164 | survives=0.20,0.25,0.30
- 2 ↔ 12: similarity=0.3163 | survives=0.20,0.25,0.30
- 2 ↔ 5: similarity=0.2916 | survives=0.20,0.25
- 11 ↔ 16: similarity=0.2913 | survives=0.20,0.25
- 3 ↔ 11: similarity=0.2901 | survives=0.20,0.25
- 1 ↔ 3: similarity=0.2866 | survives=0.20,0.25
- 3 ↔ 12: similarity=0.2849 | survives=0.20,0.25
- 1 ↔ 5: similarity=0.2754 | survives=0.20,0.25
- 3 ↔ 6: similarity=0.2751 | survives=0.20,0.25
- 5 ↔ 12: similarity=0.2745 | survives=0.20,0.25
- 3 ↔ 8: similarity=0.2627 | survives=0.20,0.25
- 5 ↔ 8: similarity=0.2622 | survives=0.20,0.25
- 3 ↔ 16: similarity=0.2613 | survives=0.20,0.25
- 1 ↔ 11: similarity=0.2593 | survives=0.20,0.25
- 1 ↔ 16: similarity=0.2554 | survives=0.20,0.25
- 1 ↔ 8: similarity=0.2514 | survives=0.20,0.25
- 9 ↔ 16: similarity=0.2509 | survives=0.20,0.25
- 4 ↔ 8: similarity=0.2487 | survives=0.20
