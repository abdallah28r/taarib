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

Before writing a build, check two things that break games silently:

- **The line break the engine really uses**, per drawing path: some engines
  wrap only on their own code (SCUMM `FF01`), a separate script line (RPG
  Maker event command 401, whose line count must match the source unless the
  format says otherwise), or a special character; a literal `\n` may be drawn
  as text. Prove it in the pilot before setting `line_sep`.
- **Values the code compares are not text.** An internal name, state, key,
  room, sprite, or password the game's code checks (`name = "ralsei"`) must
  stay as it is even if it looks like dialogue; translating one has broken the
  end of a chapter. Find the consumer before translating such a value.

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
**user's identified copy** follows QA (a standing default), without approval
at every intermediate step. Respect a `no` answer or an ambiguous
target. Give the user a
playtest window after installation and use their findings to refine the build
before preparing the shareable game package.

Subtitles and media: FFmpeg extracts and converts subtitle and audio streams,
pysubs2 reads and writes subtitle files deterministically, and Subtitle Edit
helps review timing. whisper.cpp transcription is local speech recognition:
only with the user's explicit authorization for this task, and its text is
evidence to check, never a source to trust.

## Protected archives and runtime code

Some games keep their text in encrypted archives (RPG Maker `.rgssad`/
`.rgss3a` and encrypted MV/MZ images, XOR- or Blowfish-scrambled packs), and
some can show Arabic only through code added at run time (Harmony, BepInEx,
Mono.Cecil, `DOTNET_STARTUP_HOOKS`, a proxy DLL, a byte patch). Both are
allowed only on these terms, in this order:

1. **Not for online or anti-cheat games**: run `detect_protection.py`; any
   anti-cheat, DRM, or online-service marker stops the route.
2. **Warn, then ask once per game** in one message, naming the archive or the
   code change, and get the user's explicit words confirming that they own a
   legitimate copy and have checked the game's license (EULA) and the law of
   their country. Their approval is their decision, not a legal guarantee:
   circumvention laws (such as DMCA §1201) can forbid decrypting even an owned
   copy, and a publisher's permission or a license that allows modding is what
   makes it lawful. Record the approval and the user's words in `PLAN.md`
   decisions.
3. **External tool only**: a pinned upstream tool under `.tools/`, run on a
   copy; never copy decryption code or keys into this template or a project
   repository, and never publish keys.
4. **Nothing decrypted is distributed**: the release carries only our
   translation, fonts we may ship, and reversible patches checked against the
   original hashes; never decrypted game assets or a re-encrypted full archive
   built from them.

Prefer an unencrypted language folder, a native mod API, or a runtime layer
over decryption whenever one exists. PS4 package building and signing stay
rejected.

Stop the affected operation for protection bypass, missing keys, unverified
lossy formats, or an untestable rebuild. Do not invent versions, keys, offsets,
or mappings.
