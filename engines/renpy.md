# Ren'Py engine profile

Evidence state: `documented-external`; test the exact Ren'Py version and game
customizations.

## Identification and native route

Typical markers are `game/*.rpy`, `.rpyc`, `.rpa`, a `renpy/` directory, and the
game executable. Prefer Ren'Py's native `game/tl/<language>/` translation files
and generated translations when sources/SDK workflow are available. Preserve
labels, interpolation, text tags, executable statements, and stable IDs.

`unrpyc` and `rpatool` are inspection/archive tools when lawful and necessary;
their output still needs a lossless workflow and must not replace the only copy.

## Portable resource paths

| Resource | Starting pattern | Evidence and limit |
| --- | --- | --- |
| Native translated text | `<game_root>/game/tl/<language>/**/*.rpy` | Native Ren'Py layout when translation files are supplied/generated. |
| Scripts and packed resources | `<game_root>/game/**/*.rpy`, `*.rpyc`, `*.rpa` | Confirm what is loose versus inside RPA for the exact game. |
| Images/fonts/audio | Under `game/` or an RPA archive; no mandatory subdirectory | Inspect image/audio statements and actual archive entries before recording a verified pattern. |

## Arabic

Ren'Py behavior is version-sensitive. Ren'Py's changelog documents improved
Arabic shaping when `config.rtl` and HarfBuzz are active in relevant Ren'Py 8
versions. Do not assume older versions behave identically. Test logical Unicode,
the actual game font, substitutions, neutral strings, and tags such as `{w}` and
`{p}` before bulk work.

Use a font or FontGroup with Arabic coverage. Keep logical Arabic in source and
translation memory; do not store presentation forms as the canonical target.

Verified on one project (Ren'Py 8.0.3, 2026-10-17); re-test on any other build:

- Words came out in reverse order although each word's letters were right: the
  renderer split text into segments at spaces, tags, and font changes. The fix
  stayed in the display layer (one Arabic/Latin font for the line,
  `config.rtl` set on language change, visible segments reordered, timing tags
  kept); the translation files stayed logical Arabic.
- Choice text complete in the files was still cut off inside the choice button.
  Measure the Arabic width in the real font against the button, then set a
  language-specific wrap width; never shrink every font.
- Some screen labels are literal strings in `screens.rpy`, outside the
  translation catalogue (one appeared only after a feature unlocked). Search
  the screens for literals and visit unlockable states.
- `main_menu` stays true on screens opened from the main menu (for example
  `preferences`). To show something only on the main menu itself, test
  `renpy.get_screen("main_menu") is not None`.
- The game's own Ren'Py can parse the Arabic `.rpy` files without launching the
  game; that checks syntax only, not rendering.

## Optional runtime filter

A game-specific text filter may substitute approved translations or collect
unseen strings only after explicit approval. It must call any previous filter,
catch its own failures, write only within its own data directory, use no live
machine translation, and uninstall cleanly. Write it independently; do not copy
an implementation from a proprietary application.

## Acceptance

1. Generated/native translation loads without changing game logic.
2. Interpolation and text tags match exactly.
3. Save/load, history, menus, and dialogue continue to work.
4. Arabic joining, ordering, mixed text, and line wrapping pass in-game.

## Adapter

`adapters/renpy.py` reads and writes the native `game/tl/<language>/` files
that Ren'Py's **Generate Translations** creates: dialogue blocks and the
`strings` block. It never edits the original scripts, so translation IDs always
come from Ren'Py. It passes the adapter contract on the synthetic
`examples/renpy-reference` game only; run the contract on each real game's
generated files before bulk translation. Unsupported constructs (multi-line or
single-quoted strings) fail with the file and line.

## Tools

Catalog tools: `unrpyc`, `rpatool`. Details (license, source, note, whether
already present): `python scripts/tool_doctor.py --engine renpy`. Install rules: step 4 of
`game-localization-engineering`.

Use the Ren'Py SDK and native translation generator first; use `unrpyc` or
`rpatool` only for lawful inspection and a tested copy.

## Workflow

Generate a small translation, run lint, rebuild, and verify dialogue, menus,
save/load, tags, and Arabic rendering before scaling up.

## Sources

Use the official Ren'Py translation and changelog documentation plus pinned
tool repositories listed in this profile.

Sources: [Ren'Py translation documentation](https://www.renpy.org/doc/html/translation.html),
[Ren'Py Arabic shaping changelog](https://www.renpy.org/doc/html/changelog.html),
[unrpyc](https://github.com/CensoredUsername/unrpyc),
[rpatool](https://github.com/Shizmob/rpatool).
