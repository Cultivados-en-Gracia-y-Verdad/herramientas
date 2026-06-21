# CGV markdown for authors

## Writer styles (Manual tab)

| Toolbar | Appearance | Saved in `manual.md` |
|---------|------------|----------------------|
| Contexto | H1, centered | `#` |
| Sección | H2, centered | `##` |
| Referencia | H3, Bible reference, flush left | `###` |
| Versículo | Verse block under H3 | plain line directly under `###` |
| H4 | Anchor text, scripture style | `####` |
| H5 | Comment level 1 | `#####` |
| H6 | Comment level 2 | `######` |
| Lista | Comment level 3 | `-   ` bullet under H5 (dash + three spaces) |
| Definición | Blue box | `término - X` then `: definición` |
| Cursiva (in comments) | Same as escritura | `*texto*` |
| Subrayado | Yellow highlight | `<u>texto</u>` (fill-in-the-blank) |

## Passage layout (blank lines)

```
# 1 TIMOTEO 1:1-20 EL ENCARGO Y SU PROPÓSITO

## 1 Timoteo 1:1 Autor de la carta: Un apóstol de Jesucristo

### 1 Timoteo 1:1
Pablo, apóstol de Cristo Jesús por mandato de Dios nuestro Salvador, y de Cristo Jesús nuestra esperanza,

#### Pablo, apóstol de Cristo Jesús
##### Pablo se identifica desde el comienzo como el autor de la carta y como un apóstol de Jesucristo.

##### Su autoridad no proviene de iniciativa personal. La carta presenta a Pablo como alguien que actúa bajo una comisión recibida de Dios.
-   Pablo escribe con autoridad apostólica.
-   La carta surge dentro de una responsabilidad que le fue confiada.
-   Esta autoridad será importante para las instrucciones que siguen.
```

Rules:

- `###` reference and verse text: **no** blank line between them.
- Verse block and `####` anchor: **one** blank line between them.
- `####` and the first `#####`: **no** blank line.
- Consecutive `#####` blocks: **one** blank line between them.
- `#####` and its bullet list: **no** blank line; each item uses `-   ` (three spaces after the dash).

Nesting (left margin increases at each level):

```
### Referencia bíblica
Versículo completo bajo la referencia
#### Texto ancla
##### Comentario nivel 1
###### Comentario nivel 2
-   Comentario nivel 3 (lista)
```

*Italic* inside comments uses the same «guillemet» styling as anchor text.

## Definition block

```markdown
término - TERMINO
: definición en español
```

## Presentation markers

`<!-- @quiz id -->` and blank lines between blocks for Presenter slides.
