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
  (`speaker`, `scene`, `location`, `function`, …), `max_length`,
  `translated_by`, `proofread_by`, `proofread_hash`, `evidence`, `notes`,
  `term_exceptions` (glossary terms this unit deliberately inflects or varies;
  set with `loc.py terms --allow <id> <term>`), `previous_target` (set by
  `loc.py update` when a game update changed the source).

Adapters create units with `loc_units.new_unit(...)`. When a game update
changes a source, validation fails on the hash: review the target, mark the
unit `extracted` with `--force`, then run `normalize`.

## Commands

```text
python scripts/loc.py validate                 # after every batch; zero errors before integration
python scripts/loc.py search "Press Start"     # sources and targets, text and images
python scripts/loc.py mark --batch batch-004 --status translated --by translator-1
python scripts/loc.py mark --batch batch-004 --status integrated --evidence "1.0.3 patch r2"
python scripts/loc.py progress --format chat|md|html
python scripts/loc.py terms                    # glossary conformance; the localization gate needs zero misses
python scripts/loc.py extract --adapter adapters/renpy.py --game <game_root> --out units/game.jsonl
python scripts/loc.py rebuild --adapter adapters/renpy.py --game <game_root> --out builds/r1
```

`extract` and `rebuild` go through an adapter (`adapters/README.md`).
`rebuild` writes only units at `proofread` or later unless `--min-status` says
otherwise, and only to a folder outside the game.

`mark` refuses backward moves (unless `--force`) and refuses any change that
would add a validation error.

## Showing progress

`reports/dashboard.html` is always current: code regenerates it from units,
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
