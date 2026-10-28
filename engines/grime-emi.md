# GrimE (Grim Fandango, Escape from Monkey Island) profile

Evidence state: `documented-external`; from the Escape from Monkey Island
project in the Arabic Game Localization Playbook (MXIAUDIO and contributors,
CC BY 4.0), adapted. Played through ScummVM, not the original executable.

## Identification

- Archives with signature `LABN` (`.m4b`/`.lab`, names XOR 0x96; not every
  `.m4b` is an archive), `script.tab`, LAF fonts, Lua 3.1 compiled scripts.
- `python scripts/detect_engine.py <game_root>` reports `grime-emi`.

## Localization locations

- `script.tab` inside `artAll.m4b`, scrambled (RCNE); decrypted it is `DOEL`
  then `tag TAB text CRLF`. The engine also reads unscrambled `DOEL`, so the
  build writes plain text. Unscrambling is "Protected archives and runtime
  code" in `references/extraction-integration.md`.
- Inject with a separate `datausr.m4b` and `datausr_load=true`, which ScummVM
  loads before the original: text, fonts, fixed scripts, images.
- Lua text outside `script.tab`: inventory tagged strings in the scripts.
- Do not run `MonkeyUpdate.exe`; ScummVM reads it as patch data.

## Arabic and fonts

- LAF: 32-byte header, 256 indices, 256 × 16-byte descriptors, bitmaps
  (0 transparent, 128 shadow, 255 ink). Build a 128-glyph Arabic bank at
  128–255 after reserving the accented letters English uses
  (`scripts/font_bank.py`); a font that mapped 182 to space must map it back.
- Sentence order and line wrapping needed engine changes in the project's
  ScummVM build (signed `char` in measuring, reversed line index); keep such
  patches with their source diff and recheck on every engine update.

## Workflow

1. Pin a ScummVM build with EMI support; keep the original untouched.
2. Build `datausr.m4b` with text, LAF bank, and script fixes.
3. Package as a folder ScummVM uses as `path` (localization files plus
   verified links to the originals), originals as `extrapath`; verify every
   original file hash after install and uninstall.

## Tools

Catalog tools: `scummvm`, `scummvm-tools`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine grime-emi`. Install rules: step 4 of
`game-localization-engineering`.

## Logs

ScummVM log (`%APPDATA%/ScummVM/Logs/scummvm.log`): `loc.py probe` reads it.

## Limitations

The original `Monkey4.exe` was not tested. Bink subtitles were moved by an
engine patch. Static analysis of Lua references does not prove a string is
never loaded.

## Sources

- https://github.com/Xxdm234/Arabic-Game-Localization-Playbook — `engines/GRIME_EMI.md` (commit 2475fb6, read 2026-10-28).
- https://github.com/scummvm/scummvm and https://github.com/scummvm/scummvm-tools (GPL-3.0).
