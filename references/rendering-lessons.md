# Rendering lessons: symptom → cause → rule

Read this only when a symptom appears in the pilot, a playtest, or a
screenshot. Find the symptom, apply the rule, and confirm in the game.

Adapted from «دليل تعريب الألعاب الاحترافي» — MXIAUDIO and contributors —
https://github.com/Xxdm234/Arabic-Game-Localization-Playbook (commit 2475fb6),
licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Changes:
selected, shortened, translated to English, and tied to this template's tools.
The project names say where each lesson was learned.

## Text order and direction

| Symptom | Cause | Rule |
|---|---|---|
| The end of a sentence is on the first line | The engine wrapped text that was already reversed | Wrap the logical text by the box width, then shape and reverse each line (`adapter_options` width; `arabic_shaping.render`) |
| A line that starts with a Latin word reads left to right | Each wrapped line guessed its own direction | Every Arabic line is a right-to-left paragraph; never decide direction per line |
| `62:3`, `F-CTRL`, `1 CARD MEMORY` | Numbers and Latin words were protected piece by piece | A Latin or number run continues across inner `: - , . /` and spaces when Latin or a digit follows |
| `٥٢` instead of `٢٥`, `%50` instead of `50%` | Digits or a percent sign reversed with the Arabic | Arabic-Indic numbers stay whole; `%` and currency signs stay with a Western number |
| `Name@` | Bidi moved a prefix symbol | Write the symbol after the word, or keep it with the word in the build (LRM if the engine drops it) |
| `</b>…<b>`: style lost or tags shown | A tag pair reversed like plain text | Paired tags swap places when the line is reversed; never hand-edit tags in the build |
| A value injected into a sentence reads backwards | A reversed value went into a logical template, or the reverse | Decide each template's and each value's storage direction by the code that finally draws it |
| Verb and object swap ("poster look at") | The engine joins sentence pieces left to right | Fix it where the pieces are joined (script or engine), not in the text alone; test every combination |
| Two numbers swap (`1 4`) | A space split one number | Write numbers without inner spaces |
| A crash when picking up an item | A control byte was reversed with the text | Control bytes (`\x00`–`\x1F` except newline) and engine codes are atoms; never reverse them |
| The wrong branch runs or the camera jumps (RPG Maker) | Injected event commands lost their indent level | Injected commands keep the original indent |
| A chapter ending breaks | An internal name the code compares was translated | Values the code compares are not text (`extraction-integration.md`) |

## Letters, fonts, and layout

| Symptom | Cause | Rule |
|---|---|---|
| Letters do not join | The renderer does not shape (Unicode support is not shaping) | Test the word «سلام» in the pilot; if it splits, the adapter is `needs_preshape` |
| «لا» shows as two letters or a Latin-looking glyph | The font has no lam-alef glyph | Add the glyph, or `lam_alef: false` in `adapter_options` |
| Boxes where diacritics or tanween should be | The font lacks the marks | Add them, or `strip_harakat: true`; keep them in the units |
| «الآن» shows as «الأن» | The font lacks آ | Check coverage with `check_font.py` against `glyphs_used()` of the build |
| A pause code inside a word breaks the joining | The code was treated as a word break | Pass that code as `transparent` so letters join across it |
| Last words cut off | The line was measured before shaping, or with another font | Measure shaped text with the game's own font; leave a margin |
| A long line then a one-word last line | Greedy wrapping | Balanced wrapping (the default) |
| Right alignment fails or moves text off screen | Alignment changed for every window | Change alignment per window type; keep centred text centred |
| Text appears from the end while typing out | The engine reveals visual text left to right | Reveal from the right if the engine allows it; otherwise speed it up and record the limit |

## Method

| Lesson | Rule |
|---|---|
| "Fixed" is not "seen" | A fix counts only when seen in the game, on the same build hash |
| Blame the source first | Reproduce on the original language with the same save before blaming the localization |
| A rule that touches hundreds of places | Check its biggest consumer first |
| Old screenshots prove nothing about a new build | Re-check after every rebuild |
| A text counts as Arabic only by its letters | `؟` or digits alone do not make a line translated |
