# Tool catalog and selection notes

Verify the current release and compatibility from the linked upstream project before use. Download from upstream sources, record the version and checksum, and test on copies.

The machine-readable inventory is `tools/open-source-tools.json`. Use `scripts/tool_doctor.py` to check availability by profile; this page explains selection boundaries rather than duplicating every install command.

## Engine-native first

- [Unreal localization](https://dev.epicgames.com/documentation/en-us/unreal-engine/localizing-content-in-unreal-engine): best when the project source is available; supports gathering, PO exchange, culture data, and LocRes generation.
- [Unity Localization package](https://docs.unity3d.com/Packages/com.unity.localization@latest): best when the Unity project is available; string/asset tables, Smart Strings, metadata, and locale preview.
- [Godot internationalization](https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html): best when the Godot project is available; PO/CSV resources and native BiDi/UI direction features.

## Unreal cooked-game inspection and round trips

- [FModel](https://github.com/4sval/FModel): inspect and export Unreal archives/assets; useful for discovery, not a universal writer.
- [repak](https://github.com/trumank/repak): list, extract, and build compatible Unreal `.pak` files. It does not replace an IoStore-specific workflow.
- [retoc](https://github.com/trumank/retoc): IoStore-oriented tooling for `.utoc/.ucas` workflows where compatible.
- [UAssetGUI/UAssetAPI](https://github.com/atenfyr/UAssetGUI): inspect and round-trip supported cooked assets; version and mappings matter.
- [UassetLocalize](https://github.com/rm-NoobInCoding/UassetLocalize): extracts/imports text from supported `.uasset`, `.umap`, and `.locres` files with CSV/PO exchange.
- [UnrealLocres](https://github.com/akintos/UnrealLocres): useful for older/supported LocRes variants; confirm the game's LocRes version before choosing it.

## Unity cooked-game inspection and round trips

- [AssetRipper](https://github.com/AssetRipper/AssetRipper): broad project reconstruction and analysis; useful for discovery and recovery, but not always the smallest patch route.
- [UABEA](https://github.com/nesrak1/UABEA): interactive inspection/editing of supported serialized files and bundles.
- [UnityPy](https://github.com/K0lb3/UnityPy): scriptable extraction and editing for supported Unity asset formats; pin a tested version for repeatable pipelines.
- [AssetStudio](https://github.com/Perfare/AssetStudio): inspection/export fallback; generally not the preferred writer.
- [RTLTMPro](https://github.com/pnarimani/RTLTMPro): runtime/project-side Arabic and RTL components for TextMesh Pro. It is relevant when source-level Unity integration is available.

## Godot

- Godot editor/import pipeline: preferred when project sources exist.
- [GodotPCKExplorer](https://github.com/DmitriySalnikov/GodotPCKExplorer): community packed-project inspection/repack option; verify compatibility and encryption status on a copy.

## Ren'Py and visual novels

- Prefer Ren'Py's native `tl/<language>/` translation workflow when project scripts are available.
- [unrpyc](https://github.com/CensoredUsername/unrpyc) and [rpatool](https://github.com/Shizmob/rpatool): inspect compiled scripts and RPA archives when needed; preserve labels, interpolation, and executable statements.
- [VNTranslationTools](https://github.com/arcusmaximus/VNTranslationTools): extraction/reinsertion for its supported VN engines with spreadsheet interchange.
- [Kuriimu2](https://github.com/FanTranslatorsInternational/Kuriimu2) and [GARbro](https://github.com/morkt/GARbro): plugin/archive exploration fallbacks. A format appearing in a tool is not proof of byte-safe write support.

## Engine/game-specific community tools

- [Danganronpa Another Tool (DRAT)](https://github.com/Liquid-S/Danganronpa-Another-Tool): extraction/repacking fallback for several Danganronpa releases. Prefer a proven project-specific byte-preserving pipeline when it already has stronger round-trip tests.

## Linguistic and format tooling

- [Weblate](https://docs.weblate.org/): open-source TMS with translation memory, glossary, review states, format-aware checks, and Git integration.
- Crowdin, Phrase, Lokalise, memoQ: alternatives when collaboration, screenshots, vendor workflows, or commercial CAT/TMS features justify them.
- [Poedit](https://poedit.net/): practical PO editor for smaller projects.
- [Translate Toolkit](https://toolkit.translatehouse.org/) and [Okapi Framework](https://okapiframework.org/): conversion and batch localization utilities when a supported format round trip is needed.
- Translate Toolkit `pofilter` can check variables, accelerators, and other common PO/XLIFF/TMX defects; Okapi filters are useful when a native document format needs a tested extract/merge pipeline.
- [fontTools/ttx](https://fonttools.readthedocs.io/): inspect OpenType/TrueType coverage and tables; it does not create a runtime fallback chain by itself.
- [HarfBuzz tools](https://harfbuzz.github.io/): shape test strings and inspect glyph selection; results must still be confirmed in the game's renderer.
- [Unicode Bidirectional Algorithm](https://www.unicode.org/reports/tr9/) and [CLDR plural rules](https://cldr.unicode.org/index/cldr-spec/plural-rules) are the normative references for mixed-direction text and locale plural behavior.
- `arabic-reshaper` and `python-bidi`: last-resort preprocessing for renderers without shaping/BiDi. Never use them before a native Unicode test demonstrates the need.

## Media, OCR, and release patches

- [ImageMagick](https://github.com/ImageMagick/ImageMagick) and [FFmpeg](https://ffmpeg.org/): reproducible image/audio/video/subtitle conversion and evidence capture.
- [Tesseract](https://github.com/tesseract-ocr/tesseract): OCR candidate generation for text baked into images; retain crops and manually verify every accepted string.
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp): offline speech transcription when no script exists; character names and timing remain review items.
- [Xdelta3](https://github.com/jmacd/xdelta) or [HDiffPatch](https://github.com/sisong/HDiffPatch): compact release deltas tied to an exact original checksum. Do not distribute original game data in the patch.

## AI model restriction

Local language models and machine translation are prohibited by `MODEL_AND_SUBAGENT_POLICY.md`; do not install or invoke Ollama, Argos Translate, LibreTranslate, llama.cpp, LocalAI, local Transformers models, or equivalent localhost endpoints. Local OCR/STT tools in this catalog require explicit current-task authorization. Deterministic parsers, validators, archive tools, hashers, and font tools remain normal project tooling.

## AI role

Use the model for contextual translation, terminology proposals, ambiguity detection, batch review, update merges, and generating deterministic project scripts. Do not let AI output bypass token checks, format validation, human review of representative content, or in-game LQA.
