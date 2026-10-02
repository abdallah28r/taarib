---
name: localization-project-maintenance
description: Migrate, update, archive, release, or harvest reusable improvements from an existing game-localization project.
---

# Localization project maintenance

Use for template migration, game updates, translation-memory export, releases,
or reusable improvement harvesting. Do not activate for routine translation.

## Select the route

```text
python scripts/context_plan.py maintenance --engine <engine-id>
python scripts/context_plan.py release --engine <engine-id>
```

## Maintenance contract

- Preserve project-specific progress, glossary decisions, proven engine facts,
  custom formats, and executable pipelines. Merge template capability
  additively and back up metadata before migration.
- For updates, compare stable ID, source, and available context fields. Carry
  only previously approved targets; send unapproved or context-changed targets
  to review rather than silently reusing them.
- Use `project_stats.py` for coverage, `merge_game_update.py` where compatible,
  and `export_tmx.py` only for rows with `status=approved`, a stable ID, and
  non-empty source/target. Exported TMX records game, file, ID, and context.
- Promote only generalized, evidenced improvements through
  `localization-knowledge-capture`; a proposal is not authority to install a
  model, call a service, or alter the master template.

Release checks are separate from ordinary work. For a **game-localization
release**, wait until the checked build is installed on the user's copy,
the user has playtested it, reported fixes have been addressed, and the user
explicitly accepts it. Then follow `references/release.md`: build a portable
game-specific installer/patch, test clean install and rollback on supported
builds, and generate manifest/SBOM from the actual final artifact when needed.
`verify_template.py --release`, `build_release.py`, and `.releaseinclude` are
for a **public template archive**, not a game patch. Never put copyrighted or
confidential original game data into a public archive or shared TM.
