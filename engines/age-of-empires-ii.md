# Age of Empires II: Definitive Edition (and HD) profile

Evidence state: `candidate`; drawn from community modding threads and one
font tool, not yet tested on a game build by this template.

## Identification

- DE: `AoE2DE_s.exe`, `resources/_common/`, and
  `resources/<lang>/strings/key-value/key-value-strings-utf8.txt`.
- HD: `AoK HD.exe` with language files under `resources/` (`key-value` or
  `language.ini` style); confirm by reading the files.
- `python scripts/detect_engine.py <game_root>` reports `age-of-empires-ii`.

## Localization locations

| Resource | Path | Evidence |
| --- | --- | --- |
| Game text (DE) | `resources/<lang>/strings/key-value/key-value-strings-utf8.txt`: one `ID "text"` per line, UTF-8 | community |
| Mod/scenario text (DE) | `key-value-modded-strings-utf8.txt` in the same folder | community |
| In-game fonts (DE) | `resources/_common/fonts/` texture atlases (`.dds` pages with `.box`/`.txt`/`.png` metrics) | community |
| Main menu and loading fonts (DE) | `resources/_common/wpfg/fonts/` | community |

Arabic is not an official language. Ship the translation as a mod with the
same folder layout (a local or Mods folder copy of `key-value`), replacing the
English strings by ID, never the original file in place.

## Arabic and fonts

- The renderer is reported not to shape Arabic: start the adapter as
  `needs_preshape` and confirm with «سلام» in the pilot.
- The engine wraps text itself, so long reversed text wraps in the wrong line
  order: give the adapter box widths (`adapter_options` `boxes`) for the tech
  tree, event panel, and tooltips, measured on screenshots, and break lines
  before reversing.
- The in-game atlases lack Arabic presentation forms; a missing glyph shows
  as a question mark. Regenerate the atlases from a licensed Arabic font with
  the forms the build uses (`arabic_shaping.glyphs_used`).
- Several game modes share string IDs with different meanings; Return of Rome
  is reported to ignore modded text. Check each mode in the playtest.

## Workflow

1. Detect, back up, and read the key-value files; extract units by ID.
2. Translate; build the mod's key-value files with `needs_preshape` and widths.
3. Generate font atlases with `aoe2de-font-generator` (needs `directxtex`
   texconv for DDS) into the mod, not over `resources/_common/fonts`.
4. Pilot: lobby, tech tree, one scenario's opening text.

## Tools

Catalog tools: `aoe2de-font-generator`, `genie-rs`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine age-of-empires-ii`. Install rules: step 4 of
`game-localization-engineering`. DDS conversion uses `directxtex` (media profile).

The key-value format is plain text; an adapter needs no tool to read it.
`genie-rs` (GPL-3.0) is for reading other AoE file formats as an external
tool only; do not copy its code into the template.

## Logs

No known log path; check the game folder and Documents after a launch and pass
the file to `python scripts/boot_verdict.py --log <file>`.

## Limitations

Not tested here. Atlas generation changes how every language's text looks;
keep it inside the mod and test the main menu, which the generator does not
cover. Multiplayer compatibility of text mods is unverified.

## Sources

- https://forums.ageofempires.com/t/editing-key-strings-wont-work/91785 — key-value paths and modded strings (read 2026-10-28).
- https://forums.ageofempires.com/t/modding-fonts/65081 — font folders and the generator.
- https://github.com/sgjsakura/AOE2DE-FontGenerator — MIT; atlas generation, needs TexConv.
- https://forums.ageofempires.com/t/bug-text-localization-mods-txt-not-loading-in-return-of-rome-dlc-aoe2-de/287335 — Return of Rome limit.
