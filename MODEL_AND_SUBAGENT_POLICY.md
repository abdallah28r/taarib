# Model and subagent policy

This policy is binding for the root agent and every delegated agent in this workspace. Explicit user instructions for the current task may narrow delegation further, but ordinary task approval does not waive these safeguards.

## Authorization

- Subagents are an allowed capability by default. For a **new game project**, ask once in the grouped startup intake whether the user wants to use them; record that project's choice before delegation. Do not repeat the question for every batch or resumed session. An existing project's recorded `yes` continues to authorize bounded delegation; a recorded `no` disables it for that project unless the user changes it.
- Use subagents for concrete, independent, bounded work when parallelism, specialization, review, or context separation adds value. Keep trivial work, strict sequential dependencies, and simultaneous edits to one shared file with one responsible writer.
- There is no fixed project limit on concurrent subagents. Choose any useful number dynamically from the amount of genuinely independent work, available runtime capacity, usage budget, context and merge cost. Do not create idle or overlapping agents merely to increase the count.
- Nested delegation is allowed when it is bounded and useful. Every child must inherit this policy, the same provider restrictions, a precise scope, and the one-writer-per-file rule.
- The root agent owns task decomposition, conflict resolution, integration, verification, usage-budget awareness, and the final answer.

## Local and external AI

- Local language models and local machine translation are prohibited. Do not install, download, start, call, or route work through Ollama, llama.cpp, LocalAI, Argos Translate, LibreTranslate running locally, local Hugging Face/Transformers models, or an equivalent local endpoint. An installed executable or a listening localhost service is not permission.
- Never substitute another provider or a local model when the requested OpenAI model is unavailable. Use an allowed OpenAI-hosted model exposed by the runtime or keep the work with the root agent, and disclose the limitation.
- Local OCR or speech recognition such as Tesseract or whisper.cpp is not translation or reasoning authority and still requires explicit user authorization for the current task before installation, download, or use. Its output is untrusted evidence that must be checked.
- External AI, translation, OCR, or transcription services require explicit authorization for that named service and task. The sole standing exception is official OpenAI image editing when `config/image-localization-policy.yaml` enables `openai-official` for the current project; it may receive only in-scope image assets, every output remains a candidate, and review is mandatory. Do not send proprietary game data to any other unapproved service.
- Deterministic local tools such as parsers, archive utilities, hashers, validators, font inspectors, and format converters are allowed within the normal project boundaries; they are not models.

## Model and reasoning routing

Choose the lightest available OpenAI-hosted model and reasoning effort that meets the quality and risk threshold. Correctness, structural safety, and preservation of meaning outrank token savings. Do not select `high`, `xhigh`, or `max` by habit.

| Work | Starting route |
| --- | --- |
| Inventory, counting, hashes, token comparison, simple extraction, deterministic checks | Luna / low |
| Small mechanical edits and coordinated updates from a clear brief | Luna / medium or Sol / low |
| Clear UI translation with an established glossary and context | Sol / low or medium |
| Dialogue, narrative, character voice, contextual bulk translation | Sol / medium |
| Wordplay, ambiguity, sensitive scenes, deep linguistic review, complex debugging | Sol / high; evaluate xhigh only if needed |
| Conflicting evidence, localization architecture, risky integration decisions, final adjudication after a weaker route fails | Astra / medium or high |
| Exceptional long-running analysis with a measurable quality gain | Astra / xhigh; `max` only when a representative evaluation justifies it |

Model names are capability examples, not permanent availability guarantees. Check the models exposed by the current runtime. If per-subagent model selection is unsupported and all agents inherit the root model, say so and apply the task/effort policy without pretending a different model was used.

Escalate only for a recorded reason: unresolved semantic ambiguity, conflicting project evidence, repeated verification failure, a hard-to-reverse decision, broad cross-file reasoning, or a representative evaluation showing a material quality gain. Do not downgrade final narrative translation to a mechanical route merely because the batch is large.

Lines with several protected tokens, nested plural/select syntax, or dense engine
control codes may start one route higher because structural preservation is part
of correctness. Record that reason; markup density does not automatically
justify the highest model.

## Usage planning

Before a bulk translation, run
`python scripts/estimate_tokens.py <csv-or-tsv>` and record the estimate in
`STATUS.md`. The estimate is for shard planning, not billing. If the available
quota is insufficient for two estimated batches or repeated rate-limit/quota
errors persist after bounded retries, finish or checkpoint the current batch,
record resumable state, and stop. Never switch model or provider silently.

## Delegation contract

Every subagent brief must state:

1. one bounded objective and expected deliverable;
2. assigned files or data and whether access is read-only or write-enabled;
3. the model/effort request when the runtime supports it;
4. the relevant style, glossary, context, protected syntax, and acceptance checks;
5. the ban on local LLM/MT and unapproved external services;
6. no installation, download, destructive action, game launch, or scope expansion without authority;
7. any child-agent scope and confirmation that the full policy is inherited;
8. how to report uncertainty, changed files, commands, and test results.

Only one agent may write a given file at a time. Prefer read-only subagents for research and review. Give independent writers disjoint outputs, and have the root agent merge them.

## Verification and records

- Treat a subagent result as an untrusted contribution until the root agent checks its scope, diffs, protected tokens, glossary, format, encoding, and relevant tests.
- For translation, require zero structural/token errors. Review a representative semantic sample and escalate only the ambiguous or failing subset.
- Keep one compact delegation summary per batch in `STATUS.md`: assigned scope,
  outputs, checks, and unfinished work. Record per-agent model/effort or retry
  details only when they affect quality, cost, a policy exception, or resumption;
  use the actual run output as the detailed source when available. Do not request
  or store hidden chain-of-thought.
- If a prohibited local model is attempted, stop that operation, preserve evidence, report the command/service and affected files, and do not silently retry through another model.

## Reusable improvements

When work reveals a useful subagent tool, skill, script, evaluator, prompt contract, or routing improvement, add it locally when it is safe, deterministic, relevant, and permitted. Otherwise record it in `reports/IMPROVEMENT_PROPOSALS.md` with evidence and an acceptance test. Never use this permission to install a model, contact an unapproved service, weaken this policy, or expand the user's task.

The machine-readable contract is `config/agent-policy.json`. Validate it with `python scripts/check_agent_policy.py`. Generate a bounded delegation brief with `python scripts/make_subagent_brief.py --route <route> --task <task> --scope <scope>`.
