---
name: game-image-localization
description: Classify, translate, rebuild, compare, and visually review text baked into game images or textures while preserving artwork, style, alpha, dimensions, and native format.
---

# Game image localization

Use for text baked into UI images, labels, signs, maps, illustrations, or
engine textures, not for runtime strings. If the intake set
`workflow.image_scope: no`, leave baked images untouched.

```text
python scripts/context_plan.py images --engine <engine-id>
```

`references/image-localization.md` is the full rule set; this is its outline.
Project engine evidence may change tool choice, never the preservation and
review gates.

1. Classify every region `TRANSLATE`, `KEEP`, or `REVIEW` before editing, and
   record each one (including `KEEP`) as a `kind: image` unit.
2. Never touch a `KEEP` region. If a translation would distort the art,
   invent information, or need a new caption, keep the source image.
3. Match the source treatment exactly; invent no outline, shadow, glow, panel,
   or contrast fix. Scale is matched by font and layout, never by stretching
   glyphs or resizing the image.
4. Search adaptively, one candidate for simple assets and two for complex ones;
   generated or inpainted output is only a candidate.
5. Open source and candidate and compare them; record the finding and run
   `python scripts/check_image_regions.py <manifest.json>`. Numbers are
   gates, never proof of quality.
6. Stop at the first candidate that passes both. If none does, keep the source
   and record why.
