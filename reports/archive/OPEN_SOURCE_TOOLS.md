# الأدوات المفتوحة المصدر للتعريب

تاريخ المراجعة: 2026-09-23

## ما ثُبّت وتحقق على هذا الجهاز

- بيئة Python معزولة في `.tools/venv`؛ لا تغيّر Python العام.
- `fontTools` و`uharfbuzz` و`freetype-py` وPillow لفحص الخط والتشكيل.
- Translate Toolkit و`pofilter` و`polib` وBabel و`regex` لفحوص PO/XLIFF/TMX والنص.
- ImageMagick لمعالجة صور الواجهة ومقارنات الصور.
- Tesseract 5.5.3، مع نموذج العربية `ara.traineddata` محفوظ داخل `.tools/tessdata`.
- 7zr 26.03 كأداة أرشيف محمولة داخل `.tools/bin`.
- Xdelta3 3.2.0 كأداة patch محمولة داخل `.tools/bin`، بعد التحقق من SHA-256 المنشور مع الإصدار.
- اكتشف الفاحص كذلك Git وFFmpeg. وجود أي مشغّل نموذج محلي على النظام لا يجيز لهذا القالب استخدامه ولا يعرضه الكتالوج النشط.

التقرير الآلي الكامل في `reports/TOOL_STATUS.json`. مجلد `.tools` مستثنى من Git والأرشيف النهائي لأن البيئات التنفيذية والبرامج تُعاد عبر سكربت الإعداد ولا تُنسخ بين الأجهزة.

## لماذا لم نثبت كل شيء

- FModel وrepak وretoc وUAssetGUI خاصة بمشاريع Unreal، بينما UnityPy وUABEA وBepInEx خاصة بـUnity.
- `unrpyc` و`rpatool` لا يلزمان إلا لمشاريع Ren'Py، وأدوات Kuriimu/GARbro/VNTranslationTools تعتمد على محرك الرواية البصرية وصيغتها.
- Weblate خدمة فريق كاملة وليست أداة مشروع فردي خفيفة.
- OmegaT موصى به لمن يريد واجهة CAT مستقلة؛ لم يُثبت آليا لأن حزمة Windows الحالية تطلب تثبيتا على مستوى النظام. تصدير TMX الموجود في القالب يسمح بإضافته لاحقا بلا إعادة عمل.
- أزيل ملف `local-mt` النشط وتعطلت اقتراحات Argos وLibreTranslate وOllama؛ نماذج اللغة والترجمة المحلية محظورة.
- FriBidi وLanguageTool وHDiffPatch بدائل مشروطة. Tesseract وwhisper.cpp يحتاجان إذنا صريحا للمهمة الحالية لأنهما يشغّلان OCR/STT محليا.

## الأوامر

```powershell
# البيئة الأساسية
powershell -ExecutionPolicy Bypass -File scripts/setup_tools.ps1 -Profile core -InstallApps

# فحوص صيغ الترجمة
powershell -ExecutionPolicy Bypass -File scripts/setup_tools.ps1 -Profile qa

# الخطوط والتشكيل
powershell -ExecutionPolicy Bypass -File scripts/setup_tools.ps1 -Profile fonts

# OCR عربي وصور الواجهة
# لا ينفذ هذا الأمر إلا بعد إذن صريح للمهمة الحالية
powershell -ExecutionPolicy Bypass -File scripts/setup_tools.ps1 -Profile ocr -InstallApps

# حزم delta صغيرة
powershell -ExecutionPolicy Bypass -File scripts/setup_tools.ps1 -Profile patching -InstallApps

# اكتشاف أدوات محرك من دون تثبيتها
.tools\venv\Scripts\python.exe scripts/tool_doctor.py --profile unreal
.tools\venv\Scripts\python.exe scripts/tool_doctor.py --profile unity
```

## قاعدة الاختيار

اكتشف المحرك والإصدار والصيغة أولا، ثم اختر أصغر أداة تحقق round-trip بلا تغيير. سجّل الإصدار والبصمة في manifest المشروع. وجود أداة في السجل لا يعني توافقها مع كل لعبة أو الإذن بتجاوز تشفير أو حماية أو توزيع أصول اللعبة. سياسة النماذج والوكلاء الملزمة في `MODEL_AND_SUBAGENT_POLICY.md`.
