# QA and review strategy

Run deterministic structural checks on 100% of changed units. Semantic review
is risk-based; do not spend tokens rereading every low-risk approved line.

## Required coverage

- Native parser/schema and encoding.
- Stable identity inventory: missing, extra, empty, stale, duplicate, unchanged.
- Protected tokens, markup, escapes, accelerators, plural/select branches.
- Contextual glossary conformance and suspicious Latin/mojibake/control text.
- Renderer matrix for Arabic joining, BiDi, fonts, mixed text, wrapping, and
  clipping when the relevant layer changes.

## Semantic sampling

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

For in-game defects record screen/key, build, locale, resolution, input mode,
observed/expected behavior, severity, layer, and reproduction once in
`qa/LQA_MATRIX.csv`. Keep `reports/QA.md` to the summary and `STATUS.md` to
blockers/next action; do not copy the full defect into all three. Fix the smallest
responsible layer and retest the same case plus a mixed-text regression.

Do not launch the game or upload logs/screenshots without current authority.
