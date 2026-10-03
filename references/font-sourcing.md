# Font sourcing, use, and account-level installation

Use this only when choosing or changing a font for game text or baked image
text. The one-time project authorization is recorded in `PROJECT.yaml` under
`typography`; do not ask again for each font. Do not download fonts merely to
grow a collection.

## Search and visual decision

Inspect the shipped font, fallbacks, renderer slots, and original lettering
first. Search the web for a small set of alternative Arabic-capable fonts when
the available ones are unsuitable **or** a credible external candidate may
materially improve the match. Compare actual rendered Arabic samples beside
the original game UI/art at game scale, including mixed text and the smallest
supported layout. For images, original lettering treatment takes priority over
the game's general typography plan. A candidate wins only if it improves the
result and passes shaping, metrics, readability, native-renderer, and rights
checks; do not replace an already good font just because a new one exists.

Do not use a fixed trusted-site allowlist or mark an entire site untrusted
because it is not listed here. Evaluate the **particular font and release**:
publisher/designer identity, original project or foundry, direct release URL,
version/commit, actual license file, file integrity, and compatibility. Treat
an aggregator as a discovery lead; trace the license and release to the
publisher when possible. If evidence is missing, hold that proposed use—not
the whole site—pending verification. Useful starting points, not an exclusive
list: [Google Fonts repository](https://github.com/google/fonts),
[Noto Arabic](https://github.com/notofonts/arabic),
[IBM Plex](https://github.com/IBM/plex),
[Amiri](https://github.com/aliftype/amiri), and
[SIL Arabic fonts](https://software.sil.org/arabicfonts/).
[Font Squirrel](https://www.fontsquirrel.com/faq) can surface candidates but
it asks users to read each font's license. A reputable commercial source such
as [Adobe Fonts](https://helpx.adobe.com/fonts/web/font-licensing/purchase-license-fonts.html)
is not automatically licensed for embedding its font file in a game.

Check three rights separately for the exact version: (1) rendering static
lettering into localized images, (2) using the font file during development
or in the user's own game, and (3) redistributing/embedding the font file in a
shareable patch. "Free for personal/commercial use" alone proves none of
these scopes. Preserve the exact license and notices; for OFL fonts, inspect
Reserved Font Name terms if modifying the font. See the
[OFL FAQ](https://openfontlicense.org/ofl-faq/). This is a workflow gate, not
an automatic legal certification.

## Download, storage, and records

When permitted by the project policy, download a font from a verified source
without asking again. Prefer the publisher's direct TTF/OTF release or a
documented archive with its license; avoid executable installers, bundled
download managers, and unknown mirrors. Record a published digest/signature
when available, always compute SHA-256 of the file received, inspect the font
metadata, and test it in a project-local copy before any Windows installation.
Do not execute code found in a font archive.

Keep **selected external** font files under `fonts/selected/` and exact
license/notice copies under `fonts/licenses/`. Never copy the game's shipped
font into this folder. Use `fonts/FONT_USAGE.json` for **every chosen font**,
including a shipped game font by game-relative asset reference rather than a
copied binary: source/publisher where applicable, build/version, SHA-256,
distinct rights determinations, each game-text role or image asset/pattern
where used, and a short visual/native test result. A path pattern may cover a coherent image
family; note exceptions rather than listing hundreds of redundant files.
Do not create a report for every rejected candidate. Update the registry when
a selected font or its use changes. Run `python scripts/check_font_records.py`
for structural checks; a passing result is not proof of visual quality or
license validity.

Minimal entry shape in `FONT_USAGE.json` (replace placeholders with verified
facts, and use project-relative slots/paths or concise image patterns):

```json
{
  "id": "family-regular", "origin": "external",
  "family": "[family]", "publisher": "[publisher]",
  "version_or_commit": "[exact version]", "source_url": "https://[release]",
  "font_file": "fonts/selected/[file].ttf", "sha256": "[64 hex digits]",
  "license_id": "[exact license]", "license_file": "fonts/licenses/[license].txt",
  "decision_note": "[why selected]",
  "rights": {
    "render_into_images": "allowed",
    "development_use": "allowed",
    "redistribute_font_file": "unverified"
  },
  "uses": [
    {"kind": "game-text", "target": "[UI slot or game-relative path]", "test_status": "pass", "test_note": "[observed evidence]"},
    {"kind": "image", "target": "[asset or image-family pattern]", "test_status": "pending", "test_note": "[what remains]"}
  ]
}
```

Rights values are `allowed`, `denied`, or `unverified`. An `allowed` value
must be based on the stored exact license, not on a site badge or the example
above. A selected font is not automatically approved for release.
For a shipped game font, set `origin: "game-shipped"`, omit `font_file` and
`license_file`, and record `game_asset` as a game-relative path or
archive/member reference. Record the game build under `version_or_commit` and
its SHA-256 without copying the font into the project. Do not install a
shipped game font into Windows. Possessing a game does not grant rights to
redistribute its font file; keep `redistribute_font_file` as `unverified` or
`denied` unless separate evidence establishes otherwise.

## Windows installation only if necessary

Prefer project-local font files. If the actual renderer/workflow requires a
Windows-installed font, the project's standing authorization permits installing
the **selected** font for the current Windows account without another question.
Before mutation, verify it is not already installed or conflicting, and write
a `planned` record to `fonts/SYSTEM_INSTALLS.json` containing its font ID,
source hash, intended user-scope destination/registration, and rollback route.
Use only the current user's font directory and `HKCU` Fonts registration;
never touch `C:\Windows\Fonts` or `HKLM` for this workflow.
After installation, verify and mark it `installed`. Never install every trial
font, overwrite/replace a pre-existing font, use administrator elevation,
install for all users, or change system-wide font substitutions. If a safe
current-user-only route is unavailable, continue project-local work and ask
only if that limitation truly blocks the task.

Before rollback, compare the installed file and registration with the log;
remove only what this project installed. If another process changed them,
stop rather than removing a possibly user-owned font. Keep the installation
log separate from `FONT_USAGE.json` and do not publish machine-specific paths.
Each `SYSTEM_INSTALLS.json` item has `font_id`, `source_sha256`,
`scope: "current-user"`, `preexisting: false`, `status` (`planned`,
`installed`, or `removed`), `installed_file` (this user's Fonts directory),
`registry_key: "HKCU\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts"`,
`registry_value_name`, and concrete `rollback_steps`. Do not log a planned
install as completed or remove it solely because the registry says `installed`.
Windows font installation can affect other applications; current-user scope
and a reversible record are mandatory. See
[Microsoft's font installation guidance](https://learn.microsoft.com/en-us/windows/win32/gdi/font-installation-and-deletion).

## Shareable release

The recipient package must not depend on a font installed on the developer's
Windows account. Bundle the selected font with its license/notices only if the
exact redistribution/embedding rights permit it, and test the package on a
clean supported game copy. Otherwise document the legitimate acquisition and
installation requirement; if it cannot be made practical and lawful, choose a
different font or do not claim a ready-to-share package. Exclude local font
install logs and rejected/downloaded candidates from public artifacts.
