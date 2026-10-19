# مدخل Claude Code

التعليمات المشتركة بين Codex وClaude Code موجودة في `AGENTS.md` وحده، وتُستورد هنا كاملة:

@AGENTS.md

لا تكرر قواعد `AGENTS.md` في هذا الملف. أضف هنا فقط ما يخص Claude Code.

## ما يخص Claude Code

- **المهارات:** يقرأ Claude Code المجلد `.claude/skills/`، وهو نسخة مولّدة من `.agents/skills/`.
  عدّل المهارات في `.agents/skills/` فقط، ثم شغّل `python scripts/sync_runtime.py`.
  يفشل `python scripts/verify_template.py` إذا اختلفت النسختان.
- **الأدوار:** المترجم والمدقق اللغوي موجودان كوكيلين فرعيين في `.claude/agents/`
  (`translator` و`proofreader`)، مولَّدين من `.agents/roles/`. استدعِهما باسميهما، ومرّر
  لكل منهما موجزًا من `python scripts/make_subagent_brief.py --role <role> --runtime claude-code`.
  لا يدقق الوكيل الدفعة التي ترجمها.
- **النماذج:** المسارات في `config/agent-policy.json` تحدد فئة (light/standard/deep).
  في Claude Code تقابلها haiku وsonnet وopus. مرّر الفئة المناسبة عند إنشاء وكيل فرعي،
  واستخدم `python scripts/make_subagent_brief.py --runtime claude-code` لكتابة الموجز.
- **التفويض المتداخل:** الوكيل الفرعي في Claude Code لا يستطيع إنشاء وكيل فرعي آخر.
  الوكيل الرئيسي هو من يوزع العمل على كل الوكلاء مباشرة.
- **الـ hooks (`.claude/settings.json`):** تمنع كتابة ملف موجود داخل مجلد اللعبة قبل وجود
  نسخة احتياطية له، وتمنع تعديل `backups/`، وتمنع أوامر الطرفية التي تكتب في مجلد اللعبة
  دون أدوات النسخ الاحتياطي. بعد كل كتابة تفحص الوحدات وملفات التدقيق وYAML، وتعيد توليد
  `.claude/` عند تعديل مهارة أو دور. عند بدء الجلسة تعرض `loc.py next`. إذا منعك hook فاتبع
  رسالته؛ لا تتجاوزه. فحص الأوامر تقريبي وليس حدًا أمنيًا.
- **العمل المشترك مع Codex:** إذا كان Codex يعمل على المشروع نفسه، سجّل في `STATUS.md`
  تحت «العمل النشط حسب بيئة التشغيل» الملفات التي تكتبها، ولا تكتب في ملف سجّله Codex.
