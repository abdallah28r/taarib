---
name: game-localization-engineering
description: "Use when identifying a game's engine or text files, writing or proving an adapter, extracting or rebuilding text, researching localization mods, or integrating a build. Triggers: اكتشاف المحرك، استخراج النصوص، محوّل، إعادة البناء، دمج، مود تعريب."
---

# Game localization engineering

Use for engine detection, extraction, round trips, package rebuilding, or
update merges. The outcome is a reversible pipeline built from original game
files and recorded project artifacts.

## Load only the active route

```text
python scripts/context_plan.py discovery
python scripts/context_plan.py mod-research --engine <engine-id>
python scripts/context_plan.py extraction --engine <engine-id>
python scripts/context_plan.py integration --engine <engine-id>
python scripts/context_plan.py application-research
```

Read the returned files only. Tool and engine catalogs are conditional: inspect
the detected engine/profile, not every option.

## Engineering contract

1. Discovery is read-only. Run `detect_engine.py` and
   `detect_protection.py`, inventory evidence, and label confidence. A clean
   filename scan is not proof that a game is unprotected.
2. During discovery, check the engine profile's portable resource-path map
   before a broader scan. Research the exact game and probable engine once;
   record new path patterns, source links, and confidence in `work/NOTES.md`.
   Re-search only for a version change,
   failed/missing route, stale evidence, or a specific unresolved question.
3. After engine identification, run `mod-research` once for mods that could
   enable or repair localization. Compare native support, an unmodified
   third-party mod, a lawfully modifiable fork, and an independent
   localization-only mod. Record plausible candidates and why one route is
   preferred; follow the route's legal, compatibility, and approval gates.
   Do not survey unrelated gameplay mods or silently install a runtime hook.
4. Tools, once the engine is known: run `python scripts/tool_doctor.py
   --engine <engine-id>`; it lists the engine's catalog tools with license,
   source, note, and whether each is already present. Install a missing tool
   the route needs yourself, in whatever way suits it, under these rules:
   - the official upstream release or package only, one exact version
     (Python packages: the version in `requirements/constraints-20260926.txt`
     when listed there);
   - check the SHA-256 the project publishes, or record the one you compute;
   - inside `.tools/` in this folder (Python: a venv at `.tools/venv`); no
     admin rights, no system-wide or winget install, no PATH change;
   - never a local language model or machine translation; local OCR or speech
     recognition only with the user's explicit authorization for this task;
   - record it in `tools/selected-tools.json` (catalog id, version, source,
     license, SHA-256, reason) and run `check_tool_provenance.py`; add a
     catalog entry first for a tool the catalog lacks.
   A tool that goes into the game folder (loader, plugin) is part of the route
   and needs the user's approval for this game.
5. Prefer loose/native localization, then a removable override or patch, and
   only then modification of original containers.
6. Preserve native structure, keys, context, plurals, ordering, encoding, and
   rebuild data. CSV/TSV is an interchange format, not universal truth.
7. Prove a small no-semantic-change extract/rebuild round trip before bulk
   translation: write or reuse an adapter under `adapters/` and pass
   `python scripts/adapter_contract.py --adapter <adapter> --game <copy>`.
   Then `python scripts/loc.py extract` writes one unit per player-visible
   string to `units/`; see `adapters/README.md` and
   `references/translation-units.md`. Back up every game file before mutation and record paths and
   checksums.
8. Merge game updates by stable identity and source state, never row position.
9. Record exact tool/version and the reproducible command once when a route is
   proven or changes, not after every batch. Promote reusable notes once at the
   phase boundary (or immediately for a safety-changing decision) with
   `localization-knowledge-capture`.

Before studying another application or importing third-party material, use the
`application-research` route and its legal gate. Protection, missing keys,
unknown lossy formats, or an unvalidated rebuild stop the affected operation.
Do not invent engine versions, keys, mappings, or localization identifiers.
