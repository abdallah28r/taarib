# مدخل Claude Code

التعليمات المشتركة بين Codex وClaude Code موجودة في `AGENTS.md` وحده، وتُستورد هنا كاملة:

@AGENTS.md

لا تكرر قواعد `AGENTS.md` في هذا الملف. أضف هنا فقط ما يخص Claude Code.

## ما يخص Claude Code

- **المهارات:** يقرأ Claude Code المجلد `.claude/skills/`، وهو نسخة مولّدة من `.agents/skills/`.
  عدّل المهارات في `.agents/skills/` فقط، ثم شغّل `python scripts/sync_runtime_skills.py`.
  يفشل `python scripts/verify_template.py` إذا اختلفت النسختان.
- **النماذج:** المسارات في `config/agent-policy.json` تحدد فئة (light/standard/deep).
  في Claude Code تقابلها haiku وsonnet وopus. مرّر الفئة المناسبة عند إنشاء وكيل فرعي،
  واستخدم `python scripts/make_subagent_brief.py --runtime claude-code` لكتابة الموجز.
- **التفويض المتداخل:** الوكيل الفرعي في Claude Code لا يستطيع إنشاء وكيل فرعي آخر.
  الوكيل الرئيسي هو من يوزع العمل على كل الوكلاء مباشرة.
- **العمل المشترك مع Codex:** إذا كان Codex يعمل على المشروع نفسه، سجّل في `STATUS.md`
  تحت «العمل النشط حسب بيئة التشغيل» الملفات التي تكتبها، ولا تكتب في ملف سجّله Codex.
