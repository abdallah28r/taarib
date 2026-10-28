# Proprietary PC engines (console ports) profile

Evidence state: `documented-external`; from the Chrono Trigger PC and Chrono
Cross: The Radical Dreamers Edition projects in the Arabic Game Localization
Playbook (MXIAUDIO and contributors, CC BY 4.0), adapted. Each such engine is
unique: treat this as a method, not a format reference.

## Identification

- A custom archive (Chrono Trigger `resources.bin` "ARC1"), ZIP archives with
  `.dat` names (Chrono Cross `data/*.dat`), D3D11 with DirectXTK fonts
  (`DXTKfont` signature), CSV/TXT language tables inside.
- `detect_engine.py` cannot name these engines (their files look generic):
  identify by magic bytes (`ARC1`, `DXTKfont`) and `strings` on the executable.

## Localization locations

- Read the format by experiment and disassembly; write by keeping the
  original data in place and appending replacements and a new index at the end
  (update total-size fields, or the game crashes). Archives scrambled with XOR
  or Blowfish: "Protected archives and runtime code" in
  `references/extraction-integration.md` applies.
- Some executables load `_pad` copies of text files: write both.
- Tables may contain TAB inside text: split with a limit (`split('\t', 2)`).

## Arabic and fonts

Two proven routes when the renderer cannot do right to left:

1. **Font trick (no code):** every glyph gets a twin in the Private Use Area
   with negative kerning between twins so the pen moves backwards; padding
   glyphs right-align lines; zero-width "anchor" glyphs place values after
   labels. Text is stored in reading order with Latin and digits pre-reversed.
   Remap digits 0–9 to Arabic-Indic glyphs only if the project chose them.
2. **Proxy DLL (runtime code):** hooks at the end of text layout call ICU
   `ubidi_setPara`/`ubidi_getVisualMap` per line to reorder X positions only,
   with the measuring hook returning the true advance. Check the host
   executable name and signature-check hook sites (ASLR).

DirectXTK SpriteFont: the default character 0 aborts the game on any missing
letter: set `?`. Every font that may receive Arabic needs the glyphs.

## Workflow

1. Map formats; build a matching preview renderer (`loc.py probe --preview`)
   because such games may ignore synthetic input.
2. Choose the font trick or the DLL; build; ship an archive patch and an
   installer that checks hashes and keeps the original.

## Tools

Catalog tools: `directxtk`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine proprietary-pc`. Install rules: step 4 of
`game-localization-engineering`. Disassembly and hooking tools are chosen per
game under the runtime-code rules.

## Logs

Crashes: Windows Application log event 1000 first (`0xc0000409` is `abort()`
from a C++ exception), then a handler that logs the exception text such as
"Character not in font". `loc.py probe` reads new log files after a launch.

## Limitations

Hook addresses belong to one build. Save files may be encrypted per member;
keep all members and a backup (`scripts/save_guard.py`).

## Sources

- https://github.com/Xxdm234/Arabic-Game-Localization-Playbook — `engines/PROPRIETARY_PC.md` (commit 2475fb6, read 2026-10-28).
- https://github.com/microsoft/DirectXTK (MIT).
