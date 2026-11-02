---
name: arabic-game-translation
description: "Use when translating player-facing game text into Arabic, editing existing Arabic targets, or settling terminology and character voice for a batch. Triggers: ترجمة، تعريب النصوص، دفعة ترجمة، صوت الشخصية، مصطلح."
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
load every engine profile, style reference, or legal/model policy for an
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
- Return a batch as one JSON object keyed by unit id and write it with
  `loc.py apply <file> --batch <batch> --by <label>`: it refuses the whole
  batch if any id is missing, extra, or empty, so lines can never shift or be
  dropped. Then run the native format validator. Report counts from
  `loc.py progress`, not from memory.
- To redo only the units with one problem, list them with `loc.py search
  --problem <code> --ids-only` and send just those ids back through `apply`.

Use a representative pilot only when tone, terminology, text type, or the
translation route is genuinely new. Do not repeat it for every resumed batch.
Hand every finished batch to an independent proofreader (`arabic-proofreading`
skill, `proofreader` role); never proofread your own batch.
If delegation is useful, invoke `localization-subagent-orchestration`; the root
agent performs deterministic integration checks and risk-based sampling rather
than retranslating every line.
