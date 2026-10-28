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
## Limitations
Formats and generated code vary by version; no blind offsets or unverified claims.
## Sources
No release is verified by this starter profile. Record the selected tool's
official repository URL, release/commit, license, and a read-only sample with
hashes in the project log before making changes.
