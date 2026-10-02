# Release compliance checklist

Before distributing source or binaries:

1. Confirm that the MIT license and contributor copyright designation match the
   owner's intended publishing and branding model; legal identity may be added
   before release without changing the license terms.
2. Run `python scripts/verify_template.py --release --json reports/VERIFY_TEMPLATE.json`.
3. Record exact dependency versions, URLs, licenses, and SHA-256 values.
4. Build the final ZIP, then generate its file-level CycloneDX SBOM with
   `python scripts/generate_sbom.py <output.json> --artifact <final.zip>`.
   This lists actual shipped files, not merely optional tools or declared
   dependencies; separately audit third-party binaries and transitive packages.
5. Include required third-party notices and complete license texts.
6. Exclude private research registers, game assets, extracted text, keys, and
   files covered by expired permission from public packages.
7. Test installation and removal from a clean copy and preserve the manifest.

The catalog is a research and operational aid; it is not proof that a tool may
be bundled. For example, FFmpeg's effective license depends on build options,
and 7-Zip includes multiple licenses and an unRAR restriction.
