---
name: localization-knowledge-capture
description: "Use at the end of a phase, or when a verified finding should outlive this session: an engine quirk, a working tool version, or a failed route. Triggers: توثيق اكتشاف، ملف المحرك، خبرة مكتسبة."
---

# Localization knowledge capture

Use when discovery, engineering, QA, or release work produces reusable evidence.

## Capture once, promote once

1. During the active phase, append only new findings and source links to
   `work/NOTES.md`. For resource paths, save portable patterns and exceptions,
   not every extracted filename or a machine-specific absolute path. For
   localization-useful mods, keep a short candidate/decision trail with exact
   build, version, license, conflicts, and proof; do not catalogue unrelated
   gameplay mods.
2. At the phase boundary—or immediately if a verified fact changes a safety
   or tool decision—promote reusable, evidenced items to
   `engines/<engine-id>.md`: tools and versions that worked, formats,
   renderer behavior, verified mod compatibility, and uninstall behavior.
   Discovery loads that file for the next game on the same engine; nothing
   else carries knowledge between games.
3. Leave the single resumable next action in `PLAN.md`; progress comes from units.
   If a finding should change the template itself, tell the user in one line
   in chat; do not write a proposals file.

Every promoted item needs an evidence state: `verified-project`,
`documented-external`, `candidate`, or `rejected`. Include applicability,
version/platform, source and access date, license/provenance where relevant,
tested command or artifact, failure mode, and acceptance evidence. Preserve
failed approaches so future projects do not repeat them.

Promotion to the master template is a reviewed copy of the generalized fact or
asset. Never promote game text/assets, secrets, keys, machine-specific paths,
or unsupported claims. Research again only under the triggers in `AGENTS.md`.
