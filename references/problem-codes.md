# Problem codes

Computed from each unit every time (never stored, so never stale). `validate`
prints the counts, the dashboard shows them, and `search --problem <code>`
lists the units. Error-level codes block the localization gate; warnings go to
the proofreader. A project may change any level in `PROJECT.yaml` →
`qa.levels` (for example `{latin_leak: error}`). Code spans (`{...}`, `[...]`,
tags, placeholders) are ignored by the typography checks.

| Code | Level | Meaning |
| --- | --- | --- |
| `missing_target` | error | translated or later, but the target is empty |
| `token_mismatch` | error | placeholders, tags, or escapes differ from the source |
| `source_changed` | error | the source changed after the unit was recorded |
| `proofread_stale` | error | the target changed after proofreading |
| `untranslated` | warning | the target is identical to the source |
| `lost_newline` | warning | line-break count differs from the source |
| `latin_leak` | warning | Latin words left in the Arabic (not code, not `keep_latin`) |
| `too_long` | warning | over `max_length`, or more than 3x the source |
| `glossary_term_missing` | error | an approved glossary term is not used (or `terms --allow`) |
| `forbidden_term` | error | a form listed under `forbidden:` in `glossary.yaml` (or `terms --allow`) |
| `unicode_form` | warning | presentation forms, tatweel, BiDi overrides, non-NFC |
| `persian_letters` | warning | Persian ی or ک instead of Arabic ي or ك |
| `digit_style` | warning | digits do not follow `PROJECT.yaml` → `game.digits` (`western` or `arabic-indic`) |
| `number_mismatch` | warning | a number of 11 or more, or with decimals, differs from the source (0–10 may be words) |
| `end_punctuation` | warning | the ending differs: question ?/؟, exclamation, period, ellipsis …, colon, or none |
| `latin_punctuation` | warning | Latin `? , ;` beside Arabic letters instead of `؟ ، ؛` |
| `whitespace` | warning | leading/trailing spaces differ, double spaces, or a space before punctuation |
| `doubled_word` | warning | the same word twice in a row where the source repeats nothing |
| `invisible_chars` | warning | zero-width, soft-hyphen, or control characters |
| `reversed_text` | warning | Arabic stored reversed (two or more words start with ة or ى): visual text pasted into a unit; restore the logical text |
| `needs_rewrite` | warning | a game update changed the source; rewrite from `previous_target` |

