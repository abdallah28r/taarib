# GameMaker
Evidence state: `candidate`; verify the game build before selecting a route.

## Identification
Look for `data.win` or GameMaker runner metadata; verify before choosing a method.
## Tools
No catalog tool applies. Details: `python scripts/tool_doctor.py --engine gamemaker`.

Only loose language files such as `lang/*.json` are in scope. Writing `data.win` is
out of scope (`references/extraction-integration.md`).
## Workflow
Back up; read the language file; keep control codes in count and order; run token and visual QA.
## Limitations
Formats and generated code vary by version; no blind offsets or unverified claims.
## Sources
No release is verified by this starter profile. Record the game version and a
read-only sample with hashes in the project log before making changes.
