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
5. Use adaptive candidate search. Inspect the source and every serious
   candidate visually; numeric scores and diff metrics are gates and evidence,
   never proof of visual quality.
6. A generated or inpainted result is a candidate only. Preserve the untouched
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
