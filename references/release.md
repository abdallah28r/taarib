# Release workflow

Use only when preparing a deliverable or after dependencies/catalogs changed.
Do not run these steps after ordinary translation batches. For a **game patch**,
first install the checked localization on the user's copy under the recorded
startup choice; wait for the user's playtest, fix findings, and obtain explicit
acceptance of the build before creating its shareable installer. A passing
static QA report is not a substitute for that acceptance.

1. Run `python scripts/verify_template.py --release` for template releases, or
   the project's native full verification for a game patch.
2. Verify installed output and original expectations by SHA-256.
3. Build the final artifact, then generate its manifest and file-level CycloneDX
   SBOM with `python scripts/generate_sbom.py <output.json> --artifact <final.zip>`.
   Declared Python dependencies are metadata, not evidence that they ship.
4. Audit shipped components, exact versions/build options, notices, licenses,
   source-offer or relinking obligations, fonts, and media.
   For fonts, review `fonts/FONT_USAGE.json` and include selected font files
   only where redistribution/embedding rights are verified. Exclude
   `fonts/SYSTEM_INSTALLS.json` from the game patch; its Windows account paths
   and registry details are local development records, not recipient settings.
   Do not copy game-shipped font files into the patch; reference them in the
   recipient's legitimate game build instead.
5. Exclude private research, extracted game text/assets, keys, backups, logs,
   and machine-specific data.
6. For each claimed supported game build/platform, test clean install, update,
   uninstall/rollback, and restoration on a clean copy. Reject unknown or
   mismatched originals by build/hash, without corrupting an installed game.
7. Record engine/build, language code, counts, fonts, RTL method, modified files,
   patch method, known issues, and removal instructions in `reports/FINAL.md`.

The developer patch helpers support `add` and `replace` without bundling
untouched originals. For a synthetic or authorized game copy:

```text
python scripts/build_patch_package.py <clean_game_copy> <new_package_dir> <game-relative-file> [...] --patch-root <changed_copy>
python scripts/apply_patch_package.py <clean_game_copy> <new_package_dir> --yes
python scripts/uninstall_patch_package.py <game_copy> <transaction-id> --yes
```

The install command prints the transaction path; retain its final directory
name for uninstall. If an interrupted installation leaves a `prepared`
transaction, the same uninstall command can recover it when its current files
still match either the original or the patch hashes. For an update, verify and remove the prior transaction,
then install the new package against the supported original hashes. Do not
overwrite a changed installed file: investigate or preserve the user's edit.
These scripts require Python and are **developer/test helpers**, not a finished
recipient installer. Before claiming a shareable package, provide a tested
game-specific wrapper/installer that does not require Codex or the development
toolchain, with an Arabic `INSTALL_AR.md`, supported build hashes, requirements,
update/removal instructions, and successful install/update/uninstall on clean
copies. If that wrapper is not available, label the deliverable a developer
patch candidate, not a ready-to-share release. Review every changed asset and
dependency for redistribution rights; a hash match is not a license grant.

For a game patch, make the installer portable: discover or ask for the
recipient's game directory, verify supported original game files and
supported build, and include the patch payload, an easy Arabic installation
guide, uninstall/rollback instructions, and all runtime prerequisites that may
legally be redistributed. Bundle permitted dependencies or state precisely
how to obtain anything that cannot be bundled. Do not include the original
game archives/assets, user backups, private paths/logs, or unsupported binary
patches. Do not require Codex or the development toolchain on the recipient's
machine, and do not ask for store-account credentials or bypass ownership
controls. Shareability means a recipient with a supported legitimate copy can
install it; it does not promise every edition or device is compatible.

For a **public template archive only**, use `build_release.py` and
`.releaseinclude`; they are not a game-patch builder. Review the resulting ZIP
before publishing. An allowlist is not a content/license audit. Follow
`RELEASE_COMPLIANCE.md` and `THIRD_PARTY_NOTICES.md`.
