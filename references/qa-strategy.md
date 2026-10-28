# QA and review strategy

Run deterministic structural checks on 100% of changed units. Semantic review
is risk-based; do not spend tokens rereading every low-risk approved line.

## Required coverage

- Native parser/schema and encoding.
- Stable identity inventory: missing, extra, empty, stale, duplicate, unchanged.
- Protected tokens, markup, escapes, accelerators, plural/select branches.
- Arabic plural behavior at 0, 1, 2, 3, 11, and 100 when the format supports
  pluralization; validate with the game's actual formatter, not regex alone.
- Contextual glossary conformance and suspicious Latin/mojibake/control text.
- Renderer matrix for Arabic joining, BiDi, fonts, mixed text, wrapping, and
  clipping when the relevant layer changes.
- Text complete in the units is not proof it shows complete: measure long
  strings in the real font against their box (choices, buttons), then check
  in the renderer.
- Visible text outside the translation catalogue: literals in screen or UI
  code, labels that appear only after an unlock, and baked images.

## Semantic sampling

Every translated unit is proofread once by an independent agent
(`arabic-proofreading`). The sampling below is the QA layer on top of that:
in-game and cross-batch checks, not a replacement for proofreading.

Review all high-risk units: ambiguity, wordplay, sensitive content, dense
markup, variables affecting grammar, changed source, new terminology, and prior
failures. For established low-risk UI or repeated patterns, review a
representative sample and expand it only when defects appear. Record sample,
defect classes, and escalation reason.

`loc_qa.py` handles supported CSV/TSV and structured files. `format_qa.py`
handles PO/XLIFF and common ICU plural/select structures, including inline-code
identity. For full ICU quoting/format support and engine-specific XLIFF/PO
constraints, use the native validator as well. QA warnings are candidates,
not automatic linguistic verdicts.

Use `qa/LQA_MATRIX.csv` for one row per distinct in-game defect or regression.
Its fields are `id`, `category`, `build`, `scene_or_key`, `locale`,
`resolution`, `input_mode`, `expected`, `observed`, `severity`, `layer`,
`reproduction`, `evidence`, `status`, and `retest`. Enter `n/a` when a field
does not apply; do not invent evidence. The starter rows are test cases, not
claims of completed in-game checks. Keep `PLAN.md` to blockers/next action;
do not copy the full defect there. Fix the smallest responsible layer and retest the same case plus a
mixed-text regression.

Script and image-region checks cover only their documented structural scope.
The agent must visually compare source/candidate images and test engine-native
formats, texture encoding, mips, and rendering when relevant. A synthetic
unit-test pass or manifest field claiming `visual_reviewed` never proves an
in-game visual pass.

Format tools when the game's text is in a standard format: Translate Toolkit
(`pofilter`, `pocount`, `po2tmx`) and gettext `msgfmt --check` for PO/XLIFF,
Okapi for filter-based extraction checks and pseudo-localization of formats
`loc.py pseudo` does not cover. LanguageTool only after measuring its Arabic
false positives on the game's names and tone.

Do not launch the game or upload logs/screenshots without current authority.
