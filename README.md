# Taarib — Arabic game localization with AI agents

**Taarib** (تعريب, "Arabization") is a project template that lets an AI coding
agent — [Claude Code](https://claude.com/claude-code), OpenAI Codex, or both —
localize a PC game into natural Modern Standard Arabic, from finding the text
to a removable patch you install on your own copy.

The agent does the work; the template keeps it honest. Phases advance only when
a script re-checks the files, every translated line is proofread before it can
enter the game, every game file is backed up before it changes, and progress is
counted from the data, never from the agent's own summary.

> **Status:** working, tested on real games, and still evolving. Arabic text
> rendering differs between engines; expect to confirm the result in the game
> yourself.

## What it does

- **Finds and extracts the text** through per-engine adapters with contract
  tests, into one JSONL unit per string (`units/`).
- **Translates and proofreads** in batches with separate translator and
  proofreader roles, a shared glossary (`glossary.yaml`) with character voices
  and gender variants, and placeholder, markup and terminology checks.
- **Renders Arabic correctly** for each engine: text the engine shapes itself
  stays logical Unicode; for engines that cannot, the template pre-shapes it,
  orders it for right-to-left display, and wraps lines to the real box width
  measured from the game's font (`scripts/arabic_shaping.py`).
- **Checks the game without opening it** — `loc.py probe` detects the engine,
  reads which fonts carry Arabic letters (including fonts inside Unity assets),
  draws a preview of real lines, and reads the game's log after a launch to say
  whether it booted, crashed, or lacked Arabic glyphs.
- **Installs reversibly**: backups first, a patch on your copy, a single
  playtest by you, small fixes, then a portable patch package with an
  uninstaller.
- **Localizes baked text in images** when you ask for it, region by region,
  with every candidate reviewed visually.
- **Shows you the work**: `dashboard.html` (progress, phase, gates),
  `tasks.html` (the agent's task board), `texts.html` (every line before and
  after, with search) and `images.html` (each image before and after, every
  version tried, spoilers blurred until clicked). The last two hold the game's
  own text and art, so they stay on your computer and are never committed.
- **Learns**: engine profiles in `engines/` keep what was found for the next game
  on that engine, and each project can send its lessons back to the template.

## Supported engines

Profiles with known paths, tools and pitfalls exist for:

Unity · Unreal · Godot · Ren'Py · RPG Maker · GameMaker · MonoGame/XNA ·
Source · Paradox (Clausewitz) · Bannerlord · RimWorld · Stardew Valley ·
Age of Empires II · Telltale · SCUMM/ScummVM · GrimE/EMI · Dinky · Danganronpa ·
Android APK · PS1 · PS2 · other proprietary PC engines.

An engine that is not listed is not a dead end: the agent inspects its files,
adds detection markers to `config/engine-markers.json`, and starts a new profile.
A full Ren'Py adapter ships in `adapters/`; for other engines the agent writes
the adapter for your game and must pass `scripts/adapter_contract.py` on the
real build before bulk translation.

## Requirements

- **Python 3** (developed and tested with Python 3.13 on Windows, the main
  target; log and save locations in the engine profiles are Windows paths).
- Claude Code, Codex, or both, with an active subscription.
- A legally owned copy of the game.
- Python packages: `pip install -r requirements.txt` (fontTools, Pillow, PyYAML).
  Engine-specific tools are installed only when needed, pinned, into `.tools/`.

## Quick start

1. **Copy** this repository's folder once per game and name the copy after the
   game (for example `Station`). Keep the original clean.

   ```bash
   git clone https://github.com/abdallah28r/taarib.git
   ```

2. **Install** the Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. **Open the copy** as the project folder in Claude Code (`claude`) or Codex
   (`codex`). The folder must be the one that directly contains `AGENTS.md`.
4. **Say** «عرّب اللعبة» (or "localize the game"). The agent asks one grouped set
   of questions — the game's name and where it is installed, whether images are
   in scope, whether it may launch the game, and how its helper agents should
   work — then works on its own.
5. **You are asked twice more**: once to look at a pilot (Arabic shown in the
   game before bulk translation), and once for the final playtest.

Open `template-map.html` (the template map, in Arabic) for the full picture of
what you do and what the agent does, and `dashboard.html` for live progress.

## How it works

```text
intake → discovery → extraction → pilot → localization → integration → playtest → handoff → release
```

Each phase ends at a gate: `python scripts/loc.py gate` re-checks the files and
refuses to advance while anything is missing. `python scripts/loc.py next`
always prints where the project stands and the next action, so any session —
or the other runtime — can resume.

| Part | Where |
| --- | --- |
| Agent rules (shared by Claude Code and Codex) | `AGENTS.md` (`CLAUDE.md` imports it) |
| Skills and roles | `.agents/skills/`, `.agents/roles/` → generated into `.claude/` |
| Main command line | `scripts/loc.py` — every command in `references/translation-units.md` |
| Every script and when to use it | `references/scripts.md` |
| Engine knowledge | `engines/<engine>.md` |
| Tool catalog | `tools/open-source-tools.json` |
| Plan, state, progress | `PLAN.md`, `state/`, `dashboard.html` |

## Safety and legal use

- Discovery is read-only. No game file changes before a backup exists, and the
  Claude Code hooks block writes that skip it.
- The agent never launches the game, uploads data, or contacts an external AI
  service without the permission recorded in `PROJECT.yaml`.
- DRM, anti-cheat, signatures and access controls are never bypassed.
  Decrypting a game's own archives or injecting code needs your explicit,
  per-game approval after a warning, is never used for online or anti-cheat
  games, and nothing decrypted may be redistributed
  (`references/extraction-integration.md`).
- Only patches are shared: never game files, extracted game text, or
  proprietary fonts. Check the game's license and your local law before you
  publish a patch.
- `LEGAL_AND_CLEAN_ROOM_POLICY.md` governs research on other tools: ideas only,
  no copied code. See `SECURITY.md` for reporting a vulnerability.

## Development

```bash
python -m unittest discover -s tests
python scripts/verify_template.py
```

Edit skills only in `.agents/skills/` and roles in `.agents/roles/`, then run
`python scripts/sync_runtime.py`. See `CONTRIBUTING.md` and `CHANGELOG.md`.

## License

The template is released under the [MIT License](LICENSE), **except** the
documents adapted from the *Arabic Game Localization Playbook*, which remain
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/):
`references/rendering-lessons.md`, part of `references/extraction-integration.md`,
nine engine profiles in `engines/`, and the "Lessons from …" sections of three
others. The exact list and attributions are in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Acknowledgments

- [Arabic Game Localization Playbook](https://github.com/Xxdm234/Arabic-Game-Localization-Playbook)
  by MXIAUDIO and contributors — engine guides and font/patch tools adapted here.
- [asgore-undertale](https://github.com/asgore-undertale) (Asgore Studio,
  RenovArabi, ATCEE) and [Arabic / Persian Text Shaper](https://github.com/KKING-ar/Arabic-Reshaper)
  by Ai Haka — ideas for fitting Arabic text to a box, diacritics, and rich-text
  tags.
- The Miqbas and FLTAH applications — ideas from their observed behaviour only.

## Feedback

Each project can pack its lessons with `python scripts/loc.py experiences`.
Send the file to the Hoshibana Discord server (https://discord.gg/NwhYY4YJTY)
or to [@abdallah28r](https://x.com/abdallah28r) on X.
