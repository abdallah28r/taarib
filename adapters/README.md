# Adapters

An adapter is the only code that reads or writes a game's text format. It turns
the game's files into translation units and writes translated units back.
Everything else (translation, proofreading, progress, QA) works on units.

| Adapter | Engine | Route | Proven on |
| --- | --- | --- | --- |
| `renpy.py` | Ren'Py | native `game/tl/<language>/` files from the Ren'Py SDK | `examples/renpy-reference` (synthetic) |

## Contract

Subclass `Adapter` from `base.py` and implement:

- `inventory()`: text-bearing files, relative to the game root.
- `extract()`: one unit per player-visible string via `loc_units.new_unit`,
  with stable ids, the native `file` and `key`, and context (speaker, scene).
- `rebuild(units, out_dir)`: write only files that change, only into
  `out_dir`, leaving every untranslated part byte-identical.
- `read_back(root)`: the text the game would show for each unit id.

Set `rtl` from discovery evidence: `native` when the engine shapes and orders
Arabic itself (write logical text), or `needs_preshape` when it renders left to
right only; then `render()` shapes each line with forms derived from Unicode
and reverses it for display, keeping Latin runs, numbers, and code spans
intact. Wrap lines before rendering, because reversing a wrapped paragraph puts
its lines in the wrong order. Always pass targets through `self.render()` in
`rebuild`. `unsupported` (or the default `unknown`) fails the contract and the
discovery gate. Units keep logical Arabic whatever the engine needs.

Set `token_profile` (`generic`, `renpy`, `rpgmaker`, `paradox`) and end the
module with `ADAPTER = <YourClass>`. Fail with a clear `ValueError` naming the
file and line for any construct you do not support; never guess.

## Prove it before bulk translation

```text
python scripts/adapter_contract.py --adapter adapters/<name>.py --game <copy of the game>
```

All eight checks must pass on the actual game build: rtl, inventory, extract,
deterministic, read-back, identity, round-trip, and isolation. The contract
runs in temporary copies and never writes to the game. A pass proves the text
round trip only, not in-game rendering, fonts, or RTL; those stay with QA and
the user playtest.

## Use it

```text
python scripts/loc.py extract --adapter adapters/<name>.py --game <game_root> --out units/<name>.jsonl
python scripts/loc.py rebuild --adapter adapters/<name>.py --game <game_root> --out builds/<build-id>
```

`rebuild` includes only units at `proofread` or later by default
(`--min-status`) and refuses an output folder inside the game. Installing the
built files is a separate step with backups (`safe_backup.py`,
`build_patch_package.py`).

A game-specific adapter lives in the game project's `adapters/` folder. Once it
is proven on a second game of the same engine, promote the reusable parts
here with a synthetic example under `examples/`.
