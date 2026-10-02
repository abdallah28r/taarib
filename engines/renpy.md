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

## Tools

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
