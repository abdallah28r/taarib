"""Build the taarib website in docs/ (GitHub Pages), in Arabic and English, from one source.

    python docs/_tools/build_site.py

Writes docs/index.html, how-it-works.html, install.html, showcase.html and the same four pages under
docs/en/. Numbers (tools, engine profiles, tests) are counted from the template itself. Screenshots come
from make_demo.py + capture.py; install screenshots live in docs/assets/install/.
Folders starting with "_" are not published by GitHub Pages.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1]
ROOT = DOCS.parent
REPO = "https://github.com/abdallah28r/taarib"
ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons"
FONTS = ("https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800"
         "&family=JetBrains+Mono:wght@400;600&display=swap")


def counts() -> dict:
    catalog = json.loads((ROOT / "tools" / "open-source-tools.json").read_text(encoding="utf-8"))
    tools = catalog.get("tools", catalog)
    profiles = [p for p in (ROOT / "engines").glob("*.md") if p.name not in ("README.md", "ENGINE_PROFILE_TEMPLATE.md")]
    tests = sum(len(re.findall(r"^\s+def test_", p.read_text(encoding="utf-8"), re.M)) for p in (ROOT / "tests").glob("test_*.py"))
    skills = len(list((ROOT / ".agents" / "skills").glob("*/SKILL.md")))
    return {"tools": len(tools), "engines": len(profiles), "tests": tests, "skills": skills}


# (name, Simple Icons slug or None)
ENGINES = [("Unity", "unity"), ("Unreal Engine", "unrealengine"), ("Godot", "godotengine"), ("Ren'Py", "renpy"),
           ("GameMaker", "gamemaker"), ("RPG Maker", None), ("MonoGame / XNA", "monogame"), ("Source", "valve"),
           ("Paradox Clausewitz", "paradoxinteractive"), ("Bannerlord", None), ("RimWorld", None),
           ("Stardew Valley", None), ("Age of Empires II", None), ("Telltale", None), ("SCUMM / ScummVM", None),
           ("GrimE / EMI", None), ("Dinky", None), ("Danganronpa", None), ("Android APK", "android"),
           ("PlayStation 1", "playstation"), ("PlayStation 2", "playstation"), ("Proprietary PC", None)]

# Lucide-style line icons (ISC license), drawn inline.
SVG = {
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "type": '<path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
    "gate": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "terminal": '<path d="m4 17 6-6-6-6"/><path d="M12 19h8"/>',
}


def icon(name: str) -> str:
    return (f'<span class="icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{SVG[name]}</svg></span>')


T = {  # every visible word, per language
    "ar": {
        "dir": "rtl", "other": "en", "other_label": "English", "brand_small": "taarib",
        "nav": [("index", "الرئيسية"), ("how-it-works", "كيف يعمل"), ("install", "الشرح والتثبيت"), ("showcase", "صفحات المتابعة")],
        "skip": "انتقل إلى المحتوى", "github": "المستودع على GitHub",
        "foot": "تعريب — مفتوح المصدر بترخيص MIT. يعمل مع Claude Code وCodex. نص اللعبة وصورها لا يُرفعان أبدًا.",
        "foot_marks": "أسماء المحركات وشعاراتها علامات تجارية لأصحابها، وذكرها هنا للإشارة إلى دعمها فقط.",
        # home
        "home_title": "تعريب — عرّب ألعابك بالذكاء الاصطناعي",
        "hero": "عرّب ألعابك بالذكاء الاصطناعي، دون أن تكسر اللعبة",
        "lead": "قالب مفتوح المصدر يحوّل <bdi>Claude Code</bdi> أو <bdi>Codex</bdi> إلى فريق تعريب كامل: يستكشف اللعبة، "
                "ويستخرج نصوصها، ويترجمها ويدققها، ويعرض العربي صحيحًا داخلها، ثم يسلّمك تعريبًا قابلًا للإزالة.",
        "start": "ابدأ التثبيت",
        "stats": ["أداة مفتوحة المصدر مسجلة", "محركًا لكل منها ملف خبرة", "محطات، وبوابة بعد كل واحدة", "اختبارًا آليًا"],
        "why": "لماذا تعريب؟", "why_sub": "كل ما تحتاجه لتعريب لعبة كاملة، مع ضمانات لا يتجاوزها الوكيل.",
        "features": [
            ("eye", "وكيلك يعمل، وأنت تتابع", "لوحة تقدم ولوحة مهام تتحدثان وحدهما: ما أنجزه الوكيل، وما يعمل عليه، وما ينتظر جوابك."),
            ("type", "عربي سليم داخل اللعبة", "تشكيل الحروف وترتيبها من اليمين لليسار، وتقسيم الأسطر بعرض صندوق اللعبة الحقيقي."),
            ("shield", "لا شيء يُكسر", "نسخة احتياطية قبل أي تعديل، وتثبيت قابل للإزالة، وتجربة أولى تراها بعينك قبل الترجمة الكاملة."),
            ("users", "مترجم ومدقق منفصلان", "كل جملة تُدقق قبل أن تدخل اللعبة، مع مسرد للمصطلحات وأصوات الشخصيات."),
            ("image", "الصور أيضًا", "تعريب النص داخل الصور، مع كل نسخة جُرّبت وسبب قبولها أو رفضها، وإخفاء ما يحرق الأحداث."),
            ("gate", "بوابات لا تُتجاوز", "لا تنتقل المرحلة إلا حين يتحقق الكود من الملفات نفسها، لا من كلام الوكيل."),
        ],
        "runtimes": "يعمل مع <bdi>Claude Code</bdi> و<bdi>Codex</bdi>",
        "runtimes_sub": "اختر أحدهما، أو اجعلهما يعملان معًا على المشروع نفسه.",
        "runtime_cards": [("Claude Code", "وكلاء فرعيون للمترجم والمدقق والباحث ومعرّب الصور، وحراس يمنعون الكتابة في اللعبة قبل النسخ الاحتياطي."),
                          ("Codex", "القواعد نفسها في AGENTS.md، وتعريب الصور عبر أداة الصور المدمجة في Codex.")],
        "engines": "المحركات المدعومة",
        "engines_sub": "لكل محرك ملف خبرة: أين النصوص والخطوط والسجلات، والأدوات المناسبة، والمشكلات المعروفة. "
                       "ومحرك غير مذكور ليس طريقًا مسدودًا: يفحصه الوكيل ويبدأ له ملفًا جديدًا.",
        "proprietary": "محركات PC خاصة",
        "peek": "تابع العمل من صفحاتك", "peek_sub": "أربع صفحات تُبنى من ملفات المشروع وحدها، وتتحدث وأنت تعمل.",
        "pages": [("dashboard", "لوحة التعريب", "المرحلة وشروطها، والتقدم، وما ينتظرك."),
                  ("tasks", "لوحة المهام", "ما ينوي الوكيل فعله، وما يعمل عليه، وما أنجزه بدليل."),
                  ("texts", "النصوص قبل وبعد", "كل جملة بجانب أصلها، مع بحث وملاحظات المدقق."),
                  ("images", "الصور قبل وبعد", "كل صورة بنسخها المجرّبة، وما يحرق الأحداث مخفي.")],
        "more": "شاهد الصفحات كاملة",
        # how it works
        "how_title": "كيف يعمل تعريب", "how_h1": "كيف يعمل من الداخل: تسع محطات وبوابة بعد كل واحدة",
        "how_lead": "يمر كل مشروع بالمحطات نفسها. في نهاية كل محطة بوابة يفحصها الكود من الملفات، ولا تُفتح حتى تتحقق كل شروطها.",
        "toc": "المحطات", "who": "من يعمل", "in": "يدخل", "out": "يخرج", "does": "ماذا يفعل", "doesnt": "ما لا يفعله أبدًا",
        "gate": "البوابة: لا تُفتح حتى",
        # install
        "inst_title": "الشرح والتثبيت", "inst_h1": "الشرح والتثبيت",
        "inst_lead": "من مجلد فارغ إلى أول طلب تعريب في دقائق. تحتاج نسخة أصلية من اللعبة، و<bdi>Git</bdi>، و<bdi>Python 3</bdi>، و<bdi>Claude Code</bdi> أو <bdi>Codex</bdi>.",
        "inst_toc": [("need", "ما تحتاجه"), ("get", "تنزيل القالب"), ("rename", "مجلد لكل لعبة"), ("runtime", "افتحه في وكيلك"),
                     ("codex", "في Codex"), ("claude", "في Claude Code"), ("ask", "اطلب التعريب"), ("next", "ماذا يحدث بعدها")],
        "need": ["نسخة أصلية من اللعبة على جهازك.", "<bdi>Git</bdi> و<bdi>Python 3</bdi>، مع المكتبات: <bdi><code>pip install -r requirements.txt</code></bdi>",
                 "اشتراك في <bdi>Claude Code</bdi> أو <bdi>Codex</bdi>، أو كليهما."],
        "get_text": "اختر مجلدًا على جهازك لتنزيل القالب، مثل مجلد باسم <bdi>Arabic Game</bdi>. افتح الطرفية داخله وشغّل:",
        "rename_text": "سيظهر مجلد باسم <bdi>taarib</bdi>. غيّر اسمه إلى اسم اللعبة التي تريد تعريبها، مثل <bdi>Cyberpunk 2077</bdi>. "
                       "لكل لعبة نسخة مستقلة من القالب؛ واحتفظ بالأصل نظيفًا إن أردت تعريب ألعاب أخرى.",
        "runtime_text": "افتح الوكيل الذي ستعرّب به، ثم اتبع قسمه:",
        "codex_steps": [("افتح محادثة جديدة، واختر «New project» لإنشاء مشروع جديد.", "codex-1-new-project.png"),
                        ("أضف مسار المجلد الذي غيّرت اسمه (في هذا المثال <bdi>Cyberpunk 2077</bdi>، وكان اسمه <bdi>taarib</bdi>)، واختر اسمًا للمشروع مثل «تعريب Cyberpunk 2077».", "codex-2-create-project.png"),
                        ("تأكد أن المجلد هو المجلد المضاف، ثم اضغط «Create project».", "codex-3-project-folder.png"),
                        ("افتح محادثة جديدة داخل المشروع واكتب طلب التعريب.", "codex-4-request.png")],
        "claude_steps": [("افتح محادثة جديدة في Claude Code، واضغط «Choose…» واختر المجلد الذي غيّرت اسمه (في هذا المثال <bdi>Cyberpunk 2077</bdi>).", "claude-1-choose-folder.png")],
        "claude_soon": "صور بقية خطوات Claude Code تُضاف قريبًا.",
        "ask_text": "اكتب «عرّب اللعبة». يسألك الوكيل مجموعة أسئلة واحدة في البداية: اسم اللعبة ومكانها، وهل الصور ضمن التعريب، "
                    "وهل يشغّل اللعبة بنفسه، وكيف يعمل وكلاؤه الفرعيون. بعدها يعمل وحده.",
        "next_items": ["يسألك مرة ليريك تجربة أولى: القائمة الرئيسية وأول مشهد بالعربية داخل لعبتك.",
                       "ويسألك مرة أخيرة لتجرّب النسخة كاملة وتقبلها.",
                       "وبينهما تتابع كل شيء من <a href=\"showcase.html\">صفحات المتابعة</a> في مجلد اللعبة."],
        "step": "الخطوة",
        # showcase
        "show_title": "صفحات المتابعة", "show_h1": "صفحات المتابعة",
        "show_lead": "هذه لقطات حقيقية لصفحات القالب، ببيانات لعبة خيالية اسمها «Station Kepler»، لا نص ولا صورة فيها من لعبة حقيقية.",
        "shots": [("dashboard", "لوحة التعريب <bdi>dashboard.html</bdi>", "ما ينتظرك في الأعلى، ثم المرحلة وشروط بوابتها، وآخر الأحداث، وآخر فحص للعبة، والتقدم، وجودة التدقيق، والخطة."),
                  ("tasks", "لوحة المهام <bdi>tasks.html</bdi>", "أعمدة مثل Trello: لاحقًا، التالي، قيد العمل، بانتظارك، للتحقق، منجزة. لكل بطاقة مراحلها بالتواريخ، ولا تُغلق مهمة دون دليل."),
                  ("texts", "النصوص قبل وبعد <bdi>texts.html</bdi>", "كل جملة بترجمتها، وحالتها، ومتحدثها، ومشكلات الفحص، وملاحظات المدقق، مع بحث وتصفية."),
                  ("images", "الصور قبل وبعد <bdi>images.html</bdi>", "الأصل والمعرّبة مع شريط مقارنة، وكل نسخة جُرّبت بحكمها وسببه. الصورة التي تحرق الأحداث ضبابية حتى تضغط عليها.")],
        "local": "صفحتا النصوص والصور تبقيان على جهازك ولا تُرفعان أبدًا، لأن فيهما محتوى اللعبة.",
        "zoom": "اضغط على الصورة لفتحها بحجمها الكامل.",
    },
    "en": {
        "dir": "ltr", "other": "ar", "other_label": "العربية", "brand_small": "تعريب",
        "nav": [("index", "Home"), ("how-it-works", "How it works"), ("install", "Install guide"), ("showcase", "Follow-up pages")],
        "skip": "Skip to content", "github": "GitHub repository",
        "foot": "Taarib — open source under the MIT License. Works with Claude Code and Codex. A game's text and art are never uploaded.",
        "foot_marks": "Engine names and logos are trademarks of their owners, shown only to name what is supported.",
        "home_title": "Taarib — Arabic game localization with AI agents",
        "hero": "Localize games into Arabic with AI agents, without breaking the game",
        "lead": "An open-source template that turns Claude Code or Codex into a full localization team: it explores the game, "
                "extracts its text, translates and proofreads it, renders Arabic correctly in the game, and hands you a removable patch.",
        "start": "Start installing",
        "stats": ["open-source tools catalogued", "engines with their own profile", "stations, with a gate after each", "automated tests"],
        "why": "Why Taarib?", "why_sub": "Everything a full game localization needs, with guarantees the agent cannot skip.",
        "features": [
            ("eye", "The agent works, you follow", "A progress page and a task board that update themselves: what is done, in progress, and waiting for you."),
            ("type", "Correct Arabic in the game", "Joined letters in right-to-left order, and lines wrapped to the game's real box width."),
            ("shield", "Nothing breaks", "A backup before every change, a removable install, and a pilot you check before the bulk translation."),
            ("users", "Separate translator and proofreader", "Every line is proofread before it enters the game, with a glossary of terms and character voices."),
            ("image", "Images too", "Text baked into images, with every version tried and why it was kept or rejected; spoilers stay blurred."),
            ("gate", "Gates that cannot be skipped", "A phase advances only when code re-checks the files themselves, never on the agent's word."),
        ],
        "runtimes": "Works with Claude Code and Codex", "runtimes_sub": "Pick one, or let both work on the same project.",
        "runtime_cards": [("Claude Code", "Subagents for translator, proofreader, researcher and image localizer, and hooks that block game writes before a backup."),
                          ("Codex", "The same rules in AGENTS.md, and image localization through Codex's built-in image tool.")],
        "engines": "Supported engines",
        "engines_sub": "Each engine has a profile: where the text, fonts and logs are, which tools fit, and known pitfalls. "
                       "An engine that is not listed is not a dead end: the agent inspects it and starts a new profile.",
        "proprietary": "Proprietary PC engines",
        "peek": "Follow the work from your pages", "peek_sub": "Four pages built from the project's files alone, updating while it works.",
        "pages": [("dashboard", "Dashboard", "The phase and its gate, progress, and what waits for you."),
                  ("tasks", "Task board", "What the agent plans, is doing, and has done, with evidence."),
                  ("texts", "Text before and after", "Every line beside its source, with search and proofreading notes."),
                  ("images", "Images before and after", "Every image with the versions tried; spoilers hidden.")],
        "more": "See the full pages",
        "how_title": "How Taarib works", "how_h1": "How it works inside: nine stations, a gate after each",
        "how_lead": "Every project passes the same stations. Each ends at a gate that code checks against the files, and it opens only when all its conditions hold.",
        "toc": "Stations", "who": "Who works", "in": "In", "out": "Out", "does": "What it does", "doesnt": "What it never does",
        "gate": "The gate opens only when",
        "inst_title": "Install guide", "inst_h1": "Install guide",
        "inst_lead": "From an empty folder to your first localization request in minutes. You need your own copy of the game, Git, Python 3, and Claude Code or Codex.",
        "inst_toc": [("need", "What you need"), ("get", "Get the template"), ("rename", "One folder per game"), ("runtime", "Open it in your agent"),
                     ("codex", "In Codex"), ("claude", "In Claude Code"), ("ask", "Ask for the localization"), ("next", "What happens next")],
        "need": ["Your own copy of the game.", "Git and Python 3 (with the packages: <code>pip install -r requirements.txt</code>).",
                 "A Claude Code or Codex subscription, or both."],
        "get_text": "Choose a folder for the template, for example one named <bdi>Arabic Game</bdi>. Open a terminal inside it and run:",
        "rename_text": "A folder named <bdi>taarib</bdi> appears. Rename it after the game you are localizing, for example <bdi>Cyberpunk 2077</bdi>. "
                       "Each game gets its own copy of the template; keep a clean original for other games.",
        "runtime_text": "Open the agent you will localize with, then follow its section:",
        "codex_steps": [("Open a new chat and choose “New project”.", "codex-1-new-project.png"),
                        ("Add the folder you renamed (here <bdi>Cyberpunk 2077</bdi>, formerly <bdi>taarib</bdi>) and name the project, for example “Localize Cyberpunk 2077”.", "codex-2-create-project.png"),
                        ("Check that the folder is the one you added, then press “Create project”.", "codex-3-project-folder.png"),
                        ("Open a new chat inside the project and type your localization request.", "codex-4-request.png")],
        "claude_steps": [("Open a new chat in Claude Code, press “Choose…” and pick the folder you renamed (here <bdi>Cyberpunk 2077</bdi>).", "claude-1-choose-folder.png")],
        "claude_soon": "Screenshots for the remaining Claude Code steps are coming soon.",
        "ask_text": "Type «عرّب اللعبة» (localize the game). The agent asks one set of questions at the start: the game's name and location, "
                    "whether images are in scope, whether it may launch the game, and how its subagents should work. Then it works on its own.",
        "next_items": ["It asks you once to check a pilot: the main menu and first scene in Arabic, in your game.",
                       "And once more at the end, to play the full localization and accept it.",
                       "In between, follow everything from the <a href=\"showcase.html\">follow-up pages</a> in the game's folder."],
        "step": "Step",
        "show_title": "Follow-up pages", "show_h1": "Follow-up pages",
        "show_lead": "Real screenshots of the template's pages, with data from an invented game, “Station Kepler”: no text or art from a real game.",
        "shots": [("dashboard", "Dashboard <bdi>dashboard.html</bdi>", "What waits for you on top, then the phase and its gate, recent events, the last game probe, progress, proofreading quality, and the plan."),
                  ("tasks", "Task board <bdi>tasks.html</bdi>", "Trello-like columns: later, next, doing, waiting on you, verify, done. Each card keeps its dated history, and no task closes without evidence."),
                  ("texts", "Text before and after <bdi>texts.html</bdi>", "Every line with its translation, status, speaker, problem codes and proofreading notes, with search and filters."),
                  ("images", "Images before and after <bdi>images.html</bdi>", "Source and localized image with a comparison slider, and every version tried with its verdict. Spoilers stay blurred until clicked.")],
        "local": "The text and image pages stay on your computer and are never uploaded, because they hold the game's content.",
        "zoom": "Tap the image to open it full size.",
    },
}

STATIONS_EN = [
    {"name": "Start: the project questions", "who": "Main agent + you", "input": "«localize the game» and your answers",
     "output": "The game's name, location and your permissions, saved",
     "does": ["Starts the questions as soon as you ask, without “what do you mean?”", "Suggests the folder's name as the game's name",
              "Takes the game's location from you, or finds it and shows it for you to confirm", "Saves the answers for every later session"],
     "doesnt": ["Never touches the game's files", "Never repeats the questions in later sessions", "Never takes “ask me” as a yes"]},
    {"name": "Discovery", "who": "Main agent, with the researcher", "input": "The game folder (read only)",
     "output": "The engine, how Arabic is drawn, and the right adapter",
     "does": ["Identifies the engine and its version", "Looks for existing Arabic tools and mods for this game",
              "Decides: does the engine draw Arabic itself, or does it need pre-shaped text?"],
     "doesnt": ["Never changes a game file", "Never bypasses protection or anti-cheat; decrypting archives or injecting code only with your per-game permission after a warning",
                "Never installs a tool without recording its source and license"]},
    {"name": "Extraction", "who": "Main agent", "input": "The game's files and the adapter", "output": "Every line of the game, and the batch plan",
     "does": ["Pulls every line of the game into the unit records", "Tests the adapter with eight checks: extract and write back without breaking anything",
              "Splits the work into batches and writes them in the plan"],
     "doesnt": ["Translates nothing", "Never writes into the game folder", "Never continues if any of the eight checks fails"]},
    {"name": "Pilot: is the Arabic right?", "who": "Main agent, then you", "input": "Main menu, settings and the first scene",
     "output": "Arabic showing in your game, and your confirmation recorded",
     "does": ["Localizes a small batch that deliberately includes a mixed line with numbers or English names, and the longest option",
              "Proofreads, builds and installs it on your copy after backing it up", "Asks you for a short check and a screenshot of any problem",
              "Fixes the rendering (font, joining, direction, clipping) and reinstalls until it is right"],
     "doesnt": ["Never localizes the rest before you confirm", "Never fixes rendering by reversing the stored letters", "Never records your confirmation on its own"]},
    {"name": "Translation and proofreading", "who": "Translator, then a different proofreader (or the same one if you chose so)",
     "input": "A batch of lines + the glossary", "output": "Translated, proofread lines, and batches ticked ☑",
     "does": ["Prepares a small brief per batch: the lines, their context and their terms", "The translator translates the batch",
              "Another agent proofreads it and records notes and a quality score", "Localizes image text when it is in scope"],
     "doesnt": ["The translator never proofreads its own work, unless you chose “same model”", "Never breaks code such as {name} or [key]",
                "Never departs from the glossary", "Never touches the game's files"]},
    {"name": "Build and install", "who": "Main agent", "input": "The proofread lines", "output": "The game's files in Arabic, and a backup of the originals",
     "does": ["Builds the Arabic files from proofread lines only", "Backs up every original file before replacing it", "Always installs on your copy of the game",
              "Picks a licensed Arabic font when the engine needs one"],
     "doesnt": ["Never ships an unproofread line", "Never overwrites a file without a backup (a Claude Code hook blocks it)",
                "Never installs when unsure which copy of the game is yours"]},
    {"name": "Your playtest", "who": "You, then the main agent for fixes", "input": "The Arabic build + your reports",
     "output": "Closed fixes, and your acceptance recorded",
     "does": ["Turns each small report into a “fix”: what happens, what should happen, and what must not change",
              "Re-proofreads what was fixed and rebuilds", "Logs bigger defects in the QA matrix"],
     "doesnt": ["Never records your acceptance on its own", "Never closes a fix as verified without evidence, or if anything outside it changed",
                "Never reopens a whole phase for a small problem"]},
    {"name": "Handoff: the experiences file", "who": "Main agent, then you", "input": "Lessons recorded during the work + project facts",
     "output": "An experiences-…zip file and where to send it",
     "does": ["Collects the lessons the agent recorded when it found them: template bugs, limits, engine notes, tools",
              "Adds what the code knows: the engine, the adapter check, fixes and results, reopened phases, the most frequent problems",
              "Includes the engine profile, the adapter and reusable scripts", "Tells you where to send it"],
     "doesnt": ["Never includes the game's text or files", "Never leaves your paths, user name or any secret", "Never sends the file itself"]},
    {"name": "Release (optional)", "who": "Main agent, only on request", "input": "The accepted build", "output": "A shareable localization package",
     "does": ["Prepares an install and uninstall package", "Checks licenses and what may be shared",
              "Explains any install failure in one sentence: a file in use, antivirus, disk space, or a different game version"],
     "doesnt": ["Never publishes anything without your request", "Never includes protected original game files or anything decrypted"]},
]
GATES_EN = [
    ["The game's name is written", "The game's folder really exists", "The images and launch questions are answered yes or no",
     "The runtime (Codex, Claude Code or both) and subscription are set", "The subagent mode and review mode are set"],
    ["The engine is identified", "The adapter file exists", "The adapter declares: the engine draws Arabic itself, or it needs pre-shaping",
     "Its work is on the task board, with no task left open"],
    ["The adapter contract passed on the current adapter and the current game text", "Units exist and validate without errors",
     "Every batch is written in the plan", "With images in scope: text images are inventoried, or “no images” is recorded",
     "Its work is on the task board, with no task left open"],
    ["The pilot batch is defined", "Translated, proofread and installed in the game", "Your confirmation is recorded",
     "Its work is on the task board, with no task left open"],
    ["Every translatable line is proofread", "No line waits for a decision", "No error-level problems: glossary, codes, forbidden forms",
     "Every batch in the plan is ticked ☑", "With separate review: nobody proofread their own translation",
     "Every localized image: a passing record, an accepted version with its reason, and a spoiler decision",
     "Its work is on the task board, with no task left open"],
    ["Every line is built into a release", "Units validate without errors", "Its work is on the task board, with no task left open"],
    ["No open critical defects", "No open fixes", "Your acceptance is recorded in your words", "Its work is on the task board, with no task left open"],
    ["The experiences file was built after your acceptance and handed to you"],
    None,
]


def stations_ar() -> list[dict]:
    """The nine stations as the template map shows them (template-map.html), so the site never drifts from it."""
    page = (ROOT / "template-map.html").read_text(encoding="utf-8")
    block = page[page.index("const STATIONS = ["):page.index("];", page.index("const STATIONS = ["))]
    stations = []
    for chunk in re.split(r"\{ (?:optional: true, )?name: ", block)[1:]:
        def value(key):
            match = re.search(rf'\b{key}: "((?:[^"\\]|\\.)*)"', chunk)
            return match.group(1) if match else ""

        def items(key):
            match = re.search(rf"\b{key}: \[(.*?)\]", chunk, re.S)
            return re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1)) if match else None
        stations.append({"name": re.match(r'"((?:[^"\\]|\\.)*)"', chunk).group(1), "who": value("who"),
                         "input": value("input"), "output": value("output"), "does": items("does") or [],
                         "doesnt": items("doesnt") or [], "gate": items("gate")})
    return stations


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def layout(lang: str, slug: str, title: str, body: str, description: str) -> str:
    t, prefix = T[lang], ("" if lang == "ar" else "../")
    other = f"{'en/' if lang == 'ar' else '../'}{slug}.html"
    nav = "".join(f'<a href="{s}.html"{" aria-current=\"page\"" if s == slug else ""}>{label}</a>' for s, label in t["nav"])
    return f"""<!doctype html>
<html lang="{lang}" dir="{t['dir']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="alternate" hreflang="{t['other']}" href="{other}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="{prefix}assets/site.css">
</head>
<body>
<a class="skip" href="#main">{t['skip']}</a>
<header class="site-head"><div class="wrap">
<a class="brand" href="index.html">{'تعريب' if lang == 'ar' else 'Taarib'} <small>{t['brand_small']}</small></a>
<nav class="site-nav" aria-label="{'الأقسام' if lang == 'ar' else 'Sections'}">{nav}<a href="{REPO}">GitHub</a><a class="lang" href="{other}" hreflang="{t['other']}" lang="{t['other']}">{t['other_label']}</a></nav>
</div></header>
<main id="main">
{body}
</main>
<footer class="site-foot"><div class="wrap"><span>{t['foot']}</span><span>{t['foot_marks']}</span></div></footer>
</body>
</html>
"""


def home(lang: str, n: dict) -> str:
    t, prefix = T[lang], ("" if lang == "ar" else "../")
    numbers = [n["tools"], n["engines"], 9, n["tests"]]
    stats = "".join(f'<div class="stat"><b>{v}</b><span>{label}</span></div>' for v, label in zip(numbers, t["stats"]))
    feats = "".join(f'<article class="card">{icon(i)}<h3>{h}</h3><p>{p}</p></article>' for i, h, p in t["features"])
    runtimes = "".join(f'<article class="card">{icon("terminal")}<h3><bdi>{h}</bdi></h3><p>{p}</p></article>' for h, p in t["runtime_cards"])
    engines = []
    for name, slug in ENGINES:
        label = t["proprietary"] if name == "Proprietary PC" else name
        mark = (f'<img src="{ICONS}/{slug}.svg" alt="" width="30" height="30" loading="lazy">' if slug else
                f'<span class="mono" aria-hidden="true">{"PC" if name == "Proprietary PC" else "".join(w[0] for w in name.replace("/", " ").split()[:2]).upper()}</span>')
        engines.append(f'<li>{mark}<span><bdi>{esc(label)}</bdi></span></li>')
    shots = "".join(f'<a class="shot" href="showcase.html#{s}"><div class="frame"><img src="{prefix}assets/screens/{s}.png" alt="{esc(h)}" '
                    f'loading="lazy"></div><div class="txt"><h3>{h}</h3><p>{p}</p></div></a>' for s, h, p in t["pages"])
    body = f"""<div class="wrap">
<section class="hero"><h1>{t['hero']}</h1><p class="lead">{t['lead']}</p>
<div class="cta"><a class="btn primary" href="install.html">{t['start']}</a><a class="btn ghost" href="{REPO}">{t['github']}</a></div>
<div class="cmd">git clone {REPO}.git</div></section>
<div class="stats">{stats}</div>
<section class="block"><h2>{t['why']}</h2><p class="sub">{t['why_sub']}</p><div class="grid">{feats}</div></section>
<section class="block"><h2>{t['runtimes']}</h2><p class="sub">{t['runtimes_sub']}</p><div class="runtimes">{runtimes}</div></section>
<section class="block"><h2>{t['engines']}</h2><p class="sub">{t['engines_sub']}</p><ul class="engines">{''.join(engines)}</ul>
<p class="note">{t['foot_marks']}</p></section>
<section class="block"><h2>{t['peek']}</h2><p class="sub">{t['peek_sub']}</p><div class="shots">{shots}</div>
<div class="cta"><a class="btn ghost" href="showcase.html">{t['more']}</a></div></section>
</div>"""
    return layout(lang, "index", t["home_title"], body, re.sub("<[^>]+>", "", t["lead"]))


def how(lang: str) -> str:
    t = T[lang]
    stations = stations_ar() if lang == "ar" else [dict(s, gate=g) for s, g in zip(STATIONS_EN, GATES_EN)]
    toc = "".join(f'<li><a href="#s{i}">{i}. {esc(s["name"])}</a></li>' for i, s in enumerate(stations, 1))
    parts = []
    for i, s in enumerate(stations, 1):
        does = "".join(f"<li>{esc(x)}</li>" for x in s["does"])
        doesnt = "".join(f"<li>{esc(x)}</li>" for x in s["doesnt"])
        parts.append(f"""<section class="station" id="s{i}"><header><span class="num">{i}</span><div><h2>{esc(s['name'])}</h2>
<p class="who">{t['who']}: {esc(s['who'])}</p></div></header>
<div class="io"><div><b>{t['in']}</b>{esc(s['input'])}</div><span class="arrow" aria-hidden="true">{'←' if lang == 'ar' else '→'}</span><div><b>{t['out']}</b>{esc(s['output'])}</div></div>
<div class="cols"><div><h3>{t['does']}</h3><ul>{does}</ul></div><div><h3>{t['doesnt']}</h3><ul>{doesnt}</ul></div></div></section>""")
        if s["gate"]:
            parts.append(f'<div class="gate"><h3>{t["gate"]}</h3><ul>{"".join(f"<li>{esc(g)}</li>" for g in s["gate"])}</ul></div>')
        else:
            parts.append('<div style="height:28px"></div>')
    body = f"""<div class="wrap doc"><aside class="toc"><p>{t['toc']}</p><ol>{toc}</ol></aside>
<article><h1>{t['how_h1']}</h1><p class="lead">{t['how_lead']}</p>{''.join(parts)}</article></div>"""
    return layout(lang, "how-it-works", t["how_title"], body, t["how_lead"])


def install(lang: str) -> str:
    t, prefix = T[lang], ("" if lang == "ar" else "../")
    toc = "".join(f'<li><a href="#{a}">{label}</a></li>' for a, label in t["inst_toc"])
    h = dict(t["inst_toc"])

    def steps(items):
        return "<ol class=\"steps\">" + "".join(
            f'<li><p>{text}</p><figure><img src="{prefix}assets/install/{image}" alt="" loading="lazy"></figure></li>'
            for text, image in items) + "</ol>"
    body = f"""<div class="wrap doc"><aside class="toc"><p>{t['inst_h1']}</p><ol>{toc}</ol></aside><article>
<h1>{t['inst_h1']}</h1><p class="lead">{t['inst_lead']}</p>
<h2 id="need">{h['need']}</h2><ul>{''.join(f'<li>{x}</li>' for x in t['need'])}</ul>
<h2 id="get">{h['get']}</h2><p>{t['get_text']}</p><pre class="cmd">git clone {REPO}.git
cd taarib
pip install -r requirements.txt</pre>
<h2 id="rename">{h['rename']}</h2><p>{t['rename_text']}</p>
<h2 id="runtime">{h['runtime']}</h2><p>{t['runtime_text']}</p><div class="tabs"><a href="#codex">Codex</a><a href="#claude">Claude Code</a></div>
<h3 id="codex">{h['codex']}</h3>{steps(t['codex_steps'])}
<h3 id="claude">{h['claude']}</h3>{steps(t['claude_steps'])}<div class="callout soon">{t['claude_soon']}</div>
<h2 id="ask">{h['ask']}</h2><p>{t['ask_text']}</p>
<h2 id="next">{h['next']}</h2><ul>{''.join(f'<li>{x}</li>' for x in t['next_items'])}</ul>
</article></div>"""
    return layout(lang, "install", t["inst_title"], body, t["inst_lead"])


def showcase(lang: str) -> str:
    t, prefix = T[lang], ("" if lang == "ar" else "../")
    figures = "".join(f"""<section class="full" id="{s}"><h2>{h}</h2><p class="sub">{p}</p><figure><div class="viewport">
<a href="{prefix}assets/screens/{s}.png"><img src="{prefix}assets/screens/{s}.png" alt="{esc(re.sub('<[^>]+>', '', h))}" loading="lazy"></a></div>
<figcaption>{t['zoom']}</figcaption></figure></section>""" for s, h, p in t["shots"])
    body = f"""<div class="wrap" style="padding:40px 20px 24px"><h1>{t['show_h1']}</h1><p class="sub">{t['show_lead']}</p>
<div class="callout">{t['local']}</div>{figures}</div>"""
    return layout(lang, "showcase", t["show_title"], body, t["show_lead"])


def main() -> None:
    n = counts()
    for lang in ("ar", "en"):
        folder = DOCS if lang == "ar" else DOCS / "en"
        folder.mkdir(parents=True, exist_ok=True)
        for name, page in (("index", home(lang, n)), ("how-it-works", how(lang)), ("install", install(lang)),
                           ("showcase", showcase(lang))):
            if lang == "ar":  # «وCodex» reads as a Latin word with a stray letter; a space keeps «و» Arabic
                page = re.sub(r"(?<=[\s(،])و(?=<bdi>|[A-Za-z])", "و ", page)
            (folder / f"{name}.html").write_text(page, encoding="utf-8", newline="\n")
    print(f"SITE={DOCS} tools={n['tools']} engines={n['engines']} tests={n['tests']}")


if __name__ == "__main__":
    main()
