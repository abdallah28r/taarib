# Discovery and research

Use only for a new game/build, an unknown format, or a failed existing route.

1. Inspect read-only. Inventory names, extensions, sizes, magic bytes when
   useful, locales, localization containers, fonts, and existing loaders.
   Visible text can also live in data tables, scripts, fonts, and images.
2. Run `detect_engine.py` and `detect_protection.py`. Filename detection is a
   hypothesis; a clean protection scan is not proof. A protection hit stops
   mutation and never authorizes bypass.
3. Record probable engine/version, localization architecture, candidate text,
   image/texture, font, audio/subtitle and locale/override locations, packed
   assets, required modifications, and confidence. Distinguish a path inside an
   archive from the archive's path on disk.
4. After identifying the engine, read only its profile. Research the exact
   game/build plus official engine/file-format/mod documentation and primary
   tool repositories. Use community evidence when useful and label it until
   reproduced. Run the focused `mod-research` route once: look for existing
   localization, Arabic/RTL, font, UI, subtitle, and asset-override mods that
   may solve a real task need. Compare them with native support and record
   compatibility, license, dependencies, conflicts, and rejection reasons.
5. Record URL, access date, license, version/commit, compatibility, maintenance,
   dependencies, commands, risks, and evidence state: `verified-project`,
   `documented-external`, `candidate`, or `rejected`.
6. Check known path patterns from the engine profile first, then search for
   game-specific alternatives. Store portable patterns such as
   `<game_root>/Content/Paks/*.pak`, not personal install paths or exhaustive
   lists of assets. Mark each pattern `verified-project`,
   `documented-external`, or `candidate`, with game/build/platform and a brief
   verification or extraction command. A pattern is a starting hypothesis for
   another game, never proof that its assets are there.
7. Choose the least invasive route and prove a small no-change round trip.

Research is normally one-time. Re-run only when the game/build changes, evidence
is stale, the selected tool/mod fails, a mod conflict appears, or a concrete
question remains unanswered. Do not search all community mods indiscriminately.
Do not perform broad recurring searches merely because a session resumed.

Promote reusable evidence to `engines/<engine>.md` at the phase boundary. Keep
temporary notes in `work/NOTES.md`; do not duplicate them across every report.

Before studying another application, follow `LEGAL_AND_CLEAN_ROOM_POLICY.md`.
Do not download or execute a candidate before provenance and license checks.
