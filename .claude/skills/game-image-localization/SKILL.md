---
name: game-image-localization
description: Classify, translate, rebuild, compare, and visually review text baked into game images or textures while preserving artwork, style, alpha, dimensions, and native format.
---

# Game image localization

Use this skill for text baked into UI images, transparent labels, signs, maps,
illustrations, or engine textures. Do not use it for ordinary runtime strings.
For a new game, honor the one-time image-scope choice recorded in
`PROJECT.yaml`; if the user opted out, leave baked images untouched and do not
invoke image editing merely because the tool is available.

## Load the image route

```text
python scripts/context_plan.py images --engine <engine-id>
```

Read the returned files, especially `config/image-localization-policy.yaml` and
`references/image-localization.md`. Project-specific engine evidence overrides
generic tool preferences, but not the preservation and review gates.

## Binding outcome

1. Classify every text region as `TRANSLATE`, `KEEP`, or `REVIEW` before editing.
2. Never remove, cover, caption, or translate a `KEEP` region.
3. If a translation would distort the artwork, invent information, add a new
   label/caption, or materially change the design, leave the original image
   unchanged. Do not move the translation outside the image as a workaround.
4. Match the original text treatment. Do not invent an outline, shadow, glow,
   panel, texture, decoration, color, weight, or contrast treatment.
5. Match apparent text scale where it improves the full image; never maximize
   coverage at the expense of beauty or readability. Visible-ink measurements
   are diagnostic, not targets. Try suitable font and layout options, but do
   not resize the whole image or stretch/squeeze glyphs non-uniformly to fill
   a box. Stop when further enlargement worsens balance; keep the best
   readable, non-distorting candidate even if smaller, with a short review
   note. Text-only images need extra whole-image size/balance comparison.
   Before reusing an old approved candidate or generator, inspect its glyph
   transformations; prior approval and numeric gates do not waive a fresh
   native-size visual check when the method stretched text to fill a box.
6. Use adaptive candidate search. Inspect the source and every serious
   candidate visually; numeric scores and diff metrics are gates and evidence,
   never proof of visual quality.
7. A generated or inpainted result is a candidate only. Preserve the untouched
   source, restore exact dimensions/alpha/native format, composite changes only
   in the allowed region, and require review before integration.

For a standalone character/place nameplate, use the approved glossary spelling
when the name is the image's useful content; the embedded-design `KEEP` rule
does not apply. For official OpenAI editing, use the `background-only` or
`full-text-candidate` prompt contract in `references/image-localization.md`.
When selecting an external font for image text, read
`references/font-sourcing.md`; do not assume the system's installed fonts are
the only choices. Keep source-image typography as the primary visual constraint.
Record changed regions in a lightweight manifest and run
`python scripts/check_image_regions.py <manifest.json>` before approval. The
check complements, never replaces, opening and comparing the actual images.
For each approved region, record a concise agent visual-review finding after
opening both source and candidate. A self-reported flag or numeric score alone
is not evidence of review.

Stop when one candidate passes both the hard technical gates and direct visual
comparison. If none passes after the useful bounded routes are exhausted, keep
the source unchanged and record the rejected candidates and reason.
