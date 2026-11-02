# Ren'Py reference game

A tiny original Ren'Py project, written for this template and released under
the template's MIT license. It is the fixed test bed for `adapters/renpy.py`:

```text
python scripts/adapter_contract.py --adapter adapters/renpy.py --game examples/renpy-reference
```

It covers narrator and character dialogue, interpolation (`[player_name]`),
text tags (`{i}`), an escaped quote, menu choices, and a `_()` string.

`game/tl/arabic/script.rpy` was written by hand in the format that Ren'Py's
**Generate Translations** produces. Its translation identifiers are
illustrative: Ren'Py computes them from the script, so before running this game
in Ren'Py, regenerate the `arabic` translation from the Ren'Py launcher and
re-run the adapter on the generated files. In a real game, always start from
the files the Ren'Py SDK generates; the adapter never invents identifiers.
