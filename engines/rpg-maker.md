# RPG Maker MV / MZ
Evidence state: `candidate`; confirm in the pilot. RPG Maker XP, VX, and VX Ace, and
encrypted archives, are out of scope (`references/extraction-integration.md`).

## Identification
Inspect executable names, data files, and scripts; never infer solely from a folder name.
## Tools
No catalog tool is needed: `data/*.json` and `js/plugins.js` are plain JSON and
JavaScript. Details: `python scripts/tool_doctor.py --engine rpg-maker`.

- MV and MZ draw Arabic differently: MZ (`js/rmmz_core.js`) has right-to-left message
  text and the browser shapes Arabic, so write logical text and fix only the
  menu/list alignment; MV (`www/js/rpg_core.js`) draws message text one character at
  a time, so letters never join without a language plugin. A plugin made for MZ does
  not work on MV.
## Workflow
Extract a tiny sample; preserve control codes and line breaks; test fonts, save files and event branching.

### Lessons (Arabic Game Localization Playbook, CC BY 4.0, adapted)

- Control bytes `\x00`–`\x1F` are never part of a reversed run.
- MV/MZ: canvas shapes Arabic only when a whole string is drawn; keep `\C[n]`,
  `\N[n]`, `\V[n]`, `\I[n]`.
## Limitations
Check the game's license before using a language plugin. Stop if the data is encrypted.
## Sources
No tool/version/source is verified by this starter profile. Record the engine's
official documentation and the game version in the project record.
