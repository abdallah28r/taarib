# Stardew Valley (XNA / MonoGame) profile

Evidence state: `documented-external`; the custom-language system is
documented by the official wiki, Arabic rendering is untested here.

## Identification

- `Stardew Valley.dll` (1.6, .NET) or `Stardew Valley.exe`, with `Content/`
  holding `.xnb` assets (`Content/Strings`, `Content/Data`, `Content/Fonts`).
- `StardewModdingAPI.exe` means SMAPI is installed.
- `python scripts/detect_engine.py <game_root>` reports `stardew-valley`.

## Localization locations

Stardew Valley 1.5.5+ supports custom languages through
`Data/AdditionalLanguages`, added by a Content Patcher content pack:

- Entry fields: `ID`, `LanguageCode` (letters and hyphens, e.g. `ar`),
  `ButtonTexture` (174×78 image, top half normal, bottom hover), `TimeFormat`,
  `ClockTimeFormat`, `ClockDateFormat`; optional `NumberComma`,
  `SmallFontLineSpacing`, `FontApplyYOffset`, `UseGenderedCharacterTranslations`.
- Custom font: `UseLatinFont: false`, `FontFile` (the asset name under
  `Fonts/`, not the pack's file path), `FontPixelZoom` (start at 1.5).
- Text: Content Patcher `EditData` patches on the string assets
  (`Strings/...`, `Data/...`) for the language code. Custom languages load at
  startup, so patches use no `When` conditions except immutable ones.

Extract the source text with `stardewxnbhack` (one-way unpack) and build the
content pack; never repack the game's `.xnb` files.

## Arabic and fonts

- Text is drawn from bitmap fonts (BMFont text `.fnt` with page images, white
  glyphs on transparent, `chnl=15`), which do not shape: the adapter is
  `needs_preshape`. Generate the font with `bmfont` from a licensed Arabic TTF,
  including the presentation forms the build uses (`arabic_shaping.glyphs_used`).
- The game wraps dialogue, tooltips, and letters by width itself: measure the
  boxes and wrap before reversing (`adapter_options` `boxes`, `line_unit: px`).
  Dialogue codes (`#`, `^`, `$`, `@`, `%`) are engine codes; pass them as
  `transparent` so they are kept whole.
- Number and time formats come from the language entry; keep Western digits
  unless the project chose Arabic-Indic.

## Workflow

1. Detect; unpack text with `stardewxnbhack` into `work/`.
2. Build a Content Patcher pack: the language entry, the font, and the text
   patches. Mods' own `i18n/<code>.json` files are separate and stay separate.
3. Pilot: title and language menu, the first day's dialogue, one tooltip.

## Tools

Catalog tools: `smapi`, `content-patcher`, `stardewxnbhack`, `bmfont`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine stardew-valley`. Install rules: step 4 of
`game-localization-engineering`. SMAPI and Content Patcher are installed by
the player as the game's mod loader; the pack lists them as dependencies.

## Logs

SMAPI writes `%APPDATA%/StardewValley/ErrorLogs/SMAPI-latest.txt`:
`python scripts/boot_verdict.py --engine stardew-valley`.

## Limitations

Right-to-left text, the typewriter dialogue effect, and gendered forms are
untested. Mods with their own text need their own `i18n` translation.

## Sources

- https://wiki.stardewvalley.net/Modding:Custom_languages — fields, font format, BMFont (read 2026-10-28).
- https://wiki.stardewvalley.net/Modding:Translations — translating existing assets and mod i18n.
- https://github.com/Pathoschild/SMAPI — LGPL-3.0.
- https://github.com/Pathoschild/StardewMods — Content Patcher, MIT.
- https://github.com/Pathoschild/StardewXnbHack — MIT.
