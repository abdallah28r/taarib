# Changelog

## 2026-10-29 — Bounded project storage and one verified original

- Repeated game-file changes reuse one verified pre-localization original rather
  than retaining a full copy for every update. New patch packages are complete
  snapshots: an upgrade removes files omitted from the new package, and removal
  restores the original. Older installed transactions keep their existing
  removal path; installing an old package again requires rebuilding it as v3.
- Backup and save-snapshot commands reject a source that contains its destination
  (including links and junctions) before making any folder. Large-file hashes
  and byte-range patch creation read in bounded chunks; copying checks available
  space first.
- `storage_audit.py report` inventories existing projects without following
  links. `clean-temp` and image-page refresh remove only recorded, unused
  previews or committed transaction staging; unknown old work remains for review.


## 2026-10-28 — A game file Windows holds for a moment

The test suite failed twice, once in the byte patch test and once in the package
install test, and passed on every rerun (more than 40 runs). Both tests replace a
file that was just written, which Windows refuses while another program (an
antivirus scan, the indexer) still holds it. The same happens to a user whose game
or launcher is open.

- New library `scripts/file_ops.py`: `replace_file` and `remove_file` retry for
  about two seconds, then raise `FileInUse`, which names the file and says to
  close the game and its launcher; nothing is changed.
- Used wherever the template swaps or removes a game file: `byte_patch.py`
  (which now also puts the original back if the second swap fails),
  `apply_patch_package.py`, `uninstall_patch_package.py`, `safe_replace.py`.
- A test holds the target file open as a running game would, checks the clear
  error and that nothing changed, then holds it briefly as an antivirus scan
  would and checks the patch still installs.

## 2026-10-28 — Recording is enforced, not only described

A review of whether the agent would really record its work found that the
image-localizer role never mentioned versions, verdicts or spoilers, and that
nothing stopped an agent from skipping the task board or the verdicts.

- The gates of discovery, extraction, pilot, localization, integration and
  playtest need at least one task recorded in the phase (as well as none
  open); `loc.py next` warns while a working phase has none.
- The localization gate needs, for every translated image, an accepted
  version with its reason and a spoiler decision: `image_candidate.py
  spoiler --reason ...` or the new `--none`.
- `AGENTS.md`, the image-localizer role, the image skill and
  `references/project-run.md` say when to record: before starting work,
  `--later` when postponing, `waiting --reason` when asking the user, `done
  --evidence` when finished.
- `tests/test_pages_end_to_end.py` drives the agent's commands and checks each
  record appears in its own place on dashboard.html, tasks.html, texts.html
  and images.html.

## 2026-10-28 — Text and images before and after

- `texts.html`: every text unit's source beside its Arabic, with status, batch,
  file, speaker, problem codes and proofreading findings; search, filters,
  and pages of 200 lines.
- `images.html`: each image's localized version beside its source with a
  comparison slider, the region texts, and every version tried with its
  verdict and reason. Images that give away the story are blurred until
  clicked; `PROJECT.yaml` → `reporting.spoilers`: `flagged` (default), `all`,
  `none`.
- `image_candidate.py` keeps every version of an image in
  `work/images/attempts.json` (`codex`, `composite`, and the new `record`),
  with `verdict` (accepted/rejected with a reason) and `spoiler` (flag with a
  reason, or `--clear`). New library `scripts/review_pages.py`.
- Both pages hold game content: ignored by git with `work/images/` and
  `work/proofreading/`, kept out of releases, and linked from every page.
  Checked in a browser with fake data on desktop and phone widths.

## 2026-10-28 — Task board, and pages that refresh themselves

- `tasks.html`: the agent's task board, linked from `dashboard.html`, with
  columns later → next → doing → waiting (on the user) → verify → done and
  each task's history. `loc.py task add|move|defer|list` (new library
  `scripts/loc_tasks.py`, data in `state/tasks.json`). `done` needs evidence,
  `waiting`/`dropped` a reason. A gate refuses a phase while one of its tasks
  is open. `fix open` adds a task and `fix close` moves it. PLAN.md's batches
  appear as read-only cards. `loc.py next` lists open tasks first.
- The pages are rebuilt whenever a project file is newer than them, from one
  check run after every `loc.py` command, after every Claude Code tool
  (shell commands included), and under the new `loc.py watch`. Before,
  each command had to remember to refresh: `no-images` and `normalize` did
  not, and a PLAN.md edit from Codex or the shell stayed invisible.
- A refused gate is now recorded once per shortfall and shown as an event;
  the last `loc.py probe` (engine, fonts with Arabic, boot verdict) is shown
  on the dashboard (`work/probe/last.json`).

## 2026-10-28 — Map renamed to `template-map.html`

- `خريطة-القالب.html` is now `template-map.html`, an English file name that
  works everywhere; the dashboard link, `AGENTS.md`, `README.md`, and the
  release list follow it. The page itself stays in Arabic.

## 2026-10-28 — Ready for GitHub as «taarib»

- `README.md` in English: what the template does, engines, quick start,
  phases, safety, development, license, acknowledgments.
- `LICENSE` names abdallah28r. `THIRD_PARTY_NOTICES.md` no longer says no
  third-party code was copied; it says which MIT code and CC BY 4.0 documents
  are adapted, and that the CC BY documents keep their license.
- Every font reader (`font_report`, the probe preview, `font_measure`,
  `font_bank.coverage`, `check_font.py`) now closes the font file; before, it
  stayed open, and Windows refused to delete or replace it in the same process.
- The test for a font with a GSUB table but no script list builds its own font
  instead of needing a game installed, and checks that the readers released it.
- Map: the repository and its license, the «one fix, every copy» rule, and a
  problem row for a fixed mistake that shows up elsewhere.

## 2026-10-28 — Tried on a real game: automatic launch and boot verdict

Tried on Slay the Princess (Ren'Py 8.0.3, already localized into Arabic):
`loc.py probe --launch` started the game, closed it after 120 s, found its
`log.txt` from the engine profile, and judged it; found its Arabic fonts
(Amiri under `tl/arabic`). Saves were snapshotted first; only Ren'Py's
`persistent` file changed. Three problems the synthetic tests had not shown:

- Start-up timing lines ("Loading error handling took 1.41s") counted as
  errors; such lines are no longer errors.
- A game started directly by `--launch` cannot reach Steam, so its failed
  Steam start counted as an error; with `--launch` it is listed under
  `launch_notes` instead (started by the user through Steam, it still counts).
- A valid font whose GSUB table has no script list was reported unreadable;
  a font fontTools truly cannot parse now says the game may still load it.

## 2026-10-28 — Probe for unknown engines, engine markers as data, scripts index

- `loc.py probe`: maps detected ids to their profile (`rpg-maker-mv` →
  `rpg-maker.md`; recording used to fail silently); reads log paths written in
  the profile's `## Logs`; derives exact log paths from the game's own names
  (Unity `app.info` company/product, Unreal project folder, executable names);
  `--engine <new-id> --record` creates a minimal profile that passes
  `check_knowledge.py` and adds the engine to the catalog map;
  `--deep-fonts` reads fonts inside Unity assets (Font assets through
  fontTools, TextMeshPro font assets by their character table; UnityPy).
  Tried read-only on an installed Unity game: 17 embedded fonts, one with
  Arabic, in about 9 seconds.
- Engine markers moved from `detect_engine.py` to `config/engine-markers.json`
  so an agent adds an unknown engine without touching code.
- `references/scripts.md`: one line per script; AGENTS.md: run `--help` before
  a script's first use, and the agent may change any template script, config,
  or adapter in a project when it finds a bug or a better way, recording the
  change as a lesson. A test fails when a script is missing from the index.
- Map: probe abilities, unknown engines, scripts index.
- Review fixes (each reproduced first):
  - `boot_verdict`: the Unreal pattern matched any program's log under
    `%LOCALAPPDATA%` (the Epic launcher's included); it now uses the game's
    project folder. "Non-fatal error" and Unity's "Assertion failed on
    expression" no longer count as crashes.
  - probe: Unity's `Player-prev.log` (the run before) is never judged as this
    launch; company names ("Studio") no longer tie other programs' logs to the
    game; Unreal's `Engine/` folder is not taken for the project; engine-pattern
    matches outside the game folder must name the game; `--engine unknown` is
    refused.
  - probe preview: reads translated units (pilot first) as the docstring said;
    `--native` previews engines that shape Arabic themselves; measuring and
    drawing now agree on placeholders (a `{name}` line overflowed the box while
    reported as fitting); `.ttc` fonts work; `--deep-fonts` saves embedded fonts
    for the preview, reads likely font files first, includes `.unity3d`, and
    reports how many asset files it read or skipped.
  - probe `--save-baseline`: later runs count only errors the unpatched game
    did not log; `--launch` warns when the executable handed over to a launcher.
  - Adapters: `line_unit: chars` no longer counts tags as characters; a
    relative `font` resolves from the project folder; missing `font`/`font_size`
    is a clear error.
  - `font_bank assign` no longer gives new slots to characters the original
    text already draws (é, …).
  - Scripts no longer crash when their output is captured in memory.

## 2026-10-28 — Everything usable from the reviewed sources: nine engines, 31 tools, probe

- Policy: decrypting a game's own archives and injecting code are allowed only
  per game after a warning, with the user confirming ownership and that they
  checked the game's license and their country's law, using external tools
  only, and distributing nothing decrypted; never for online or anti-cheat
  games (`extraction-integration.md` → "Protected archives and runtime code").
  PS4 package building stays rejected.
- Nine engine profiles adapted from the Arabic Game Localization Playbook
  (CC BY 4.0): MonoGame/XNA, SCUMM/ScummVM, GrimE, Telltale, Dinky,
  proprietary PC ports, Android APK, PS1, PS2; Playbook lessons added to the
  Unity, GameMaker, and RPG Maker profiles. `detect_engine.py` recognizes
  them (SYSTEM.CNF decides PS1 vs PS2).
- Catalog: 31 tools (now 93), each named in its engine profile or reference.
- `loc.py probe` (`scripts/game_probe.py`): the game's fonts and whether they
  hold Arabic, a preview of rendered lines in the game's own font at the box
  width (overflow, missing glyphs), and the game's logs, from the engine
  profile or discovered after a launch and recorded with `--record`; launches
  the game itself only when `allow_launch_game` is true.
- `arabic_shaping`: diacritics no longer detach from their letter when a line
  is reversed (bug); `unrender()` restores logical text from shipped Arabic;
  `marks_one_later` for engines that draw marks one letter early.
- New scripts: `font_bank.py` (one-byte glyph banks with a stable seed,
  coverage, DTE pairs; MIT code adapted), `byte_patch.py` (guarded byte edits
  and hash-checked range patches; MIT code adapted), `save_guard.py` (player
  save snapshots). Image check: a candidate must keep the source's
  transparency kind.
- References: more rendering lessons (fonts, images, testing, building),
  install failure reasons, large-archive patches; template map updated
  (and its trouble table's station numbers corrected).

## 2026-10-28 — Boot verdict from game logs; AoE II, Stardew Valley, RimWorld profiles

- New `scripts/boot_verdict.py` (read-only): after the user opens the patched
  game, it reads the engine's usual log (Unity/BepInEx, Unreal/UE4SS, Ren'Py,
  Godot, SMAPI, RimWorld) and reports `crashed`, `missing_arabic_glyphs`
  (TextMeshPro and similar missing-character warnings for Arabic code points),
  `booted_with_errors` (new against a `--baseline` clean boot),
  `booted_clean`, or that no fresh log exists. Used in the pilot before the
  user is asked; the user's words still confirm the Arabic.
- New engine profiles `age-of-empires-ii`, `stardew-valley`, `rimworld`, each
  with its tools, Arabic route, workflow, and log path; `detect_engine.py`
  recognizes them (RimWorld over plain Unity) and reports SMAPI.
- Catalog: AoE2 DE Custom Font Generator, genie-rs, SMAPI, Content Patcher,
  StardewXnbHack, AngelCode BMFont, Harmony; engine map updated.

## 2026-10-28 — Arabic display fixes, measured wrapping, rendering lessons

From the review of six Arabic localization repositories and the Miqbas/FLTAH
research pack (report outside the template, `../research/`).

- `arabic_shaping.render` fixes three display bugs found by testing it:
  Arabic-Indic numbers came out reversed (`٢٥` → `٥٢`), `50%` became `%50`,
  and tag pairs reversed into `</b>…<b>`. Ordering now follows the Unicode
  Bidi Algorithm for a right-to-left line (`+25` stays `25+` as native
  renderers show it).
- Wrapping before reversing, which the docs required but no code did:
  `wrap()` measures shaped text (`len` for fixed-pitch boxes, `font_measure`
  for the game's TTF/OTF) and balances lines. Adapters set it with
  `adapter_options` (`line_width` or `boxes`, `line_unit`, `font`,
  `font_size`, `line_sep`). `shape()` gains `strip_harakat`, `lam_alef`, and
  `transparent` engine codes; `glyphs_used()` lists what the font must hold.
- QA: new `reversed_text` warning; `loc_qa` and `format_qa` count a line as
  Arabic only by its letters; `capture_filter` drops FPS/CPU/GHz overlays.
- New `references/rendering-lessons.md` (symptom → cause → rule, adapted under
  CC BY 4.0 from the Arabic Game Localization Playbook), optional in the
  `qa-rendering` route. Line-break and "values the code compares" rules in
  `extraction-integration.md`; pilot lines cover the rendering cases; RPG
  Maker MV vs MZ; optional `religious_terms` in `glossary.yaml`; no silent
  model or provider switch. Attribution and acknowledgments in
  `THIRD_PARTY_NOTICES.md`.

## 2026-10-28 — Audit: every tool named where the agent reads, fewer scripts

- Tool catalog: dropped Weblate, OmegaT, and Kuriimu2 (team/GUI or console
  tools the agent does not use); added UnrealLocres, RE-UE4SS, and
  ValveResourceFormat, which engine profiles already named. New `engines` map
  from engine id to catalog profiles.
- Every engine profile lists its catalog tool ids; general tools are named in
  the references that use them (QA, rendering, extraction/media, release).
  A test fails if a catalog tool is named nowhere or missing from its engine.
- `tool_doctor.py --engine <id>` prints that engine's tools with license,
  source, and note, so the agent never reads the whole catalog.
- Removed `scripts/setup_tools.ps1` and the `requirements/` profile lists: it
  installed system-wide through winget. The engineering skill now states the
  install rules (upstream, exact version, SHA-256, under `.tools/`, no admin or
  PATH change, recorded in `selected-tools.json`); the pinned constraints file
  stays.
- New `engines/danganronpa.md`; RPG Maker, Source, and GameMaker tool lists
  corrected to what the catalog holds.
- `check_font_shaping.py` merged into `check_font.py --shape`.
- New tests for `safe_backup.py`, which had none.

## 2026-10-28 — Tool installation procedure and SIGNALIS Unity findings

- `game-localization-engineering` step 4 now tells the agent how to get tools:
  `tool_doctor.py --profile`, one pinned upstream release under `.tools/`
  (Python packages in `.tools/venv` from `setup_tools.ps1`), and a record in
  `tools/selected-tools.json` checked by `check_tool_provenance.py`. Both
  scripts existed but no instruction named them.
- Installing pinned open-source tools under `.tools/` is a fourth standing
  default; a tool that goes into the game folder still needs the user's
  approval for that game.
- `engines/unity.md`: what SIGNALIS verified (IL2CPP marker, `member:path ID`
  identity, legacy TMP needing a display bridge, texture round-trip limits,
  separate removable loader) and the tool versions it tried, as candidates.

## 2026-10-28 — Pilot phase: see Arabic in the game before bulk translation

- New phase `pilot` (التجربة الأولى) between extraction and localization. The
  first batch, `pilot`, holds the main menu, settings, and the first 20 to 40
  lines of the first scene, with a mixed-text line and the longest choice. It
  is translated, proofread, installed, and checked by the user; its gate needs
  those units `integrated` and `loc.py pilot-ok --note`, recorded only on the
  user's words. Rendering fixes go in the display layer; the translations stay.
- Reopening the pilot or an earlier phase clears the confirmation.
- AGENTS.md lists the pilot as the second planned stop; the map shows the new
  user step and station.

## 2026-10-28 — Intake: runtime, usage, and review choices

- Four new intake questions, asked with the others in one message and checked
  by the intake gate: `workflow.runtime` (codex, claude-code, both; with both,
  `runtime_root`), `subscription` (only to suggest numbers),
  `subagent_mode` (economic, balanced, fast) with `subagent_concurrency` for
  balanced and fast, and `review_mode` (separate or self). They replace
  `subagent_preference` and `allow_subagents`; subagents stay allowed.
- `review_mode: self`: the translator's brief carries the proofreading
  checklist and it marks its batch with `loc.py mark --status proofread
  --self-review` (`proofread_by: self-review:<translator>`). With `separate`,
  the localization gate refuses self-reviewed units.
- New `scripts/delegate.py`: with `runtime: both`, the main agent runs a brief
  in the other runtime (`codex exec` or `claude -p`).
- The image question says each image takes about 5 minutes or more. With
  Codex in use, the agent raises Codex's concurrent-agent limit to the user's
  number after reading Codex's docs and backing up `config.toml`.
- The experiences package records these choices under `setup`.

## 2026-10-28 — v7 review: lean briefs, Codex image route, image gates

- `loc.py brief` inlines the style references (and, for proofreaders, the
  checklist and problem codes) in its cacheable first layer, plus `dates` and
  `time_format`. The translator and proofreader roles read only the brief: no
  skill, route, `PROJECT.yaml`, `PLAN.md`, or full glossary per batch.
- New `scripts/image_candidate.py`: `codex` sends one source image to Codex's
  built-in image tool (both runtimes; Claude Code has no image tool) and
  `composite` confines the raw edit to the mask or box over the untouched
  source. At most `image_localization.max_generative_attempts` (default 5)
  Codex edits per image, counted in `work/images/attempts.json`.
- Gates: with images in scope, extraction needs image units or
  `loc.py no-images --reason`; localization needs every translated image in a
  `work/images/*.json` region manifest that passes `check_image_regions.py`.
- One source per rule: the delegation policy lives in
  `MODEL_AND_SUBAGENT_POLICY.md`; AGENTS.md, CLAUDE.md, and the orchestration
  skill point to it. `PROJECT.yaml` drops 29 keys nothing read (output,
  restated image and font policy, unused workflow switches).

## 2026-10-27 — v7 review: safe fixes

- `loc.py brief` warns when a batch exceeds `max_batch_strings` or
  `max_batch_source_tokens`; before this, nothing read those ceilings.
- `check_image_regions.py`: a `KEEP` region's mask is honoured like a
  `TRANSLATE` mask, so a label beside a logo in one box no longer reports a
  false overlap.
- `engines/renpy.md`: five Ren'Py findings from the Slay the Princess
  experience pack (segment word order, choice width, literal screen strings,
  `renpy.get_screen`, parse-only check). `references/qa-strategy.md`: width and
  off-catalogue text checks.
- `AGENTS.md`: removed the stale "tiers mapped per runtime" line.

## 2026-10-27 — Handoff phase: the experiences package

- New phase `handoff` (التسليم) between playtest and release. Its gate needs
  `experiences-<game>-<date>.zip`, built after the user's acceptance.
- `loc.py lesson add|list` records lessons for the developer in
  `work/experiences.jsonl` (template bug, limit, lesson, engine, translation,
  tool, workflow), each with evidence and an optional suggested change and file.
- `loc.py experiences` packs the lessons, facts the code collects (engine,
  adapter contract, fixes, reopened phases, problem counts, phase times), the
  engine profile, the adapter, and reusable scripts. Game text, game files,
  user paths, and secrets stay out; free text is capped. It prints where to
  send it: the Hoshibana Discord server or X, from `config/feedback.json`.
  The dashboard shows the lesson count and, once built, the file and contacts.
- `scripts/maintainer/import_experiences.py` unpacks received zips safely into
  `work/experiences-inbox/`, lists lessons not yet decided, and records each
  decision in `knowledge/experiences-ledger.json` by a content key.

## 2026-10-21 — Remove what nobody reads

- Deleted files no route loads and no skill links: four skill references
  (`ai-localization-workflow`, `engine-playbooks`, `tool-catalog`,
  `improvement-proposals`), `qa/RTL_TEST_MATRIX.md`, the empty
  `loc-kit/GAME_CONTEXT.md` and `SYSTEMS.md`, `scripts/build_manifest.py`,
  `scripts/translation_map_stats.py` with its test, and `reports/archive/`.
- Deleted records nobody reads: `knowledge/PROJECT_DISCOVERIES.md`,
  `knowledge/GENERAL_LOCALIZATION_KNOWLEDGE.md` (its unique lessons moved
  into the references that are loaded), `reports/QA.md`, and
  `reports/IMPROVEMENT_PROPOSALS.md`. `engines/<engine>.md` is now the one
  place knowledge carries between games; template ideas go to the user in
  chat. The `loc.py estimate` result is no longer written to `PLAN.md`.

## 2026-10-21 — Record only what someone uses

- No more recording of each subagent's model, reasoning effort, outputs, or
  checks in `PLAN.md`: nobody reads them, models change, and code recomputes
  outputs and checks. The batch checklist line is the only delegation record,
  with `— unfinished: ...` while a batch is stopped midway.
- Dropped "never switch model, tier, or runtime silently"; model choice is
  free. The quota checkpoint-and-stop rule stays. `translated_by` and
  `proofread_by` are unchanged.

## 2026-10-21 — No model names in the template

- Model names are gone from the policy, its JSON, `CLAUDE.md`, the skills, and
  the generated Claude Code agents. Three tiers remain (light, standard, deep)
  as descriptions; the agent picks a model from those its runtime offers at
  work time. Claude Code roles use `model: inherit`. The policy check rejects
  a runtime that names models.

## 2026-10-21 — The root agent chooses subagent models freely

- No lightest-first rule: the root agent picks any tier (light, standard,
  deep) and effort for each subagent by its own judgment, with no expected
  default and no recorded reason. Route tiers in `config/agent-policy.json`
  and a Claude Code role's `model:` are suggestions
  (`authorization.model_selection`). `make_subagent_brief.py` takes `--tier`
  and `--effort`.

## 2026-10-21 — Fewer intake questions: install, subagents and image editing are fixed

- Installing the checked build on the user's identified copy, using subagents,
  and sending in-scope images to official OpenAI image editing are now
  standing defaults (`"yes"` in `PROJECT.yaml`) and are never asked. The
  intake keeps four questions: game name, its location, images (with a note
  that image work is slower and works best under Codex), and launching the
  game. The intake gate no longer waits for the removed answers.
- Subagents are always used: every translation batch, proofreading pass,
  research question and image set goes to its role.

## 2026-10-21 — The progress page is `dashboard.html`

- `لوحة-التقدم.html` is renamed `dashboard.html`; it stays in the template
  root of every game's folder, beside `خريطة-القالب.html`.

## 2026-10-21 — The progress page lives in each game's folder

- The dashboard moved from `reports/dashboard.html` to `لوحة-التقدم.html` in
  the template root, beside `خريطة-القالب.html`, and ships with the template
  as an empty project's page; every game copy has its own.
- Its time is the newest project data's, not the render's, so an unchanged
  project regenerates the same bytes. A test keeps the shipped page equal to
  an empty project's render. The page links to the map.

## 2026-10-21 — «عرّب اللعبة» is enough to start

- `AGENTS.md`: while the phase is intake, a bare start request starts the
  new-game intake instead of a clarifying question.
- `references/project-run.md`: the intake asks the game name (suggesting the
  working folder's name) and offers to take the install path from the user or
  find it with a read-only search of the usual game libraries.
- The template map shows the same start: copy, name it after the game, point a
  Claude Code or Codex project at it, say «عرّب اللعبة».

## 2026-10-21 — The template map is the starting point

- `خريطة-القالب.html` replaces `اقرأني.md` as the human entry point. It adds
  step zero: copy the whole template folder per game, open that copy itself in
  Claude Code or Codex, and leave the game where it is. Release commands stay
  in `references/release.md`; tool setup stays in the engineering skill.

## 2026-10-21 — Roadmap phase 5: fix lane, needs-rewrite, RTL rendering

- Fix lane: `loc.py fix open|close|list`. A fix records what happens now,
  what should happen, what must not change, and the unit ids it may touch.
  `apply` now refuses to change proofread text unless `--fix` names an open fix
  listing the unit. `fix close --verdict verified` requires evidence,
  re-proofread units, and no change to any other unit's text since the fix
  opened (checked against a snapshot); `partial` and `failed` are honest
  alternatives. The playtest gate blocks on open fixes; the dashboard lists
  them.
- `needs_rewrite`: units a game update sent back to `extracted` with a
  `previous_target` are a problem code and a line in progress reports.
- Adapters declare `rtl` (`native` | `needs_preshape` | `unsupported`);
  `render()` pre-shapes and visually orders text for left-to-right engines with
  `scripts/arabic_shaping.py` (forms derived from the Unicode database, no
  dependency; matches `arabic_reshaper` on 21 test words, keeps diacritics).
  The contract has an eighth check (`rtl`), and the discovery gate requires a
  declared capability. Ren'Py is `native` (needs `config.rtl = True`).

## 2026-10-21 — Roadmap phase 3: batch briefs and an MQM-style proofreader

- `loc.py brief --batch --role --runtime` writes a self-contained brief in
  three layers: rules, role, project conventions, and output contract
  (byte-identical across batches, reported as `CACHEABLE_PREFIX_SHA`), then
  the characters and glossary terms the batch uses, then continuity lines and
  the units (with targets and problem codes for the proofreader).
- Units may carry `context.addressee`, `addressee_gender`, and
  `addressee_number` (validated); speakers come from `loc-kit/CHARACTERS.yaml`.
- Proofreading is an MQM-style estimate: new categories `dialect`,
  `culture`, `wordplay`; each category maps to an MQM dimension; `findings`
  prints the flag rate and penalty per 1,000 words (minor 1, major 5,
  critical 10, blocker 25), and the dashboard shows them across batches. The
  checklist gained six Arabic calibration examples.

## 2026-10-21 — Roadmap phase 2: Arabic typography checks and levels

- New problem codes: `digit_style` (follows `game.digits`), `number_mismatch`
  (numbers 11+ or decimals; 0–10 may be written as words), `end_punctuation`,
  `latin_punctuation` (`? , ;` beside Arabic letters), `whitespace`,
  `doubled_word`, `invisible_chars`, and `forbidden_term` from a new
  `forbidden:` section in `glossary.yaml`. Code spans are ignored.
- Every code is `error` or `warning`; `PROJECT.yaml` → `qa.levels` can
  promote or demote any code. The localization gate now blocks on every
  error-level code (including glossary misses and forbidden forms) instead of
  a separate glossary line; `loc.py terms` also lists forbidden forms.
- A test fails if a problem code is missing from the reference table.

## 2026-10-21 — Roadmap phase 1: batch alignment and problem codes

- `loc.py apply <answer.json> --batch|--ids --by`: writes a translator's
  batch answer (JSON keyed by unit id) only when every expected id is present,
  non-empty, and nothing extra came back; otherwise nothing is written and the
  missing/extra/empty ids are listed. Unchanged targets keep their
  proofreading; changed ones return to `translated`.
- Eleven stable problem codes (`latin_leak`, `lost_newline`, `too_long`,
  `glossary_term_missing`, `persian_letters`, ...) computed per unit, shown by
  `validate` and the dashboard, and listed with `loc.py search --problem
  <code> --ids-only` for selective re-translation.
- The translator role never edits unit files directly; it writes one JSON
  answer and applies it. `search` gained `--path` for problem-only searches.

## 2026-10-21 — Roadmap phase 0: skill descriptions, budgets, manifest

- All eight skill descriptions are now trigger-only (`Use when ...` plus
  Arabic trigger words) instead of summaries of their steps.
- `tests/test_budgets.py`: `AGENTS.md` and `CLAUDE.md` under 200 lines,
  `AGENTS.md` well under Codex's 32 KiB cut-off, skill names matching their
  folders, descriptions within 1,024 characters, skill bodies under 500 lines.
- `sync_runtime.py` records every generated file with its SHA-256 in
  `.claude/generated-manifest.json`; `--check` tells a hand edit from an
  out-of-date copy. Fixed: a sync used to delete the whole `.claude/skills`
  and `.claude/agents` folders, including skills a user added there.
- `AGENTS.md` tells Codex which hook checks to run by hand.

## 2026-10-21 — loc.py commands made discoverable

- One table in `references/translation-units.md` lists all 18 `loc.py`
  commands with their phase and when to use them; a test fails if a new
  command is missing from it.
- Every `--help` line now says when to use the command.
- `pseudo` is now in the extraction reference and QA skill, `estimate` in the
  new-game run before the first batch, and `AGENTS.md` tells Codex to run
  `loc.py dashboard` after editing `PLAN.md` or the LQA matrix.

## 2026-10-21 — Batch plan rule and reference list

- The full batch plan is written as a checklist under `## الدفعات` in
  `PLAN.md` before extraction closes, and each batch is ticked when proofread.
  The extraction gate requires the list and the localization gate requires
  every box ticked; the dashboard shows it live.
- `اقرأني.md` gained a short reference list for human readers and the
  proofreading, images, and release route commands.

## 2026-10-21 — Phase 6: glossary check, script rule, images, roles

- `loc.py terms` checks every translated unit against `glossary.yaml`
  (general, game-specific, names, keep-Latin, and context rules), folding
  Arabic spelling variants and the article/proclitics. A deliberate variant is
  recorded per unit with `--allow <id> <term>`. The localization gate now
  requires zero open misses, and the proofreading skill runs it first.
- Explicit rule in `AGENTS.md` for when agents write scripts, with a registry
  (`tools/project-scripts.json`, validated by `check_project_scripts.py`)
  listed at every session start so later sessions and models reuse them.
- `references/image-localization.md` condensed from 218 to 145 lines and the
  skill from 66 to 33 without dropping a rule; the policy YAML is now optional
  context. The images route went from 7,521 to 4,765 estimated tokens.
- New roles: `researcher` (read-only, light tier, web tools) and
  `image-localizer` (standard tier), with `research` and `image_work` routes.

## 2026-10-21 — Phase 5: efficiency, PLAN.md, and the dashboard

- Token waste: `context_plan.py` no longer lists the skill file it was invoked
  from; Claude Code subagent briefs no longer repeat the role text (2,715 →
  1,321 characters); `loc.py validate` and `search` print at most 20/50 lines
  plus counts by kind (500 identical errors → 22 lines).
- `STATUS.md` is replaced by `PLAN.md` (24 lines, capped at 150 by a hook):
  decisions, batches, open questions, notes, blocker, next action. Counts,
  phase, intake answers, backup paths, and command logs live in their own
  files instead of being copied into it.
- `reports/dashboard.html` is generated by code from units, state, the LQA
  matrix, and `PLAN.md`; hooks and every state-changing `loc.py` command
  refresh it, and it reloads itself every 15 seconds. Gate messages are Arabic.
- Template-only scripts moved to `scripts/maintainer/` (`build_release`,
  `license_guard`, `check_agent_policy`, `check_context_routes`).
- CSV-era tools replaced by unit commands: `loc.py update` (game updates,
  with `previous_target`), `tmx`, `estimate` (Arabic-aware), and `pseudo`.
  Removed `check_tokens`, `project_stats`, `merge_game_update`, `export_tmx`,
  `estimate_tokens`, `pseudo_localize`, `source/`, `target/`,
  `STRING_CONTEXT.csv`, `GUIDE.md`, `STYLE.md`, `.releaseignore`, and the
  committed report snapshots.
- Fixed: on Windows the hooks compared lowercased paths, so the YAML check on
  `PROJECT.yaml` never ran after an edit.

## 2026-10-19 — Phase 4: phase gates and Claude Code hooks

- Added `scripts/loc_pipeline.py` and `loc.py next | gate | reopen | accept`.
  Seven phases (intake, discovery, extraction, localization, integration,
  playtest, release) advance only when file-based exit criteria pass; the
  extraction gate runs the adapter contract and records it against the
  adapter and game-text fingerprints. State lives in `state/pipeline.json`;
  `workflow.current_route` was removed so the phase has one source of truth.
- Added `.claude/settings.json` hooks via `scripts/claude_hooks.py`: block
  writes to an existing game file without a backup, any write under backups,
  and shell commands that write into the game folder without a backup-first
  tool; re-validate units, findings, and YAML after edits; regenerate
  `.claude/` after skill or role edits; show `loc.py next` at session start.
- The adapter contract now copies and hashes only inventory files, so it
  stays cheap on multi-gigabyte games.

## 2026-10-19 — Phase 3: adapters and the Ren'Py reference game

- Added the `Adapter` interface (`adapters/base.py`): inventory, extract,
  rebuild into a separate folder, and read back what the game would show.
- Added `scripts/adapter_contract.py` with seven checks (inventory, extract,
  deterministic, read-back, identity, round-trip with pseudo-Arabic, and
  isolation of the game folder); adapter exceptions fail the step instead of
  crashing. It runs in `verify_template.py`.
- Added `adapters/renpy.py` for Ren'Py's native `game/tl/<language>/` files
  and `examples/renpy-reference`, an original MIT-licensed micro game.
- Added `loc.py extract` and `loc.py rebuild` (proofread units only by
  default; never writes inside the game folder).

## 2026-10-19 — Phase 2: proofreading skill and roles

- Added the `arabic-proofreading` skill with a category/severity checklist,
  a findings file per batch, a one-pass stop rule, and a `proofreading`
  context route and model route (standard/medium).
- `loc.py mark --status proofread` now requires `--by` and stores a hash of
  the proofread target; validation fails if a unit reaches proofread or later
  without proofreading, or if its target changes afterwards.
- Added `loc.py findings` to validate findings against units and summarize
  them by severity, category, and resolution.
- Added runtime-neutral `translator` and `proofreader` roles in
  `.agents/roles/`. `scripts/sync_runtime.py` (renamed from
  `sync_runtime_skills.py`) renders them as Claude Code subagents in
  `.claude/agents/`; `make_subagent_brief.py --role` gives Codex the same
  instructions.

## 2026-10-19 — Phase 1: translation units and measured progress

- Added `units/**/*.jsonl`, one record per string and per image text region,
  with five forward-only statuses: extracted, translated, proofread,
  integrated, tested. Integrated and tested require recorded evidence; a
  proofreader must differ from the translator; source hashes catch changed
  sources.
- Added `scripts/loc.py` (`validate`, `normalize`, `search`, `mark`,
  `progress`) and `scripts/loc_units.py`. Progress is computed from units and
  `qa/LQA_MATRIX.csv` and rendered as chat text, `reports/PROGRESS.md`, or
  `reports/progress.html`; `PROJECT.yaml` → `reporting.progress_display`
  defaults to showing it only when asked.
- Image text regions, including KEEP ones, are now searchable units.
- `STATUS.md` no longer carries counts; documented per-batch Git commits and
  tags for private game repositories.

## 2026-10-19 — Phase 0: runtime-neutral, safe defaults

- Fixed `glossary.yaml`: unquoted `Yes`/`No`/`On`/`Off` keys loaded as YAML
  booleans and silently dropped `نعم` and `لا`. Added `scripts/check_yaml.py`
  (rejects non-string and duplicate keys) to `verify_template.py`.
- Template defaults for installing on the user's copy and for OpenAI image
  editing are now `"ask"`; the new-game intake asks for both explicitly.
- Model routes now name tiers (light/standard/deep) mapped per runtime for
  Codex and Claude Code; the policy allows the active runtime's hosted models
  and keeps the local-model ban (reason: translation quality).
- Claude Code support: `CLAUDE.md` imports `AGENTS.md`; `.claude/skills/` is
  generated from `.agents/skills/` by `scripts/sync_runtime_skills.py` and
  checked for drift. Added a mixed-runtime single-writer rule.
- `source/` and `target/` READMEs no longer claim they fill automatically.

## 2026-10-03 — Font sourcing and records

- Added conditional web search and direct visual comparison of Arabic font
  candidates for game text and images; source examples are not a site allowlist.
- Allowed verified font downloads and necessary current-user-only Windows
  installation under the project's standing policy, with rights and rollback
  gates; no all-users or existing-font replacement route.
- Added project font/notice folders, separate selected-use and system-install
  records, structural validation, and a public-template release exclusion for
  nonempty local records or actual font binaries.

## 2026-10-03 — Full-template audit fixes

- Created an exact Git baseline before these changes and developed them in a
  separate worktree/branch.
- Extended developer patch packages to add and replace files, check hashes,
  back up originals, uninstall, and recover interrupted prepared installs;
  final recipient installers remain a separate game-specific release gate.
- Prevented approved translations from carrying into changed context; mapped
  detected engine IDs to their existing profiles and repaired missing tool
  profile declarations.
- Clarified Arabic plural categories, image structural-check limits, direct
  visual QA, typography contrast/style constraints, and detailed LQA records.
- Added explicit engine-profile evidence states and selected-tool provenance;
  application downloads now require exact versions/tags and published hashes.
- Added synthetic regression tests and distinct backup transaction names.

## 2026-10-02 — Localization mod route

- Added a focused one-time survey of game/engine mods that solve Arabic
  localization, font, RTL, UI, subtitle, or asset-override needs.
- Defined how to compare native support, an unmodified dependency, a lawfully
  modified mod, and an independent localization-only mod, with compatibility,
  license, conflict, protection, rollback, and release gates.
- Added a `mod-research` context route and reusable engine-profile evidence
  fields without requiring a broad mod catalogue or gameplay changes.

## 2026-09-28 — New-game autonomous run and playtest gate

- Added one grouped startup intake for new games, including project preferences
  for subagents and baked-image translation.
- Defined continuous execution through verified installation on the user's
  identified copy, followed by user playtesting and a fix loop without
  phase-by-phase approval requests.
- Separated the post-acceptance portable game installer from the public
  template archive; required compatibility checks, rollback, dependencies,
  and Arabic installation instructions.

## 2026-09-28 — Lean records and resource-path maps

- Made STATUS a short resumable snapshot; kept detailed QA defects in the LQA
  matrix and summaries in the QA report, avoiding per-batch duplication.
- Aligned discovery notes and engine-profile promotion to phase boundaries,
  except for verified safety/tool decisions needing immediate documentation.
- Added portable image, text, font, audio/subtitle and localization path maps
  with version/platform evidence, without listing every asset or personal paths.

## 2026-09-28 — Audit hardening

- Fixed ICU branch-text false positives and checked XLIFF inline-code identity.
- Restricted update carry-forward and TMX export to approved, context-safe rows.
- Made safe replacement and patch install backups unique per transaction;
  added exact-original preflight and synthetic build/install/restore tests.
- Switched public ZIP creation to `.releaseinclude` and generated file-level
  CycloneDX inventories from an actual ZIP or directory.
- Required a concise agent visual-review record for approved image regions;
  visually rejected three representative existing Danganronpa image candidates.

## 2026-09-28 — Image localization policy

- Added the `game-image-localization` skill, `images` context route, and a
  machine-readable image policy.
- Added `TRANSLATE/KEEP/REVIEW` classification, adaptive multi-method search,
  mandatory direct visual inspection, source-style fidelity, and a prohibition
  on invented captions or effects.
- Added tested conditional roles for OpenCV, PaddleOCR, IOPaint/LaMa, SAM2, and
  DirectXTex. Official OpenAI image editing is enabled per project, with review
  required before integration.

## 2026-09-27

- Replaced full-corpus startup reading with validated progressive-disclosure
  routes for discovery, translation, QA, delegation, maintenance, and release.
- Split the large guide and style documents into focused references while
  preserving the safety, Arabic, renderer, integration, and release rules.
- Reduced duplicated skill instructions and changed root review to deterministic
  integration plus risk-based semantic sampling instead of full retranslation.
- Added `context_plan.py`, route tests, a temporary knowledge inbox, and
  phase-boundary promotion to prevent duplicated notes.
- Separated ordinary template verification from release-only SBOM work and
  archived historical reports outside the normal workflow and public package.

## 2026-09-26

- Added a single deterministic verification command.
- Hardened patch hash verification, path checks, backups, and rollback.
- Preserved placeholders and markup during pseudo-localization.
- Reduced false-positive rejection in extracted text classification.
- Made engine knowledge validation accept the documented profile structure.
- Added project licensing and security/contribution documentation.
- Added PO/XLIFF/ICU QA, Arabic plural diagnostics, HarfBuzz shaping smoke tests,
  CycloneDX SBOM generation, pinned Python constraints, and privacy-aware public
  release packaging.
