# AI-assisted localization workflow

Use this reference for large translation runs, updates, or projects where repeated questions and rediscovery are costly.

## Context packet

Before bulk translation, assemble context from available evidence:

- game synopsis, setting, rating, platform, and target audience;
- current scene/quest/screen and neighboring strings;
- speaker, addressee, gender/number when established, and character voice;
- glossary terms with definitions, status, forbidden variants, and examples;
- string function, length/line constraints, placeholders, markup, and screenshots;
- decisions inherited from prior batches and prior official locales when reliable.

Do not invent missing lore. Infer only when evidence is strong; record the inference. Keep unresolved non-blocking entries marked for review while continuing the rest.

## Two-pass behavior in one run

1. Translate coherent groups with context and terminology.
2. Review them as Arabic: meaning, voice, fluency, grammar, terminology, tokens, and UI constraints.

These are logical passes, not approval checkpoints. They should normally happen in the same run.

## Translation memory and glossary

- Reuse an exact prior translation only when source, context, and function match.
- Treat fuzzy matches as evidence, not instructions.
- Store stable keys and source hashes so game updates can distinguish new text from changed English.
- A glossary entry should include meaning/context when the English term is polysemous. One global mapping such as `Case` is unsafe without a domain note.
- Keep product names and intentionally untranslated terms explicitly marked, rather than relying on “no Arabic detected” exceptions.

## Recommended record fields

Use the native format when possible. For an interchange table, retain at least:

`id`, `source`, `target`, `context`, `speaker`, `location`, `note`, `status`, `max_length`, `source_hash`

Add plural/select variants and screenshot references when the source format supports them. Do not flatten them into a single string if reconstruction would be lossy.

Suggested statuses: `new`, `translated`, `review`, `approved`, `do_not_translate`, `blocked`.

## Model use

A coding agent (Codex or Claude Code) is most useful when it can inspect the actual project, surrounding assets, existing locales, and validation scripts. Use it to translate, maintain terminology, merge updates, generate format-aware helpers, and diagnose screenshots. External machine-translation APIs can provide alternatives or a first pass, but they do not replace the same context packet, terminology controls, deterministic checks, or in-game LQA.

Never send proprietary game text to an external service unless the user has authorized that service and the project's confidentiality terms allow it.

Local language models and local machine translation are prohibited by `MODEL_AND_SUBAGENT_POLICY.md`. Subagents are always used; never request authorization for a batch. The root agent picks any tier (light, standard, deep) and effort for each task by its own judgment; `config/agent-policy.json` lists suggested routes and maps tiers to Codex or Claude Code models. No tier replaces representative evaluation and deterministic QA.
