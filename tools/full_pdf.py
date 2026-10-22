"""ملف PDF كامل للعميل: غلاف برابط ورمز QR للجولة الافتراضية + لوحات الأوتوكاد + صور الرندر الواقعي + صور 360°.

python tools/full_pdf.py <autocad.pdf> <مجلد realistic> <رابط الجولة> <الإخراج.pdf> [عنوان] [سطر_الحقائق]
"""
import io
import json
import sys
from pathlib import Path

import pymupdf
import qrcode

W, H = 1191, 842        # A3 أفقي (نقطة)
BRAND, INK, MUTED, CEDAR = "#3B2416", "#1C2420", "#5E6B63", "#A3653A"


def html(page, rect, body, size=14, color=INK, align="right", weight="normal"):
    page.insert_htmlbox(pymupdf.Rect(*rect), f'<div style="font-size:{size}px;color:{color};text-align:{align};'
                        f'font-weight:{weight};line-height:1.55">{body}</div>')


def qr_png(url):
    img = qrcode.make(url, box_size=12, border=2)
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def main(autocad, real, url, out, title="", facts=""):
    real = Path(real)
    doc = pymupdf.open()
    # ---- الغلاف
    p = doc.new_page(width=W, height=H)
    p.draw_rect(pymupdf.Rect(0, 0, W, 110), color=None, fill=pymupdf.utils.getColor("white"))
    p.draw_rect(pymupdf.Rect(0, 0, W, 14), color=None, fill=(0.23, 0.14, 0.09))
    html(p, (60, 40, W - 60, 90), "مصنع وتد الأخشاب", 22, CEDAR, weight="bold")
    html(p, (60, 95, W - 60, 190), title, 40, BRAND, weight="bold")
    html(p, (60, 190, W - 60, 240), facts, 17, MUTED)
    cover = sorted(real.glob("x1.jpg")) or sorted(real.glob("*.jpg"))
    if cover:
        p.insert_image(pymupdf.Rect(60, 260, 760, 700), filename=str(cover[0]), keep_proportion=True)
    q = pymupdf.Rect(830, 270, 1130, 570)
    p.insert_image(q, stream=qr_png(url))
    p.insert_link({"kind": pymupdf.LINK_URI, "from": q, "uri": url})
    html(p, (790, 580, 1150, 650), "امسح الرمز بكاميرا الجوال — أو اضغط عليه<br>"
         "<b>الجولة الافتراضية: يتحرك بالمشروع كامل</b>", 16, INK, "center")
    btn = pymupdf.Rect(840, 660, 1120, 705)
    p.draw_rect(btn, color=None, fill=(0.18, 0.36, 0.29), radius=0.2)
    html(p, (btn.x0, btn.y0 + 9, btn.x1, btn.y1), "افتح الجولة الافتراضية", 18, "#FFFFFF", "center", "bold")
    p.insert_link({"kind": pymupdf.LINK_URI, "from": btn, "uri": url})
    html(p, (60, 730, W - 60, 800), "محتوى الملف: لوحات الأوتوكاد (الموقع واللاندسكيب، المساقط، الواجهات، السقف والقطاع، الجداول، "
         "المساحات والتسعير، الفرش) — ثم صور الرندر الواقعي نهار وليل وداخلي — وصور 360°.", 13, MUTED)
    # ---- لوحات الأوتوكاد
    doc.insert_pdf(pymupdf.open(autocad))
    # ---- الرندر الواقعي
    meta = json.loads((real / "shots.json").read_text(encoding="utf-8")) if (real / "shots.json").exists() else {}
    groups = [("الرندر الواقعي — الخارج نهاراً", meta.get("exterior", [])),
              ("الرندر الواقعي — وقت الغروب وبالليل", meta.get("dusk", [])),
              ("الرندر الواقعي — الداخل", meta.get("interior", []))]
    for gtitle, items in groups:
        for fn, name in items:
            f = real / fn
            if not f.exists():
                continue
            p = doc.new_page(width=W, height=H)
            html(p, (40, 22, W - 40, 60), f"{gtitle} · <b>{name}</b>", 18, BRAND)
            p.insert_image(pymupdf.Rect(40, 66, W - 40, H - 60), filename=str(f), keep_proportion=True)
            html(p, (40, H - 48, W - 40, H - 18), "مصنع وتد الأخشاب — للجولة الافتراضية اضغط هنا", 12, MUTED, "center")
            p.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(300, H - 50, W - 300, H - 16), "uri": url})
    panos = sorted(real.glob("pano-*.jpg"))
    if panos:
        for i in range(0, len(panos), 2):
            p = doc.new_page(width=W, height=H)
            html(p, (40, 22, W - 40, 60), "صور 360° — تنعرض متحركة في الجولة الافتراضية (اضغط هنا)", 18, BRAND)
            p.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(40, 22, W - 40, 60), "uri": url})
            for k, f in enumerate(panos[i:i + 2]):
                p.insert_image(pymupdf.Rect(60, 80 + k * 370, W - 60, 430 + k * 370), filename=str(f), keep_proportion=True)
    doc.save(out, deflate=True, garbage=3)
    return doc.page_count


if __name__ == "__main__":
    print(main(*sys.argv[1:]), "صفحة")
