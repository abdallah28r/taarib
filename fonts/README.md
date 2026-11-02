# Project fonts

`selected/` holds **external** font files actually chosen for this game.
`licenses/` holds their exact license/notice copies. Do not place trial fonts
or copied game-shipped fonts here. Record each chosen external **or shipped**
font, its rights and where it is used in `FONT_USAGE.json`; record
any current-user Windows installation separately in `SYSTEM_INSTALLS.json`.
Both registries start empty in a new template. Follow
`references/font-sourcing.md` before obtaining or installing a font.

Font binaries and third-party license files in a game project are not included
in the **public template** archive by default. Review redistribution rights
for each actual game patch before bundling them. The template also ignores
these files in Git by default; keep a project backup and explicitly track or
package a verified selection when its rights permit it.
