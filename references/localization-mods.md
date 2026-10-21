# Localization mod research and adaptation

Use once after identifying the exact game/build and probable engine, and again
only when a selected route fails, the game updates, or a concrete mod conflict
appears. Research **mods that materially enable or improve this localization**,
not every popular gameplay mod. Research alone does not establish a mod's
license, compatibility, or permission to redistribute it; adoption follows the
checks and project installation authority below.

## Find relevant candidates

Start with the game's official modding/localization documentation and existing
native language support. Then inspect primary mod repositories, maintained
releases, issues, compatibility notes, and credible community reports for:

- existing Arabic/localization patches, string or asset overrides, and loaders;
- Arabic shaping/BiDi, font fallback/atlas, UI sizing, subtitles, and image
  localization fixes;
- documented conflicts, load order, version/platform differences, and
  interaction with already installed mods.

Search the exact title and build first; use the engine ecosystem to find gaps
or comparable solutions. Do not assume a mod for another game or engine version
will work. Record only plausible candidates in `work/NOTES.md`: problem solved,
source URL/access date, author, exact release/commit, license/provenance,
supported game/engine/build/platform, dependencies, maintenance, installation
and removal method, known conflicts, and evidence state. Note rejected routes
briefly so the same dead end is not retried. Community claims remain candidates
until tested on the user's build.

## Choose the least invasive lawful route

1. Prefer the game's native locale/mod API or a small removable override when
   it solves the problem without another dependency.
2. An existing mod may be used **unmodified as a separate dependency** when
   its source, version, terms, and compatibility are clear. Do not bundle its
   files merely because they are publicly downloadable. A compatible,
   removable, localization-only dependency may be installed on the user's
   identified copy under the project's recorded install authority without a
   new phase-by-phase question; the runtime-hook exception below still applies.
3. Modify/fork a mod only when the exact component's license or current grant
   permits the planned derivative and distribution. Work on a separate copy,
   preserve its required notices, track upstream version and local diff, and
   test the modified build. Follow `LEGAL_AND_CLEAN_ROOM_POLICY.md`; a tool
   classified `external-tool-only` is not to be modified or vendored into the
   template. Copyleft components remain separate from the permissive core
   unless their exact obligations and packaging are reviewed.
4. If no suitable mod exists, design an independent localization-only mod or
   adapter with the engine's supported extension route. Use clean-room
   requirements for ideas learned from unlicensed/proprietary work; do not
   copy protected code, artwork, text, or binaries.

Choose by measured Arabic quality, reversibility, build compatibility,
maintenance burden, performance, conflict risk, and release obligations—not
popularity. Do not add a mod that changes gameplay, saves, networking, or
achievements unless the localization truly requires it and the user approves
the specific consequence. Runtime loaders, hooks, DLL injection, or an
anti-cheat/online-sensitive route require explicit per-game approval after a
protection check; never bypass DRM, signatures, access controls, or anti-cheat.
If licensing or compatibility cannot be established, keep the mod research-only
and continue with a safe independent/native route when possible.

## Prove and preserve

On copies of the exact supported build, verify a no-change baseline, install
and load order, dependencies, coexistence with the user's relevant mods,
Arabic text/font/RTL and UI behavior, update sensitivity, and clean removal.
Back up verified originals; never edit the only third-party mod installation
or base archive. A mod that fixes one screen but breaks another is not accepted.
Follow the normal QA and user-playtest gate before shipping. A recipient-facing
package must state mod dependencies and licenses, verify its supported build,
and include only files that may be redistributed.

At the phase boundary, promote tested mod knowledge to `engines/<engine>.md`: chosen route, alternatives rejected,
version, evidence, conflicts, rollback, and what must be rechecked in another
game. Do not copy a game's assets or private install paths into the template.
