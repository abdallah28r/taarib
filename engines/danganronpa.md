# Danganronpa (Spike Chunsoft PC releases)
Evidence state: `documented-external`; from the tools' own documentation, not
yet proven on a game build in this template.

## Identification
Danganronpa 1 and 2 on PC keep their data in WAD archives holding PAK
containers and LIN script files. Danganronpa V3 uses CPK/SPC archives and STX
text. Confirm the exact title, store build, and archive names first.

## Tools
Catalog tools: `drat`, `danganronpa-tools`, `spiral`, `hlm-wad-explorer`, `hyouta-tools`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine danganronpa`. Install rules: step 4 of
`game-localization-engineering`.

- Spiral: Kotlin framework and the most detailed WAD/PAK/LIN/CPK format
  reference; build it and prove a no-change round trip before use.
- danganronpa-tools (`wad_archiver`, `pak_archiver`, `lin_compiler`):
  archived reference tools; pin and prove a round trip on copies.
- HLMWadExplorer: WAD inspection and editing candidate.
- DRAT (Danganronpa Another Tool): fallback or comparison only.
- HyoutaTools: multi-game collection Spiral credits for PAK/LIN research;
  identify the exact module first.

## Workflow
Copy the WAD, unpack one PAK, decompile one LIN, change one line, rebuild,
compare the structure, and test that line in the game before bulk work.

## Limitations
Several tools are archived or community-maintained; licenses must be read in
each repository. LIN text carries control codes and text boxes with fixed
widths; Arabic shaping and direction need a renderer test like any engine.

## Sources
Repositories are listed in `tools/open-source-tools.json` (profile
`danganronpa`). Record the exact commit and license used in
`tools/selected-tools.json`.
