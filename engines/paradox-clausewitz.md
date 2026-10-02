# Paradox Clausewitz/Jomini profile

Evidence state: `candidate`. Paradox titles differ substantially by generation;
confirm against the exact game's official modding documentation.

## Identification

Candidate markers include `launcher-settings.json`, localization YAML files with
language headers, `gui/*.gui`, font configuration, and a mod descriptor. Do not
infer a specific title/version from the localization folder alone.

## Safe route

Prefer a removable mod with its own descriptor, localization, GUI overrides,
fonts, and manifest. Do not overwrite base-game localization. Record whether a
new culture is supported or an existing locale must be overridden.

Common protected syntax can include scripted localization in brackets,
`$VARIABLE$`, `@icon!`, and styled text markers. The exact grammar is game-
specific; add fixtures from lawful project files and run `loc_qa.py` with the
appropriate profile before integration.

## Arabic

Arabic/RTL support is unverified by this profile. Test renderer shaping, ordering,
alignment, fonts, and mixed tokens. A mod can affect checksums, multiplayer
compatibility, achievements, or Ironman behavior; document the exact title's
rules rather than generalizing.

## Acceptance

1. Native parser accepts every localization and GUI file.
2. Protected syntax is unchanged.
3. Mod removal restores the base game without touching original files.
4. Checksum/multiplayer/achievement effects are documented for the title.

## Tools

Use a removable mod, a YAML-aware validator, and the title's launcher/mod tools;
do not overwrite base-game files.

## Sources

Record exact title/version documentation and tested mod structure.
