# GameMaker
Evidence state: `candidate`; verify the exact runner, archive version, and
game build before selecting any write route.

## Identification
Look for data.win, Undertale-style archives, or GameMaker runner metadata; verify before choosing a method.
## Tools
Catalog tools: `imhex`, `kaitai-struct`, `undertale-mod-tool`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine gamemaker`. Install rules: step 4 of
`game-localization-engineering`.

UndertaleModTool reads and writes `data.win` strings and fonts for supported
versions. ImHex and Kaitai Struct help map an unknown binary layout before
any write route exists.
## Workflow
Back up; extract a small sample; identify strings and fonts; patch a test build; run token and visual QA.

## Lessons from DELTARUNE (Arabic Game Localization Playbook, CC BY 4.0, adapted)

- `lang/lang_en.json` holds keys like `obj_x_Create_0_gml_12_0`. Code written as
  `if (global.lang == "en") {…} else {…}` sends every other language down the
  Japanese path (fonts, layout, line cutting): **replace English, do not add
  `ar`**. Keep the original as `lang_en.orig.json` and lock the language switch.
- Direction: the writer advances with `wx += hspace`; a **negative `hspace`**
  equal to the Arabic glyph width makes it draw from the right and keeps the
  engine's own centring and widths right. Objects that set `writer.hspace`
  later need the sign flipped too (search the code by pattern).
- Storage direction per key: text drawn by the patched writer stays logical;
  text drawn directly by `draw_text` is stored visually reversed. Decide each
  key by tracing it to the function that finally draws it; a professionally
  translated chapter, if any, is the anchor: a rule that breaks it is wrong.
- Templates with `~N` values: mark logical templates and reverse the value when
  it is injected, never a value that contains control codes.
- Control codes (`^N` pause, `&` newline are free for the translator; `/`, `%`
  end messages; `\E*`, `\M*`, `\c*`, `\I*`, `#`) keep count and order.
- `UndertaleModCli` calls need stdin closed (`< /dev/null`) or they hang.
  Android builds use an existing community port with the same bytecode
  (`engines/android-apk.md`).
## Limitations
Formats and generated code vary by version; no blind offsets or unverified claims.
## Sources
No release is verified by this starter profile. Record the selected tool's
official repository URL, release/commit, license, and a read-only sample with
hashes in the project log before making changes.
