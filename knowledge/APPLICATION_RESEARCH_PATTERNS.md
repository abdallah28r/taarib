# Application research patterns

These are source-neutral requirements synthesized from publicly documented
localization applications and lawful behavioral research. They are not copied
code, prompts, UI text, or internal architecture. Source handling is controlled
by `LEGAL_AND_CLEAN_ROOM_POLICY.md` and
`../compliance/RESEARCH_SOURCE_REGISTER.json`.

## 1. Adapter boundary

Every engine/format adapter should expose the same conceptual stages:

1. detect with evidence and confidence;
2. inventory localizable containers and fonts;
3. extract stable IDs, source, context, and protected syntax;
4. prove a no-change round trip;
5. build a minimal separate patch;
6. verify hashes, parseability, boot evidence, Arabic rendering, and uninstall.

An adapter must not silently fall back to binary patching, runtime injection, or
a different tool when a supported route fails.

## 2. Translation job contract

A batch has a stable ID, source hash, context range, protected-token profile,
glossary revision, model/provider route, attempts, and output hash. It is either
committed completely or remains pending. Never mark partial output complete.

Safe recovery rules:

- deduplicate exact source/context pairs before paid translation;
- skip already approved Arabic targets;
- retry transient errors with bounded backoff;
- split a structurally failing batch in half to a bounded depth;
- preserve an empty target plus an explicit reason when no safe translation was
  produced; runtime display may fall back to source, but authored target data
  must not disguise failure as translation;
- checkpoint after every committed batch.

## 3. Translation memory and cache

Use stable keys and provenance. Cache entries record source hash, target,
context, engine/game scope, glossary revision, producer, review state, and date.
Import into a temporary database/table, validate counts and integrity, then swap
atomically. A truncated or inconsistent import changes nothing.

Do not upload game text, translation memory, crash logs, or screenshots to a
community/cloud service without explicit authorization for that named service.

## 4. Capture and OCR

Use asset extraction before OCR when possible. Screen/OCR workflows should
support calibrated regions, preprocessing profiles, confidence, deduplication,
debounce/stability time for typewriter text, and evidence crops. OCR output is a
candidate, never accepted translation source without review.

`scripts/capture_filter.py` rejects obvious identifiers, paths, and numeric noise
while recording the reason. Preserve rejected rows so filters can be tuned.

## 5. Runtime layers

A runtime layer is opt-in and game-specific. It may substitute only approved
translations and collect unseen text. It must:

- fail open to the original game text without raising into the game;
- avoid live MT by default;
- write only inside its own data directory;
- rate-limit and deduplicate collection;
- delay rapidly changing text until stable;
- use non-conflicting configurable hotkeys;
- include a complete file manifest and uninstall path;
- be refused when anti-cheat/protection or online-service risk is unresolved.

## 6. Arabic renderer decision

Store logical Arabic as canonical. The renderer decision is one of:

- `native`: logical Unicode plus Arabic-capable font;
- `runtime-adapter`: logical source transformed at render time;
- `build-visual`: generated shaping/visual order for a proven legacy renderer.

For `build-visual`, wrap logical text to the real width first and transform each
line independently. Never use character reversal. Record the exact font,
measurement method, box width, shaping library/version, and reversibility test.

## 7. Installation and release

All writes must be contained under an explicitly resolved game/project root.
Reject traversal, absolute archive entries, symlink escapes, and collisions.
Back up changed files by relative path and hash. Apply a package atomically where
possible. Verify the installed manifest before asking the user for one compact
boot/render verdict.

Self-updating code, automatic crash upload, account login, community caches, and
remote package stores are product features, not requirements of the localization
pipeline. They remain excluded until separately designed for privacy, security,
licensing, and user consent.

## 8. Clean-room acceptance

An implementation is eligible for the core only when:

- its neutral requirement and acceptance tests are recorded;
- no prohibited source material was consulted while implementing it;
- names, structure, messages, constants, and tests are original;
- relevant format/tool sources and licenses are recorded;
- `python scripts/license_guard.py` and repository tests pass.
