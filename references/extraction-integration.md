# Extraction, updates, and integration

## Scope

Translate player-visible menus, HUD, dialogue, subtitles, quests, items,
tutorials, notifications, settings, credits, warnings, and player-facing errors.
Exclude internal IDs, filenames, variables, GUIDs, code, debug strings, shaders,
and commands unless runtime evidence proves visibility.

## Extraction

- Prefer the engine's localization system and existing proven tools.
- Build every time from the verified original, never from a previously
  patched file, so changes cannot pile up.
- Garbled Arabic in a terminal is not proof of corruption: check the bytes
  and read with an explicit encoding before any bulk replace.
- Never commit game files to Git or tests; use a small synthetic fixture or
  hashes and structural reports.
- Preserve the native format as source of truth. CSV/TSV is an interchange
  format only when every key, namespace, context, plural, comment, ordering,
  escape, encoding requirement, and rebuild field survives the round trip.
- Keep source, target, and generated artifacts separate. Record string counts.
- Prove extract → rebuild without semantic changes before bulk translation by
  passing `python scripts/adapter_contract.py` for the game's adapter on a copy
  of the actual build (see `adapters/README.md`).
- Then build a pseudo-Arabic copy with `python scripts/loc.py pseudo --adapter
  <adapter> --game <game_root> --out builds/pseudo` and check it on a copy of
  the game (with launch authority or by the user): Arabic shaping, direction,
  fonts, and longer lines show up before any real translation is spent.

## Updates

Merge by stable identity and source text/context, never row number. Separate
unchanged, changed-source, added, removed, and conflicting entries. Carry a
translation only when identity and source are unchanged. `loc.py update` does
this; changed units show as `needs_rewrite` with their old Arabic in
`previous_target`.

## Integration

Prefer an existing Arabic locale, then a new `ar` locale, then a removable
override as a documented last resort. Never change gameplay values. Rebuild only
modified assets, preserving paths, IDs, hierarchy, and required compression.
Prefer small removable patch packages over replacing base archives.

If a localization mod/loader is the selected route, read
`references/localization-mods.md` before adoption or implementation. Use a
supported native mod API where possible; verify third-party terms, exact build,
dependencies, load order, conflicts, and uninstall on copies. A runtime hook,
DLL injection, or anti-cheat-sensitive route requires explicit per-game
approval and must never bypass protection. A general request to localize does
not authorize unrelated gameplay modifications.

Before mutation, back up with hashes. After installation, verify output hashes,
uninstall behavior, native parsing, and the no-change baseline. Game launch and
runtime testing require current authority. For a new game's end-to-end run,
follow `references/project-run.md`: checked, reversible installation on the
**user's identified copy** follows QA when the intake approved it, without
approval at every intermediate step. Respect a `no` answer or an ambiguous
target. Give the user a
playtest window after installation and use their findings to refine the build
before preparing the shareable game package.

Stop the affected operation for protection bypass, missing keys, unverified
lossy formats, or an untestable rebuild. Do not invent versions, keys, offsets,
or mappings.
