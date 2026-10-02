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

For a cooked game, first prove the exact container and LocRes versions. Prefer a
small, removable patch container over replacing the base archive. Never extract
AES keys, bypass signatures, or redistribute Oodle binaries obtained from a
game installation.

## Tools

- FModel: discovery/export.
- repak: compatible `.pak` list/extract/build workflows.
- retoc: compatible IoStore workflows.
- UAssetGUI/UAssetAPI: supported cooked asset inspection/editing.
- UnrealLocres/UassetLocalize: candidates; confirm LocRes and engine version.
- UE4SS: runtime research/override only after explicit approval and protection
  checks; never make it the default authored localization route.

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

Prefer gather/export/import/compile with PO when project sources exist. For a
cooked build, prove the container version and build a small removable patch.

## Limitations

IoStore, LocRes versions, encryption, signatures, anti-cheat, and online
constraints vary by title and may make a patch unsafe or impossible.

## Sources

See Epic's localization documentation and the pinned repositories listed above;
record exact versions in the project profile.

Sources: [Epic localization overview](https://dev.epicgames.com/documentation/unreal-engine/localization-overview-for-unreal-engine),
[Epic localization tools](https://dev.epicgames.com/documentation/unreal-engine/localization-tools-in-unreal-engine),
[repak](https://github.com/trumank/repak),
[UAssetGUI](https://github.com/atenfyr/UAssetGUI).
