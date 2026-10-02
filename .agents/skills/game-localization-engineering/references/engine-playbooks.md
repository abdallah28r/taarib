# Engine playbooks

Read only the section matching evidence from the game.

## Unreal Engine

Markers include `Engine/`, `Content/Paks/`, `.pak`, `.utoc`, `.ucas`, `.uasset`, `.uexp`, `.locres`, `.locmeta`, and `Content/Localization`.

- Prefer existing `.locres`/PO/string-table workflows. Preserve namespace, key, and source identity.
- Use an override or patch pak when supported; do not repack the full base archive without a demonstrated need.
- Match the game's actual archive generation, compression, mount point, engine version, and IoStore usage. `.pak` tools do not automatically support `.utoc/.ucas`.
- Asset text can also live in data tables, string tables, `FText`/`FString` properties, widgets, or cooked Blueprint assets. A `.locres` scan alone may be incomplete.
- Validate mixed Arabic/Latin/numbers in the actual Slate/UMG renderer and font stack.

## Unity

Markers include `UnityPlayer.dll`, `<Game>_Data`, `globalgamemanagers`, `resources.assets`, `sharedassets*.assets`, `StreamingAssets`, bundles, Addressables catalogs, and TextMesh Pro assets.

- Prefer loose JSON/CSV/XML or the Unity Localization package data when present.
- For serialized assets, retain path IDs, type trees, references, bundle compression, and the exact Unity version. Prove a no-change round trip before editing.
- Text may live in `TextAsset`, `MonoBehaviour`, ScriptableObject, custom databases, Addressables, or remote bundles. Do not assume every `TextAsset` is player-visible.
- Inspect TextMesh Pro font assets, fallback chains, atlas population mode, materials, and all used weights. Adding glyphs to a font file alone does not update a baked TMP atlas.
- RTLTMPro or another runtime solution requires source/project integration; it is not automatically usable for a closed compiled game.

## Godot

Markers include `project.godot`, `.pck`, `.tscn`, `.tres`, `.translation`, `.po`, and `.csv` imports.

- Prefer PO/CSV/translation resources and the engine TranslationServer path.
- Godot 4 provides native BiDi shaping and UI layout-direction controls when the export includes the required text-server data. Verify the specific build rather than pre-shaping by default.
- Packed-project modification requires a compatible pack workflow. Preserve import metadata and resource paths.

## Other or custom engines

- Search for loose locale directories and structured files before binary assets.
- Identify the parser and lookup key from evidence such as neighboring locales, schemas, or code references.
- Preserve BOM/encoding, newline style, escape rules, comments if significant, and ordering if the loader is order-sensitive.
- Treat Ren'Py, RPG Maker, GameMaker, visual-novel engines, and proprietary engines as separate formats. Do not force a Unity/Unreal workflow onto them.

