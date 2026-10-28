# RPG Maker / KiriKiri / NScripter
Evidence state: `candidate`; this groups distinct engines for initial
identification only, not a shared extraction or repacking procedure.

## Identification
Inspect executable names, archive extensions, scripts and runtime files; never infer solely from a folder name.
## Tools
Catalog tools: `vntranslationtools`, `garbro`, `hyouta-tools`, `rpgmakerdecrypter`, `rubymarshal`, `mkxp-z`, `translator-plus-plus`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine rpg-maker`. Install rules: step 4 of
`game-localization-engineering`.

- RPG Maker MV/MZ: `data/*.json` and `js/plugins.js` are plain JSON and
  JavaScript; an adapter edits them directly, no tool needed.
- MV and MZ draw Arabic differently (`candidate`, confirm in the pilot):
  MZ (`js/rmmz_core.js`) has right-to-left message text and the browser shapes
  Arabic, so write logical text and fix only the menu/list alignment; MV
  (`www/js/rpg_core.js`) draws message text one character at a time, so
  letters never join unless a plugin draws each Arabic run in one call (the
  typewriter effect then shows run by run). A plugin made for MZ does not work
  on MV. Injected event commands keep the original indent level, or the wrong
  branch runs.
- RPG Maker XP/VX/VX Ace: Ruby Marshal data (`.rxdata`, `.rvdata`,
  `.rvdata2`), often inside an encrypted archive (`Game.rgssad`, `.rgss2a`,
  `.rgss3a`). Prefer loose `Data/` files or a language plugin; decrypting the
  archive with `rpgmakerdecrypter` follows "Protected archives and runtime
  code" in `references/extraction-integration.md` (approval, external tool,
  nothing decrypted distributed). Ruby Marshal: read with `rubymarshal`, but
  write with real Ruby (`mkxp-z`'s or the game's), because Python writers
  break shared objects.
- KiriKiri, NScripter, and other visual-novel engines: VNTranslationTools
  (VNTextPatch) for supported engines' script extract/reinsert, GARbro to
  discover and read their archives.
## Workflow
Extract a tiny sample; preserve control codes and line breaks; test fonts, save files and event branching.

### Lessons from To the Moon, Impostor Factory, OMORI (Arabic Game Localization Playbook, CC BY 4.0, adapted)

- RPG Maker XP through mkxp: loose files do not override the archive except
  `Fonts/`, so every change rebuilds the archive (decryption rules above).
- Direction in XP: a Ruby script intercepts `Bitmap#draw_text` and
  `text_size` (measure after shaping) and `Window_Message#refresh`, which draws
  one character at a time. Protect codes with a pattern such as
  `(\[A-Za-z]+\[[^\]]*\]|\[A-Za-z]+|\.)`; guard against shaping twice by
  object identity, not content; expand injected names (`\n[n]`) before shaping
  when needed. Paragraph formatter scripts that draw letter by letter need
  their own interception; widen `text_size` by about 10% + 8 px when a script
  measures the whole line but draws per character.
- Ruby 1.8 (RGSS1): `$KCODE='u'`, no `force_encoding`.
- Injected event commands keep their original indent level; control bytes
  `\x00`–`\x1F` are never part of a reversed run (a game crashed on picking up
  an item).
- MV/MZ: canvas shapes Arabic only when a whole string is drawn; fonts through
  `gamefont.css` or a custom-font plugin; keep `\C[n]`, `\N[n]`, `\V[n]`,
  `\I[n]`. On Android the game runs in a WebView under `assets/www`
  (`engines/android-apk.md`).
- `translator-plus-plus` has RPG Maker parsers but no Arabic support of its
  own; use it to extract and reinsert, never to render.
## Limitations
Engine version and encryption vary; tools may be community-maintained and require license review.
## Sources
No tool/version/source is verified by this starter profile. Capture each
engine's official documentation and each selected tool's repository URL,
release/commit, and license in the project record before using it.
