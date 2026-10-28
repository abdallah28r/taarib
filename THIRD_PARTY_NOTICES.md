# Third-party notices

This file lists material actually copied into or distributed with a release.
Merely researching or invoking a separately installed tool does not add it here.

At the time this template was audited on 2026-09-26, no third-party application
source code or binary from `compliance/RESEARCH_SOURCE_REGISTER.json` was copied
into the template. Python requirements are installation dependencies, not
vendored packages. A packaged executable or offline bundle must be audited again
because it may embed those dependencies.

For every shipped external component record:

- component and exact version/commit;
- upstream URL and downloaded SHA-256;
- exact license and copyright notice;
- files copied or linked and whether they were modified;
- location of the full license under `third_party/licenses/`;
- NOTICE text and source-offer obligations when applicable;
- whether the component ships in source, binary, or both.

Do not redistribute copyrighted game assets, extracted game text, proprietary
fonts/models, private research files, or material covered only by expired
permission.

## Material adapted into the template

- `references/rendering-lessons.md` and the rules in
  `references/extraction-integration.md` (line breaks; values the code
  compares) are adapted from «دليل تعريب الألعاب الاحترافي» — MXIAUDIO and
  contributors — https://github.com/Xxdm234/Arabic-Game-Localization-Playbook
  (commit 2475fb6, read 2026-10-28), licensed CC BY 4.0
  (https://creativecommons.org/licenses/by/4.0/). Changed: selected,
  shortened, translated to English. No code was copied; `scripts/arabic_shaping.py`
  is our own implementation of the same rules.

## Acknowledgments

Ideas only, no material copied: the Arabic text tools of asgore-undertale
(https://github.com/asgore-undertale — Asgore Studio, RenovArabi, ATCEE) for
fitting text to a box and handling diacritics, and Arabic / Persian Text
Shaper by Ai Haka (https://github.com/KKING-ar/Arabic-Reshaper, MIT) for
keeping rich-text tags valid when a line is reversed.
