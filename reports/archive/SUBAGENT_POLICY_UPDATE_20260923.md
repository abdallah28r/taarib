# Subagent and model-policy update — 2026-09-23

## Outcome

- Added explicit, current-task authorization for subagents; permission does not persist.
- Prohibited local LLM and machine translation, including Ollama, Argos Translate, LibreTranslate, llama.cpp, LocalAI, and equivalent local endpoints.
- Made local OCR/STT explicit-authorization-only and removed OCR from the `all` setup profile.
- Historical 2026-09-23 state: added a three-agent default and no nested delegation. Superseded on 2026-09-25 by adaptive concurrency with no fixed project cap and bounded policy-inheriting nested delegation; one writer per file remains active.
- Added a reusable orchestration skill, machine-readable policy, deterministic policy checker, delegation-brief generator, and regression tests.
- Removed the active `local-mt` requirements/profile/catalog entries and refreshed tool-status and manifest reports.
- Optimized `tool_doctor.py` to index Python distributions once per run rather than once per tool.

## Verification

- `python scripts/check_agent_policy.py`: passed.
- `python -m unittest discover -s tests -p "test_*.py"`: 8 tests passed.
- Modified and new shared skills passed the Skill Creator validator.
- `scripts/setup_tools.ps1` passed PowerShell parser validation.
- Generated reports contain no active `local-mt`, Ollama, Argos Translate, or LibreTranslate entries.

No subagent or local AI model was used to implement or verify this update.

## Sources

- [OpenAI model selection](https://developers.openai.com/api/docs/guides/model-selection)
- [OpenAI reasoning effort](https://developers.openai.com/api/docs/guides/reasoning)
- [OpenAI Multi-agent](https://developers.openai.com/api/docs/guides/responses-multi-agent)
- [OpenAI agent models and providers](https://developers.openai.com/api/docs/guides/agents/models)
