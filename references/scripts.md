# Scripts index

One line per script: when to use it. Before the first use of a script in a
session, run `python scripts/<name>.py --help` (or read its docstring): the
options and examples live there. Modules marked *(library)* are used by other
scripts; you rarely run them directly. A test fails if a script under
`scripts/` has no line here.

**Changing them.** You may change any template script, config, or adapter in
this project when you find a bug or a better way, as you judge best. Run
`verify_template.py` afterwards and record the change at once with
`loc.py lesson add --type template-bug|workflow --what ... --evidence ...
--suggest ... --file scripts/<name>.py`, so the template's developer receives
it. Add a line here for any new script.

**One fix, every copy.** A bug found in one place is rarely only there. Before
calling it fixed, search `scripts/`, `adapters/`, `work/tools/`, and `config/`
for the same idea: the same regex, assumption, path pattern, encoding, or
per-engine branch. Fix every copy or confirm in the lesson why it is safe, and
add a test that fails on the old behaviour so the mistake cannot return.

**An engine the detector does not know.** Inspect its files yourself; add its
file and folder markers to `config/engine-markers.json` (no code change), or
write a detector script when names are not enough; then
`loc.py probe --game <root> --engine <new-id> --record` starts its profile and
catalog entry.

## Every phase

| Script | When |
| --- | --- |
| `loc.py` | Units, phases, gates, briefs, progress, fixes, lessons; every subcommand is in `translation-units.md` → Commands. |
| `context_plan.py` | Before a task: prints the few files the route needs. |
| `verify_template.py` | After changing any template file (script, reference, skill, config). |
| `check_yaml.py` | After editing a YAML file (hooks do it in Claude Code). |
| `sync_runtime.py` | After editing `.agents/skills/` or `.agents/roles/`. |
| `claude_hooks.py` | *(library)* Claude Code hooks; never run by hand. |

## Discovery

| Script | When |
| --- | --- |
| `detect_engine.py` | First look at a game: engine and existing mod loaders. Unknown engine: add markers to `config/engine-markers.json`. |
| `detect_protection.py` | Before any change: anti-cheat, DRM, and online markers stop the route. |
| `game_probe.py` (`loc.py probe`) | Fonts and their Arabic (`--deep-fonts` inside Unity assets, saved for the preview), a preview in the game's font (`--native` for engines that shape Arabic), logs after a launch (`--save-baseline` on the unpatched game first); `--engine <id> --record` starts a profile for an unknown engine. |
| `tool_doctor.py` | After the engine is known: that engine's catalog tools and which are installed. |
| `check_tool_provenance.py` | After choosing or installing a tool: validates `tools/selected-tools.json`. |
| `check_knowledge.py` | After editing or creating an engine profile: its sections and evidence state. |
| `capture_filter.py` | Filtering strings captured from screens, logs, or memory into candidates with reasons. |

## Extraction and adapters

| Script | When |
| --- | --- |
| `adapter_contract.py` | Before bulk translation: proves an adapter extracts, rebuilds, and reads back on a copy. |
| `check_project_scripts.py` | After writing a game script in `work/tools/`: validates its registry entry. |

## Translation and proofreading

| Script | When |
| --- | --- |
| `make_subagent_brief.py` | A brief for a research or image subagent (text batches use `loc.py brief`). |
| `delegate.py` | Run a written brief in the other runtime when the project uses Codex and Claude Code together. |
| `loc_brief.py` | *(library)* builds `loc.py brief`. |
| `loc_units.py` | *(library)* the translation-unit record and its validation. |
| `loc_tools.py` | *(library)* problem codes, terms, update, TMX, estimate, pseudo. |
| `loc_pipeline.py` | *(library)* phases and gates behind `loc.py next/gate`. |
| `loc_tasks.py` | *(library)* the task board behind `loc.py task` and `tasks.html`. |
| `file_ops.py` | *(library)* replace or remove a game file, retrying while Windows briefly holds it; a clear "file in use" error otherwise. |
| `review_pages.py` | *(library)* `texts.html` and `images.html`: the game's text and images before and after. |
| `loc_experiences.py` | *(library)* lessons and the experiences package. |

## QA

| Script | When |
| --- | --- |
| `loc_qa.py` | CSV/TSV/JSON/YAML translation tables: tokens, line breaks, Latin leaks. |
| `format_qa.py` | PO, XLIFF, and ICU message files. |
| `check_font.py` | A TTF/OTF against the characters the text needs; `--shape` HarfBuzz smoke test. |
| `font_bank.py` | One-byte engines: Arabic glyph slots with a stable seed; `coverage` of a font against the build; `dte` pairs. |
| `check_font_records.py` | After selecting or installing a font: its usage and install records. |
| `check_image_regions.py` | Image region manifests and candidates (outside pixels and transparency kind unchanged). |
| `image_candidate.py` | A generative image candidate through Codex, then `composite` into the text region. |
| `boot_verdict.py` | After a launch: crash, new errors, or missing Arabic glyphs from the game's log. |

## Build, install, and release

| Script | When |
| --- | --- |
| `arabic_shaping.py` | *(library)* shaping, line wrapping, visual order, `unrender`; used by adapters' `render()`. |
| `storage_core.py` | *(library)* streaming hashes, link checks, and free-space preflight for large files. |
| `original_store.py` | *(library)* one verified pre-localization original per game file. |
| `patch_v3.py` | *(library)* full-snapshot patch update, removal, rollback, and crash recovery. |
| `storage_audit.py` | `report <root>` inventories a project; `clean-temp <root>` removes only verified template-owned temporary files. |
| `safe_backup.py` | Before changing a game file: preserve its original once; repeated calls verify and reuse it. |
| `safe_replace.py` | Replace or restore one game file atomically using the verified original. |
| `save_guard.py` | Snapshot the player's save folder before the first launch of a patched build. |
| `build_patch_package.py` | A hash-checked full-snapshot package of added and replaced files. |
| `apply_patch_package.py` | Install or upgrade a schema 3 package on the user's identified copy; rebuild old packages before installing. |
| `uninstall_patch_package.py` | Restore the single original after verifying installed hashes; previously installed legacy transactions remain removable. |
| `byte_patch.py` | Archives or disc images too large to ship whole: byte-range patch, hash-checked apply; guarded byte edits. |
| `generate_sbom.py` | Release: a file-level SBOM of the actual release archive. |

## Template maintenance (`scripts/maintainer/`)

| Script | When |
| --- | --- |
| `maintainer/import_experiences.py` | In the master template: bring users' experiences zips in and decide each lesson. |
| `maintainer/build_release.py` | A public template ZIP (not a game patch). |
| `maintainer/check_agent_policy.py` | *(run by verify_template)* subagent policy and tool surfaces. |
| `maintainer/check_context_routes.py` | *(run by verify_template)* context routes and their coverage. |
| `maintainer/license_guard.py` | *(run by verify_template)* research-source and release licensing metadata. |
