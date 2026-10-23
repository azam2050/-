"""ملف PDF كامل للعميل: لوحات الأوتوكاد ← صور الرندر الواقعي ← صور 360° ← آخر صفحة: تجربة الواقع الافتراضي (نهار/ليل برمز QR وزر).

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
    vr = url not in ("-", "none", "")          # "-" = ملف أوتوكاد + صور فقط (بدون واقع افتراضي)
    doc = pymupdf.open()
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
            if not vr:
                html(p, (40, H - 48, W - 40, H - 18), "مصنع وتد الأخشاب", 12, MUTED, "center")
                continue
            html(p, (40, H - 48, W - 40, H - 18), "مصنع وتد الأخشاب — الواقع الافتراضي في آخر صفحة (أو اضغط هنا)", 12, MUTED, "center")
            p.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(300, H - 50, W - 300, H - 16), "uri": url})
    if not vr:
        doc.save(out, deflate=True, garbage=3)
        return doc.page_count
    panos = sorted(real.glob("pano-*.jpg"))
    if panos:
        for i in range(0, len(panos), 2):
            p = doc.new_page(width=W, height=H)
            html(p, (40, 22, W - 40, 60), "صور 360° — تنعرض متحركة في الجولة الافتراضية (اضغط هنا)", 18, BRAND)
            p.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(40, 22, W - 40, 60), "uri": url})
            for k, f in enumerate(panos[i:i + 2]):
                p.insert_image(pymupdf.Rect(60, 80 + k * 370, W - 60, 430 + k * 370), filename=str(f), keep_proportion=True)
    # ---- آخر صفحة: تجربة الواقع الافتراضي (نهار / ليل)
    p = doc.new_page(width=W, height=H)
    p.draw_rect(pymupdf.Rect(0, 0, W, 14), color=None, fill=(0.23, 0.14, 0.09))
    html(p, (60, 40, W - 60, 90), "مصنع وتد الأخشاب", 22, CEDAR, weight="bold")
    html(p, (60, 95, W - 60, 170), "جرّب الواقع الافتراضي", 42, BRAND, weight="bold")
    html(p, (60, 172, W - 60, 260), f"{title} — امشِ داخل التصميم: الحوش والجلسات والدورين، ولف 360° بكل غرفة. "
         "امسح الرمز بكاميرا الجوال أو اضغط على الزر.", 17, MUTED)
    for k, (lbl, u, col) in enumerate((("بالنهار", url + "#day", (0.18, 0.36, 0.29)),
                                       ("بالليل والإنارة شغالة", url + "#night", (0.08, 0.12, 0.2)))):
        x0 = W - 60 - 340 - k * 420
        q = pymupdf.Rect(x0 + 30, 290, x0 + 310, 570)
        p.insert_image(q, stream=qr_png(u))
        p.insert_link({"kind": pymupdf.LINK_URI, "from": q, "uri": u})
        btn = pymupdf.Rect(x0 + 20, 590, x0 + 320, 640)
        p.draw_rect(btn, color=None, fill=col, radius=0.2)
        html(p, (btn.x0, btn.y0 + 10, btn.x1, btn.y1), "افتح الجولة " + lbl, 18, "#FFFFFF", "center", "bold")
        p.insert_link({"kind": pymupdf.LINK_URI, "from": btn, "uri": u})
    side = sorted(real.glob("d1.jpg")) or sorted(real.glob("x1.jpg"))
    if side:
        p.insert_image(pymupdf.Rect(60, 290, W - 900, 640), filename=str(side[0]), keep_proportion=True)
    html(p, (60, 680, W - 60, 760), f'الرابط: <span style="color:#2F5D4A">{url}</span>', 14, MUTED)
    p.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(60, 680, W - 60, 710), "uri": url})
    doc.save(out, deflate=True, garbage=3)
    return doc.page_count


if __name__ == "__main__":
    print(main(*sys.argv[1:]), "صفحة")
