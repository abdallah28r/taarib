# Image localization: decisions, style, search, review

The single source for baked-image text. `config/image-localization-policy.yaml`
mirrors the same rules as data; this file wins if they ever differ.

## 1. Classify every text region first

- `TRANSLATE`: UI labels, buttons, instructions, warnings, maps, signs, or
  story/gameplay text worth reading, when the image can change without
  distortion or new information.
- `KEEP`: text embedded in clothing, accessories, character design, food,
  packaging, products, cosmetics, consumables, or weapons/tools characters use;
  logos, brands, signatures, incidental scenery, illegible microtext; anything
  whose translation would need a new caption, box, or design change.
- `REVIEW`: function unclear, context missing, or decorative in one scene and
  critical in another.

A standalone character/place nameplate is `TRANSLATE` when its glossary
spelling is approved and fits the design; this never extends to names in
clothing, logos, or decoration. Critical text may override a `KEEP` category
only if it can be replaced inside the same design without distortion.
Never add a subtitle, tooltip, caption, legend, or overlay that the source lacks.

## 2. Preserve the source style

Record only properties that affect the edit: fill, outline (width or none),
shadow (or none), glow (or none), opacity, font character, weight, spacing,
alignment, baseline, rotation, perspective, texture, blending. Absence is a
property: no outline in the source means no outline in Arabic. Never flatten a
textured or perspective label, and never fix contrast with an invented panel,
stroke, shadow, or glow; if Arabic cannot stay readable without one, keep the
source.

**Typography:** compare with the source image's lettering first and with
`PROJECT.yaml` → `typography.role_fonts` second. Reuse a game font only if it
fits this image; a distinct style may need another licensed Arabic face
(`references/font-sourcing.md`, not just installed fonts). Do not force one
font on every image or retype icon glyphs. Record image font use in
`fonts/FONT_USAGE.json`.

**Size:** priority is readable correct Arabic > intact artwork > source
typography > approximate scale > occupancy numbers. Visible-ink bounds are
evidence, not a target to maximize; keep intentional empty space. If Arabic
looks small, try face, size, weight, tracking, line spacing, alignment, line
breaks, and safe layout inside the design. Never resize the whole image,
stretch or squeeze glyphs non-uniformly, add effects, or move text outside.
Stop enlarging when the next step hurts balance; a slightly smaller balanced
result beats exact width with distorted letters.

For each new or reworked **text-only** image, record `source_text_bounds`,
`target_text_bounds`, `source_visible_height`, `target_visible_height`,
`visual_scale_ratio`, `size_match` (`close` | `best-safe` with a note |
`needs-improvement` = unfinished), and a short `fit_attempts` note; if the ink
cannot be isolated, say why and give a visual finding. No ratio is pass/fail.
For illustrated images, measure only to settle a size question. Never backfill
invented measurements into older approvals.

**Reusing old candidates:** a prior approval or passing pixel gate does not
carry over. Check how the lettering was made; if glyphs were resampled only to
fill the source width, compare the full image at native size against the
pristine source and a natural-proportion alternative, and replace only a
visually worse result. Never discard a correct translation over a stretch
factor alone.

## 3. Adaptive candidate search

Pick routes by image type; do not run every method on every image:

1. Flat opaque UI: deterministic cleanup and Arabic typesetting first.
2. Transparent text texture: rebuild the text layer; preview on dark, light,
   and checkerboard; never inpaint the whole transparent canvas.
3. Complex artwork: tight mask, restoration plus typesetting; an OpenAI
   full-text candidate (if approved) when perspective/style is the hard part.
4. DDS/BC or engine texture: edit a lossless copy; reproduce format, mips,
   compression, and alpha only after the visual candidate is accepted.

One candidate for simple assets, at least two different ones for complex or
uncertain assets. Expand only after a visual or technical failure. Stop at the
first candidate that passes; if every useful route fails, keep the source.

## 4. OpenAI image editing (on whenever images are in scope)

Allowed when images are in scope and `PROJECT.yaml` →
`image_localization.external_image_editing.enabled` is `"yes"` (the default),
only for `TRANSLATE` regions, and only for this project's images. It runs
through Codex's built-in image tool in both runtimes; Claude Code has no image
tool of its own and reaches it with the same script:

```text
python scripts/image_candidate.py codex --source <png> --box x0 y0 x1 y1 --text "<approved Arabic>" [--mask <png>]
python scripts/image_candidate.py composite --source <png> --raw <raw png> --mask <png> --out <candidate png>
```

The first writes Codex's edit to `work/images/raw/`. The built-in tool takes no
mask and no output size, so a raw edit is never a candidate:
`composite` resizes it to the source and copies back only the pixels inside
the mask (or box); everything outside is the untouched source. Then record the
candidate and run `check_image_regions.py`.

Every candidate is a numbered version of its source image in
`work/images/attempts.json`: `codex` and `composite` add theirs, and
`image_candidate.py record --source <png> --candidate <png> --method typeset`
adds one made another way. After looking at a version, give it a verdict and
its reason with `image_candidate.py verdict --source <png> --version N
--verdict accepted|rejected --reason "..."`. `images.html` shows the source,
the accepted candidate with a comparison slider, and every version with its
verdict, so the user sees what was tried. Flag an image that gives away the
story with `image_candidate.py spoiler --source <png> --reason "..."` (or
`"spoiler"` in its manifest entry), and record `--none` for one that does not;
the page blurs flagged images until clicked, as `PROJECT.yaml` →
`reporting.spoilers` says (`flagged`, `all`, `none`). The localization gate
refuses a translated image without an accepted version and its reason, or
without this spoiler decision.

Each source image gets at most `image_localization.max_generative_attempts`
Codex edits (default 5); the script counts them in `work/images/attempts.json`
and refuses beyond the cap. Change one thing per retry (wording of the style,
mask, or box). At the cap, keep the source or mark the region `REVIEW` with
the reason. Codex usage limits are real: a refused or failed call is not a
reason to switch to another service.

Prefer deterministic typesetting (section 3) when the background is flat; use
Codex when perspective, texture, or a rebuilt background is the hard part.
The model may not reclassify or widen the region. Every result is a
candidate; check its Arabic visually.

## 5. Records

- Every region (including `KEEP`) is a `kind: image` translation unit
  (`references/translation-units.md`) so image text is searchable and counted.
- Changed images also get one manifest entry under `images` in a
  `work/images/*.json` region manifest (the localization gate checks every
  translated image unit is listed there and passes): `image`,
  `source`, `source_sha256`, `regions` (`box`, `decision`, `reason`; plus
  `target_text` and `review_status` when translated). At image level: the
  candidate path, its SHA-256, `method`, `visual_reviewed: true`,
  `technical_qa: pass`. For approved regions, `visual_review` with
  `reviewer: agent`, `source_opened: true`, `candidate_opened: true`, and one
  `findings` sentence. Mask, transcription, prompt/model only when relevant.
- `python scripts/check_image_regions.py <manifest.json>` checks hashes,
  dimensions, mode, and that nothing changed outside `TRANSLATE` boxes. It
  cannot prove an image was looked at.

## 6. Visual review is mandatory

Open the source and the candidate. Compare side by side at native size (the
decision) and zoomed (glyph edges); transparent assets on dark, light, and
checkerboard; generative edits also by overlay at the mask boundary; judge in
the adjacent UI when possible, not as a crop alone.

Repair or reject when, after reasonable attempts: Arabic spelling, shaping,
order, or terminology is wrong; placement, baseline, perspective, weight,
color, opacity, spacing, or style distorts the source or clashes with nearby
assets (size alone means improve, not reject); an outline, shadow, glow,
panel, decoration, or glyph was invented; source text remains, the background
is blurred or repeated, or any subject, lighting, composition, or transparency
changed; or the image passes the numbers but looks worse.

Automated gates still apply: dimensions, mode, alpha, outside-mask diff,
residual source script, clipping, exact text, glossary, native format, mips,
compression. They never approve a visually poor image by themselves.

## 7. Tool roles

- Pillow/ImageMagick: deterministic typesetting and compositing, no added effects.
- OpenCV Telea/Navier-Stokes: small flat regions only.
- LaMa/IOPaint: restoration with a tight mask and a residual-text retry;
  IOPaint is archived, keep it replaceable.
- PaddleOCR/Tesseract: detection only, when local OCR is authorized.
- SAM2-class segmentation: refines surfaces; not a text detector.
- OpenAI image editing: section 4; raw output is untrusted.
- texture2ddecoder decodes BC/DXT/ETC/ASTC textures for review and etcpak
  re-encodes DXT/ETC without resizing; python-zstandard opens zstd-compressed
  emulator states and archives.
- DirectXTex/texconv: reproduce DDS formats; never add block compression the
  source lacks.
