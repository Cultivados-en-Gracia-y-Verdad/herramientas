# MACRO STRUCTURE — 1CORINTIOS

<!-- Render mecánico desde datasets existentes. No interpreta, no calibra, no suaviza. -->

## 1. Archivos usados

- stream: /Users/johnwry/Nextcloud/Documents/GitHub/herramientas/MNA/data/independent-stream/1corintios-independent-stream.jsonl
- connector_registry: /Users/johnwry/Nextcloud/Documents/GitHub/herramientas/MNA/data/connectors/1corintios-connector-registry.jsonl
- paso9_support: /Users/johnwry/Nextcloud/Documents/GitHub/herramientas/MNA/data/paso9-support/1corintios-paso9-support.jsonl
- continuity_field: /Users/johnwry/Nextcloud/Documents/GitHub/herramientas/MNA/data/continuity-field/1corintios-continuity-field.jsonl
- paso13_action_support: /Users/johnwry/Nextcloud/Documents/GitHub/herramientas/MNA/data/paso13-action-support/1corintios-paso13-action-support.jsonl

## 2. Totales observables

- predicaciones: 1018
- macro regiones detectadas: 26
- registros paso9: 1018
- registros continuidad: 1018
- registros paso13: 1018
- conectores registrados: 276

## 3. Flujo macro observable

- 1:4–1:16: campo ACLARA dominante; continuidad unstable; conector dominante explanatory
- 1:17–1:30: campo EXPONE dominante; continuidad stable; conector dominante purpose
- 1:31–3:2: campo EXPONE dominante; continuidad stable; conector dominante purpose
- 3:2–3:11: campo ACLARA dominante; continuidad stable; conector dominante comparative
- 3:11–4:9: campo EXPONE dominante; continuidad stable; conector dominante conditional
- 4:9–6:7: campo ACLARA dominante; continuidad unstable; conector dominante comparative
- 6:7–6:19: campo ACLARA dominante; continuidad stable; conector dominante explanatory
- 6:19–7:11: campo EXPONE dominante; continuidad stable; conector dominante conditional
- 7:11–7:27: campo EXPONE dominante; continuidad stable; conector dominante conditional
- 7:27–8:8: campo EXPONE dominante; continuidad stable; conector dominante conditional
- 8:8–9:18: campo EXPONE dominante; continuidad stable; conector dominante conditional
- 9:18–10:6: campo EXPONE dominante; continuidad stable; conector dominante purpose
- 10:6–10:14: campo ACLARA dominante; continuidad stable; conector dominante comparative
- 10:15–10:30: campo ACLARA dominante; continuidad unstable; conector dominante explanatory
- 10:30–11:16: campo EXPONE dominante; continuidad stable; conector dominante conditional
- 11:16–11:34: campo EXPONE dominante; continuidad stable; conector dominante conditional
- 11:34–12:15: campo EXPONE dominante; continuidad stable; conector dominante comparative
- 12:15–13:9: campo EXPONE dominante; continuidad stable; conector dominante conditional
- 13:9–14:5: campo EXPONE dominante; continuidad stable; conector dominante comparative
- 14:5–14:17: campo ACLARA dominante; continuidad stable; conector dominante conditional
- 14:18–14:28: campo EXPONE dominante; continuidad stable; conector dominante explanatory
- 14:28–15:12: campo ACLARA dominante; continuidad stable; conector dominante conditional
- 15:13–15:32: campo EXPONE dominante; continuidad stable; conector dominante conditional
- 15:32–15:49: campo EXPONE dominante; continuidad stable; conector dominante conditional
- 15:50–16:3: campo ACLARA dominante; continuidad unstable; conector dominante temporal
- 16:3–16:22: campo ACLARA dominante; continuidad stable; conector dominante conditional

## 4. Macro regiones evidenciadas

### Región 1 — 1:4–1:16

**Campo observable:** campo ACLARA dominante; continuidad unstable; conector dominante explanatory.

#### Evidencia de persistencia

- predicaciones: 24
- etiquetas: ACLARA=19, EXPONE=6, RAZÓN=5, PROPÓSITO=2
- continuidad: unstable=15, stable=5, recovering=2, transitioning=2
- sujetos: implicit-1S=9, implicit-2P=6, unknown=5, implicit-3S=4
- conectores: explanatory=5, purpose=2, comparative=1
- superficies conectoras: ὅτι=5, ἵνα=2, καθὼς=1
- fuerza interna: etiqueta=0.594 continuidad=0.625

#### Gatillo de transición

- inicio del flujo observado

#### Evidencia ancla

```text
1:4 1corintios-1-4-P01 | implicit-1S → εὐχαριστῶ | labels=EXPONE | state=recovering
1:12 1corintios-1-12-P01 | implicit-1S → λέγω | labels=RAZÓN/ACLARA | state=unstable
1:12 1corintios-1-12-P03 | implicit-1S → εἰμι | labels=RAZÓN/ACLARA | state=unstable
1:15 1corintios-1-15-P01 | unknown → εἴπῃ | labels=RAZÓN/ACLARA | state=unstable
1:15 1corintios-1-15-P02 | implicit-2P → ἐβαπτίσθητε | labels=PROPÓSITO/ACLARA | state=transitioning
1:16 1corintios-1-16-P01 | implicit-1S → ἐβάπτισα | labels=RAZÓN/ACLARA | state=transitioning
1:16 1corintios-1-16-P03 | implicit-1S → ἐβάπτισα | labels=EXPONE | state=stable
```

### Región 2 — 1:17–1:30

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante purpose.

#### Evidencia de persistencia

- predicaciones: 24
- etiquetas: EXPONE=14, ACLARA=10, PROPÓSITO=4, CONDICIÓN=1, RAZÓN=1
- continuidad: stable=14, transitioning=7, unstable=2, recovering=1
- sujetos: unknown=10, implicit-3S=9, implicit-1S=2, implicit-2P=2, implicit-1P=1
- conectores: purpose=4, conditional=1, explanatory=1
- superficies conectoras: ἵνα=4, εἴ=1, ὅτι=1
- fuerza interna: etiqueta=0.467 continuidad=0.583

#### Gatillo de transición

- etiqueta dominante cambia: ACLARA → EXPONE
- continuidad cambia: unstable → stable
- conector dominante cambia: explanatory → purpose

#### Evidencia ancla

```text
1:17 1corintios-1-17-P01 | implicit-3S → ἀπέστειλέν | labels=CONDICIÓN/ACLARA | state=transitioning
1:18 1corintios-1-18-P01 | unknown → ἐστίν | labels=PROPÓSITO/EXPONE | state=stable
1:26 1corintios-1-26-P01 | implicit-2P → βλέπετε | labels=RAZÓN/ACLARA | state=transitioning
1:27 1corintios-1-27-P03 | implicit-3S → ἐξελέξατο | labels=PROPÓSITO/EXPONE | state=stable
1:28 1corintios-1-28-P01 | implicit-3S → ἐξελέξατο | labels=PROPÓSITO/EXPONE | state=stable
1:29 1corintios-1-29-P01 | implicit-3S → καυχήσηται | labels=PROPÓSITO/EXPONE | state=stable
1:30 1corintios-1-30-P02 | unknown → ἐγενήθη | labels=ACLARA | state=transitioning
```

### Región 3 — 1:31–3:2

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante purpose.

#### Evidencia de persistencia

- predicaciones: 36
- etiquetas: EXPONE=25, ACLARA=14, PROPÓSITO=3, CONDICIÓN=2, RAZÓN=1
- continuidad: stable=25, transitioning=6, recovering=3, unstable=2
- sujetos: implicit-3S=12, unknown=10, implicit-1P=6, implicit-1S=5, implicit-3P=2, implicit-2P=1
- conectores: purpose=3, comparative=2, conditional=2, explanatory=1
- superficies conectoras: ἵνα=3, καθὼς=2, εἰ=2, ὅτι=1
- fuerza interna: etiqueta=0.556 continuidad=0.694

#### Gatillo de transición

- región continuada por tamaño máximo del campo mecánico

#### Evidencia ancla

```text
1:31 1corintios-1-31-P01 | implicit-3S → γέγραπται | labels=EXPONE | state=stable
1:31 1corintios-1-31-P02 | unknown → καυχάσθω | labels=PROPÓSITO/ACLARA/EXPONE | state=stable
2:9 1corintios-2-9-P02 | unknown → εἶδεν | labels=ACLARA/EXPONE | state=stable
2:12 1corintios-2-12-P01 | implicit-1P → ἐλάβομεν | labels=CONDICIÓN/ACLARA | state=transitioning
2:13 1corintios-2-13-P01 | implicit-1P → λαλοῦμεν | labels=PROPÓSITO/EXPONE | state=stable
2:15 1corintios-2-15-P01 | unknown → ἀνακρίνει | labels=RAZÓN/ACLARA/EXPONE | state=stable
3:2 1corintios-3-2-P02 | implicit-2P → ἐδύνασθε | labels=ACLARA | state=transitioning
```

### Región 4 — 3:2–3:11

**Campo observable:** campo ACLARA dominante; continuidad stable; conector dominante comparative.

#### Evidencia de persistencia

- predicaciones: 24
- etiquetas: ACLARA=14, EXPONE=10, RESULTADO=1
- continuidad: stable=10, unstable=8, transitioning=4, recovering=2
- sujetos: implicit-2P=7, implicit-3S=7, unknown=5, implicit-1S=3, implicit-3P=1, implicit-1P=1
- conectores: comparative=2, temporal=1, inferential=1
- superficies conectoras: ὡς=2, ὅταν=1, ὥστε=1
- fuerza interna: etiqueta=0.56 continuidad=0.417

#### Gatillo de transición

- etiqueta dominante cambia: EXPONE → ACLARA
- conector dominante cambia: purpose → comparative

#### Evidencia ancla

```text
3:2 1corintios-3-2-P03 | implicit-2P → δύνασθε | labels=EXPONE | state=stable
3:4 1corintios-3-4-P02 | implicit-1S → εἰμι | labels=ACLARA | state=unstable
3:6 1corintios-3-6-P01 | implicit-1S → ἐφύτευσα | labels=ACLARA | state=transitioning
3:7 1corintios-3-7-P01 | unknown → ἐστίν | labels=RESULTADO/EXPONE | state=stable
3:10 1corintios-3-10-P02 | implicit-3S → ἐποικοδομεῖ | labels=ACLARA | state=transitioning
3:10 1corintios-3-10-P04 | implicit-3S → ἐποικοδομεῖ | labels=EXPONE | state=stable
3:11 1corintios-3-11-P01 | unknown → δύναται | labels=EXPONE | state=stable
```

### Región 5 — 3:11–4:9

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 60
- etiquetas: EXPONE=40, ACLARA=21, CONDICIÓN=6, PROPÓSITO=6, RAZÓN=3, RESULTADO=2
- continuidad: stable=40, transitioning=11, unstable=6, recovering=3
- sujetos: unknown=21, implicit-3S=17, implicit-2P=10, implicit-1S=6, implicit-2S=4, implicit-3P=1
- conectores: conditional=6, purpose=6, explanatory=3, inferential=2
- superficies conectoras: ἵνα=6, εἴ=4, ὅτι=3, εἰ=2, ὥστε=2
- fuerza interna: etiqueta=0.513 continuidad=0.667

#### Gatillo de transición

- etiqueta dominante cambia: ACLARA → EXPONE
- conector dominante cambia: comparative → conditional

#### Evidencia ancla

```text
3:11 1corintios-3-11-P02 | unknown → ἐστιν | labels=EXPONE | state=stable
3:13 1corintios-3-13-P04 | unknown → ἐστιν | labels=RAZÓN/ACLARA/EXPONE | state=stable
3:21 1corintios-3-21-P01 | unknown → καυχάσθω | labels=RAZÓN/ACLARA/RESULTADO | state=transitioning
4:7 1corintios-4-7-P01 | implicit-3S → διακρίνει | labels=PROPÓSITO/ACLARA | state=transitioning
4:7 1corintios-4-7-P05 | implicit-2S → καυχᾶσαι | labels=CONDICIÓN/EXPONE | state=stable
4:9 1corintios-4-9-P01 | implicit-1S → δοκῶ | labels=PROPÓSITO/ACLARA | state=recovering
4:9 1corintios-4-9-P02 | unknown → ἀπέδειξεν | labels=ACLARA | state=transitioning
```

### Región 6 — 4:9–6:7

**Campo observable:** campo ACLARA dominante; continuidad unstable; conector dominante comparative.

#### Evidencia de persistencia

- predicaciones: 60
- etiquetas: ACLARA=41, EXPONE=20, CONDICIÓN=5, RAZÓN=4, PROPÓSITO=3, RESULTADO=1
- continuidad: unstable=32, stable=20, transitioning=5, recovering=3
- sujetos: implicit-2P=17, implicit-1P=13, implicit-1S=12, unknown=12, implicit-3S=5, implicit-3P=1
- conectores: comparative=5, conditional=5, explanatory=4, purpose=3, inferential=1
- superficies conectoras: ὅτι=4, ὡς=3, ἐὰν=3, ἵνα=3, καθὼς=1, καθώς=1, ὥστε=1, ἐάν=1
- fuerza interna: etiqueta=0.554 continuidad=0.533

#### Gatillo de transición

- etiqueta dominante cambia: EXPONE → ACLARA
- continuidad cambia: stable → unstable
- conector dominante cambia: conditional → comparative

#### Evidencia ancla

```text
4:9 1corintios-4-9-P03 | implicit-1P → ἐγενήθημεν | labels=ACLARA | state=transitioning
4:11 1corintios-4-11-P01 | implicit-1P → πεινῶμεν | labels=ACLARA/RAZÓN/EXPONE | state=stable
6:2 1corintios-6-2-P03 | implicit-3S → κρίνεται | labels=RAZÓN/ACLARA | state=recovering
6:2 1corintios-6-2-P04 | implicit-2P → ἐστε | labels=CONDICIÓN/ACLARA | state=unstable
6:4 1corintios-6-4-P01 | implicit-2P → ἔχητε | labels=RAZÓN/ACLARA | state=unstable
6:4 1corintios-6-4-P02 | implicit-2P → καθίζετε | labels=CONDICIÓN/EXPONE | state=stable
6:7 1corintios-6-7-P01 | unknown → ἐστιν | labels=EXPONE | state=stable
```

### Región 7 — 6:7–6:19

**Campo observable:** campo ACLARA dominante; continuidad stable; conector dominante explanatory.

#### Evidencia de persistencia

- predicaciones: 36
- etiquetas: ACLARA=22, EXPONE=15, RAZÓN=5, CONDICIÓN=1
- continuidad: stable=15, transitioning=10, unstable=9, recovering=2
- sujetos: implicit-2P=16, unknown=11, implicit-3S=6, implicit-1S=2, implicit-3P=1
- conectores: explanatory=5, conditional=1
- superficies conectoras: ὅτι=5, ἐὰν=1
- fuerza interna: etiqueta=0.512 continuidad=0.417

#### Gatillo de transición

- continuidad cambia: unstable → stable
- conector dominante cambia: comparative → explanatory

#### Evidencia ancla

```text
6:7 1corintios-6-7-P02 | implicit-2P → ἔχετε | labels=ACLARA | state=transitioning
6:7 1corintios-6-7-P03 | implicit-2P → ἀδικεῖσθε | labels=RAZÓN/ACLARA/EXPONE | state=stable
6:9 1corintios-6-9-P03 | implicit-2P → πλανᾶσθε | labels=RAZÓN/ACLARA | state=unstable
6:15 1corintios-6-15-P03 | implicit-1S → ποιήσω | labels=RAZÓN/ACLARA | state=unstable
6:16 1corintios-6-16-P03 | implicit-3P → ἔσονται | labels=RAZÓN/ACLARA | state=recovering
6:18 1corintios-6-18-P03 | unknown → ἐστιν | labels=CONDICIÓN/EXPONE | state=stable
6:19 1corintios-6-19-P03 | implicit-2P → ἔχετε | labels=RAZÓN/ACLARA | state=transitioning
```

### Región 8 — 6:19–7:11

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 24
- etiquetas: EXPONE=14, ACLARA=10, CONDICIÓN=4, PROPÓSITO=2
- continuidad: stable=14, transitioning=6, unstable=3, recovering=1
- sujetos: implicit-2P=7, unknown=6, implicit-3S=4, implicit-1S=4, implicit-3P=3
- conectores: conditional=4, purpose=2, comparative=1
- superficies conectoras: εἰ=2, ἵνα=2, ἐὰν=2, ὡς=1
- fuerza interna: etiqueta=0.467 continuidad=0.583

#### Gatillo de transición

- etiqueta dominante cambia: ACLARA → EXPONE
- conector dominante cambia: explanatory → conditional

#### Evidencia ancla

```text
6:19 1corintios-6-19-P04 | implicit-2P → ἐστὲ | labels=EXPONE | state=stable
7:5 1corintios-7-5-P03 | implicit-2P → ἦτε | labels=CONDICIÓN/PROPÓSITO/EXPONE | state=stable
7:6 1corintios-7-6-P01 | implicit-1S → λέγω | labels=PROPÓSITO/ACLARA | state=unstable
7:8 1corintios-7-8-P01 | implicit-1S → λέγω | labels=ACLARA | state=transitioning
7:9 1corintios-7-9-P01 | implicit-3P → ἐγκρατεύονται | labels=CONDICIÓN/EXPONE | state=stable
7:9 1corintios-7-9-P02 | implicit-3P → γαμησάτωσαν | labels=CONDICIÓN/EXPONE | state=stable
7:11 1corintios-7-11-P02 | implicit-3S → μενέτω | labels=CONDICIÓN/EXPONE | state=stable
```

### Región 9 — 7:11–7:27

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 48
- etiquetas: EXPONE=34, ACLARA=16, CONDICIÓN=7
- continuidad: stable=34, transitioning=12, unstable=2
- sujetos: unknown=16, implicit-3S=15, implicit-2S=10, implicit-1S=5, implicit-2P=2
- conectores: conditional=7, comparative=2
- superficies conectoras: εἰ=5, εἴ=2, ὡς=2
- fuerza interna: etiqueta=0.596 continuidad=0.708

#### Gatillo de transición

- región continuada por tamaño máximo del campo mecánico

#### Evidencia ancla

```text
7:11 1corintios-7-11-P03 | implicit-3S → καταλλαγήτω— | labels=EXPONE | state=stable
7:16 1corintios-7-16-P03 | implicit-2S → οἶδας | labels=CONDICIÓN/EXPONE | state=stable
7:17 1corintios-7-17-P01 | implicit-3S → ἐμέρισεν | labels=CONDICIÓN/ACLARA | state=transitioning
7:17 1corintios-7-17-P02 | unknown → κέκληκεν | labels=CONDICIÓN/ACLARA/EXPONE | state=stable
7:17 1corintios-7-17-P03 | unknown → περιπατείτω | labels=ACLARA/EXPONE | state=stable
7:21 1corintios-7-21-P04 | implicit-2S → χρῆσαι | labels=CONDICIÓN/EXPONE | state=stable
7:27 1corintios-7-27-P03 | implicit-2S → λέλυσαι | labels=EXPONE | state=stable
```

### Región 10 — 7:27–8:8

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 60
- etiquetas: EXPONE=41, ACLARA=20, CONDICIÓN=8, PROPÓSITO=3, RESULTADO=1, RAZÓN=1
- continuidad: stable=41, transitioning=8, recovering=7, unstable=4
- sujetos: implicit-3S=26, unknown=16, implicit-1S=6, implicit-3P=5, implicit-1P=4, implicit-2S=3
- conectores: conditional=8, comparative=4, purpose=3, inferential=1, explanatory=1
- superficies conectoras: ἐὰν=5, ἵνα=3, ὡς=3, εἰ=2, ὥστε=1, ὅτι=1, εἴ=1, καθὼς=1
- fuerza interna: etiqueta=0.554 continuidad=0.683

#### Gatillo de transición

- región continuada por tamaño máximo del campo mecánico

#### Evidencia ancla

```text
7:27 1corintios-7-27-P04 | implicit-2S → ζήτει | labels=EXPONE | state=stable
7:31 1corintios-7-31-P01 | implicit-3S → παράγει | labels=PROPÓSITO/ACLARA | state=recovering
8:1 1corintios-8-1-P03 | unknown → φυσιοῖ | labels=RAZÓN/ACLARA | state=transitioning
8:2 1corintios-8-2-P02 | implicit-3S → ἔγνω | labels=CONDICIÓN/EXPONE | state=stable
8:3 1corintios-8-3-P01 | unknown → ἀγαπᾷ | labels=ACLARA/EXPONE | state=stable
8:3 1corintios-8-3-P02 | unknown → ἔγνωσται | labels=CONDICIÓN/EXPONE | state=stable
8:8 1corintios-8-8-P02 | implicit-1P → φάγωμεν | labels=ACLARA | state=transitioning
```

### Región 11 — 8:8–9:18

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 60
- etiquetas: EXPONE=33, ACLARA=28, CONDICIÓN=12, PROPÓSITO=3, RAZÓN=2
- continuidad: stable=33, transitioning=16, unstable=10, recovering=1
- sujetos: implicit-1S=15, unknown=14, implicit-3S=13, implicit-1P=11, implicit-2P=5, implicit-2S=1
- conectores: conditional=12, purpose=3, explanatory=2
- superficies conectoras: εἰ=7, ἐὰν=5, ἵνα=3, ὅτι=2
- fuerza interna: etiqueta=0.423 continuidad=0.55

#### Gatillo de transición

- región continuada por tamaño máximo del campo mecánico

#### Evidencia ancla

```text
8:8 1corintios-8-8-P03 | implicit-1P → περισσεύομεν | labels=CONDICIÓN/EXPONE | state=stable
9:13 1corintios-9-13-P03 | unknown → συμμερίζονται | labels=RAZÓN/ACLARA/EXPONE | state=stable
9:15 1corintios-9-15-P04 | unknown → κενώσει | labels=PROPÓSITO/EXPONE | state=stable
9:16 1corintios-9-16-P02 | implicit-3S → ἔστιν | labels=CONDICIÓN/ACLARA | state=transitioning
9:17 1corintios-9-17-P01 | implicit-1S → πράσσω | labels=CONDICIÓN/EXPONE | state=stable
9:17 1corintios-9-17-P02 | implicit-1S → ἔχω | labels=CONDICIÓN/EXPONE | state=stable
9:18 1corintios-9-18-P01 | implicit-3S → ἐστιν | labels=CONDICIÓN/ACLARA | state=transitioning
```

### Región 12 — 9:18–10:6

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante purpose.

#### Evidencia de persistencia

- predicaciones: 36
- etiquetas: EXPONE=25, ACLARA=16, PROPÓSITO=10, RAZÓN=2
- continuidad: stable=25, unstable=4, recovering=4, transitioning=3
- sujetos: implicit-1S=19, unknown=7, implicit-3P=4, implicit-2P=3, implicit-3S=3
- conectores: purpose=10, comparative=4, explanatory=2
- superficies conectoras: ἵνα=10, ὡς=4, ὅτι=2
- fuerza interna: etiqueta=0.472 continuidad=0.694

#### Gatillo de transición

- conector dominante cambia: conditional → purpose

#### Evidencia ancla

```text
9:18 1corintios-9-18-P02 | implicit-1S → θήσω | labels=ACLARA | state=transitioning
9:20 1corintios-9-20-P03 | implicit-1S → κερδήσω | labels=ACLARA/PROPÓSITO/EXPONE | state=stable
9:21 1corintios-9-21-P01 | implicit-1S → κερδάνω | labels=ACLARA/PROPÓSITO/EXPONE | state=stable
9:22 1corintios-9-22-P01 | implicit-1S → ἐγενόμην | labels=ACLARA/PROPÓSITO/EXPONE | state=stable
9:27 1corintios-9-27-P01 | implicit-1S → ὑπωπιάζω | labels=ACLARA/EXPONE | state=stable
10:1 1corintios-10-1-P03 | unknown → διῆλθον | labels=RAZÓN/ACLARA/EXPONE | state=stable
10:6 1corintios-10-6-P01 | unknown → ἐγενήθησαν | labels=EXPONE | state=stable
```

### Región 13 — 10:6–10:14

**Campo observable:** campo ACLARA dominante; continuidad stable; conector dominante comparative.

#### Evidencia de persistencia

- predicaciones: 24
- etiquetas: ACLARA=16, EXPONE=11, RESULTADO=1, CONDICIÓN=1
- continuidad: stable=11, unstable=10, recovering=2, transitioning=1
- sujetos: unknown=8, implicit-3S=6, implicit-2P=4, implicit-3P=4, implicit-1P=2
- conectores: comparative=4, inferential=1, conditional=1
- superficies conectoras: καθώς=3, καθὼς=1, ὥστε=1, εἰ=1
- fuerza interna: etiqueta=0.552 continuidad=0.458

#### Gatillo de transición

- etiqueta dominante cambia: EXPONE → ACLARA
- conector dominante cambia: purpose → comparative

#### Evidencia ancla

```text
10:6 1corintios-10-6-P02 | unknown → ἐπεθύμησαν | labels=EXPONE | state=stable
10:7 1corintios-10-7-P03 | implicit-3S → ἐκάθισεν | labels=ACLARA/EXPONE | state=stable
10:8 1corintios-10-8-P03 | implicit-3P → ἔπεσαν | labels=ACLARA/EXPONE | state=stable
10:9 1corintios-10-9-P03 | implicit-3P → ἀπώλλυντο | labels=ACLARA/EXPONE | state=stable
10:12 1corintios-10-12-P01 | unknown → βλεπέτω | labels=RESULTADO/EXPONE | state=stable
10:13 1corintios-10-13-P03 | implicit-2P → δύνασθε | labels=CONDICIÓN/ACLARA | state=unstable
10:14 1corintios-10-14-P01 | implicit-2P → φεύγετε | labels=ACLARA | state=unstable
```

### Región 14 — 10:15–10:30

**Campo observable:** campo ACLARA dominante; continuidad unstable; conector dominante explanatory.

#### Evidencia de persistencia

- predicaciones: 36
- etiquetas: ACLARA=28, EXPONE=11, RAZÓN=4, CONDICIÓN=2
- continuidad: unstable=16, stable=11, transitioning=7, recovering=2
- sujetos: unknown=14, implicit-2P=8, implicit-1S=6, implicit-1P=6, implicit-3P=2
- conectores: explanatory=4, conditional=2, comparative=1
- superficies conectoras: ὅτι=4, ὡς=1, εἴ=1, ἐὰν=1
- fuerza interna: etiqueta=0.622 continuidad=0.444

#### Gatillo de transición

- continuidad cambia: stable → unstable
- conector dominante cambia: comparative → explanatory

#### Evidencia ancla

```text
10:15 1corintios-10-15-P01 | implicit-1S → λέγω | labels=ACLARA | state=unstable
10:17 1corintios-10-17-P02 | implicit-1P → μετέχομεν | labels=RAZÓN/ACLARA/EXPONE | state=stable
10:19 1corintios-10-19-P03 | unknown → ἐστιν | labels=RAZÓN/ACLARA/EXPONE | state=stable
10:20 1corintios-10-20-P02 | implicit-3P → θύουσιν | labels=RAZÓN/ACLARA/EXPONE | state=stable
10:27 1corintios-10-27-P02 | implicit-2P → θέλετε | labels=CONDICIÓN/ACLARA | state=transitioning
10:28 1corintios-10-28-P02 | unknown → ἐστιν | labels=CONDICIÓN/EXPONE | state=stable
10:30 1corintios-10-30-P01 | implicit-1S → μετέχω | labels=ACLARA | state=transitioning
```

### Región 15 — 10:30–11:16

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 36
- etiquetas: EXPONE=24, ACLARA=15, CONDICIÓN=5, RAZÓN=4, PROPÓSITO=1
- continuidad: stable=24, unstable=7, transitioning=5
- sujetos: implicit-3S=13, implicit-2P=9, unknown=7, implicit-1S=6, implicit-3P=1
- conectores: conditional=5, explanatory=4, comparative=2, purpose=1
- superficies conectoras: ὅτι=4, εἰ=3, καθὼς=2, ἐὰν=2, ἵνα=1
- fuerza interna: etiqueta=0.49 continuidad=0.667

#### Gatillo de transición

- etiqueta dominante cambia: ACLARA → EXPONE
- continuidad cambia: unstable → stable
- conector dominante cambia: explanatory → conditional

#### Evidencia ancla

```text
10:30 1corintios-10-30-P02 | implicit-1S → βλασφημοῦμαι | labels=CONDICIÓN/EXPONE | state=stable
11:4 1corintios-11-4-P01 | implicit-3S → καταισχύνει | labels=RAZÓN/ACLARA/EXPONE | state=stable
11:6 1corintios-11-6-P02 | implicit-3S → κειράσθω | labels=CONDICIÓN/EXPONE | state=stable
11:7 1corintios-11-7-P01 | implicit-3S → ὀφείλει | labels=CONDICIÓN/EXPONE | state=stable
11:14 1corintios-11-14-P03 | unknown → ἐστιν | labels=RAZÓN/ACLARA/CONDICIÓN/EXPONE | state=stable
11:15 1corintios-11-15-P02 | unknown → ἐστιν | labels=CONDICIÓN/EXPONE | state=stable
11:16 1corintios-11-16-P01 | unknown → δοκεῖ | labels=RAZÓN/ACLARA/EXPONE | state=stable
```

### Región 16 — 11:16–11:34

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 48
- etiquetas: EXPONE=30, ACLARA=19, CONDICIÓN=5, RAZÓN=2, PROPÓSITO=2, RESULTADO=2
- continuidad: stable=30, unstable=7, transitioning=7, recovering=4
- sujetos: implicit-3S=17, implicit-2P=11, implicit-1S=8, unknown=6, implicit-1P=5, implicit-3P=1
- conectores: conditional=5, explanatory=2, purpose=2, inferential=2
- superficies conectoras: εἰ=2, ὅτι=2, ἵνα=2, ἐὰν=2, ὥστε=2, εἴ=1
- fuerza interna: etiqueta=0.5 continuidad=0.625

#### Gatillo de transición

- región continuada por tamaño máximo del campo mecánico

#### Evidencia ancla

```text
11:16 1corintios-11-16-P02 | implicit-1P → ἔχομεν | labels=CONDICIÓN/ACLARA | state=unstable
11:23 1corintios-11-23-P04 | implicit-3S → ἔλαβεν | labels=RAZÓN/ACLARA/EXPONE | state=stable
11:26 1corintios-11-26-P02 | implicit-2P → πίνητε | labels=CONDICIÓN/EXPONE | state=stable
11:27 1corintios-11-27-P01 | unknown → ἐσθίῃ | labels=RESULTADO/EXPONE | state=stable
11:31 1corintios-11-31-P02 | implicit-1P → ἐκρινόμεθα | labels=CONDICIÓN/EXPONE | state=stable
11:33 1corintios-11-33-P01 | implicit-2P → ἐκδέχεσθε | labels=PROPÓSITO/RESULTADO/ACLARA | state=unstable
11:34 1corintios-11-34-P02 | implicit-3S → ἐσθιέτω | labels=CONDICIÓN/EXPONE | state=stable
```

### Región 17 — 11:34–12:15

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante comparative.

#### Evidencia de persistencia

- predicaciones: 24
- etiquetas: EXPONE=15, ACLARA=13, RAZÓN=2, PROPÓSITO=1
- continuidad: stable=15, transitioning=6, recovering=2, unstable=1
- sujetos: unknown=8, implicit-3S=5, implicit-2P=4, implicit-1S=4, implicit-1P=2, implicit-3P=1
- conectores: comparative=3, explanatory=2, purpose=1
- superficies conectoras: ὡς=2, ὅτι=2, ἵνα=1, καθὼς=1
- fuerza interna: etiqueta=0.484 continuidad=0.625

#### Gatillo de transición

- conector dominante cambia: conditional → comparative

#### Evidencia ancla

```text
11:34 1corintios-11-34-P03 | implicit-2P → συνέρχησθε | labels=ACLARA | state=transitioning
11:34 1corintios-11-34-P04 | implicit-1S → ἔλθω | labels=PROPÓSITO/ACLARA | state=transitioning
11:34 1corintios-11-34-P05 | implicit-1S → διατάξομαι | labels=ACLARA/EXPONE | state=stable
12:2 1corintios-12-2-P03 | implicit-2P → ἤγεσθε | labels=RAZÓN/ACLARA/EXPONE | state=stable
12:3 1corintios-12-3-P03 | unknown → δύναται | labels=RAZÓN/ACLARA/EXPONE | state=stable
12:12 1corintios-12-12-P01 | unknown → ἐστιν | labels=ACLARA/EXPONE | state=stable
12:15 1corintios-12-15-P01 | implicit-3S → εἴπῃ | labels=EXPONE | state=stable
```

### Región 18 — 12:15–13:9

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 60
- etiquetas: EXPONE=41, ACLARA=22, CONDICIÓN=5, RAZÓN=2, PROPÓSITO=1, RESULTADO=1
- continuidad: stable=41, transitioning=11, recovering=5, unstable=3
- sujetos: implicit-3S=22, unknown=17, implicit-1S=15, implicit-1P=3, implicit-2P=2, implicit-3P=1
- conectores: conditional=5, explanatory=2, comparative=1, purpose=1, inferential=1
- superficies conectoras: ἐὰν=4, ὅτι=2, καθὼς=1, εἰ=1, ἵνα=1, ὥστε=1
- fuerza interna: etiqueta=0.569 continuidad=0.683

#### Gatillo de transición

- conector dominante cambia: comparative → conditional

#### Evidencia ancla

```text
12:15 1corintios-12-15-P02 | implicit-1S → εἰμὶ | labels=CONDICIÓN/ACLARA | state=transitioning
12:15 1corintios-12-15-P03 | implicit-1S → εἰμὶ | labels=RAZÓN/ACLARA/EXPONE | state=stable
12:16 1corintios-12-16-P03 | implicit-1S → εἰμὶ | labels=RAZÓN/ACLARA/EXPONE | state=stable
13:1 1corintios-13-1-P02 | implicit-1S → ἔχω | labels=CONDICIÓN/EXPONE | state=stable
13:2 1corintios-13-2-P02 | implicit-1S → εἰδῶ | labels=CONDICIÓN/EXPONE | state=stable
13:2 1corintios-13-2-P04 | implicit-1S → ἔχω | labels=RESULTADO/EXPONE | state=stable
13:9 1corintios-13-9-P01 | implicit-1P → γινώσκομεν | labels=ACLARA | state=transitioning
```

### Región 19 — 13:9–14:5

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante comparative.

#### Evidencia de persistencia

- predicaciones: 24
- etiquetas: EXPONE=16, ACLARA=11, PROPÓSITO=1
- continuidad: stable=16, transitioning=5, recovering=2, unstable=1
- sujetos: implicit-1S=10, implicit-3S=7, implicit-2P=3, implicit-1P=2, unknown=2
- conectores: comparative=4, temporal=1, purpose=1
- superficies conectoras: ὡς=3, ὅταν=1, καθὼς=1, ἵνα=1
- fuerza interna: etiqueta=0.571 continuidad=0.667

#### Gatillo de transición

- conector dominante cambia: conditional → comparative

#### Evidencia ancla

```text
13:9 1corintios-13-9-P02 | implicit-1P → προφητεύομεν | labels=EXPONE | state=stable
13:11 1corintios-13-11-P04 | implicit-1S → ἐλογιζόμην | labels=ACLARA/EXPONE | state=stable
13:11 1corintios-13-11-P05 | implicit-1S → γέγονα | labels=ACLARA/EXPONE | state=stable
13:11 1corintios-13-11-P06 | implicit-1S → κατήργηκα | labels=ACLARA/EXPONE | state=stable
13:13 1corintios-13-13-P01 | implicit-3S → μένει | labels=ACLARA | state=transitioning
14:2 1corintios-14-2-P01 | implicit-3S → λαλεῖ | labels=PROPÓSITO/ACLARA | state=transitioning
14:5 1corintios-14-5-P01 | implicit-1S → θέλω | labels=ACLARA | state=unstable
```

### Región 20 — 14:5–14:17

**Campo observable:** campo ACLARA dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 36
- etiquetas: ACLARA=21, EXPONE=15, CONDICIÓN=10, PROPÓSITO=4
- continuidad: stable=15, unstable=11, transitioning=9, recovering=1
- sujetos: unknown=11, implicit-1S=10, implicit-2P=6, implicit-3S=6, implicit-2S=3
- conectores: conditional=10, purpose=4
- superficies conectoras: ἐὰν=8, ἵνα=4, εἰ=2
- fuerza interna: etiqueta=0.42 continuidad=0.417

#### Gatillo de transición

- etiqueta dominante cambia: EXPONE → ACLARA
- conector dominante cambia: comparative → conditional

#### Evidencia ancla

```text
14:5 1corintios-14-5-P02 | implicit-2P → προφητεύητε | labels=ACLARA | state=unstable
14:11 1corintios-14-11-P02 | implicit-1S → ἔσομαι | labels=CONDICIÓN/EXPONE | state=stable
14:13 1corintios-14-13-P01 | unknown → προσευχέσθω | labels=PROPÓSITO/ACLARA | state=unstable
14:14 1corintios-14-14-P01 | implicit-1S → προσεύχωμαι | labels=PROPÓSITO/ACLARA | state=transitioning
14:14 1corintios-14-14-P02 | unknown → προσεύχεται | labels=CONDICIÓN/ACLARA | state=transitioning
14:16 1corintios-14-16-P02 | implicit-3S → ἐρεῖ | labels=CONDICIÓN/ACLARA | state=unstable
14:17 1corintios-14-17-P02 | unknown → οἰκοδομεῖται | labels=ACLARA | state=transitioning
```

### Región 21 — 14:18–14:28

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante explanatory.

#### Evidencia de persistencia

- predicaciones: 36
- etiquetas: EXPONE=22, ACLARA=15, RAZÓN=3, CONDICIÓN=3, PROPÓSITO=1, RESULTADO=1
- continuidad: stable=22, transitioning=6, unstable=4, recovering=4
- sujetos: implicit-3S=12, unknown=12, implicit-1S=5, implicit-2P=5, implicit-3P=2
- conectores: explanatory=3, conditional=3, purpose=1, inferential=1, temporal=1
- superficies conectoras: ὅτι=3, ἐὰν=3, ἵνα=1, ὥστε=1, ὅταν=1
- fuerza interna: etiqueta=0.489 continuidad=0.611

#### Gatillo de transición

- etiqueta dominante cambia: ACLARA → EXPONE
- conector dominante cambia: conditional → explanatory

#### Evidencia ancla

```text
14:18 1corintios-14-18-P01 | implicit-1S → εὐχαριστῶ | labels=ACLARA | state=transitioning
14:22 1corintios-14-22-P01 | unknown → εἰσιν | labels=RESULTADO/ACLARA | state=transitioning
14:23 1corintios-14-23-P02 | unknown → λαλῶσιν | labels=CONDICIÓN/ACLARA | state=recovering
14:24 1corintios-14-24-P01 | unknown → προφητεύωσιν | labels=RAZÓN/ACLARA | state=transitioning
14:24 1corintios-14-24-P02 | implicit-3S → εἰσέλθῃ | labels=CONDICIÓN/ACLARA | state=recovering
14:26 1corintios-14-26-P01 | implicit-3S → ἐστιν | labels=RAZÓN/ACLARA/EXPONE | state=stable
14:28 1corintios-14-28-P02 | unknown → σιγάτω | labels=CONDICIÓN/EXPONE | state=stable
```

### Región 22 — 14:28–15:12

**Campo observable:** campo ACLARA dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 60
- etiquetas: ACLARA=36, EXPONE=29, CONDICIÓN=7, RAZÓN=6, PROPÓSITO=1, RESULTADO=1
- continuidad: stable=29, recovering=14, transitioning=9, unstable=8
- sujetos: unknown=17, implicit-3S=16, implicit-1S=12, implicit-2P=9, implicit-3P=5, implicit-1P=1
- conectores: conditional=7, explanatory=6, purpose=1, comparative=1, inferential=1
- superficies conectoras: ὅτι=6, εἰ=5, ἐὰν=1, ἵνα=1, καθὼς=1, εἴ=1, ὥστε=1
- fuerza interna: etiqueta=0.45 continuidad=0.483

#### Gatillo de transición

- etiqueta dominante cambia: EXPONE → ACLARA
- conector dominante cambia: explanatory → conditional

#### Evidencia ancla

```text
14:28 1corintios-14-28-P03 | implicit-3S → λαλείτω | labels=EXPONE | state=stable
14:38 1corintios-14-38-P01 | unknown → ἀγνοεῖ | labels=RAZÓN/ACLARA/EXPONE | state=stable
15:4 1corintios-15-4-P01 | implicit-3S → ἐτάφη | labels=RAZÓN/ACLARA/EXPONE | state=stable
15:4 1corintios-15-4-P02 | implicit-3S → ἐγήγερται | labels=RAZÓN/ACLARA/EXPONE | state=stable
15:5 1corintios-15-5-P01 | implicit-3S → ὤφθη | labels=RAZÓN/ACLARA/EXPONE | state=stable
15:6 1corintios-15-6-P01 | implicit-3S → ὤφθη | labels=RAZÓN/ACLARA/EXPONE | state=stable
15:12 1corintios-15-12-P04 | unknown → ἔστιν | labels=ACLARA | state=recovering
```

### Región 23 — 15:13–15:32

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 36
- etiquetas: EXPONE=23, ACLARA=16, CONDICIÓN=6, RAZÓN=4, PROPÓSITO=1
- continuidad: stable=23, recovering=6, unstable=4, transitioning=3
- sujetos: unknown=16, implicit-3S=9, implicit-1P=5, implicit-1S=3, implicit-3P=2, implicit-2P=1
- conectores: conditional=6, explanatory=4, temporal=4, purpose=1
- superficies conectoras: εἰ=6, ὅτι=4, ὅταν=4, ἵνα=1
- fuerza interna: etiqueta=0.46 continuidad=0.639

#### Gatillo de transición

- etiqueta dominante cambia: ACLARA → EXPONE

#### Evidencia ancla

```text
15:13 1corintios-15-13-P01 | unknown → ἔστιν | labels=RAZÓN/ACLARA/EXPONE | state=stable
15:15 1corintios-15-15-P04 | implicit-3S → ἤγειρεν | labels=RAZÓN/ACLARA/EXPONE | state=stable
15:19 1corintios-15-19-P02 | implicit-1P → ἐσμέν | labels=CONDICIÓN/EXPONE | state=stable
15:28 1corintios-15-28-P01 | implicit-3S → ὑποταγῇ | labels=RAZÓN/ACLARA/EXPONE | state=stable
15:29 1corintios-15-29-P01 | implicit-3P → ποιήσουσιν | labels=PROPÓSITO/ACLARA | state=recovering
15:29 1corintios-15-29-P03 | implicit-3P → βαπτίζονται | labels=CONDICIÓN/EXPONE | state=stable
15:32 1corintios-15-32-P01 | implicit-1S → ἐθηριομάχησα | labels=EXPONE | state=stable
```

### Región 24 — 15:32–15:49

**Campo observable:** campo EXPONE dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 36
- etiquetas: EXPONE=22, ACLARA=16, CONDICIÓN=5
- continuidad: stable=22, unstable=8, transitioning=5, recovering=1
- sujetos: implicit-3S=14, unknown=7, implicit-1P=5, implicit-2P=3, implicit-3P=3, implicit-2S=3
- conectores: conditional=5, comparative=2
- superficies conectoras: εἰ=4, καθὼς=2, ἐὰν=1
- fuerza interna: etiqueta=0.512 continuidad=0.611

#### Gatillo de transición

- región continuada por tamaño máximo del campo mecánico

#### Evidencia ancla

```text
15:32 1corintios-15-32-P02 | unknown → ἐγείρονται | labels=CONDICIÓN/ACLARA | state=transitioning
15:32 1corintios-15-32-P03 | implicit-1P → φάγωμεν | labels=CONDICIÓN/ACLARA | state=transitioning
15:37 1corintios-15-37-P01 | implicit-2S → σπείρεις | labels=CONDICIÓN/ACLARA | state=transitioning
15:38 1corintios-15-38-P01 | unknown → δίδωσιν | labels=CONDICIÓN/EXPONE | state=stable
15:41 1corintios-15-41-P01 | implicit-3S → διαφέρει | labels=ACLARA/EXPONE | state=stable
15:44 1corintios-15-44-P04 | unknown → ἔστιν | labels=CONDICIÓN/EXPONE | state=stable
15:49 1corintios-15-49-P02 | implicit-1P → φορέσομεν | labels=ACLARA/EXPONE | state=stable
```

### Región 25 — 15:50–16:3

**Campo observable:** campo ACLARA dominante; continuidad unstable; conector dominante temporal.

#### Evidencia de persistencia

- predicaciones: 24
- etiquetas: ACLARA=18, EXPONE=7, RAZÓN=2, RESULTADO=1, CONDICIÓN=1, PROPÓSITO=1
- continuidad: unstable=12, stable=7, recovering=3, transitioning=2
- sujetos: unknown=9, implicit-1S=5, implicit-3S=4, implicit-1P=3, implicit-2P=3
- conectores: temporal=3, explanatory=2, inferential=1, conditional=1, purpose=1
- superficies conectoras: ὅταν=3, ὅτι=2, ὥστε=1, ἐὰν=1, ἵνα=1
- fuerza interna: etiqueta=0.6 continuidad=0.5

#### Gatillo de transición

- etiqueta dominante cambia: EXPONE → ACLARA
- continuidad cambia: stable → unstable
- conector dominante cambia: conditional → temporal

#### Evidencia ancla

```text
15:50 1corintios-15-50-P01 | implicit-1S → φημι | labels=ACLARA | state=recovering
15:50 1corintios-15-50-P03 | unknown → κληρονομεῖ | labels=RAZÓN/ACLARA/EXPONE | state=stable
15:58 1corintios-15-58-P01 | implicit-2P → γίνεσθε | labels=RESULTADO/ACLARA | state=unstable
16:1 1corintios-16-1-P01 | implicit-1S → διέταξα | labels=RAZÓN/ACLARA | state=unstable
16:2 1corintios-16-2-P03 | implicit-1S → ἔλθω | labels=CONDICIÓN/ACLARA | state=unstable
16:2 1corintios-16-2-P04 | unknown → γίνωνται | labels=PROPÓSITO/ACLARA | state=unstable
16:3 1corintios-16-3-P02 | implicit-2P → δοκιμάσητε | labels=ACLARA | state=unstable
```

### Región 26 — 16:3–16:22

**Campo observable:** campo ACLARA dominante; continuidad stable; conector dominante conditional.

#### Evidencia de persistencia

- predicaciones: 46
- etiquetas: ACLARA=30, EXPONE=17, CONDICIÓN=6, PROPÓSITO=6, RAZÓN=2
- continuidad: stable=17, unstable=16, transitioning=9, recovering=4
- sujetos: implicit-1S=14, implicit-3S=13, implicit-2P=7, unknown=6, implicit-3P=5, implicit-2S=1
- conectores: conditional=6, purpose=6, temporal=2, explanatory=2
- superficies conectoras: ἵνα=6, ἐὰν=5, ὅταν=2, ὅτι=2, εἴ=1
- fuerza interna: etiqueta=0.492 continuidad=0.37

#### Gatillo de transición

- continuidad cambia: unstable → stable
- conector dominante cambia: temporal → conditional

#### Evidencia ancla

```text
16:3 1corintios-16-3-P03 | implicit-1S → πέμψω | labels=CONDICIÓN/ACLARA | state=unstable
16:12 1corintios-16-12-P05 | implicit-3S → ἐλεύσεται | labels=PROPÓSITO/EXPONE | state=stable
16:15 1corintios-16-15-P04 | implicit-3P → ἔταξαν | labels=RAZÓN/ACLARA | state=recovering
16:17 1corintios-16-17-P01 | implicit-1S → χαίρω | labels=PROPÓSITO/ACLARA | state=unstable
16:18 1corintios-16-18-P01 | implicit-3P → ἀνέπαυσαν | labels=RAZÓN/ACLARA/EXPONE | state=stable
16:22 1corintios-16-22-P02 | implicit-3S → ἤτω | labels=CONDICIÓN/EXPONE | state=stable
16:22 1corintios-16-22-P03 | implicit-2S → θά | labels=ACLARA | state=transitioning
```

## 5. Límite de lectura

Este archivo comprime persistencia estructural observada. No asigna títulos temáticos finales ni interpreta contenido.
