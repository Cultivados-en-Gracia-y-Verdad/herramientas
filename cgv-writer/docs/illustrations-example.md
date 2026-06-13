# Illustrations example (draft)

This is a **preview of one possible model**, not a final spec. The goal is to show how text (`manual.md`) and illustrations can stay separate so PDF builds ignore them and Presenter can still step through images.

## Course folder (unchanged idea)

```
courses/Santiago/
  manual.md
  quizzes/
    santiago-2-1-26.yaml
  images/
    portada.png
  illustrations/                    ← new, optional
    santiago-2-14-faith-works.json
    santiago-2-14-faith-works/
      01-faith-alone.png
      02-works-visible.png
      03-together.png
```

PDF build keeps using **`manual.md` only** (today’s pandoc script). Nothing new required in Writer for PDF.

## 1. What stays in `manual.md` (Presenter already cares about this)

Normal CGV structure. One extra line where you want a diagram—same *idea* as `<!-- @quiz ... -->`:

```markdown
### Santiago 2:14

¿De qué sirve, hermanos míos, si alguno dice que tiene fe…?

#### Fe sin obras

##### Comentario
- La fe que no se ve en la vida no es la fe de la que habla Santiago.

<!-- @illustration santiago-2-14-faith-works -->
```

- **PDF:** Renders the headings and bullets; the HTML comment is invisible (or omitted).
- **Presenter:** At this slide, can offer “Show illustration” and advance **steps** from the sidecar (below).

If you never add illustrations, you never add these lines—Writer is just a better way to edit `manual.md`.

## 2. Sidecar: `illustrations/santiago-2-14-faith-works.json`

```json
{
  "id": "santiago-2-14-faith-works",
  "title": "Fe y obras",
  "steps": [
    {
      "image": "illustrations/santiago-2-14-faith-works/01-faith-alone.png",
      "caption": "Fe declarada"
    },
    {
      "image": "illustrations/santiago-2-14-faith-works/02-works-visible.png",
      "caption": "Obras visibles"
    },
    {
      "image": "illustrations/santiago-2-14-faith-works/03-together.png",
      "caption": "Juntas en la vida del creyente"
    }
  ]
}
```

Presenter loads `id` from the marker, reads this file, shows step 1 → 2 → 3 (like building a slide in PowerPoint, but **authored in Writer**, not typed into markdown).

## 3. What you might see in CGV Writer (not Presenter)

```
┌─────────────────────────────────────────────────────────────┐
│  manual.md (outline)          │  Illustration (optional)     │
├───────────────────────────────┼──────────────────────────────┤
│  ## Capítulo 2                │  santiago-2-14-faith-works │
│    ### 2:14                   │  ┌────┐ ┌────┐ ┌────┐       │
│    #### Fe sin obras          │  │ 1  │ │ 2  │ │ 3  │  +    │
│    ##### Comentario           │  └────┘ └────┘ └────┘       │
│    📎 illustration linked     │  captions under each thumb   │
└─────────────────────────────────────────────────────────────┘
```

- **Left:** Word-like outline + body for the manual (headings, verse, definitions).
- **Right:** Only when you select a slide that has `@illustration`—a simple **storyboard** (reorder steps, swap images). Not mixed into the paragraph flow.

That is the “cross between Word and simplified PowerPoint”: Word for text; a small storyboard panel for steps—not a full deck editor.

## 4. What Presenter would do in class (future)

On the slide that contains the marker:

1. Projector shows the usual text (same as today).
2. You tap **Show illustration** (or it auto-opens if you prefer).
3. Projector shows image 1, then 2, then 3 (arrow keys / click).
4. Dismiss → back to text slide.

No change to PDF; students with printed manual never see the PNG sequence unless you add figures to LaTeX separately later.

## 5. Simpler alternative (if markers feel heavy)

Skip comments in `manual.md`. Instead, a single `illustrations/index.json` maps **slide number** → sequence:

```json
{
  "bySlideIndex": {
    "142": "santiago-2-14-faith-works"
  }
}
```

Easier for tools, harder for authors (“what is slide 142?”). The `@illustration` marker is usually clearer because it sits next to the passage you are teaching.

## 6. What you can decide later

| Question | Options |
|----------|---------|
| Link in md? | `<!-- @illustration id -->` vs slide index only |
| Auto-show? | Manual button vs auto when slide opens |
| Animation | Step images only first; fades later |
| Writer v1 | **Md only**—add illustration panel in v2 |

**Recommendation:** Ship Writer v1 as fast md authoring + outline; add the storyboard panel once you have tried one real diagram (e.g. one Santiago passage) using the folder layout above.
