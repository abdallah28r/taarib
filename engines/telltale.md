# Telltale Tool profile

Evidence state: `documented-external`; from the Tales of Monkey Island
project in the Arabic Game Localization Playbook (MXIAUDIO and contributors,
CC BY 4.0), adapted.

## Identification

- `Pack/*.ttarch` (version 7 with compressed blocks, 8 uncompressed),
  `*.langdb` (signature `ERTM` when not encrypted), `*.d3dtx` textures,
  `.dlg` dialogs, `.scene` UI.
- `python scripts/detect_engine.py <game_root>` reports `telltale`.

## Localization locations

- `english.langdb`: per record animation and voice ids, four texts, flags.
  In later episodes it is encrypted (blocks of 256 bytes: every eighth a
  modified Blowfish, the rest XOR 0xFF): "Protected archives and runtime code"
  in `references/extraction-integration.md` applies. Rewrite without loss and
  check the decoded bytes match.
- A loose `english.langdb` or a separate override archive crashed even with
  unchanged English text: do not blame Arabic. What worked: a copy of the
  original archive with the resource replaced, only the affected blocks
  recompressed, the resource table, sizes, and offsets preserved.
- Choices: read `.dlg` from the original archive to find choice records.

## Arabic and fonts

- Fonts: 256 slots, 20-byte descriptors (texture + 4 UV), DDS/DXT5 atlas.
  Extend the atlas and recompute UVs; boxes meant `.notdef` for isolated forms
  the font lacked (use NFKC to the base letter).
- Wrap logical text before shaping each line, by atlas width (1180 px for
  spoken subtitles; 1260 pushed a choice out of its box); right-align with a
  transparent padding glyph (slot 127, 4 px wide, taken from transparent rows
  of the atlas), not spaces or the alignment property.
- Performance cues `{...}` go before the shown text; at most eight lines.
- The typewriter reveal goes left to right: speed it up and record the limit.

## Workflow

1. Unpack read-only (`ttg-tools` or `telltale-explorer`), decode the langdb.
2. Rebuild only `*_data.ttarch` and `*_tx.ttarch` copies per episode.
3. Ship forward and reverse byte diffs with SHA-256 per direction and an
   installer that refuses unknown hashes and can recover an interrupted swap.

## Tools

Catalog tools: `ttg-tools`, `telltale-explorer`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine telltale`. Install rules: step 4 of
`game-localization-engineering`. Texture conversion: `directxtex`.

## Logs

A hidden D3D window exits with code 1; show it during start-up. `prefs.prop`
holds `Windowed` with a CRC64; save and restore it byte for byte.
`loc.py probe` looks for new log files after a launch.

## Limitations

Reveal-from-right needs an executable change, not done. Save descriptions and
fixed UI strings needed same-length constants.

## Sources

- https://github.com/Xxdm234/Arabic-Game-Localization-Playbook — `engines/TELLTALE.md` (commit 2475fb6, read 2026-10-28).
- https://github.com/HeitorSpectre/TTG-Tools (GPL-3.0), https://github.com/coccofresco/telltale-explorer (no license file: reference only).
