# Improvement proposals

Record reusable tools, skills, scripts, automation ideas, or workflow lessons
discovered during a project. Include problem, proposed solution, security and
license review, maintenance cost, evidence, and recommendation. Proposals do
not authorize installation or external AI use.

## 2026-09-26 application-research intake

- `promote` — Clean-room and licensing gate. Added
  `LEGAL_AND_CLEAN_ROOM_POLICY.md`, an application source catalog, a clean-room
  ledger, and `scripts/license_guard.py`. Evidence: the intended project may be
  open-source and commercial, while research includes permissive, copyleft,
  proprietary, no-license, and expired-permission sources. Acceptance: the
  license guard and tests pass; no proprietary source is copied.
- `promote` — Read-only discovery preflight. Added independent
  `detect_engine.py` and `detect_protection.py`. Acceptance: synthetic Unity
  IL2CPP and anti-cheat fixtures produce the expected reports without reading
  binary contents.
- `promote` — Capture filtering and engine token profiles. Added an independent
  candidate filter and QA profiles for RPG Maker, Paradox, and Ren'Py.
  Acceptance: synthetic fixtures preserve every control token.
- `promote` — Engine knowledge profiles for Unity, Unreal, Ren'Py, Paradox, and
  Bannerlord. All begin as `documented-external` or `candidate`, never as proof
  for an exact game.
- `trial` — Pixel-measured logical-wrap then per-line Arabic visual conversion.
  The general requirement is documented, but a reusable implementation is
  deferred until the exact Danganronpa build script is reviewed independently
  and synthetic acceptance fixtures are defined.
# Improvement proposals and implementation status

## Implemented in 2026-09-26 review

- Patch package hash verification and rollback.
- Safe-backup root containment check.
- Protected-token-aware pseudo-localization.
- Context-aware extraction filtering for visible acronyms and labels.
- Unified template verification command.
- Godot engine profile and context-sensitive glossary entries.

## Follow-up candidates

- Add full native PO/XLIFF/ICU validation beyond the common structural cases
  now covered by `format_qa.py`; retain engine-native validation.
- Add HarfBuzz shaping smoke tests and font license metadata.
- Audit third-party components/licenses in an actual binary release; the
  file-level CycloneDX SBOM now inventories the actual artifact.
- Add native engine fixture projects and in-game no-change round-trip tests;
  a synthetic build/install/restore case and three image comparisons now exist.
