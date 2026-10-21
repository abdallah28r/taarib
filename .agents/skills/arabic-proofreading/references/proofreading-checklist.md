# Proofreading checklist

Check each unit in this order; meaning outranks polish. Severity follows
`game-localization-qa/references/lqa-severity.md` (player impact, not effort).

| Category | What to check | Typical severity |
| --- | --- | --- |
| `meaning` | Mistranslation, reversed sense, wrong referent, wrong gameplay instruction | major / critical |
| `omission` | Source meaning, condition, or emphasis missing; extra meaning added | major |
| `context` | Speaker, addressee gender/number, kinship, or scene contradicted | major |
| `terminology` | Approved `glossary.yaml` term not used, or one term rendered two ways | major |
| `grammar` | Agreement (gender, number, dual), case after `إنّ`/`كان`, verb–subject order, broken idafa | minor / major |
| `spelling` | Hamza position, `ة`/`ه`, `ى`/`ي`, `تنوين الفتح` on the letter before alif (`كتابًا`), typos | minor |
| `punctuation` | Arabic `، ؛ ؟`, `…`, no space before a mark, no full stop on buttons | minor |
| `style` | Calques (`تمّ فتح`، `قام بإغلاق`، `من قبل`), unnatural word order, padding | minor |
| `voice` | Register or character voice inconsistent with `glossary.yaml` → characters | minor / major |
| `length` | Target over `max_length` or clearly longer than the UI allows | minor / major |
| `numbers` | Digits, units, dates, or quantities changed | major |

Tokens, markup, NFC, tatweel, presentation forms, digits, numbers, endings,
Arabic punctuation, spacing, doubled words, glossary terms, and forbidden forms
are checked by `loc.py validate` (`references/problem-codes.md`); do not spend review time
re-checking them by eye. Read the flagged units first.

## Findings file

One JSON object per line in `work/proofreading/<batch>.jsonl`:

```json
{"id": "dlg/ch1#002", "severity": "minor", "category": "spelling", "issue": "همزة القطع في «أنتبه» خاطئة", "before": "أنتبه.", "after": "انتبه.", "resolution": "applied", "by": "proofreader-1"}
{"id": "dlg/ch1#014", "severity": "major", "category": "context", "issue": "جنس المخاطَب غير معروف من السياق", "resolution": "needs_decision", "by": "proofreader-1"}
```

- `id`: a unit id that exists in `units/`.
- `severity`: `blocker`, `critical`, `major`, or `minor`.
- `category`: one of the categories above.
- `resolution`: `applied` (fixed in the unit's `target`, with `before` and
  `after`), `needs_decision` (unit stays `translated`, `decision: review`), or
  `rejected` (finding withdrawn after checking context; give the reason in
  `issue`), or `resolved` (a later line that settles an earlier
  `needs_decision` for the same id after the user or root agent decided; give
  `after`).
- `by`: the proofreader's role label.

`python scripts/loc.py findings <file>` validates the file, checks that the
last `applied`/`resolved` change for each unit matches its current target,
rejects findings signed by the unit's translator, refuses any unit already
marked proofread while it still has an open `needs_decision` finding, and
prints counts by severity, category, and resolution.
