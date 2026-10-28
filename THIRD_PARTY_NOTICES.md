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

- The engine profiles `engines/monogame-xna.md`, `scumm-scummvm.md`,
  `grime-emi.md`, `telltale.md`, `dinky.md`, `proprietary-pc.md`,
  `android-apk.md`, `ps1.md`, `ps2.md`, and the "Lessons from …" sections of
  `unity.md`, `gamemaker.md`, and `rpg-maker.md` are adapted from the same
  playbook's `engines/` guides (CC BY 4.0). Changed: selected, shortened,
  translated to English, and tied to this template's policy and tools.
- `scripts/font_bank.py` (`assign_bank`, `coverage`) and
  `scripts/byte_patch.py` (`patch_bytes`, `diff_ranges`, `make_patch`,
  `apply_patch`) are adapted from the playbook's `code/font_tools.py` and
  `code/patch_tools.py` under the MIT License:

  ```text
  MIT License

  Copyright (c) 2026 MXIAUDIO and contributors

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.
  ```

  `scripts/save_guard.py` and the transparency check in
  `scripts/check_image_regions.py` are our own code written from the
  playbook's ideas.

## Acknowledgments

Ideas only, no material copied: the Arabic text tools of asgore-undertale
(https://github.com/asgore-undertale — Asgore Studio, RenovArabi, ATCEE) for
fitting text to a box and handling diacritics, and Arabic / Persian Text
Shaper by Ai Haka (https://github.com/KKING-ar/Arabic-Reshaper, MIT) for
keeping rich-text tags valid when a line is reversed, restoring logical text
from shaped output, and drawing diacritics one letter later; the Miqbas and
FLTAH research package (ideas from observed behaviour only: per-game line
width, install failure reasons, boot verdict from logs).
