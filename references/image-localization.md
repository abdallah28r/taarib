# Image localization decision and review policy

Use this reference only for images or textures containing player-visible text.

## Decide whether to translate

Classify each independent text region before editing:

- `TRANSLATE`: ordinary UI labels, buttons, instructions, warnings, maps, signs,
  or story/gameplay text whose reading is useful and whose image can be changed
  without distorting the artwork or introducing new information.
- `KEEP`: decorative or identity-bearing text embedded in clothing, accessories,
  character design/body details, food, packaging, products, cosmetics,
  consumables, weapons, or tools used by characters. Also keep logos, brands,
  signatures, incidental scenery text, illegible microtext, and any region whose
  translation would require a new caption, explanatory box, or design change.
- `REVIEW`: the function is ambiguous, context is missing, or the same asset may
  be decorative in one scene and gameplay-critical in another.

A standalone nameplate whose purpose is to identify a character or place is
`TRANSLATE` when its spelling is approved in the glossary and the localized
name fits the original design. This does not license changing a name embedded
in clothing, a logo, a brand, or decorative artwork. The same names in ordinary
game text follow the translation glossary, not the image `KEEP` default.

Gameplay/story-critical text may override the category default only when the
translation can replace the original text inside the same design without
distortion or invented information. Otherwise classify it `KEEP`. Never solve
an unsafe image edit by adding a subtitle, tooltip, caption, legend, or external
overlay that did not exist in the source.

## Preserve the original style

Inspect and record only properties that affect the edit: fill, outline and its
width (including none), shadow (including none), glow (including none), opacity,
font character, weight, spacing, alignment, baseline, rotation, perspective,
texture, and blending. Absence is a property: a source with no black outline
must not gain a black outline for readability.

Do not simplify a textured or perspective-integrated label into flat text. Do
not improve contrast by inventing a panel, stroke, shadow, or glow. If the
required Arabic cannot remain readable without such an invention, reject the
candidate and keep the source.

### Match text size without sacrificing the design

The original text's visible ink bounds, height, width, baseline, and occupancy
are comparison evidence, **not targets to maximize**. Preserve intentional
empty space and the full image's visual balance. Priority: correct, readable
Arabic; intact artwork/composition; faithful typographic character; then
approximate scale. A numerical occupancy or width match never justifies an
uglier image. This matters especially for images made mostly of text: compare
the complete native-size asset and its neighboring UI, not just a tight crop.

If the Arabic looks too small, try suitable non-distorting routes: a better
Arabic face, native font size/weight, tracking, line spacing, alignment, line
breaks, and safe layout inside the existing design. Do not resize the whole
image to fit text, stretch or squeeze glyphs non-uniformly to hit a target
width, add an outline/shadow/panel, or move text outside the image. Stop
enlarging when the next gain in size makes the result cramped, disproportionate,
or less attractive. A slightly smaller but balanced rendering can be better
than an exact-width rendering with distorted letters.

Before reusing an older generator or an already approved image, inspect how
the lettering was made. A saved approval or passing pixel gate does not
grandfather a candidate under the current visual policy. If a script resized
rendered glyphs merely to occupy the source text width, flag its outputs for
full-image, native-size comparison with the pristine source and a natural-
proportion alternative. Replace only a visually inferior candidate after
review; never discard a correct translation or rebuild the game solely from a
stretch factor or occupancy number.

Use the native-size view for the decision and a zoomed view for diagnosing
glyph edges. Compare candidate variants as whole images. If the candidate
still differs after useful routes are tried, keep the best readable,
non-distorting, visually balanced candidate and record the limitation for
review; do not reject the translation solely because its size is imperfect.
For each newly approved or reworked text-only image, compare visible ink and
record `source_text_bounds`, `target_text_bounds`, `source_visible_height`,
`target_visible_height`, `visual_scale_ratio`, `size_match`, and a concise
`fit_attempts` note where the lettering can be isolated reliably. When it
cannot, record why measurement is unreliable and give a direct visual finding
instead. Do not backfill invented measurements into older approvals. No fixed
ratio is a pass/fail threshold: Arabic glyph proportions and line layout can
differ from the source. The measurements support visual judgment, not replace
it. For illustrated images, record the same data only where it helps resolve a
size concern. Use `size_match: close` when the scale fits, or `best-safe` with a
short limitation note when further enlargement would distort the design;
`needs-improvement` marks an unfinished candidate, not a rejection of the
translation.

When choosing or generating Arabic lettering, compare it with the original
image's typography **first** and with the game's selected Arabic typography
plan (`PROJECT.yaml` -> `typography.role_fonts`) **second**. Match the original
role, mood, weight, proportions, and treatment while keeping related UI assets
visually coherent. Reuse a selected in-game font only when it also fits this
image; a distinct source style may need a different licensed Arabic face or
carefully matched lettering. Do not force one font onto every image, replace
symbol/icon glyphs as text, or invent outlines or effects to hide a mismatch.
Judge the result in-game or in its adjacent UI context when available, not as
an isolated crop alone. If the font choice cannot preserve the source design,
reject the edit and keep the source image.
If a different Arabic face is needed, use the project font search and rights
route in `references/font-sourcing.md`; do not limit image lettering to fonts
already installed on the machine. Record the selected font's image/asset use
in `fonts/FONT_USAGE.json` without duplicating the per-region image manifest.

## Adaptive candidate search

Do not run every expensive method on every image. Choose routes from the image:

1. Flat opaque UI: deterministic cleanup/rebuild and Arabic typesetting first.
2. Transparent text texture: rebuild the transparent text layer; use dark,
   light, and checkerboard previews. Avoid inpainting the full transparent
   canvas.
3. Complex artwork: use a tight text mask. Try restoration plus deterministic
   typesetting and, when authorized, an OpenAI full-text candidate if matching
   perspective/style is the harder problem.
4. DDS/BC or engine texture: edit a lossless working copy, then reproduce the
   source format, mip chain, compression, and alpha behavior only after the
   visual candidate is accepted.

Start with one candidate for simple assets and at least two meaningfully
different candidates for complex or uncertain assets. Open and inspect each
serious candidate. Expand to another route only when the current candidate
fails visually or technically. Stop when a candidate passes; if all useful
routes fail, preserve the original.

## Official OpenAI image-editing modes

When the new-game intake approved it (`PROJECT.yaml` →
`image_localization.external_image_editing.enabled: "yes"`), choose a mode only after the region
is `TRANSLATE`. The authorization applies to this project's images, not to
other external services. These are prompt contracts, not fixed model names:

- `background-only`: supply the untouched source and a tight text mask. Ask to
  remove only the source lettering and reconstruct the hidden background. Add
  **no text**. Keep characters, clothing, objects, colors, lighting, framing,
  perspective, dimensions, and transparency unchanged. Composite the restored
  region into the source, then typeset exact glossary-approved Arabic separately.
- `full-text-candidate`: supply the source, tight allowed region, and the exact
  approved Arabic. Ask to replace only the source lettering inside that region
  while matching its existing placement, perspective, fill, opacity, outline,
  shadow, glow, and texture (including their absence). Add no other lettering,
  panel, caption, decoration, or artwork change. This is a candidate, never an
  automatically accepted result.

For either mode, append only the relevant image-specific facts: file name,
source/target text, allowed region or mask, surface/background description,
and protected subjects. A model may choose how to reconstruct pixels inside
the permitted region; it may not change the classification or expand that
region. If the raw result changes dimensions or anything outside the region,
normalize and composite from the untouched source; reject it if fidelity
cannot be restored. Do not assume generative Arabic is wrong or right: inspect
the exact spelling and appearance visually.

## Lightweight region record

Keep one JSON record per changed image under an `images` array. Required:
`image`, `source`, `source_sha256`, and `regions`; each region records `box`,
`decision` (`TRANSLATE`/`KEEP`/`REVIEW`), and `reason`. For a translated
region also record `target_text` and `review_status`
(`pending`/`approved`/`rejected`). Put the candidate path once at image level;
record its SHA-256, `method`, `visual_reviewed: true`, and `technical_qa: pass`
before approving a region. Add a tight mask, source transcription,
prompt/model, or QA notes only when relevant. For an approved region, include
`visual_review` with `reviewer: agent`,
`source_opened: true`, `candidate_opened: true`, and a short `findings` sentence
about typography, artwork, and any remaining source text. These fields record
the agent's actual comparison; they cannot prove a model opened an image. Run
`python scripts/check_image_regions.py <manifest.json>` to verify source hashes,
dimensions, mode, and no changed pixels outside `TRANSLATE` boxes. This is a
compact decision trail, not an obligation to populate dozens of empty fields.

## Visual review is mandatory

The reviewing agent must actually open the source and candidate images. Compare
at native scale and zoomed scale, side by side; inspect transparent assets over
dark, light, and checkerboard backgrounds. For generative edits, also blink or
overlay source/candidate and inspect the allowed-mask boundary.

Repair or reject a candidate when any of these is true after suitable attempts:

- Arabic spelling, shaping, order, or terminology is wrong.
- placement, baseline, perspective, weight, color, opacity, spacing, or style
  distorts the source, or clashes with adjacent assets without a source-style
  reason. A size difference alone calls for improvement, not automatic
  rejection; retain the best readable, non-distorting, visually balanced
  result with a review note if a closer match cannot be reached safely;
- an outline, shadow, glow, panel, decoration, or extra glyph was invented;
- source text remains, background reconstruction is blurred/repeated, or a
  character, face, clothing, prop, lighting, composition, or transparency
  changed unintentionally;
- the image passes numeric checks but looks worse or inconsistent with adjacent
  game assets.

Automated checks remain required: dimensions, mode, alpha semantics, outside-
mask diff, residual source-script detection, clipping, exact text, glossary,
native format, mipmaps, and compression. They cannot approve a visually poor
image by themselves.

## Tested tool roles

- Pillow/ImageMagick: deterministic UI typesetting and compositing. Fit Arabic
  to the measured region; do not add style effects absent from the source.
- OpenCV Telea/Navier-Stokes: small flat regions only; complex art may blur.
- LaMa/IOPaint: restoration candidate with a tight mask and a residual-text
  retry loop. Treat IOPaint as replaceable because the repository is archived.
- PaddleOCR/Tesseract: candidate detection only when local OCR is authorized;
  transparent microtextures need alpha-aware backgrounds and upscaling.
- SAM2-class segmentation: refine the containing object or surface, then
  intersect with text evidence; it is not a text detector.
- OpenAI official image editing: permitted only when the project intake approved it.
  Raw output dimensions and surrounding art are untrusted; normalize and
  composite only inside the allowed mask. Full-text is a reviewed candidate,
  not an automatic final asset.
- DirectXTex/texconv: reproduce/verify required DDS formats; block compression
  is lossy and must not be introduced when the source does not require it.
