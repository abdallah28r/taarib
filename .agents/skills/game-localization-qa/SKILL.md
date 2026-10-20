---
name: game-localization-qa
description: Validate localized game files and diagnose Arabic rendering, RTL, fonts, layout, terminology, update, or in-game screenshot defects.
---

# Game localization QA

Use for structural checks, linguistic risk sampling, fonts, RTL/BiDi, layout,
screenshot triage, and regressions. It is not a substitute for extraction or
translation.

## Choose one route

```text
python scripts/context_plan.py qa-structural
python scripts/context_plan.py qa-rendering --engine <engine-id>
```

Read only the returned files. The detailed strategy and renderer decision tree
live in those references and are not repeated here.

## QA contract

- Parse the native format first, then run `loc_qa.py` or `format_qa.py` for the
  supported interchange artifact.
- For rendering questions before translation exists, use the pseudo-Arabic
  build from `loc.py pseudo` rather than waiting for real text.
- Treat lost tokens, duplicate IDs, schema/parse errors, encoding corruption,
  and missing required entries as blockers.
- Use 100% deterministic structural checks. Use semantic sampling targeted by
  risk: new tone, ambiguity, variables, glossary conflicts, outliers, and
  changed-source rows. Full retranslation is not the default review method.
- Diagnose glyph coverage, shaping, BiDi direction, layout direction, and
  clipping as separate layers. Logical Unicode Arabic remains canonical.
- Runtime evidence is authoritative for rendering. Never launch the game or
  upload logs unless the current task authorizes it.
- Mark units `integrated` only with the build they entered and `tested` only
  with what was observed in the running game (`loc.py mark --evidence`). A
  passing validator is never evidence for `tested`.
- Record each distinct defect once in `qa/LQA_MATRIX.csv` with screen/key,
  environment, observed/expected result, severity, evidence, and retest.

Update `reports/QA.md` at a QA milestone, blocker, or handoff with concise
counts, blockers, and untested areas; do not rewrite a full report after every
clean translation batch. `PLAN.md` gets only the blocker and next action.
