"""ملف التصميم الكامل للعميل (ترتيب المصنع): غلاف ← لوحات الأوتوكاد ← صور المشروع ← الجداول ← التسعيرة بالأخير
← صور 360° ← آخر صفحة: تجربة الواقع الافتراضي (نهار/ليل برمز QR وزر). الخط عربي احترافي (assets/fonts).

python tools/full_pdf.py <autocad.pdf> <مجلد realistic> <رابط الجولة> <الإخراج.pdf> [عنوان] [سطر_الحقائق]
"""
import io
import json
import sys
from pathlib import Path

import pymupdf
import qrcode

W, H = 1191, 842        # A3 أفقي (نقطة)
BRAND, INK, MUTED, CEDAR, GOLD = "#3B2416", "#1C2420", "#5E6B63", "#A3653A", "#B8955A"
FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
ARCH = pymupdf.Archive(str(FONTS))
CSS = """
@font-face {font-family: tj; src: url(Tajawal-Regular.ttf);}
@font-face {font-family: tj; src: url(Tajawal-Bold.ttf); font-weight: bold;}
@font-face {font-family: px; src: url(IBMPlexSansArabic-Regular.ttf);}
@font-face {font-family: px; src: url(IBMPlexSansArabic-Bold.ttf); font-weight: bold;}
div {font-family: px;} .h {font-family: tj;}
"""


def html(page, rect, body, size=14, color=INK, align="right", weight="normal", head=False):
    page.insert_htmlbox(pymupdf.Rect(*rect), f'<div class="{"h" if head else ""}" style="font-size:{size}px;color:{color};'
                        f'text-align:{align};font-weight:{weight};line-height:1.55;direction:rtl">{body}</div>',
                        css=CSS, archive=ARCH)


def band(p, text, sub=""):
    """شريط عنوان الصفحة: خلفية غامقة + خط ذهبي + العنوان بخط عريض (مثل هوية المصنع)."""
    p.draw_rect(pymupdf.Rect(0, 0, W, 62), color=None, fill=(0.17, 0.11, 0.07))
    p.draw_rect(pymupdf.Rect(0, 62, W, 65), color=None, fill=(0.72, 0.58, 0.35))
    html(p, (40, 14, W - 40, 56), f"<b>{text}</b>" + (f'<span style="color:#D9C39A;font-size:15px">  ·  {sub}</span>' if sub else ""),
         22, "#FFFFFF", head=True)
    html(p, (40, H - 34, W - 40, H - 12), "مصنع وتد الأخشاب", 11, MUTED, "center", head=True)


def _kind(page):
    t = page.get_text()
    if "التسعير" in t:
        return "price"
    if "جدول" in t:
        return "table"
    return "draw"


def qr_png(url):
    img = qrcode.make(url, box_size=12, border=2)
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def main(autocad, real, url, out, title="", facts=""):
    real = Path(real)
    vr = url not in ("-", "none", "")          # "-" = ملف أوتوكاد + صور فقط (بدون واقع افتراضي)
    doc = pymupdf.open()
    meta = json.loads((real / "shots.json").read_text(encoding="utf-8")) if (real / "shots.json").exists() else {}
    # ---- الغلاف: اسم المشروع + أجمل لقطة
    cover = next((real / f for f in ("d1.jpg", "x1.jpg") if (real / f).exists()), None)
    p = doc.new_page(width=W, height=H)
    if cover:
        p.insert_image(pymupdf.Rect(0, 0, W, H), filename=str(cover), keep_proportion=False)
    p.draw_rect(pymupdf.Rect(0, H - 210, W, H), color=None, fill=(0.1, 0.07, 0.05), fill_opacity=0.82)
    p.draw_rect(pymupdf.Rect(0, H - 213, W, H - 210), color=None, fill=(0.72, 0.58, 0.35))
    logo = Path(__file__).resolve().parent.parent / "assets" / "watad_logo.png"
    if logo.exists():
        p.insert_image(pymupdf.Rect(50, H - 190, 210, H - 30), filename=str(logo), keep_proportion=True)
    html(p, (240, H - 195, W - 50, H - 140), "مصنع وتد الأخشاب · ملف التصميم", 18, "#D9C39A", head=True, weight="bold")
    html(p, (240, H - 145, W - 50, H - 80), f"<b>{title}</b>", 34, "#FFFFFF", head=True)
    if facts:
        html(p, (240, H - 80, W - 50, H - 30), facts, 15, "#E8E0D2")
    # ---- لوحات الأوتوكاد (الرسومات أول، والجداول والتسعيرة تتأخر لآخر الملف)
    src = pymupdf.open(autocad)
    kinds = [_kind(pg) for pg in src]
    for i, k in enumerate(kinds):
        if k == "draw":
            doc.insert_pdf(src, from_page=i, to_page=i)
    groups = [("الخارج — نهاراً", meta.get("exterior", [])),
              ("وقت الغروب وبالليل", meta.get("dusk", [])),
              ("الداخل", meta.get("interior", []))]
    for gtitle, items in groups:
        for fn, name in items:
            f = real / fn
            if not f.exists():
                continue
            p = doc.new_page(width=W, height=H)
            band(p, name, gtitle)
            p.insert_image(pymupdf.Rect(30, 76, W - 30, H - 40), filename=str(f), keep_proportion=True)
            if vr:
                p.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(300, H - 36, W - 300, H - 10), "uri": url})
    # ---- الجداول ثم التسعيرة بالأخير
    for want in ("table", "price"):
        for i, k in enumerate(kinds):
            if k == want:
                doc.insert_pdf(src, from_page=i, to_page=i)
    if not vr:
        doc.save(out, deflate=True, garbage=3)
        return doc.page_count
    panos = sorted(real.glob("pano-*.jpg"))
    if panos:
        for i in range(0, len(panos), 2):
            p = doc.new_page(width=W, height=H)
            band(p, "صور 360°", "تنعرض متحركة في الواقع الافتراضي — اضغط هنا")
            p.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(40, 10, W - 40, 60), "uri": url})
            for k, f in enumerate(panos[i:i + 2]):
                p.insert_image(pymupdf.Rect(60, 80 + k * 370, W - 60, 430 + k * 370), filename=str(f), keep_proportion=True)
    # ---- آخر صفحة: تجربة الواقع الافتراضي (نهار / ليل)
    p = doc.new_page(width=W, height=H)
    p.draw_rect(pymupdf.Rect(0, 0, W, 14), color=None, fill=(0.23, 0.14, 0.09))
    html(p, (60, 40, W - 60, 90), "مصنع وتد الأخشاب", 22, CEDAR, weight="bold", head=True)
    html(p, (60, 95, W - 60, 170), "جرّب الواقع الافتراضي", 42, BRAND, weight="bold", head=True)
    html(p, (60, 172, W - 60, 260), f"{title} — امسح الرمز بكاميرا الجوال أو اضغط الزر: يفتح المشروع مباشرة "
         "وتمشي داخله بالدورين، بالنهار أو بالليل والإنارة شغالة.", 17, MUTED)
    for k, (lbl, u, col) in enumerate((("بالنهار", url + "#day", (0.18, 0.36, 0.29)),
                                       ("بالليل والإنارة شغالة", url + "#night", (0.08, 0.12, 0.2)))):
        x0 = W - 60 - 340 - k * 420
        q = pymupdf.Rect(x0 + 30, 290, x0 + 310, 570)
        p.insert_image(q, stream=qr_png(u))
        p.insert_link({"kind": pymupdf.LINK_URI, "from": q, "uri": u})
        btn = pymupdf.Rect(x0 + 20, 590, x0 + 320, 640)
        p.draw_rect(btn, color=None, fill=col, radius=0.2)
        html(p, (btn.x0, btn.y0 + 10, btn.x1, btn.y1), "ادخل المشروع " + lbl, 18, "#FFFFFF", "center", "bold", head=True)
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
