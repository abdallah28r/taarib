# Application research integration — 2026-09-26

## Outcome

The master template now supports legally conservative application research and
clean-room implementation. No file, code, prompt, internal string, binary,
generated package, account data, or private resource from the two proprietary
expired-permission applications was copied into the template. Their old research
export was treated as untrusted evidence and used only to identify general
problems worth expressing independently.

## Verified public application sources

The current license/handling catalog is
`compliance/RESEARCH_SOURCE_REGISTER.json`:

- XUnity.AutoTranslator — MIT — permissive reuse with notices.
- Translumo — Apache-2.0 — permissive reuse with license/NOTICE obligations.
- GameLingo — MIT — permissive reuse with notices.
- UGT and RSTGameTranslation — BSD-style attribution — inspect and preserve the
  exact notices before copying.
- LunaTranslator and AurexTranslator — GPL-3.0 — clean-room/reference only for
  this permissive-core objective.
- AiNiee — AGPL-3.0 — clean-room/reference only, including hosted-service work.
- Translator++ — reported GPL with mixed components — clean-room only until the
  exact source/release license scope is verified.
- Closed, source-available, unknown-license, no-license, and expired-permission
  applications — clean-room only.

Primary URLs and access date are stored in the machine-readable catalog. Names
in this report/catalog are research provenance, not product marketing credits.

## Independent implementations added

- `scripts/license_guard.py`: validates application handling and prevents
  unverified/copyleft sources from being classified as permissive core inputs.
- `scripts/detect_engine.py`: read-only engine/backend/loader hypotheses.
- `scripts/detect_protection.py`: conservative filename-only stop gate.
- `scripts/capture_filter.py`: source-neutral extraction candidate classifier.
- `scripts/estimate_tokens.py`: deterministic batch-planning estimate.
- `scripts/loc_qa.py`: added RPG Maker, Paradox, and Ren'Py token profiles plus
  configurable line-break, Latin-leftover, unchanged, and detached-article
  warnings.

Every independent implementation is recorded in
`compliance/CLEAN_ROOM_LEDGER.csv` with its neutral specification and tests.

## Knowledge and policy added

- `LEGAL_AND_CLEAN_ROOM_POLICY.md`
- `knowledge/APPLICATION_RESEARCH_PATTERNS.md`
- engine profiles for Unity, Unreal, Ren'Py, Paradox, and Bannerlord
- application/source handling catalog
- strengthened engineering, QA, translation, and subagent skills
- usage planning and protected-markup escalation triggers
- third-party notice rules that distinguish research, external invocation,
  source incorporation, and binary redistribution

## Deliberately excluded

- proprietary application code/scripts/binaries and cached packages;
- decompilation, obfuscation bypass, private session/browser/account data;
- copied prompts or documentation wording;
- unofficial web-translation endpoints;
- live translation services without named authorization;
- automatic crash/text upload and community-memory upload;
- runtime injection or binary patching as a default route;
- local language models and local machine translation;
- generated font atlases or game assets from another product.

## Verification

- `python -m unittest discover -s tests -v`: 18 tests passed.
- `python scripts/check_agent_policy.py`: passed.
- `python scripts/license_guard.py`: passed.
- Search for the two proprietary application names, domains, install paths, and
  private endpoint markers inside the template: no matches.

## Remaining publication decision

The repository still has no top-level open-source `LICENSE`. This was not added
silently because selecting a license grants durable rights to recipients and the
owner name/organization is not configured. Apache-2.0 remains the recommended
default for the original core if the owner wants a permissive commercial/open
source path with an express patent grant. Before publication, add that license
under the intended owner identity and rerun the release audit.
