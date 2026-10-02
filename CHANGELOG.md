# Changelog

## 2026-10-03 — Full-template audit fixes

- Created an exact Git baseline before these changes and developed them in a
  separate worktree/branch.
- Extended developer patch packages to add and replace files, check hashes,
  back up originals, uninstall, and recover interrupted prepared installs;
  final recipient installers remain a separate game-specific release gate.
- Prevented approved translations from carrying into changed context; mapped
  detected engine IDs to their existing profiles and repaired missing tool
  profile declarations.
- Clarified Arabic plural categories, image structural-check limits, direct
  visual QA, typography contrast/style constraints, and detailed LQA records.
- Added explicit engine-profile evidence states and selected-tool provenance;
  application downloads now require exact versions/tags and published hashes.
- Added synthetic regression tests and distinct backup transaction names.

## 2026-10-02 — Localization mod route

- Added a focused one-time survey of game/engine mods that solve Arabic
  localization, font, RTL, UI, subtitle, or asset-override needs.
- Defined how to compare native support, an unmodified dependency, a lawfully
  modified mod, and an independent localization-only mod, with compatibility,
  license, conflict, protection, rollback, and release gates.
- Added a `mod-research` context route and reusable engine-profile evidence
  fields without requiring a broad mod catalogue or gameplay changes.

## 2026-09-28 — New-game autonomous run and playtest gate

- Added one grouped startup intake for new games, including project preferences
  for subagents and baked-image translation.
- Defined continuous execution through verified installation on the user's
  identified copy, followed by user playtesting and a fix loop without
  phase-by-phase approval requests.
- Separated the post-acceptance portable game installer from the public
  template archive; required compatibility checks, rollback, dependencies,
  and Arabic installation instructions.

## 2026-09-28 — Lean records and resource-path maps

- Made STATUS a short resumable snapshot; kept detailed QA defects in the LQA
  matrix and summaries in the QA report, avoiding per-batch duplication.
- Aligned discovery notes and engine-profile promotion to phase boundaries,
  except for verified safety/tool decisions needing immediate documentation.
- Added portable image, text, font, audio/subtitle and localization path maps
  with version/platform evidence, without listing every asset or personal paths.

## 2026-09-28 — Audit hardening

- Fixed ICU branch-text false positives and checked XLIFF inline-code identity.
- Restricted update carry-forward and TMX export to approved, context-safe rows.
- Made safe replacement and patch install backups unique per transaction;
  added exact-original preflight and synthetic build/install/restore tests.
- Switched public ZIP creation to `.releaseinclude` and generated file-level
  CycloneDX inventories from an actual ZIP or directory.
- Required a concise agent visual-review record for approved image regions;
  visually rejected three representative existing Danganronpa image candidates.

## 2026-09-28 — Image localization policy

- Added the `game-image-localization` skill, `images` context route, and a
  machine-readable image policy.
- Added `TRANSLATE/KEEP/REVIEW` classification, adaptive multi-method search,
  mandatory direct visual inspection, source-style fidelity, and a prohibition
  on invented captions or effects.
- Added tested conditional roles for OpenCV, PaddleOCR, IOPaint/LaMa, SAM2, and
  DirectXTex. Official OpenAI image editing is enabled per project, with review
  required before integration.

## 2026-09-27

- Replaced full-corpus startup reading with validated progressive-disclosure
  routes for discovery, translation, QA, delegation, maintenance, and release.
- Split the large guide and style documents into focused references while
  preserving the safety, Arabic, renderer, integration, and release rules.
- Reduced duplicated skill instructions and changed root review to deterministic
  integration plus risk-based semantic sampling instead of full retranslation.
- Added `context_plan.py`, route tests, a temporary knowledge inbox, and
  phase-boundary promotion to prevent duplicated notes.
- Separated ordinary template verification from release-only SBOM work and
  archived historical reports outside the normal workflow and public package.

## 2026-09-26

- Added a single deterministic verification command.
- Hardened patch hash verification, path checks, backups, and rollback.
- Preserved placeholders and markup during pseudo-localization.
- Reduced false-positive rejection in extracted text classification.
- Made engine knowledge validation accept the documented profile structure.
- Added project licensing and security/contribution documentation.
- Added PO/XLIFF/ICU QA, Arabic plural diagnostics, HarfBuzz shaping smoke tests,
  CycloneDX SBOM generation, pinned Python constraints, and privacy-aware public
  release packaging.
