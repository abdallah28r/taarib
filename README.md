# Taarib

**Localize PC games into natural Arabic with an AI coding agent, when you have the right to.**

Taarib (تعريب, "Arabization") is a project template for
[Claude Code](https://claude.com/claude-code) and OpenAI Codex. It helps an agent
translate and proofread a game's text, display Arabic correctly, and install a patch
you can remove.

**Website:** [Arabic](https://abdallah28r.github.io/taarib/) ·
[English](https://abdallah28r.github.io/taarib/en/)

> Unofficial community project. Not affiliated with, endorsed by, or sponsored by any
> game publisher, engine maker, Anthropic, or OpenAI.

## Who it is for

Use Taarib only if one of these is true:

- You made the game.
- The game's own language files or documented mod system support the work, and its
  license allows it.
- The rights holder gave you written permission.

Owning a copy of a game is not enough. Online games are not supported.

## What you get

- **Translation you can check:** separate translator and proofreader roles, a
  shared glossary, and checks for placeholders and markup.
- **Arabic display:** right-to-left order, joined letters, and line wrapping fitted to
  the game's text boxes.
- **Backups:** game files are backed up before they change, and the patch can be
  removed.
- **Pages that show the work:** progress, tasks, and every line and image before and
  after.
- **Notes on common engines:** see [`engines/`](engines/).

Arabic display differs between games, so confirm the result in the game yourself.

## Requirements

- Windows (main target)
- [Python 3](https://www.python.org/downloads/) (tested with 3.13)
- [Git](https://git-scm.com/downloads)
- Claude Code or Codex, with an active subscription
- A game you have the right to localize

## Install

1. Open a terminal in the folder where you keep your projects, then download the
   template:

   ```bash
   git clone https://github.com/abdallah28r/taarib.git
   ```

2. Install the Python packages:

   ```bash
   cd taarib
   pip install -r requirements.txt
   ```

3. Make one copy of the `taarib` folder for each game, and name the copy after the
   game. Keep the original clean.

## Use

1. Open the game's copy as your project folder in Claude Code or Codex.
2. Say **"localize the game"** or **«عرّب اللعبة»**.
3. Answer the agent's first questions, including your right to localize the game.
4. Check the pilot when asked. This is a short test of Arabic inside the game.
5. Play the game when asked for the final test.

Open `dashboard.html` at any time to see progress.

## What is sent to AI services

Your AI tool sends the game text it works on to its provider (Anthropic or OpenAI),
under your account and their terms. If you include images, those images are also
sent to OpenAI through Codex for editing, but only if you answer yes when asked. Do
not use this template on material you are not allowed to send.

Taarib itself has no server and collects nothing. Sharing your project's lessons
with the developer is optional and manual.

## Legal use

- You are responsible for following the game's license (EULA), the store's terms, the
  terms of your AI provider, and the laws of your country.
- Translating a game and sharing the translation can need permission from its
  copyright owner. Taarib will not build a shareable package until you record that
  permission and a content review. This record is a reminder, not legal clearance.
- Never share game files, extracted game text, game art, or fonts you have no right
  to share.
- Taarib does not bypass DRM, anti-cheat, signatures, or other access controls, decrypt
  game data, decompile games, or add code to them, except inside a game's own
  documented mod system. Its protection check reads file names only and can miss
  protection.
- AI output can be wrong. Taarib is provided without warranty, so keep your own
  backups. This page is not legal advice.

## Rights holders

If you believe something here infringes your rights, open an issue in this repository
or contact [@abdallah28r](https://x.com/abdallah28r) on X. Include the file and what
you own. You can also use
[GitHub's DMCA process](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy).

## Development

```bash
python -m unittest discover -s tests
python scripts/verify_template.py
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md),
[`LEGAL_POLICY.md`](LEGAL_POLICY.md), and [`references/scripts.md`](references/scripts.md).

## License

[MIT](LICENSE), **except** the documents adapted from the *Arabic Game Localization
Playbook*, which stay under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
See [`NOTICE.md`](NOTICE.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Acknowledgments

[Arabic Game Localization Playbook](https://github.com/Xxdm234/Arabic-Game-Localization-Playbook)
by MXIAUDIO and contributors, whose guides and font and patch tools are adapted here.
Thanks also to [asgore-undertale](https://github.com/asgore-undertale) and
[Arabic / Persian Text Shaper](https://github.com/KKING-ar/Arabic-Reshaper) by Ai Haka
for ideas.

## Feedback

Run `python scripts/loc.py experiences` to pack your project's lessons. Read the file
first and remove any game text. Then send it privately to
[@abdallah28r](https://x.com/abdallah28r) on X. Do not post it publicly.
