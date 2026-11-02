# Unreal Engine profile

Evidence state: `documented-external` starting points; verify against the exact
engine/game/platform version.

## Identification

- `Content/Paks/*.pak` and `Binaries/Win64/*-Win64-Shipping.exe` are common.
- `.utoc` plus `.ucas` indicates IoStore.
- `.locres`, `.locmeta`, localization manifests/archives, and string tables are
  stronger localization evidence than archive names alone.

## Portable resource paths

| Resource | Starting pattern | Evidence and limit |
| --- | --- | --- |
| Packaged assets | `<game_root>/Content/Paks/*.pak` or `*.utoc` + `*.ucas` | Common cooked-build container location; inspect its internal mount paths. |
| Native localization | Inside the project or container: `Content/Localization/<target>/<locale>/*.locres` | Documented Unreal localization layout; target and locale vary by game/build. |
| UI images/fonts | Inside cooked assets, often `.uasset`/`.uexp`; no universal subdirectory | Candidate only: search asset names/types and verify in the exact build. |

Record the game's actual container path and internal texture/string/font paths
with its engine version when found; never equate this table with proof for a
different title.

## Preferred localization route

With project sources, use Unreal Localization Targets, PO export/import, and the
engine compile pipeline. Epic documents that runtime translations are compiled
into `.locres`; manifests and archives are pipeline inputs and should not be
blindly hand-edited.

A cooked game without a documented mod route is out of scope. Never extract AES
keys, bypass signatures, or redistribute binaries obtained from a game installation.

## Tools

Use Epic's localization tools with project sources. Packed game archives are
out of scope (`references/extraction-integration.md`).

## Arabic

Slate/UMG commonly supports complex text shaping, but the exact game font,
widget, shaping method, and build must be tested. Begin with logical Unicode and
an Arabic-capable font. Do not pre-shape or visually reverse without in-game
evidence that the target renderer lacks shaping/BiDi.

## Acceptance

1. Exact engine/container/LocRes version recorded.
2. No-change round trip succeeds and archive entry paths remain identical.
3. Patch priority and uninstall behavior are verified on a copy.
4. Arabic test covers joining, mixed text, digits, punctuation, and clipping.
5. Anti-cheat, signatures, encryption, and online-service risks are resolved
   without bypassing controls.

## Workflow

Use gather/export/import/compile with PO when project sources exist.

## Limitations

IoStore, LocRes versions, encryption, signatures, anti-cheat, and online
constraints vary by title and may make a patch unsafe or impossible.

## Sources

See Epic's localization documentation; record exact versions in the project profile.

Sources: [Epic localization overview](https://dev.epicgames.com/documentation/unreal-engine/localization-overview-for-unreal-engine),
[Epic localization tools](https://dev.epicgames.com/documentation/unreal-engine/localization-tools-in-unreal-engine).
