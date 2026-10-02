# Mount & Blade II: Bannerlord profile

Evidence state: `candidate`; confirm with the current TaleWorlds modding and
localization documentation before use.

## Identification

Typical evidence includes `Modules/*/SubModule.xml`, language data beneath
`ModuleData/Languages/`, and `std_*.xml` localization files. Validate XML and
module dependencies; do not modify the base game's only copies.

## Safe route

Prefer an independent module/language package with its own manifest and removal
steps. Preserve string IDs and XML structure. Keep base-game, official-module,
and third-party-mod translations separate so removing one never touches another.

## Arabic and fonts

Renderer behavior and font formats are version-sensitive. Test logical Unicode
first. If the game requires a bitmap font or preprocessed visual text, keep the
logical Arabic as canonical and generate renderer-specific output during build.
Do not reuse another application's generated atlas or font package; generate it
from a properly licensed font and this project's corpus.

## Acceptance

1. Module loads and removes without altering base archives.
2. XML/string IDs round-trip and parse successfully.
3. Arabic joining/order and bitmap font coverage pass in-game.
4. Official content and separately installed mods remain isolated.

## Tools

Use XML-aware editors and a reversible module build; confirm the exact game
version before adopting community tools.

## Sources

Record current TaleWorlds documentation and tested module references in the
project profile.
