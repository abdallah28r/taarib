# Source / Source 2
Evidence state: `candidate`; this is a discovery hint, not verified support
for any particular Source or Source 2 game.

## Identification
Confirm VPK/PAK assets, localization files, and engine version before extraction.
## Tools
Catalog tools: `vpkedit`, `valve-resource-format`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine source-engine`. Install rules: step 4 of
`game-localization-engineering`.

VPKEdit opens and repacks VPK archives. ValveResourceFormat (Source 2
Viewer) inspects and exports Source 2 resources; check write support first.
Localization text often lives in loose `resource/*_<language>.txt` files that
need no archive tool.
## Workflow
Extract one package, preserve paths and encoding, edit localization, repack only after a reversible test.
## Limitations
Game-specific schemas, signing and updates can invalidate patches.
## Sources
Source references are not yet pinned here. Before using a tool, record its
official repository URL, exact release/commit, license, game version, and a
successful read-only sample in the project profile.
