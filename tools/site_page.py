"""نسخة مستقلة من صفحة الجولة (للرابط العام بدون منصة): تضيف رأس HTML كامل (عربي، يمين لليسار، viewport).

python tools/site_page.py <vr/index.html> <vr/tour.html>
"""
import sys

src, dst = sys.argv[1], sys.argv[2]
body = open(src, encoding="utf-8").read()
head = ('<!doctype html>\n<html lang="ar" dir="rtl">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta property="og:title" content="مصنع وتد الأخشاب — جولة افتراضية">\n</head>\n<body>\n')
# ملاحظة المصنع: الرابط يفتح المشروع مباشرة (ملء الشاشة) والعميل يتحرك فيه فوراً — الصفحة التعريفية خلف زر "التفاصيل"
direct = """
<style>
body.direct { overflow: hidden }
body.direct #model-stage { position: fixed !important; inset: 0 !important; width: 100vw !important; height: 100vh !important;
  height: 100dvh !important; max-height: none !important; aspect-ratio: auto !important; z-index: 50; border-radius: 0; margin: 0 }
body.direct #walkbar { position: fixed; left: 8px; right: 8px; bottom: calc(10px + env(safe-area-inset-bottom)); z-index: 60;
  display: flex; gap: 6px; overflow-x: auto; justify-content: center }
body.direct #walkbar button { backdrop-filter: blur(6px); background: rgba(20, 14, 9, .62); color: #fff; border-color: rgba(216, 190, 140, .55) }
body.direct #walkbar button[aria-pressed="true"] { background: #B8955A; color: #1a120b }
body.direct .dn { position: fixed; top: calc(10px + env(safe-area-inset-top)); left: 10px; z-index: 60 }
#dx-info { display: none }
body.direct #dx-info { display: block; position: fixed; top: calc(10px + env(safe-area-inset-top)); right: 10px; z-index: 60;
  font: inherit; font-size: .95rem; padding: 7px 14px; border-radius: 8px; border: 1px solid rgba(216, 190, 140, .6);
  background: rgba(20, 14, 9, .62); color: #fff; backdrop-filter: blur(6px); cursor: pointer }
body.direct #model-stage .tools { bottom: auto; top: calc(58px + env(safe-area-inset-top)) }
body.direct #joy { bottom: calc(118px + env(safe-area-inset-bottom)) !important }
</style>
<button type="button" id="dx-info">تفاصيل المشروع والصور</button>
<script>
(function () {
  if (/page/.test(location.hash)) return;
  document.body.classList.add("direct");
  document.getElementById("dx-info").addEventListener("click", function () {
    document.body.classList.remove("direct"); window.scrollTo(0, 0);
  });
})();
</script>
"""
open(dst, "w", encoding="utf-8").write(head + body + direct + "\n</body>\n</html>\n")
