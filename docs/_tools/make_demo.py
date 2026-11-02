"""Build a demo project for a fictional game, "Station Kepler", to screenshot the four follow-up pages.

    python docs/_tools/make_demo.py <empty folder>

Copies the template into the folder, fills it with invented data (text, translations, findings, tasks,
images and their versions), then builds dashboard.html, tasks.html, texts.html and images.html there.
Everything is invented for the site: no real game's text or art. The folder can be deleted afterwards.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2]

LINES = [  # (id, batch, speaker, source, target, status)
    ("menu#new", "pilot", "", "New Game", "لعبة جديدة", "tested"),
    ("menu#continue", "pilot", "", "Continue", "متابعة", "tested"),
    ("menu#settings", "pilot", "", "Settings", "الإعدادات", "tested"),
    ("menu#quit", "pilot", "", "Quit to Desktop", "الخروج إلى سطح المكتب", "tested"),
    ("ch1#001", "pilot", "Eileen", "Welcome aboard Station Kepler, [player_name].",
     "أهلًا بك على متن محطة كبلر يا [player_name].", "tested"),
    ("ch1#002", "pilot", "Mara", "The lights have been flickering since the storm.",
     "الأضواء ترتعش منذ العاصفة.", "tested"),
    ("set#volume", "batch-001", "", "Master Volume", "مستوى الصوت العام", "integrated"),
    ("set#subtitles", "batch-001", "", "Subtitles: {on_off}", "الترجمة النصية: {on_off}", "integrated"),
    ("set#language", "batch-001", "", "Language", "اللغة", "integrated"),
    ("set#apply", "batch-001", "", "Apply Changes", "تطبيق التغييرات", "integrated"),
    ("ch1#003", "batch-002", "Iko", "Oxygen reserves at {percent}%. Recommend calm breathing.",
     "احتياطي الأكسجين {percent}%. أنصح بالتنفس بهدوء.", "proofread"),
    ("ch1#004", "batch-002", "Mara", "Did you hear that? {i}Something{/i} is moving in the vents.",
     "هل سمعت ذلك؟ {i}شيءٌ{/i} يتحرك في فتحات التهوية.", "proofread"),
    ("ch1#005", "batch-002", "Eileen", "Stay close. We check the reactor first.",
     "ابقَ قريبًا. نتفقد المفاعل أولًا.", "proofread"),
    ("ch1#006", "batch-002", "Iko", "The Reactor core is stable. For now.", "قلب الـ Reactor مستقر. حتى الآن.",
     "translated"),
    ("ch1#007", "batch-002", "Mara", "Who sealed the cargo bay from the inside?",
     "من أغلق مخزن الشحن من الداخل؟", "translated"),
    ("ch2#001", "batch-003", "Eileen", "Log entry 47. The crew is getting nervous.",
     "السجل رقم 47. الطاقم بدأ يتوتر.", "translated"),
    ("ch2#002", "batch-003", "Mara", "I found footprints. Small ones.", "وجدت آثار أقدام. صغيرة.", "translated"),
    ("ch2#003", "batch-003", "Iko", "Footprint analysis inconclusive.", "", "extracted"),
    ("ch2#004", "batch-003", "Eileen", "Then we follow them.", "", "extracted"),
    ("ch3#001", "batch-004", "Mara", "This was never a research station.", "", "extracted"),
    ("ch3#002", "batch-004", "Iko", "Access denied. Clearance level: Commander.", "", "extracted"),
]
IMAGES = [  # (file, English, Arabic, spoiler reason or "", versions: [(arabic text, method, verdict, reason)])
    ("title.png", "STATION KEPLER", "محطة كبلر", "", [
        ("م ح ط ة  ك ب ل ر", "typeset", "rejected", "الحروف منفصلة: الخط لا يشكّل العربية"),
        ("محطة كبلر", "codex", "rejected", "تغيّر لون الخلفية خارج صندوق النص"),
        ("محطة كبلر", "typeset", "accepted", "الحروف متصلة، والخلفية والإطار كما في الأصل"),
    ]),
    ("door_sign.png", "CARGO BAY 7", "مخزن الشحن 7", "", [
        ("مخزن الشحن 7", "typeset", "accepted", "مطابق للأصل في الحجم والموضع"),
    ]),
    ("ending_reveal.png", "THE COMMANDER LIED", "القائدة كذبت", "تكشف حقيقة القائدة في النهاية", [
        ("القائدة كذبت", "typeset", "accepted", "مطابقة للأصل"),
    ]),
    ("warning_panel.png", "OXYGEN LOW", "الأكسجين منخفض", "", []),
]
TASKS = [  # (title, kind, phase, final status, note/evidence/reason)
    ("اختيار خط عربي مرخّص لصناديق الحوار", "research", "discovery", "done",
     "Noto Naskh Arabic (OFL): يغطي كل الحروف والتشكيل"),
    ("إثبات المحوّل على نسخة اللعبة الحالية", "tool", "extraction", "done", "adapter_contract.py: 8/8 PASS"),
    ("تثبيت دفعة التجربة على نسخة المستخدم", "integration", "pilot", "done", "نسخة احتياطية m-001، وتأكيد المستخدم مسجّل"),
    ("سؤال: نترجم «Reactor» أم نبقيها؟", "question", "localization", "waiting",
     "«المفاعل» أم تبقى Reactor كما في واجهة اللعبة؟ تؤثر على 12 جملة"),
    ("تدقيق الدفعة batch-002", "translation", "localization", "doing", ""),
    ("إصلاح قصّ زر «تطبيق التغييرات»", "fix", "localization", "verify", "صياغة أقصر، تحتاج لقطة من اللعبة"),
    ("تعريب صورة لوحة التحذير", "other", "localization", "next", ""),
    ("فحص تقسيم الأسطر في الترجمات الطويلة", "qa", "integration", "later", ""),
    ("ترجمة أسماء الإنجازات", "translation", "localization", "dropped",
     "اللعبة لا تعرض الإنجازات خارج Steam"),
]


def picture(path: Path, text: str, colors: tuple[str, str, str], arabic: bool = False) -> None:
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (960, 420), colors[0])
    draw = ImageDraw.Draw(image)
    for x in range(-200, 1160, 64):
        draw.line([(x, 0), (x - 220, 420)], fill=colors[1], width=20)
    draw.rounded_rectangle([170, 140, 790, 280], radius=18, fill=colors[2])
    if arabic:
        font = ImageFont.truetype("C:/Windows/Fonts/tahoma.ttf", 64, layout_engine=ImageFont.Layout.RAQM)
        draw.text((480, 210), text, font=font, fill="white", anchor="mm", direction="rtl", language="ar")
    else:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 58)
        draw.text((480, 210), text, font=font, fill="white", anchor="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty")
    files = subprocess.run(["git", "-C", str(TEMPLATE), "ls-files"], capture_output=True, text=True,
                           encoding="utf-8", check=True).stdout.splitlines()
    for rel in files:
        if rel.startswith("docs/"):
            continue
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATE / rel, target)
    sys.path.insert(0, str(out / "scripts"))
    import yaml

    game = out / "game"
    settings = yaml.safe_load((out / "PROJECT.yaml").read_text(encoding="utf-8"))
    settings["game"].update(name="Station Kepler", install_path=str(game))
    settings["workflow"].update(image_scope="yes", runtime="claude-code", review_mode="separate")
    (out / "PROJECT.yaml").write_text(yaml.safe_dump(settings, allow_unicode=True, sort_keys=False), encoding="utf-8")

    units = [{"id": i, "kind": "text", "file": f"story/{i.split('#')[0]}.rpy", "source": s, "target": t,
              "status": st, "batch": b, **({"context": {"speaker": sp}} if sp else {})}
             for i, b, sp, s, t, st in LINES]
    colors = [("#1d2b3a", "#22344a", "#8a3b2b"), ("#1e3327", "#233c2e", "#2e6a46"),
              ("#2c1717", "#361c1c", "#6b2a2a"), ("#2d2a14", "#363219", "#8a6d12")]
    for (name, english, arabic, spoiler, versions), color in zip(IMAGES, colors):
        picture(game / "ui" / name, english, color)
        units.append({"id": f"img#{name.split('.')[0]}", "kind": "image", "file": f"ui/{name}", "asset": f"ui/{name}",
                      "source": english, "target": arabic, "decision": "translate", "batch": "images",
                      "status": "proofread" if versions else "extracted"})
    (out / "units").mkdir(exist_ok=True)
    (out / "units" / "station-kepler.jsonl").write_text(
        "\n".join(json.dumps(u, ensure_ascii=False) for u in units) + "\n", encoding="utf-8")

    (out / "PLAN.md").write_text("""# خطة تعريب Station Kepler

## الهدف
تعريب القوائم والحوار وصور الواجهة، وتثبيته على نسخة المستخدم.

## الدفعات
- [x] pilot — القائمة الرئيسية وأول مشهد — translator-1 / proofreader-1
- [x] batch-001 — الإعدادات — translator-1 / proofreader-1
- [ ] batch-002 — الفصل الأول — translator-1 / proofreader-2 — unfinished: 5/7
- [ ] batch-003 — الفصل الثاني — translator-2 / proofreader-1
- [ ] batch-004 — الفصل الثالث — translator-2 / proofreader-2

## القرارات
- الأسماء تُنقل حرفيًا: Mara = مارا، Eileen = آيلين، Iko = إيكو.

## الخطوة التالية
إنهاء تدقيق batch-002، ثم انتظار جوابك عن «Reactor».
""", encoding="utf-8")
    proofreading = out / "work" / "proofreading"
    proofreading.mkdir(parents=True, exist_ok=True)
    (proofreading / "batch-002.jsonl").write_text("\n".join(json.dumps(f, ensure_ascii=False) for f in [
        {"id": "ch1#004", "severity": "minor", "category": "spelling", "issue": "تنوين «شيءٌ» في موضعه الصحيح",
         "before": "شيئ", "after": "شيءٌ", "resolution": "applied", "by": "proofreader-2"},
        {"id": "ch1#006", "severity": "major", "category": "terminology", "issue": "Reactor غير مترجم: هل «المفاعل»؟",
         "resolution": "needs_decision", "by": "proofreader-2"},
    ]) + "\n", encoding="utf-8")
    (out / "qa" / "LQA_MATRIX.csv").write_text(
        "id,screen,severity,status,observed,expected\n"
        "qa-001,settings,minor,pass,زر التطبيق مقصوص,يظهر كاملًا\n"
        "qa-002,dialogue,major,open,سطر طويل يتجاوز الصندوق,يُقسم على سطرين\n", encoding="utf-8")

    subprocess.run([sys.executable, str(out / "scripts" / "loc.py"), "normalize"], cwd=out, check=True,
                   capture_output=True)
    pipeline = __import__("loc_pipeline")
    candidate = __import__("image_candidate")
    state = {"schema_version": 1, "phase": "localization", "history": [
        {"event": "passed", "phase": p, "at": f"2026-10-{20 + n:02d}T09:{10 * n:02d}:00Z"}
        for n, p in enumerate(("intake", "discovery", "extraction", "pilot"))]}
    state["history"].insert(3, {"event": "blocked", "phase": "pilot", "missing": 1, "at": "2026-10-22T18:40:00Z"})
    state["pilot"] = {"note": "the user: «العربي واضح ومتصل في القائمة وأول مشهد»", "at": "2026-10-23T09:30:00Z"}
    state_file = out / "state" / "pipeline.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    board = pipeline.tasks
    for title, kind, phase, final, text in TASKS:
        ident = board.add(state_file, title, kind, phase)
        if final == "done":
            board.move(state_file, ident, "doing")
            board.move(state_file, ident, "done", evidence=text)
        elif final in ("waiting", "dropped"):
            board.move(state_file, ident, final, reason=text)
        elif final == "verify":
            board.move(state_file, ident, "doing")
            board.move(state_file, ident, "verify", note=text)
        elif final != "next":
            board.move(state_file, ident, final)

    attempts = out / "work" / "images" / "attempts.json"
    for (name, _, _, spoiler, versions), color in zip(IMAGES, colors):
        source = game / "ui" / name
        for n, (text, method, verdict, reason) in enumerate(versions, 1):
            made = out / "work" / "images" / "candidates" / f"{source.stem}.v{n}.png"
            picture(made, text, color, arabic=True)
            candidate.main(["record", "--source", str(source), "--candidate", str(made), "--method", method,
                            "--attempts", str(attempts)])
            candidate.main(["verdict", "--source", str(source), "--version", str(n), "--verdict", verdict,
                            "--reason", reason, "--attempts", str(attempts)])
        flag = ["--reason", spoiler] if spoiler else ["--none"]
        candidate.main(["spoiler", "--source", str(source), *flag, "--attempts", str(attempts)])
    (out / "work" / "probe").mkdir(parents=True, exist_ok=True)
    (out / "work" / "probe" / "last.json").write_text(json.dumps(
        {"at": "2026-10-28 18:05", "game": "Station Kepler", "engine": "renpy", "fonts": {"total": 4, "arabic": 2},
         "boot": "booted_clean"}, ensure_ascii=False), encoding="utf-8")
    subprocess.run([sys.executable, str(out / "scripts" / "loc.py"), "next"], cwd=out, check=True, capture_output=True)
    print(f"DEMO={out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
