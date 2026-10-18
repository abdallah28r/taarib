# New-game operating contract

Use for a user's end-to-end request to localize a **new game**. This contract
defines decision boundaries, not a required daily report or a license to widen
the task. Existing projects keep their recorded choices; do not repeat intake.

## One grouped intake, before bulk localization or game mutation

Read the current request and `PROJECT.yaml`, make a quick read-only check if it
helps identify the actual game/build, and ask **one compact set** of questions
for missing project choices. Do not ask for facts already established. Include:

1. Game name and the user's installation path/build/platform if not clear. The
   agent may discover the exact build read-only; ask which copy to modify only
   if multiple installations or editions make the target ambiguous.
2. Whether the agent may install the verified, reversible build on that copy
   (`yes`/`no`). Record it as `workflow.install_to_user_copy`; the template's
   `"ask"` value is not permission.
3. Whether to use subagents for this game (`yes`/`no`). They are available by
   policy, but this one-time project preference controls whether to delegate.
4. Whether baked text in UI/art images is in scope (`yes`/`no`). If yes, follow
   the image policy; this does not mean translating every visible marking.
   If yes, also ask whether in-scope images may be sent to official OpenAI
   image editing (`yes`/`no`), recorded as
   `image_localization.external_image_editing.enabled`.
5. Whether the agent may launch the game for a smoke test (`yes`/`no`). Default
   is no; user playtesting is still required for final quality.

Ask about tone, dialect, mature language, a preferred font, or accessibility
only if the game evidence or user's wording leaves a material choice. Do not
make the user choose tools, batch sizes, routine tests, or every font candidate.
The agent should test appropriate licensed fonts itself; ask only if viable
options have a meaningful aesthetic tradeoff it cannot resolve objectively.
If a required answer is missing, continue read-only discovery and reversible
preparation, then ask once for the unresolved choice before crossing its
boundary. Do not install unless the intended user-owned copy is unambiguous.
Record answers in `PROJECT.yaml`/`STATUS.md`; do not ask again on
every resumed session. A user may revise any preference later.

## Continuous execution after intake

Move through discovery → focused localization-mod research and evidence-based
tool/route selection → extraction and small
round-trip → contextual translation (including opted-in images) → structural
and visual QA → validated build → checked installation on the user's copy.
Parallelize useful independent work under the chosen subagent preference.
Run routine tests, fix bounded failures, and resume from `STATUS.md` without
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

## Install, user trial, then shareable package

Installation to the user's named copy is the completion step when the intake
recorded `install_to_user_copy: "yes"` and the target is unambiguous; with
`"no"`, stop at a verified build and its install instructions. Before it, verify target build and
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
