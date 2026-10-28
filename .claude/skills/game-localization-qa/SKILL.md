---
name: game-localization-qa
description: "Use when checking localized files or a build for structural, rendering, RTL, font, layout, or terminology defects, or when the user reports an in-game problem or screenshot. Triggers: فحص، خطأ في اللعبة، حروف مقطعة، اتجاه النص، الخط، لقطة شاشة."
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
- A small playtest report (a wrong line, a clipped label) goes through the fix
  lane instead of reopening a phase: `loc.py fix open` with what happens now,
  what should happen, and what must not change, then `apply --fix`, proofread,
  `fix close` with a verdict. Reopen a phase only for systemic problems.
- Never assume a defect lives only where it was seen. Before `fix close`, look
  for its siblings: `loc.py search` for the same term, wording, or problem code;
  other screens, boxes, and fonts of the same kind; other files of the same
  format. Fix every hit in the same lane (`--ids`), or note why each is safe,
  and add a QA rule or test when one would catch it next time.
- Record each distinct defect once in `qa/LQA_MATRIX.csv` with screen/key,
  environment, observed/expected result, severity, evidence, and retest.

`PLAN.md` gets only the blocker and next action; the dashboard shows the counts.
