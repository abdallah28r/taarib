# PlayStation 2 (emulated) profile

Evidence state: `documented-external`; from Wild Arms 3/4/5 and Alter Code F
in the Arabic Game Localization Playbook (MXIAUDIO and contributors, CC BY
4.0), adapted. Only for an image the user dumped from a disc they own; never
download BIOS files or images. PS4 packages stay out of scope.

## Identification

- An ISO9660 image (sometimes dual layer) with `SYSTEM.CNF` and an ELF MIPS
  R5900 executable `SLUS_xxx.xx`.
- `python scripts/detect_engine.py <folder>` reports `ps2`.

## Localization locations

- Dual layer: the second layer repeats files at an offset; write every change
  to both and never move or resize a file (fixed sector reads). Otherwise
  append a grown file at the end and update its directory record (LBA and
  size, both byte orders).
- Text: SJIS with control codes below 0x20 of fixed lengths; event scripts are
  a command machine (07 text, 09/0a jump, 01 call, 00 return; 23/15 point to
  standalone strings). "Jump out": replace the first 5 bytes of a text command
  with a jump to an Arabic copy at the end of the file and jump back, so
  nothing else moves. Never split a message mid-page; restate the style code
  at the start of each line (the engine measures each line in the default
  style).
- Executable strings sit behind pointer tables (aligned to 4, pointing at a
  string start); watch for false pointers inside font data.
- printf messages `%1 %2`: the higher number reads first, with an Arabic word
  between two arguments.

## Arabic and fonts

- Arabic glyphs replace unused kana slots with their SJIS codes; width tables
  per style; wide letters split over two slots; the hardware drops an edge
  pixel column, so joins overlap by one pixel (`scripts/font_bank.py`).
- Right alignment and reveal-from-right need R5900 code caves in verified
  empty regions (runtime code rules); never use k0/k1, cover every exit.

## Workflow

1. Order per game: font, direction, all text, menus and images, then tests.
2. Test in a separate `pcsx2` install with PINE on its own port; test memory
   cards with `mymcplus`, never the user's card; close the emulator before
   building; executable changes need a fresh boot.
3. Ship a manifest (signature, sizes, SHA-256, ranges) and payload, checked
   against the Redump hash.

## Tools

Catalog tools: `pcsx2`, `mymcplus`, `pycdlib`, `capstone`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine ps2`. Install rules: step 4 of
`game-localization-engineering`. Patches: `xdelta3`.

## Logs

PCSX2 writes `emulog.txt` in its logs folder; count "R5900 Exception" lines
when bisecting a crash. `python scripts/boot_verdict.py --log <emulog.txt>`.

## Limitations

Save states carry the archive index and uploaded atlases: old states load old
text and images. Screenshots do not show typewriter motion or sound: ask the
user to watch.

## Sources

- https://github.com/Xxdm234/Arabic-Game-Localization-Playbook — `engines/PS2.md` (commit 2475fb6, read 2026-10-28).
- https://github.com/PCSX2/pcsx2 (GPL-3.0), https://github.com/thestr4ng3r/mymcplus (GPL-3.0, archived), https://github.com/clalancette/pycdlib (LGPL-2.1), https://github.com/capstone-engine/capstone (BSD-3-Clause).
