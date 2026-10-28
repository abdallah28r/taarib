# Android APK profile

Evidence state: `documented-external`; from Yuppie Psycho (.NET for Android),
DELTARUNE (community port), and OMORI (RPG Maker MV in a WebView) in the
Arabic Game Localization Playbook (MXIAUDIO and contributors, CC BY 4.0),
adapted. Only for the user's own APK of a game they own.

## Identification

| In the APK | Kind | Route |
| --- | --- | --- |
| `assemblies/assemblies.blob`, `libmonodroid.so`, `libxamarin-app.so` | .NET for Android | patch inside the assembly with `mono-cecil` (`engines/monogame-xna.md`) |
| `assets/game.droid`, `libyoyo.so` | GameMaker | check the bytecode version; a community port may be easier |
| `assets/www/` and a WebView | RPG Maker MV/MZ or HTML5 | replace assets, add a JS plugin (`engines/rpg-maker.md`) |
| `assets/bin/Data/`, `libunity.so`, `libil2cpp.so` | Unity IL2CPP | untested |

`python scripts/detect_engine.py <unpacked_apk>` reports `android-apk`.

## Workflow

1. Unpack as ZIP (`apktool` when resources must be decoded); keep entry order,
   compression, and alignment.
2. Repack copying unchanged entries raw; rebuild only changed entries.
3. `zipalign -p 16` when raw assemblies are read in place (misaligned
   assemblies run but `try/catch` stops working).
4. Sign v1+v2+v3 with `apksigner` (target SDK 34 rejects v1 alone) and a key
   the user keeps; another key cannot install over the previous APK.
5. Verify inside the signed APK: every expected file, signature, alignment,
   no extra files; compare entry by entry with the original.
6. Test on a real device with the `ar-SA` locale, or say it was not tested.

## .NET for Android pitfalls

No startup hooks or Harmony: insert calls into `game.dll` with Cecil. MVID and
type tokens are referenced from `libxamarin-app.so` and must not change; RVA
constant data can be lost silently; write the patched assembly uncompressed
and 16-byte aligned; languages may be hard-coded, so add `ar` before the device
locale is read; XNB platform byte `d` becomes `a`. Code insertion is runtime
code: "Protected archives and runtime code" in
`references/extraction-integration.md` applies.

## Tools

Catalog tools: `apktool`, `android-build-tools`, `android-platform-tools`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine android-apk`. Install rules: step 4 of
`game-localization-engineering`.

## Logs

`adb logcat` (for .NET: `adb logcat -s DOTNET`) or the game's log under
`/sdcard/Android/data/<package>/files/`; save it to a file and run
`python scripts/boot_verdict.py --log <file>`.

## Limitations

A build of about 20 minutes may be killed midway: check the output size and
time. Unity IL2CPP APKs were not tried.

## Sources

- https://github.com/Xxdm234/Arabic-Game-Localization-Playbook — `engines/ANDROID.md` (commit 2475fb6, read 2026-10-28).
- https://github.com/iBotPeaches/Apktool (Apache-2.0); https://developer.android.com/tools/apksigner and https://developer.android.com/tools/zipalign (Android SDK build-tools).
