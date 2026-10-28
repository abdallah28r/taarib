# MonoGame / XNA / FNA (.NET) profile

Evidence state: `documented-external`; from the Yuppie Psycho (and
Catechesis, Android) project in the Arabic Game Localization Playbook
(MXIAUDIO and contributors, CC BY 4.0), adapted. Stardew Valley has its own
profile (`engines/stardew-valley.md`).

## Identification

- A .NET `game.dll` (or `<Game>.exe`) with `*.deps.json` and
  `runtimeconfig.json`, `Content/*.xnb`, and `MonoGame.Framework.dll` or
  `FNA.dll`. XNB header: `XNB` + platform byte (`d` desktop, `a` Android).
- The game's own name does not tell the engine: decompile `game.dll` with
  `ilspycmd` and find the text manager, font manager, and renderer.
- `python scripts/detect_engine.py <game_root>` reports `monogame-xna`.

## Localization locations

- Text formats vary by game; read the parser in the decompiled code and follow
  it exactly (Yuppie: `content/string/*.properties`, UTF-8 without BOM, split
  at the first `=`, `\n` is the only line break, `GetText` strips every
  backslash so an LRM must be the raw character U+200E).
- Languages are often discovered from file suffixes and `CultureInfo`: adding
  `*_ar.properties` registered `ar` without a patch; confirm in the game log.
- A game's `mods/` folder may accept text and atlas PNGs but not code or fonts.
- Context is often free in the keys (speaker and area codes).

## Arabic and fonts

- Bitmap fonts in XNB: a missing character may draw as nothing (index 0 with
  zero size), not a box. Add the Arabic glyphs to the existing atlas so Latin
  stays byte-identical and mixed text needs no font switch; choose size by
  measuring the UI, not readability alone. With BMFont fonts the advance can be
  ink width + 1: set Arabic glyph width = bounds width − 1 so letters touch.
- Three independent layers: L1 logical Arabic text (mod), L2 font (append
  only), L3 direction at run time: a library loaded with
  `DOTNET_STARTUP_HOOKS` that patches the text renderer with `harmony` after
  formatting is parsed (wrap logical, reverse each line, reorder per-character
  colours the same way), every patch gated on the Arabic locale. Writing
  reversed text into the files breaks the engine's own wrapping and runtime
  values. A launcher sets the environment variable; Steam bypasses it, so a
  permanent call can be added to `game.dll` with `mono-cecil`. Both are runtime
  code: "Protected archives and runtime code" in
  `references/extraction-integration.md` applies.

## Workflow

1. Detect; decompile read-only; find text, font, and drawing code.
2. Text as a mod or language file; font by appending glyphs; direction layer.
3. Verify shaping against `arabic_shaping` and order against a BiDi reference
   (FriBidi or `python-bidi`), documenting intended differences.
4. Pilot with the launcher; then decide the permanent loader.

## Tools

Catalog tools: `ilspycmd`, `mono-cecil`, `harmony`, `python-lz4`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine monogame-xna`. Install rules: step 4 of
`game-localization-engineering`.

## Logs

The game's own log, if any, is usually next to the executable or under
`%APPDATA%`/`%LOCALAPPDATA%`; `loc.py probe` finds new log files after a
launch and records the path here.

## Limitations

For Android builds see `engines/android-apk.md` (no startup hooks; MVID, type
tokens, RVA data, and 16-byte alignment must be preserved).

## Sources

- https://github.com/Xxdm234/Arabic-Game-Localization-Playbook — `engines/MONOGAME_DOTNET.md` (commit 2475fb6, read 2026-10-28).
- https://github.com/icsharpcode/ILSpy (MIT), https://github.com/jbevain/cecil (MIT), https://github.com/pardeike/Harmony (MIT).
