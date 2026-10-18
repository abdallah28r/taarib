---
name: arabic-game-translation
description: Translate or linguistically review player-facing game text into Arabic with consistent terminology, context, character voice, and protected syntax.
---

# Arabic game translation

Use for translation, editing, terminology, dialogue, subtitles, UI copy, or
linguistic review. Do not use it for archive extraction or font engineering.

## Load only the active route

Run one of these and read the returned required files:

```text
python scripts/context_plan.py translation-ui
python scripts/context_plan.py translation-dialogue
python scripts/context_plan.py subtitles
```

Add `--engine <engine-id>` only when engine behavior affects the text. Do not
load `GUIDE.md`, `STYLE.md`, every engine profile, or legal/model policy for an
ordinary translation batch.

## Work contract

- Translate player-visible meaning using the available speaker, scene, screen,
  neighboring strings, screenshots, and gameplay function.
- Preserve IDs, placeholders, tags, escapes, accelerator syntax, plural/select
  branches, and meaningful line breaks exactly.
- Follow approved terms and voice notes in `glossary.yaml`; record a new stable
  decision once rather than silently varying it.
- Never guess meaning-changing gender, kinship, puzzle, lore, or gameplay
  context. Mark it for review and continue with independent rows.
- Skip already approved Arabic targets. Use coherent scenes/screens rather than
  arbitrary row slices when context exists.
- Write each translation into its unit (`target`, `status: translated`,
  `translated_by`, `batch`) per `references/translation-units.md`, then run
  `python scripts/loc.py validate` and the native format validator. Report
  counts from `loc.py progress`, not from memory.

Use a representative pilot only when tone, terminology, text type, or the
translation route is genuinely new. Do not repeat it for every resumed batch.
If delegation is useful, invoke `localization-subagent-orchestration`; the root
agent performs deterministic integration checks and risk-based sampling rather
than retranslating every line.
