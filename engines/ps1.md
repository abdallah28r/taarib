# PlayStation 1 (emulated) profile

Evidence state: `documented-external`; from Harvest Moon: Back to Nature and
Wild Arms 2 in the Arabic Game Localization Playbook (MXIAUDIO and
contributors, CC BY 4.0), adapted. Only for a disc image the user dumped from
a disc they own; never download BIOS files or images. PS4 packages stay out
of scope.

## Identification

- `.bin/.cue` (MODE2/2352) with ISO9660 and a PS-X EXE (`SLUS_xxx.xx`,
  `SCES_…`, `SYSTEM.CNF`).
- `python scripts/detect_engine.py <folder>` reports `ps1`.

## Localization locations

- Read files by sector (LBA) with `pycdlib`; after any change recompute each
  sector's EDC/ECC.
- Internal archives: pointer tables plus compression (PackBits-like RLE,
  Okumura LZSS with a 4 KB window starting at 0xFEE); keep headers and pad to
  the original length; stop the build if compression overflows.
- Text: 16-bit glyph indices (Harvest Moon) or SJIS-like bytes with a script
  command machine (Wild Arms 2: 06/07 text, 09 jump, 01 call). Many strings
  are reached by 32-bit pointers, not text commands: scan the loaded region
  for pointers to uncovered text. Run a conflict check (same text, two
  translations) before every build.

## Arabic and fonts

- The font is a VRAM sheet (Harvest Moon 128×120, 4-bit, 8×12 cells): Arabic
  goes into unused ranges plus reclaimed empty cells; joins are drawn into
  the glyphs at the baseline row (`scripts/font_bank.py` plans the slots).
- Byte limits: common letters one byte, some (آ ؤ) two: prefer forms that fit.
- Right-aligned lines cost padding to full width; a code before the text stays
  first and one after it moves last; write numbers without inner spaces.
- Drawing from the right needs an R3000 patch of the draw routine (runtime
  code rules): found with a read watchpoint on translated text in memory.

## Workflow

1. Dump and hash the user's image; extract with `pycdlib`.
2. Font bank, text with byte limits, images inside original sizes.
3. Rebuild the image with EDC/ECC; test in `duckstation`; ship an xdelta or
   byte-range patch checked against the original hash.

## Tools

Catalog tools: `duckstation`, `pycdlib`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine ps1`. Install rules: step 4 of
`game-localization-engineering`. Patches: `xdelta3`.

## Logs

DuckStation log (enable file logging in its settings) next to its settings
folder; `loc.py probe` reads new log files. Save states carry old VRAM (old
font): test from a fresh boot after a font change.

## Limitations

Close the emulator before building (files stay locked). A return to the title
screen may be the attract demo, not a crash: compare with the original.

## Sources

- https://github.com/Xxdm234/Arabic-Game-Localization-Playbook — `engines/PS1.md` (commit 2475fb6, read 2026-10-28).
- https://github.com/stenzek/duckstation (CC BY-NC-ND 4.0: use as an external program only), https://github.com/clalancette/pycdlib (LGPL-2.1).
