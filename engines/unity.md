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

Catalog tools: `unitypy`, `uabea`, `assetripper`, `bepinex`, `xunity-autotranslator`, `unitydoorstop`, `assetstools-net`, `cpp2il`, `rtltmpro`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine unity`. Install rules: step 4 of
`game-localization-engineering`.

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

## Verified on one project (SIGNALIS, Unity 2020.3.36f1 IL2CPP, 2026-10)

Re-prove each point on any other game; never reuse its hashes, path IDs, or
measurements.

- IL2CPP was confirmed by `global-metadata.dat` starting with bytes
  `af1bb1fa`; the data archive `data.unity3d` started with `UnityFS`.
- An image or text asset's stable identity was `<archive member>:<path ID>`
  (for example `sharedassets14.assets:112`). Path IDs can change with a game
  update; re-map them after one.
- Legacy TextMesh Pro under IL2CPP needed an Arabic font and a separate display
  bridge. A glyph present in the font did not mean correct order or readable
  menus: test logical Unicode in the renderer first.
- After rebuilding a texture, decode it again and compare pixels, mode, size,
  format, and mip count with the approved candidate. That proves the data,
  not readability: 8 px labels on a 3D surface were rejected by the user, and
  some surfaces were too small on camera for any Arabic.
- The loader (BepInEx) and the display bridge were installed as files separate
  from `data.unity3d`, each with its own removal record.

Versions that project tried (state `candidate`: staged and tested in
isolation, not proven installed in the game):

| Tool | Version | Use there |
| --- | --- | --- |
| UnityPy | 1.25.4 | read and rebuild the UnityFS archive in an isolated copy |
| BepInEx Unity IL2CPP | 6.0.0-be.704 | removable loader |
| XUnity.AutoTranslator (BepInEx IL2CPP) | 5.6.2 | only to register a TMP fallback font; its translation services disabled |
| RTLTMPro | commit ba92e02 | shaping subset compiled into an isolated display bridge |
| fontTools | 4.60.1 | font coverage checks, variable-font instancing |

## Lessons from ENA: Dream BBQ (Arabic Game Localization Playbook, CC BY 4.0, adapted)

- Yarn Spinner dialogue: `Yarn.Unity.Localization` checks its runtime string
  table first, so `AddLocalizedString` fills it without touching the dialogue
  bundle; strings stored in Yarn variables need separate extraction.
- UI text through one Harmony postfix on `TMP_Text.ParseInputText` (every
  path that sets text passes there), looked up in layers: exact, case-
  insensitive (games call `ToUpper()`), patterns for composed strings, title
  plus rest, then line by line; a dump mode logs every English string that
  passed untranslated.
- TextMeshPro: store `reverse(bidi(shape(logical)))` with
  `isRightToLeftText = true`; TMP draws the buffer reversed, so words stay in
  reading order for wrapping and the typewriter. Set the flag in both
  directions (components are reused) and restore the original state when a
  component's text is not Arabic again.
- Fonts at run time: `TMP_FontAsset.CreateFontAsset(ttf)` registered as a
  fallback for every game font, with the game font's scale, ascent, descent,
  and line height copied in proportion; one font asset per TTF.
  `getFontFeatures = false` for pre-shaped text.
- Per-component layout: Left/Justified become Right (read the live value),
  autosize capped at the original size, line spacing compensated from the
  Arabic font's measured ink.
- BepInEx 5: the plugin object may get only `Awake`; create a dedicated
  `GameObject` with `DontDestroyOnLoad` for `Update` and coroutines.
- Achievements (from Steam) and dialogue history stored in old saves stay
  English.

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
