# Godot engine profile

Evidence state: `documented-external`; verify the exact Godot major version and
whether the project uses CSV, PO/gettext, or custom resources.

## Identification

Look for `project.godot`, `.pck`, `.tscn`, `.tres`, `translations/`, CSV/PO
translation files, and the project renderer/version. A `.pck` alone does not
prove that all text is stored in a standard translation table.

## Portable resource paths

| Resource | Starting pattern | Evidence and limit |
| --- | --- | --- |
| Project resources | `res://` within source project or packed `.pck` | Root is common; archive layout and resource remaps vary. |
| Translation sources | CSV/PO or translation resources referenced by project settings/scripts | `res://translations/**` is a candidate convention, not a guaranteed path. |
| Images/fonts/audio | Paths referenced by scenes/resources under `res://` | Follow actual references and remaps; record the exact game/build pattern after verification. |

## Tools

Prefer the project's import/export workflow. Use Godot's own translation
importer where source files exist; use a PCK explorer only for lawful copies and
only after a no-change extract/repack proof. Preserve resource paths, keys,
plural forms, comments, and encoding.

## Workflow

1. Record the exact Godot version and renderer.
2. Extract or import a tiny translation sample.
3. Validate CSV/PO structure and protected placeholders.
4. Test logical Arabic, the actual font, mixed numbers, and UI direction.
5. Reimport or build a removable patch and compare the original project hash.

## Limitations

Godot projects vary between CSV, gettext, custom scripts, and packed exports.
Runtime asset remaps can affect localized textures or audio. Do not assume RTL
layout or font fallback without an in-game test.

## Sources

- https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html
- https://docs.godotengine.org/en/stable/tutorials/i18n/localization_using_gettext.html
- https://github.com/DmitriySalnikov/GodotPCKExplorer
