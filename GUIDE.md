# Arabic game localization guide — router

This file is an index, not a document to load for every task. Start with
`AGENTS.md`, then run `python scripts/context_plan.py <route>`.

For a **new game requested end-to-end**, read `references/project-run.md` once:
ask the short grouped startup questions, work continuously without phase
approvals, install a checked build on the user's authorized copy, wait for the
user's playtest and fixes, then create the portable game patch after acceptance.

## References

- New-game intake, autonomy, installation, playtest, and shareable package:
  `references/project-run.md`
- Discovery, engine identification, and one-time research:
  `references/discovery.md`
- Focused research, selection, lawful adaptation, and testing of mods that
  solve a localization problem: `references/localization-mods.md`
- Extraction, native formats, updates, integration, and patching:
  `references/extraction-integration.md`
- Shared Arabic translation rules: `references/translation-core.md`
- UI text: `references/ui-style.md`
- Dialogue and narrative: `references/dialogue-style.md`
- Subtitles: `references/subtitles-style.md`
- Arabic rendering, RTL/BiDi, fonts, and layout:
  `references/arabic-rendering.md`
- Text baked into images and textures: `references/image-localization.md`
- QA and review strategy: `references/qa-strategy.md`
- Packaging and release: `references/release.md`

Read several references only when the current task genuinely spans those
phases. End-to-end work may read all relevant references once, then rely on
`STATUS.md` for later resumptions.
