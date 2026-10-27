---
name: localization-subagent-orchestration
description: "Use when deciding whether to split localization work across subagents, writing their briefs, or merging and verifying their results. Triggers: وكلاء فرعيون، توزيع الدفعات، تفويض."
---

# Localization subagent orchestration

`MODEL_AND_SUBAGENT_POLICY.md` is the delegation policy (authorization, model
tiers, providers, brief contract); run `python scripts/context_plan.py
delegation` once and read what it returns. This skill is only the procedure.

## Briefs

```text
python scripts/loc.py brief --batch <batch> --role translator|proofreader --runtime codex|claude-code
python scripts/make_subagent_brief.py --role <role> --task <task> --scope <paths> --write-mode read-only|write
```

Text batches use `loc.py brief`. Its first layer (rules, role, project
conventions, output contract, and the style and review references) is
byte-identical for every batch of a role, so a runtime can cache it; it reports
`CACHEABLE_PREFIX_SHA` to confirm that. Give the agent the brief file; it reads
nothing else. Split a batch when the command prints a `WARNING` about
`max_batch_*`. Research questions and image sets use `make_subagent_brief.py`.

## Roles and order

Roles in `.agents/roles/` (native subagents with the same names in Claude
Code): `translator` and `proofreader` for text batches, `researcher` for
read-only discovery and mod questions (keeps web pages out of the root
context), and `image-localizer` for image sets (keeps heavy visual context
out of the root). Skip delegation for small games, adapter work, integration,
and glossary decisions; the root agent owns those.
Run them in sequence per batch (translate, then proofread by a different
agent); different batches may run in parallel when their unit files are
disjoint. Give writers disjoint files; one writer owns each file at a time.

## Merge and verify

The root agent validates scope and diffs, runs deterministic format/token tests,
checks terminology conflicts, and samples semantic high-risk cases. It does not
retranslate every successful row by default. Split structurally failing batches
and retry only within the bounded policy; preserve unresolved rows and reasons
instead of looping indefinitely.
