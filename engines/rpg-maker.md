# RPG Maker / KiriKiri / NScripter
Evidence state: `candidate`; this groups distinct engines for initial
identification only, not a shared extraction or repacking procedure.

## Identification
Inspect executable names, archive extensions, scripts and runtime files; never infer solely from a folder name.
## Tools
Catalog tools: `vntranslationtools`, `garbro`, `hyouta-tools`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine rpg-maker`. Install rules: step 4 of
`game-localization-engineering`.

- RPG Maker MV/MZ: `data/*.json` and `js/plugins.js` are plain JSON and
  JavaScript; an adapter edits them directly, no tool needed.
- RPG Maker XP/VX/VX Ace: Ruby Marshal data (`.rxdata`, `.rvdata`,
  `.rvdata2`), often inside an encrypted archive; choose a tool only after
  license review, and never decrypt protected archives.
- KiriKiri, NScripter, and other visual-novel engines: VNTranslationTools
  (VNTextPatch) for supported engines' script extract/reinsert, GARbro to
  discover and read their archives.
## Workflow
Extract a tiny sample; preserve control codes and line breaks; test fonts, save files and event branching.
## Limitations
Engine version and encryption vary; tools may be community-maintained and require license review.
## Sources
No tool/version/source is verified by this starter profile. Capture each
engine's official documentation and each selected tool's repository URL,
release/commit, and license in the project record before using it.
