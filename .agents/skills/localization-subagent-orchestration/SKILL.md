---
name: localization-subagent-orchestration
description: "Use when deciding whether to split localization work across subagents, writing their briefs, or merging and verifying their results. Triggers: وكلاء فرعيون، توزيع الدفعات، تفويض."
---

# Localization subagent orchestration

Subagents are allowed as a capability. For a new game, first honor the one-time
project choice recorded under `references/project-run.md`; do not delegate if
the user selected no or the choice is still unresolved. When enabled, use them
only when parallel or specialist value exceeds briefing and merge cost; there
is no fixed concurrency cap. Do not ask again for every batch.

## Required policy

Run `python scripts/context_plan.py delegation` and read every returned file.
The machine-readable policy is binding. Do not duplicate model/provider rules
in a task prompt by memory.

Generate each bounded contract with:

```text
python scripts/make_subagent_brief.py --route <route> --task <task> --scope <paths> --write-mode read-only|write
python scripts/loc.py brief --batch <batch> --role translator|proofreader --runtime codex|claude-code
```

For text batches use `loc.py brief`: its first layer (rules, role, project
conventions, output contract) is byte-identical for every batch, so a runtime
can cache it, and it reports `CACHEABLE_PREFIX_SHA` so you can confirm that.
Give the agent the brief file; it needs nothing else.

Roles in `.agents/roles/` (native subagents with the same names in Claude
Code): `translator` and `proofreader` for text batches, `researcher` for
read-only discovery and mod questions (keeps web pages out of the root
context), and `image-localizer` for image sets (keeps heavy visual context
out of the root). Skip delegation for small games, adapter work, integration,
and glossary decisions; the root agent owns those.
Run them in sequence per batch (translate, then proofread by a different
agent); different batches may run in parallel when their unit files are
disjoint.

- Give writers disjoint files; one writer owns each file at a time.
- Nested delegation is allowed only when children inherit the complete policy
  and keep disjoint scopes.
- Choose the lightest allowed hosted model/effort that meets semantic and
  structural risk. Escalate after recorded failure evidence, not by habit.
- Never ask for hidden chain-of-thought.

The root agent validates scope and diffs, runs deterministic format/token tests,
checks terminology conflicts, and samples semantic high-risk cases. It does not
retranslate every successful row by default. Split structurally failing batches
and retry only within the bounded policy; preserve unresolved rows and reasons
instead of looping indefinitely.
