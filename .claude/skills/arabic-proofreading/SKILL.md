---
name: arabic-proofreading
description: "Use when a batch of translation units is at status translated and needs its independent proofreading pass, or when proofreading findings must be recorded or checked. Triggers: تدقيق لغوي، مراجعة الترجمة، ملاحظات المدقق."
---

# Arabic proofreading

Use after a batch reaches `status: translated`. Do not use it to translate
from scratch, to engineer files, or to judge in-game rendering.

## Independence

- The proofreader is never the agent that translated the batch. Work from a
  fresh context: read the units, their context, the glossary, and the style
  references, not the translator's notes or reasoning.
- Use a role label different from the unit's `translated_by` (for example
  `proofreader-1`). `loc.py` rejects a unit whose proofreader equals its
  translator.

## Load only this route

```text
python scripts/context_plan.py proofreading
```

Add `references/ui-style.md`, `references/dialogue-style.md`, or
`references/subtitles-style.md` only for the text type in the batch.

## One pass per batch

1. Get the batch with `python scripts/loc.py brief --batch <batch> --role
   proofreader` (units with targets, their problem codes, character cards, and
   the glossary slice); a delegating agent passes you that file. Run `python scripts/loc.py validate` (it lists problem codes) and
   `python scripts/loc.py terms --path <batch file>` first; start reading at
   the units `loc.py search --problem <code> --ids-only` flags; structural errors go back to the
   translator. Each glossary miss is either fixed (a `terminology` finding)
   or, when the inflected variant is right, allowed with `loc.py terms
   --allow <id> <term>`. The localization gate requires zero open misses.
2. Read **every** unit in the batch once against its source and context, using
   `references/proofreading-checklist.md`. Units flagged as high risk
   (ambiguity, wordplay, sensitive scenes, grammar driven by variables) use the
   `deep_review` route; the rest use `proofreading`.
3. Record each problem once in `work/proofreading/<batch>.jsonl` (format in
   the checklist).
4. Fix directly only clear-cut errors: spelling, hamza, ة/ه, ى/ي, grammar
   agreement, punctuation, spacing, and approved-glossary terms. Record the
   before/after in the finding with `"resolution": "applied"`.
5. Do not rewrite for taste. A meaning, tone, gender, or terminology question
   that the source and context do not settle gets
   `"resolution": "needs_decision"`; set that unit's `decision` to `review` and
   leave its status at `translated`.
6. Run `python scripts/loc.py findings work/proofreading/<batch>.jsonl`, then
   advance every unit with no open finding:
   `python scripts/loc.py mark --ids ... --status proofread --by proofreader-1`.

## Stop rule

A unit is proofread once. `mark` stores a hash of the proofread target; if the
target changes later, `loc.py validate` fails until that unit is proofread
again. Re-proofread only those units, never the whole batch, and do not start
another pass on unchanged units because a later batch revealed a style
preference: record the preference in `glossary.yaml` or the style reference
for future batches instead.

## Report

Return counts from `loc.py findings` (by severity and category), the number of
units advanced to proofread, the open `needs_decision` items with their ids,
and any glossary additions proposed.
