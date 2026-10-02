# Unity engine profile

Evidence state: `documented-external` starting points; nothing is
`verified-project` until reproduced on the exact game build.

## Identification

- `<Game>_Data/` with `UnityPlayer.dll` strongly suggests Unity.
- `Managed/Assembly-CSharp.dll` suggests Mono.
- `GameAssembly.dll` together with
  `il2cpp_data/Metadata/global-metadata.dat` suggests IL2CPP.
- `StreamingAssets/aa/catalog.json` or `catalog.bin` suggests Addressables.

Run `python scripts/detect_engine.py <game_root>` and confirm important files by
magic/format before selecting a writer. A filename match alone is not proof.

## Localization locations

Prefer an existing Unity Localization string/asset table or a game-specific
language file. Other candidates include I2 Localization resources, JSON/CSV,
TextAssets, Addressables bundles, and serialized MonoBehaviours. Embedded code
strings are a last resort and require a separate architecture decision.

## Portable resource paths

| Resource | Starting pattern | Evidence and limit |
| --- | --- | --- |
| Packed assets | `<game_root>/<Game>_Data/*.assets`, `resources.assets`, bundles, or `StreamingAssets/**` | Candidate patterns; exact Unity version and content pipeline matter. |
| Addressables | `<game_root>/<Game>_Data/StreamingAssets/aa/catalog.json` or `catalog.bin` | Marker only; follow the catalog to actual bundles. |
| Localized strings/assets | Unity Localization String/Asset Tables or game-specific files inside assets/bundles | No universal installed-game directory; inspect serialized types and locale references. |
| Images/fonts/audio | Textures, TMP font assets, and audio may be embedded in assets/bundles | Record verified internal asset path/type for the exact game, not a guessed folder. |

## Tools

- UnityPy and UABEA: supported asset/bundle inspection and edits.
- AssetsTools.NET: MIT read/write library; pin and test the exact Unity version.
- AssetRipper/AssetStudio: discovery and reconstruction, not automatically a
  byte-safe final writer.
- Cpp2IL: lawful IL2CPP metadata inspection candidate; stop on protected or
  encrypted metadata.
- BepInEx, UnityDoorstop, and XUnity.AutoTranslator: optional runtime tools only
  after protection checks and explicit per-game approval.

Use tools from their upstream repositories, never from another commercial
application's cached copy. Consult `LEGAL_AND_CLEAN_ROOM_POLICY.md`.

## Arabic and fonts

Do not assume TextMesh Pro or legacy `UI.Text` shapes and orders Arabic in the
exact game. Test native logical Unicode first. If it fails, compare a source-side
solution such as RTLTMPro, a runtime adapter, and build-time visual text. Keep
logical Arabic in translation memory; transform only at the renderer boundary.

For TMP, inspect font assets and fallback chains. Build atlases from the actual
Arabic corpus where possible and verify mixed Arabic/Latin/digits/placeholders.

## Acceptance

1. No-change extract/rebuild round trip on copies.
2. Existing loaders and their versions recorded before installation.
3. Protection scan has no stop marker, or the user has explicitly chosen a safe
   non-bypass route.
4. Minimal Arabic test proves shaping, ordering, fallback font, and line breaks.
5. Patch/removal manifest restores every added or changed file.

## Workflow

Detect the exact Unity build, perform a no-change extract/rebuild, test one
Arabic table, then create a removable locale or patch package.

## Limitations

Serialized assets, Addressables, IL2CPP, and runtime hooks vary by version;
never treat a filename match as proof of a writable route.

## Sources

See the official Unity Localization documentation and the pinned repositories
listed above; record exact versions in the project profile.

Sources: [Unity Localization package](https://docs.unity3d.com/Packages/com.unity.localization@latest),
[UnityPy](https://github.com/K0lb3/UnityPy),
[AssetsTools.NET](https://github.com/nesrak1/AssetsTools.NET),
[XUnity.AutoTranslator](https://github.com/bbepis/XUnity.AutoTranslator).
