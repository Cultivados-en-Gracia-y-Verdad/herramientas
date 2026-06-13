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
| Lista | Comment level 3 | `-` bullet under H6 |
| Definición | Blue box | `término - X` then `: definición` |
| Cursiva (in comments) | Same as escritura | `*texto*` |
| Subrayado | Yellow highlight | `<u>texto</u>` (fill-in-the-blank) |

Nesting (left margin increases at each level):

```
### Referencia bíblica
Versículo completo bajo la referencia
#### Texto ancla
##### Comentario nivel 1
###### Comentario nivel 2
- Comentario nivel 3 (lista)
```

*Italic* inside comments uses the same «guillemet» styling as anchor text.

## Definition block

```markdown
término - TERMINO
: definición en español
```

## Presentation markers

`<!-- @quiz id -->` and blank lines between blocks for Presenter slides.
