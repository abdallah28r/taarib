# Arabic rendering, fonts, and layout

RTL alignment is not shaping or BiDi. Test separately: glyph coverage, joining,
run order, punctuation/numbers, container direction, wrapping, and clipping.

Use logical Unicode first with representative strings such as:

```text
اضغط F لفتح الباب
RTX 4080
المستوى 25
HP: 100
```

Never reverse characters. Pre-shape or generate visual order only after the
exact renderer is proven unable to handle logical Arabic. Keep transformed text
as generated output, never canonical translation memory. For a non-BiDi
renderer, wrap using actual font advances first, then shape/reorder each line.

Do not mirror the entire UI. Evaluate containers individually. Do not mirror
logos, portraits, maps, gameplay art, controller/weapon icons, or directional
symbols whose meaning would change.

Font priority: shipped Arabic coverage, shipped fallback, added licensed
fallback, then replacement. Inspect every used weight, fallback, icon font, and
atlas. `check_font.py` proves cmap coverage only, and `check_font.py --shape`
is a HarfBuzz smoke test only. Neither proves the game uses that renderer path.
GNU FriBidi gives a reference BiDi order to compare a renderer against;
msdf-atlas-gen builds SDF atlases when the engine renders text from them.
When an existing font is unsuitable or an external face may clearly fit the
game better, follow `references/font-sourcing.md` to search, compare, obtain,
record, and—only if required—install the selected font for this Windows user.

After discovering the game's actual font slots and visual style, make one
compact typography plan for this game. Compare the source type's character
(playful, formal, pixel, handwritten, etc.), proportions, weight, and hierarchy
with a small set of Arabic-capable, distributable candidates. Preview them in
representative game screens when available and authorized; otherwise use
captured UI/assets and record that in-game appearance remains unverified.
Choose for legibility and the game's visual identity, not glyph coverage alone.
Also compare contrast against the actual changing background and readability
at the smallest supported UI scale. Preserve the source asset's effects when
typesetting baked-in image text: do not invent an outline, shadow, backing
panel, or glow just to boost a numeric contrast score. If readability cannot
be achieved without altering the visual design, keep the asset as a review
case and seek a design-level solution rather than silently changing it.
Record only the selected role -> font/weight
mapping and any important constraint in `PROJECT.yaml` under `typography`;
record its exact files, rights, uses, and test result in `fonts/FONT_USAGE.json`.
do not create a report for every candidate or ask the user to choose each font.

Where the renderer supports separate slots and it improves coherence, assign
appropriate fonts or weights by role (for example headings, body/UI labels,
dialogue, numbers, or image-adjacent labels). Prefer a small coordinated family
or compatible set over a different font for every element. If slots cannot be
changed independently, document that limitation and choose the best supported
fallback. Icon fonts or glyph atlases may encode symbols in character slots:
preserve their glyph mapping; do not replace them as ordinary text fonts.
Check actual Arabic shaping, metrics, clipping, readability at game scale, and
license/redistribution terms for each selected role in the real renderer.

Use this plan as a visual reference for text baked into images, but preserve
each image's original lettering treatment first; the same Arabic typeface
need not be forced into every texture, logo-like label, or perspective effect.

For atlases, derive codepoints from the actual corpus and include punctuation,
digits, diacritics used, and relevant Arabic extensions. Presentation Forms are
not a substitute for shaping. Record the exact font license and reserved-name
terms before distribution.

For overflow, prefer shorter natural text, slight font adjustment, safe
container changes, then auto-sizing. Preserve meaningful line breaks and test
mixed Arabic/Latin/digits/placeholders at target resolutions and input modes.
