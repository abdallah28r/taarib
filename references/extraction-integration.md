# Extraction, updates, and integration

## Scope

Translate player-visible menus, HUD, dialogue, subtitles, quests, items,
tutorials, notifications, settings, credits, warnings, and player-facing errors.
Exclude internal IDs, filenames, variables, GUIDs, code, debug strings, shaders,
and commands unless runtime evidence proves visibility.

## Extraction

- Prefer the engine's localization system and existing proven tools.
- Preserve the native format as source of truth. CSV/TSV is an interchange
  format only when every key, namespace, context, plural, comment, ordering,
  escape, encoding requirement, and rebuild field survives the round trip.
- Keep source, target, and generated artifacts separate. Record string counts.
- Prove extract → rebuild without semantic changes before bulk translation.

## Updates

Merge by stable identity and source text/context, never row number. Separate
unchanged, changed-source, added, removed, and conflicting entries. Carry a
translation only when identity and source are unchanged.

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
