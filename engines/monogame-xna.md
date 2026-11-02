# MonoGame / XNA / FNA (.NET) profile

Evidence state: `documented-external`; adapted from the Arabic Game Localization
Playbook (MXIAUDIO and contributors, CC BY 4.0). Stardew Valley has its own profile
(`engines/stardew-valley.md`).

## Identification

- `*.deps.json`, `runtimeconfig.json`, `Content/*.xnb`, and `MonoGame.Framework.dll`
  or `FNA.dll`.
- `python scripts/detect_engine.py <game_root>` reports `monogame-xna`.

## Localization locations

- Look for plain language files or a documented `mods/` folder. Adding a language
  file may register a language without other changes; confirm in the game log.
- Context is often free in the keys (speaker and area codes).

## Arabic and fonts

Use this profile only when the game's documented files accept Arabic text and a font.
Direction or shaping that needs a code change is out of scope.

## Workflow

1. Detect; read the language files.
2. Write text as a language file or a documented mod.
3. Verify shaping against `arabic_shaping` and order against a BiDi reference.

## Tools

Catalog tools: `python-lz4`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine monogame-xna`. Install rules: step 4 of
`game-localization-engineering`.

## Logs

The game's own log, if any, is usually next to the executable or under
`%APPDATA%`/`%LOCALAPPDATA%`; `loc.py probe` finds new log files after a
launch and records the path here.

## Limitations

Many games in this family offer no documented route; they are out of scope.

## Sources

- https://github.com/Xxdm234/Arabic-Game-Localization-Playbook — `engines/MONOGAME_DOTNET.md` (commit 2475fb6, read 2026-10-28).
