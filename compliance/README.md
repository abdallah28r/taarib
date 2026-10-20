# Compliance records

Keep legal and clean-room evidence here. Do not place secrets, proprietary
files, extracted game assets, copied prompts, or copied source code in this
directory.

`RESEARCH_SOURCE_REGISTER.json` is an internal provenance and handling register.
It is consumed by `scripts/maintainer/license_guard.py`; it is not a product feature,
marketing list, endorsement, or a reason to display application names in the UI.

For each independently implemented feature, add a row to
`CLEAN_ROOM_LEDGER.csv`. The specification must be source-neutral and the tests
must describe observable behavior rather than reproduce another program's
internal implementation.

Before a public or commercial release:

1. Remove the example ledger row.
2. Run `python scripts/maintainer/license_guard.py`.
3. Confirm every bundled third-party file has a notice and license text.
4. Confirm no proprietary research export or game asset is included.
5. Review fonts, models, data sets, icons, and documentation separately from
   program-code licenses.
