# RimWorld profile

Evidence state: `candidate`; the language folder layout is documented by the
community wiki, Arabic rendering is untested here and no Arabic mod was found.

## Identification

- `RimWorldWin64.exe` with `RimWorldWin64_Data/` (Unity, Mono) and
  `Data/Core/Languages/`; DLCs under `Data/<DLC>/`.
- `python scripts/detect_engine.py <game_root>` reports `rimworld` (it also
  matches Unity markers; the RimWorld profile wins).

## Localization locations

A language is a folder `Languages/<Name>/` inside a mod (or per DLC):

- `Keyed/*.xml`: UI strings, root `LanguageData`, element name is the key.
- `DefInjected/<DefType>/*.xml`: content text, keys `DefName.field`
  (e.g. `Beer.label`); the subfolder must match the Def type.
- `Strings/`: word lists for name and sentence generation.
- Files are UTF-8. Copy the folder structure and any language info file from
  an official language in `Data/Core/Languages/` rather than inventing it.

Keys from all content and mods share one table: keep the base game, each DLC,
and each third-party mod in separate folders. Dev Mode shows missing keys as
glitched text.

## Arabic and fonts

- The UI is Unity's immediate-mode GUI with the game's own fonts; it is not
  expected to shape or order Arabic. Two routes, decide in discovery:
  1. `needs_preshape`: write shaped, visually ordered text into the XML. The
     game wraps text by width itself, so wrap first with measured box widths;
     text whose width changes with the window stays at risk.
  2. A runtime mod (C# with `harmony`) that shapes and orders text when it is
     drawn, keeping logical Arabic in the XML. Needs explicit per-game approval
     (references/extraction-integration.md) and testing with other mods.
- Grammar tokens (`{0}`, `[PAWN_nameDef]`, `{PAWN_pronoun}`) are code: keep
  them whole and test sentences built from them.

## Workflow

1. Detect; read English `Keyed` and `DefInjected` from `Data/Core/Languages`
   and the DLC folders into units.
2. Translate; build a separate language mod with the chosen route.
3. Pilot: main menu, options, one colonist's info card, one event letter.

## Tools

Catalog tools: `harmony`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine rimworld`. Install rules: step 4 of
`game-localization-engineering`. The XML needs no tool; Unity tools apply only
to the game's fonts (`engines/unity.md`).

## Logs

Unity log: `%USERPROFILE%/AppData/LocalLow/Ludeon Studios/RimWorld by Ludeon Studios/Player.log`:
`python scripts/boot_verdict.py --engine rimworld`.

## Limitations

Untested. Mods that add text need their own translation folders; load order
decides which translation wins on a shared key.

## Sources

- https://rimworldwiki.com/wiki/Modding_Tutorials/Translation — Keyed, DefInjected, Strings (read 2026-10-28).
- https://github.com/pardeike/Harmony — MIT; runtime patching library.
