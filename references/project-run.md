# New-game operating contract

Use for a user's end-to-end request to localize a **new game**. This contract
defines decision boundaries, not a required daily report or a license to widen
the task. Existing projects keep their recorded choices; do not repeat intake.

## One grouped intake, before bulk localization or game mutation

Read the current request and `PROJECT.yaml`, make a quick read-only check if it
helps identify the actual game/build, and ask **one compact set** of questions
for missing project choices. Do not ask for facts already established. Include:

1. The game name. Users name their copy of the template after the game, so
   offer the working folder's name as the suggested answer to confirm or
   correct.
2. Where the game is installed, as two choices: the user gives the path, or
   the agent finds it. Finding it is a read-only search for a folder matching
   the name in Steam libraries (`steamapps/libraryfolders.vdf`), Epic, GOG,
   Xbox/Microsoft Store, and Program Files. If a quick search already found
   one likely match, show it as the suggested answer. Show what was found for
   confirmation; list several installations or editions and ask which copy;
   ask for the path if nothing matches. Never change anything while searching.
3. Whether baked text in UI/art images is in scope (`yes`/`no`), recorded as
   `workflow.image_scope`. Tell the user that each image takes about 5 minutes
   or more, so many images add hours; image editing runs through Codex (also
   from Claude Code) and uses its usage limit. If yes, follow the image policy;
   this does not mean translating every visible marking.
4. Whether the agent may launch the game for a smoke test (`yes`/`no`). Default
   is no; user playtesting is still required for final quality.
5. Which runtime the user works in (`workflow.runtime`): `codex`,
   `claude-code`, or `both`. For `both`, ask which one is the main agent
   (`runtime_root`): the main agent plans, integrates, and checks; the other
   does the delegated batches, research, and images through
   `scripts/delegate.py`. Example: Claude Code main, Codex for the subagent
   work, or the reverse.
6. Their subscription in their words (`subscription`, e.g. "Claude Pro 20$",
   "ChatGPT Plus 20$", "Max 100$"). It is only used to suggest the next
   answers; say so.
7. How much work goes to subagents (`subagent_mode`):
   - `economic`: the main agent translates; subagents only proofread (when
     review is separate), research, and do images. Slowest, least usage.
   - `balanced`: every batch goes to a subagent, a few at a time.
   - `fast`: many subagents at once; the main agent only coordinates. Fastest,
     most usage.
   For `balanced` and `fast`, ask how many subagents may run at the same time
   (`subagent_concurrency`): more is faster but spends the limit faster.
   Suggest numbers and accept any number the user types: about 20$ → economic,
   or balanced with 2; about 100$ → balanced with 3 to 4; 200$ or more → fast
   with 6 to 8.
8. How each batch is checked (`review_mode`):
   - `separate`: one agent translates and another reads the same text again to
     proofread it. Higher quality, about twice the usage.
   - `self`: the translating agent reviews its own batch in the same pass.
     Less usage; quality may be lower depending on the game, not always.
   The automatic checks and gates apply in both. Suggest `self` for about 20$
   and `separate` above it.

Ask everything in one message, each question with its suggested answer, so a
limited plan spends one turn on it. Record every answer in `PROJECT.yaml`
`workflow`; the intake gate checks them.

**Codex subagent limit.** When the runtime includes Codex and
`subagent_concurrency` is above the number Codex allows, raise Codex's limit
once. Read the official Codex configuration docs to find the setting that caps
concurrent agent threads (at the time of writing, `[agents]
max_concurrent_threads_per_session` in `~/.codex/config.toml`; verify it, the
name can change). Copy `config.toml` to `config.toml.bak-<date>` first, change
only that value, and tell the user what changed and whether Codex must be
restarted for it to apply (the docs say when config is read).

Never ask, because the template fixes them: installation on the identified
copy (`install_to_user_copy: "yes"`), that subagents are allowed, and OpenAI
image editing for in-scope images (`external_image_editing.enabled: "yes"`).
A user may still change any of them later.

Ask about tone, dialect, mature language, a preferred font, or accessibility
only if the game evidence or user's wording leaves a material choice. Do not
make the user choose tools, batch sizes, routine tests, or every font candidate.
The agent should test appropriate licensed fonts itself; ask only if viable
options have a meaningful aesthetic tradeoff it cannot resolve objectively.
If a required answer is missing, continue read-only discovery and reversible
preparation, then ask once for the unresolved choice before crossing its
boundary. Do not install unless the intended user-owned copy is unambiguous.
Record answers in `PROJECT.yaml` only; do not ask again on
every resumed session. A user may revise any preference later.

## Phases and gates

`python scripts/loc.py next` shows the phase and its open exit criteria;
`python scripts/loc.py gate` advances only when all pass. Phases: intake →
discovery → extraction (adapter contract passed, units extracted, every batch
listed in `PLAN.md`; with images in scope, image units or `loc.py no-images`)
→ localization (every translatable unit proofread, no open review, glossary
clean, every batch ticked, every translated image in a passing region
manifest) →
integration (every unit integrated into a build) → playtest (no open
blocker/critical defect, user acceptance recorded) → handoff (the experiences
package built after acceptance and given to the user) → release, only if the
user asked for a shareable package. The gates are
the stop rule: when `next` reports a phase ready, gate it and move on instead
of reviewing again.

## Continuous execution after intake

Move through discovery → focused localization-mod research and evidence-based
tool/route selection → extraction and small
round-trip → contextual translation (including opted-in images) → structural
and visual QA → validated build → checked installation on the user's copy.
Use subagents as `subagent_mode` says, at most `subagent_concurrency` at once.
Before the first bulk translation batch, run `python scripts/loc.py estimate`
to size batches.
Run routine tests, fix bounded failures, and resume from `loc.py next` and `PLAN.md` without
requesting phase-by-phase approval. Report only meaningful progress or a real
blocker; do not present each completed phase as a question.

The agent may select tools, translation batches, glossary candidates, and
technically and aesthetically suitable fonts. After font discovery, choose and
record one compact, role-aware typography plan per `references/arabic-rendering.md`.
The standing project font policy in `PROJECT.yaml` permits source-verified font
downloads and a necessary current-user-only Windows install without repeated
approval; follow `references/font-sourcing.md` and its two records. It does not
permit an all-users install, replacement of an existing system font, or bundling
a font without rights.
Apply it to game text and use it as a secondary coherence check for localized
images; the image's source style remains the primary constraint. Do not ask the
user to approve each font or stop after the typography plan. The agent must not
silently guess gameplay-changing text, bypass protection, install unauthorized
dependencies/models/services, overwrite
the sole original, or claim a runtime pass it did not observe. An inability to
test a live renderer is a stated limitation, not a reason to skip other work.
Researching a mod is not permission to modify or bundle it. Use
`references/localization-mods.md` for the decision and approval boundaries.

## Handoff: the experiences package

After acceptance, run `python scripts/loc.py experiences`. It packs the lessons
recorded during the work, facts the code collects (engine, adapter contract,
fixes and their verdicts, reopened phases, problem counts, phase times), the
engine profile, the adapter, and scripts marked reusable into
`experiences-<game>-<date>.zip` in this folder, without game text, game files,
user paths, or secrets. Tell the user in Arabic what it contains, where it is,
and where to send it (Discord server and X account from `config/feedback.json`,
printed by the command). Then `loc.py gate`. The command also works earlier,
for example when a project stops halfway; a stopped project teaches limits too.

## Install, user trial, then shareable package

Installation to the user's identified copy is the completion step
(`install_to_user_copy: "yes"`, the default) once the target is unambiguous; only
if a user changed it to `"no"`, stop at a verified build and its install
instructions. Before it, verify target build and
original hashes, create restorable backups outside the replacement set, run
native/structural/image gates, and use the least invasive reversible method.
Verify installed files and give a rollback procedure. If the build is unknown,
hashes differ, rollback is unproven, or the method would bypass protection,
stop that affected operation and ask; do not silently replace a live archive.

After installation, hand the game to the user for unhurried playtesting. Give a
short test checklist and an easy way to report screenshots, text errors,
missing images, crashes, UI clipping, and font issues. This is **one intended
human gate**, not a request to approve each preceding test. Do not start the
shareable package merely because local validators passed. When the user reports
issues, fix them, reinstall a verified update under the same installation
choice, and return to playtesting. Continue until the user explicitly accepts
the localized build or directs an earlier release.

Only after that acceptance, create a **game-localization package**, not the
public template archive. It must be portable across supported installations:
include the patch/localization payload, a straightforward installer or
well-tested installation script, a removal/rollback route, required
redistributable runtime components, a build/version compatibility check, and
Arabic installation/use instructions (`INSTALL_AR.md` or equivalent). A
recipient should not need an AI agent or the development toolchain to install it.
The installer discovers or asks for the recipient's game directory; never
hard-code the creator's `C:\` path. Validate
the recipient's original game/build before applying deltas; do not request
account credentials or bypass a store's ownership checks. Test install and
uninstall on a clean copy of every claimed supported variant. Do not promise
compatibility with all editions or devices without those tests.

Do not ship the original game's copyrighted archives/textures/text, private
logs, user backups, secrets, or tools whose redistribution is not permitted.
When a required component cannot legally be bundled, state that dependency
and its acquisition step plainly rather than calling the package self-contained.
`references/release.md` gives the release checks. Packaging alone does not
publish or distribute the package; sharing is a separate user action.
