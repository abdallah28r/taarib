# Dinky / GGPack (Return to Monkey Island, Thimbleweed Park) profile

Evidence state: `documented-external`; from the Return to Monkey Island
project in the Arabic Game Localization Playbook (MXIAUDIO and contributors,
CC BY 4.0), adapted. That project was not finished.

## Identification

- `*.ggpack*` archives (GGDict with 2-byte string indices), `weird.dink`
  compiled scripts, `Text_en.tsv`, TTF fonts, KTX1 textures (zlib, BC7/BC3).
- `python scripts/detect_engine.py <game_root>` reports `dinky`.

## Localization locations

- Archive XOR keys come from the executable by hash match: "Protected archives
  and runtime code" in `references/extraction-integration.md` applies; keys
  are never published.
- `Text_en.tsv`: unquoted TSV with LF; rebuild without changing other fields,
  never convert it to CSV. Arabic went, visually ordered, into the `en` column
  of a copy; it is not a new language.
- Injection: a copy of the archive with replacement resources appended at
  16-byte alignment, index and guid kept, every replaced resource re-extracted
  and compared.
- Isolated testing: a copy of the executable whose company name is replaced
  by a same-length name, so its profile folder is separate.

## Arabic and fonts

- The engine reads Unicode but does not shape or reverse. Build: wrap
  logically per text role with that role's font and width, shape and reverse
  each line, join lines with `⏎` (U+23CE, which the renderer turns into LF;
  `\n` shows as letters), and turn spaces inside a line into `▫` (U+25AB) so
  the engine does not re-wrap. Protect `%BTN%` and `%s` during reordering.
- Add Arabic glyphs to every English TTF in use, scaling to the target
  unitsPerEm and keeping existing metrics; for variable fonts load
  `gvar`/`HVAR` before adding (`fonttools`).
- Pieces joined by scripts: build the paragraph logically before reordering;
  the first piece carries the whole paragraph, the others `▫`.

## Workflow

1. Read archives with `dinky-explorer` (reference); extract TSV and fonts.
2. Build the TSV copy, fonts, and textures (`ispc-texcomp` re-encodes only the
   changed BC7 blocks and mipmaps).
3. QA seeds (test-only scripts that open document rooms) never leak into the
   normal build. Puzzle checks (note orders, directions) are never removed
   to fit a translation.

## Tools

Catalog tools: `dinky-explorer`, `ispc-texcomp`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine dinky`. Install rules: step 4 of
`game-localization-engineering`.

## Logs

The profile folder is under `%APPDATA%/<company>/<game>`; `loc.py probe` looks
there for new files after a launch.

## Limitations

Unfinished project; distribution was not reached. A second archive (`9a`)
load path was not confirmed.

## Sources

- https://github.com/Xxdm234/Arabic-Game-Localization-Playbook — `engines/DINKY.md` (commit 2475fb6, read 2026-10-28).
- https://github.com/bgbennyboy/Dinky-Explorer (no license file: reference only), https://github.com/GameTechDev/ISPCTextureCompressor (MIT, archived).
