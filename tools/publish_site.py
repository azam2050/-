"""ينسخ صفحة جولة مشروع إلى مجلد الموقع العام site/<slug>/ (Cloudflare Pages: مجلد الإخراج = site).

python tools/publish_site.py <مجلد vr> <slug> "<اسم المشروع>"
النتيجة: site/<slug>/index.html + الصور والمجسم والفيديو والـPDF، وsite/index.html فهرس المشاريع.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


def main(vr, slug, name):
    vr, dst = Path(vr), SITE / slug
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(vr, dst, ignore=shutil.ignore_patterns("index.html", "tour.html", "model.glb"))
    shutil.copy(vr / "tour.html", dst / "index.html")
    reg = SITE / "projects.json"
    projects = json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else {}
    projects[slug] = name
    reg.write_text(json.dumps(projects, ensure_ascii=False, indent=1), encoding="utf-8")
    items = "\n".join(f'<li><a href="{s}/">{n}</a></li>' for s, n in projects.items())
    (SITE / "index.html").write_text(f"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>مصنع وتد الأخشاب — التصاميم</title>
<style>body{{font-family:"Segoe UI",Tahoma,sans-serif;background:#F1F2EE;color:#1C2420;padding:32px 16px;max-width:720px;margin:auto;line-height:1.8}}
h1{{color:#3B2416}}a{{color:#2F5D4A;font-size:1.15rem}}</style></head>
<body><h1>مصنع وتد الأخشاب</h1><p>جولات افتراضية لتصاميم المصنع:</p><ul>
{items}
</ul></body></html>
""", encoding="utf-8")
    (SITE / "_headers").write_text("/*\n  X-Robots-Tag: noindex\n", encoding="utf-8")   # ما تطلع بمحركات البحث
    print("site/" + slug)


if __name__ == "__main__":
    main(*sys.argv[1:4])
