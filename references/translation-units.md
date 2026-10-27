# Translation units

`units/**/*.jsonl` is the per-string source of truth for a game project: one
JSON object per line for every player-visible string **and** every text region
inside an image. Progress, search, and status come from these files, never
from an agent's estimate. Native game files stay authoritative for structure;
units carry the text, its context, and how far it has travelled.

## Statuses (forward only, each implies the previous)

| Status | Meaning | Required to enter |
| --- | --- | --- |
| `extracted` | source recorded | `id`, `kind`, `file`, `source`, `source_hash` |
| `translated` | Arabic exists in the unit | non-empty `target` (unless `decision: keep`), matching tokens |
| `proofread` | checked once by a different agent (`arabic-proofreading`) | `mark --by`; stores `proofread_by` (≠ `translated_by`) and `proofread_hash` of the target |
| `integrated` | part of a game build | `evidence.integrated_build` (which build) |
| `tested` | seen working in the game | `evidence.tested` (what was observed, where) |

A unit cannot reach `integrated` without being proofread, and editing its
target afterwards fails validation until it is proofread again.
Translated is not integrated, and integrated is not tested. Never mark a unit
`tested` from a validator pass; only runtime observation by the user or an
authorized agent launch counts.

`decision` is `translate` (default), `keep` (deliberately left as source, such
as a logo on clothing; excluded from progress percentages), or `review` (a
blocking question; keep the unit at `extracted` or `translated` until resolved).

## Fields

- Required: `id` (stable, unique across the project, e.g. `ui/menu#new_game`),
  `kind` (`text` or `image`), `file` (native file, relative path), `source`,
  `source_hash` (written by `loc_units.new_unit` / `loc.py normalize`), `status`.
- Image units add `asset` and `box` `[x, y, width, height]`; `source` is the
  text visible in that region, so image text is searchable like any string.
  Record every region, including `keep` ones. Image-specific approval data
  still lives in the region manifest checked by `check_image_regions.py`.
- Optional: `key` (native key), `target`, `decision`, `batch`, `context`
  (`speaker`, `scene`, `location`, `function`, `addressee`,
  `addressee_gender` m|f|mixed|unknown, `addressee_number`
  singular|dual|plural), `max_length`,
  `translated_by`, `proofread_by`, `proofread_hash`, `evidence`, `notes`,
  `term_exceptions` (glossary terms this unit deliberately inflects or varies;
  set with `loc.py terms --allow <id> <term>`), `previous_target` (set by
  `loc.py update` when a game update changed the source).

Adapters create units with `loc_units.new_unit(...)`. When a game update
changes a source, validation fails on the hash: review the target, mark the
unit `extracted` with `--force`, then run `normalize`.

## Commands

Every command is `python scripts/loc.py <command>`; `<command> --help` gives
its options. This table is the one map of when to use each.

| Phase | Command | When |
| --- | --- | --- |
| any | `next` | Session start or when unsure: phase, blockers, what to load. |
| any | `gate` (`--check`) | When `next` says ready; never skip it to move on. |
| any | `reopen <phase> --reason` | A game update or finding sends work back. |
| any | `dashboard` | In Codex after editing `PLAN.md` (Claude Code hooks do it). |
| any | `progress --format chat\|md\|html` | When the user asks, or per `reporting.progress_in_chat`. |
| extraction | `extract --adapter --game --out` | Once the adapter contract passes. |
| extraction | `pseudo --adapter --game --out` | Before translating: install on a copy to test Arabic rendering and length. |
| extraction | `estimate` | Before the first bulk batch, to size batches (not recorded anywhere). |
| localization | `brief --batch --role --runtime` | Before sending a batch to a translator or proofreader. |
| localization | `apply <answer.json> --batch --by` | Translator: write a batch answer keyed by unit id; refused unless every id matches. |
| extraction | `no-images --reason` | Images in scope but the game has no baked text images; say what was searched. |
| localization | `mark --status translated --by` | Only for units whose target was written another way (images). |
| localization | `validate` | After every batch and every edit; zero errors before integration. |
| localization | `terms` (`--allow <id> <term>`) | Proofreader first step; the gate needs zero misses. |
| localization | `findings <file>` | Proofreader, after recording findings; prints flag rate and MQM score. |
| localization | `mark --status proofread --by` | Proofreader, for units with no open finding. |
| any | `search "<text>"` / `search --problem <code> --ids-only --path <units>` | Find a string or image text; list units with one problem to redo or review them. |
| integration | `rebuild --adapter --game --out` | Build files from proofread units, outside the game. |
| integration | `mark --status integrated --evidence` | After installing a build, naming it. |
| playtest | `mark --status tested --evidence` | Only for what was observed in the running game. |
| playtest | `accept --note` | Only on the user's explicit acceptance in chat. |
| any | `lesson add\|list` | The moment you find a template bug, limit, engine quirk, translation lesson, tool result, or workflow problem. |
| handoff | `experiences` | After acceptance: build `experiences-<game>-<date>.zip` and tell the user where to send it. |
| playtest | `fix open\|close\|list` | A small reported problem: record current / expected / unchanged, change the units with `apply --fix`, re-proofread, close with a verdict. |
| maintenance | `update --adapter --game --path` (`--dry-run`) | A new game version arrived; then `reopen`. |
| maintenance | `normalize` | After resetting a changed unit to `extracted`. |
| release | `tmx --out <file>` | Keep a translation memory for later games. |

Problem codes (`validate`, `search --problem`) and their levels are listed in
`references/problem-codes.md`.

`extract` and `rebuild` go through an adapter (`adapters/README.md`).
`rebuild` writes only units at `proofread` or later unless `--min-status` says
otherwise, and only to a folder outside the game.

`mark` refuses backward moves (unless `--force`) and refuses any change that
would add a validation error. `apply` refuses to change proofread text unless
`--fix F-xxx` names an open fix that lists the unit; closing that fix as
`verified` needs evidence, re-proofread units, and no change to any other
unit's text since the fix was opened. After closing, rebuild and mark the
units `integrated` again.

## Showing progress

`dashboard.html`, in the root of each game's copy, is always current: code regenerates it from units,
`state/pipeline.json`, `qa/LQA_MATRIX.csv`, and `PLAN.md` after every change
(Claude Code hooks, and every `loc.py` command that changes state). It refreshes
itself in the browser every 15 seconds. Never write it by hand.

In the conversation, `PROJECT.yaml` → `reporting.progress_in_chat` decides:
`on_request` (default) prints `loc.py progress` only when the user asks;
`batch` prints it at each batch or phase boundary. `--format md` writes
`reports/PROGRESS.md` when a Markdown copy is wanted. `PLAN.md` never repeats
counts.

## Versions in Git

In a game project's **private** repository, commit `units/` and `glossary.yaml`
after each batch (`batch-004: translated 312 units`) and tag it
(`git tag batch-004`); tag each installed build (`build-1.0.3-r2`). Restore or
compare any batch with `git diff batch-003 batch-004 -- units/`. Game binaries,
textures, and backups stay out of Git in `backups/`, keyed by hash. The public
template ignores `units/*` so copyrighted game text can never be published by
accident; remove that ignore line only in a private game repository.
