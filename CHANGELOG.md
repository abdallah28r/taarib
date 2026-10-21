# Changelog

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
