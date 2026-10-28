# SCUMM: Special Editions, classic SCUMM, and ScummVM profile

Evidence state: `documented-external`; from the Monkey Island 1/2 Special
Edition, classic, and The Curse of Monkey Island projects in the Arabic Game
Localization Playbook (MXIAUDIO and contributors, CC BY 4.0), adapted.

## Identification

- Special Editions: a `.pak` with signature `KAPL`, `audio/speech.info`,
  `localization/uiText.info` (MI1 SE `MISE.exe`, MI2 SE `Monkey2.exe`).
- Classic SCUMM V5: `monkey1.000`/`.001` (XOR 0x69).
- SCUMM V8 through ScummVM: `COMI.LA0`/`LA1`/`LA2`,
  `RESOURCE/LANGUAGE.TAB`, fonts `FONT0..4.NUT`, SMUSH videos.
- `python scripts/detect_engine.py <game_root>` reports `scumm-scummvm`.

## Localization locations

- **SE:** loose files are read before the archive (fonts, `speech.info`,
  `uiText.info`, `art/`): no repack. Arabic goes in the **French** slot and
  English stays intact; an empty INFO record needs a pointer to a NUL, never
  0. MI2 SE text: append Arabic at the end and repoint only the French
  pointers. `Monkey2.exe` reads the Steam language; forcing French needs a
  hash-checked byte patch (runtime code rules apply).
- **Classic:** `scummtr` extracts and reinserts text and recomputes sizes and
  jumps (`-g monkey2` for MI2); its companion ScummRP replaces CHAR resources.
  Keep classic and SE copies separate: edited SCUMM text breaks SE voice
  matching.
- **V8 / ScummVM:** `scummtr` does not support V8; read the ScummVM source at
  the tag matching the shipped build. ScummVM ignores `LANGUAGE.TAB` when
  English is selected, so use `language=fr`. Limits: 384 bytes per string,
  512 in SMUSH.

## Arabic and fonts

- Single-byte banks: build an Arabic bank that keeps every byte English
  uses (… — ™ é ê), reserves a few unused ASCII codes for lam-alef forms,
  and never uses 0xFE/0xFF (command prefixes): `scripts/font_bank.py`.
- The engine wraps visual text from its start, so build-time wrapping with
  the engine's own break per path: actor speech `FF01` (370 px in MI3),
  dialogue choices LF (560), SMUSH a space then LF (470); SE dialogue by
  measured width (1500 px of the dialogue font in MI1).
- Verb-and-object lines are assembled left to right; fixing the order needs a
  script or executable change (`references/rendering-lessons.md`).
- NUT fonts: 256 frames, codecs 21/44; connect joins to the cell edge.

## Workflow

1. Identify the edition; back up; choose loose files (SE), `scummtr` (classic),
   or archive copies with byte-equal patches (V8).
2. Font bank, measured wrapping with the engine's break codes, then text.
3. Test in an isolated ScummVM config (`--boot-param=<room>`, Alt-S captures);
   a hidden black window is not evidence.

## Tools

Catalog tools: `scummtr`, `scummvm`, `misetranslator`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine scumm-scummvm`. Install rules: step 4 of
`game-localization-engineering`.

## Logs

ScummVM writes `%APPDATA%/ScummVM/Logs/scummvm.log` on Windows:
`python scripts/boot_verdict.py --log <file>`; `loc.py probe` finds it.

## Limitations

`scummtr` and ScummRP may need to run outside the Windows sandbox. Old saves
keep old sentence templates. Fonts used by the Playbook for 8–14 px banks may
not be licensed for public distribution; check before release.

## Sources

- https://github.com/Xxdm234/Arabic-Game-Localization-Playbook — `engines/SCUMM_SCUMMVM.md` (commit 2475fb6, read 2026-10-28).
- https://github.com/dwatteau/scummtr (MIT), https://github.com/scummvm/scummvm (GPL-3.0), https://github.com/ShadowNate/MISETranslator (no license file: reference only).
