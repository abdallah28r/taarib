حالة مراحل المشروع: `pipeline.json` (المرحلة الحالية، سجل البوابات، نتيجة عقد المحوّل، قبول المستخدم).
يكتبه `python scripts/loc.py gate|reopen|accept` فقط؛ لا تعدّله يدويًا.
المراحل بالترتيب: intake ← discovery ← extraction ← localization ← integration ← playtest ← release.
القالب العام يتجاهل `pipeline.json` في Git؛ في مستودع اللعبة الخاص احفظه مع كل دفعة.
