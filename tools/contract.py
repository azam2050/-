"""عقد تنفيذ وإنشاء كوخ خشبي — مؤسسة وتد الأخشاب للصناعة.

القالب: contracts/contract_template.html (نفس نص ونسق العقد المعتمد من المصنع).
  عقد معبّى:   python tools/contract.py بيانات.yaml -o عقد.pdf
  نسخة فاضية:  python tools/contract.py --blank -o عقد_فاضي.pdf   ← PDF بحقول قابلة للكتابة

البيانات المتغيرة (اللي يعلّم عليها المصنع بالأحمر) — مثال في contracts/contract_example.yaml:
  date, client_name, client_id, client_phone, client_address, project_type, site, area,
  total, payments [4 نسب %], duration (يوم), warranty (سنوات)
الباقي يُحسب تلقائيًا: اليوم من التاريخ، المبلغ كتابة، مبالغ الدفعات من النسب.
ملفات بيانات العملاء ما تُرفع للمستودع (contracts/data/ في .gitignore).
"""
import argparse
import datetime as dt
import html
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "contracts" / "contract_template.html"

PAYMENTS = [("الدفعة الأولى عند توقيع العقد", "p1"),
            ("الدفعة الثانية عند بدء التصنيع/التنفيذ", "p2"),
            ("الدفعة الثالثة عند وصول المشروع للموقع/بدء التركيب", "p3"),
            ("الدفعة النهائية عند اكتمال التنفيذ", "p4")]
DAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

ONES = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"]
TEENS = ["عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر",
         "ثمانية عشر", "تسعة عشر"]
TENS = ["", "", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
HUNDREDS = ["", "مائة", "مائتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"]


def _below_1000(n):
    h, r = divmod(n, 100)
    parts = [HUNDREDS[h]] if h else []
    if 10 <= r < 20:
        parts.append(TEENS[r - 10])
    elif r:
        t, o = divmod(r, 10)
        parts.append(" و".join(x for x in (ONES[o], TENS[t]) if x))
    return " و".join(parts)


def _scale(n, one, two, plural, acc, last=False):
    """ألف/ألفان/ثلاثة آلاف/أحد عشر ألفًا/مائة ألف."""
    if n == 1:
        return one
    if n == 2:
        return two
    r = n % 100
    w = _below_1000(n)
    if 3 <= r <= 10:
        return f"{w} {plural}"
    if 11 <= r <= 99:
        return f"{w} {one if last else acc}"      # آخر الرقم قبل المعدود: "ثمانون ألف ريال"
    return f"{w} {one}"


def tafqeet(n):
    """رقم صحيح → كتابة عربية (مثل: تسعة عشر ألفًا ومائة وستة وثلاثون)."""
    n = int(round(n))
    if n == 0:
        return "صفر"
    m, rest = divmod(n, 1_000_000)
    k, u = divmod(rest, 1000)
    parts = []
    if m:
        parts.append(_scale(m, "مليون", "مليونان", "ملايين", "مليونًا", last=not rest))
    if k:
        parts.append(_scale(k, "ألف", "ألفان", "آلاف", "ألفًا", last=not u))
    if u:
        parts.append(_below_1000(u))
    return " و".join(parts)


def riyal_words(n):
    r = int(round(n)) % 100
    noun = "ريالات سعودية" if 3 <= r <= 10 else "ريالًا سعوديًا" if r >= 11 else "ريال سعودي"
    return f"{tafqeet(n)} {noun}"


def money(v):
    return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"


def values(d):
    """يكمل الحقول المحسوبة من بيانات العقد."""
    v = dict(d)
    date = v.get("date")
    if isinstance(date, str):
        date = dt.date.fromisoformat(date.replace("/", "-"))
    if date:
        v.setdefault("day", DAYS[date.weekday()])
        v["date"] = date.strftime("%Y/%m/%d")
    total = float(v["total"])
    v.setdefault("total_words", riyal_words(total))
    v["total"] = v["total2"] = money(total)
    pcts = v.get("payments") or [100, 0, 0, 0]
    if abs(sum(pcts) - 100) > 1e-6:
        sys.exit(f"نسب الدفعات مجموعها {sum(pcts)}% — لازم 100%")
    amounts = [round(total * p / 100) for p in pcts]
    amounts[-1 if pcts[-1] else pcts.index(max(pcts))] += round(total) - sum(amounts)   # فرق التقريب
    for (_l, key), p, a in zip(PAYMENTS, pcts, amounts):
        v[key + "_pct"] = f"{p:g}"
        v[key + "_amount"] = money(a)
    v.setdefault("duration", 35)
    v.setdefault("warranty", 10)
    v.setdefault("client_name_sig", v.get("client_name", ""))
    v.setdefault("date_sig1", v.get("date", ""))
    v.setdefault("date_sig2", v.get("date", ""))
    v["area"] = f"{float(v['area']):g}" if v.get("area") not in (None, "") else ""
    return v


def render(data=None, blank=False):
    """يرجع (PDF bytes، قائمة الحقول [(اسم، علامة، عرض pt)])."""
    import jinja2
    from weasyprint import HTML
    fields = []

    def fld(key, width):
        if blank:
            mark = f"F{len(fields):02d}X"
            fields.append((key, mark, width))
            return jinja2.utils.markupsafe.Markup(f'<span class="f" style="width:{width}pt">{mark}</span>')
        return jinja2.utils.markupsafe.Markup(f'<span class="f">{html.escape(str(data.get(key, "")))}</span>')

    env = jinja2.Environment(autoescape=True)
    src = env.from_string(TPL.read_text(encoding="utf-8")).render(fld=fld, blank=blank, payments=PAYMENTS)
    pdf = HTML(string=src, base_url=str(TPL)).write_pdf()
    return pdf, fields


def make_blank(out):
    """نسخة فاضية بحقول نص قابلة للتعبئة (AcroForm) مكان البيانات المتغيرة."""
    import pymupdf
    pdf, fields = render(blank=True)
    doc = pymupdf.open("pdf", pdf)
    for key, mark, width in fields:
        for page in doc:
            hits = page.search_for(mark)
            if not hits:
                continue
            r = hits[0]
            cy = (r.y0 + r.y1) / 2
            w = pymupdf.Widget()
            w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
            w.field_name = key
            w.rect = pymupdf.Rect(r.x1 - width, cy - 6.5, r.x1 + 1, cy + 6.5)
            w.text_font = "Helv"
            w.text_fontsize = 0
            w.border_width = 0              # الخانة مخفية: بدون إطار ولا لون — تبان فاضية وتنكتب عند الضغط
            w.border_color = None
            w.fill_color = None
            page.add_redact_annot(r)
            page.apply_redactions(images=0, graphics=0)
            ann = page.add_widget(w)
            doc.xref_set_key(ann.xref, "Q", "2")          # محاذاة يمين للعربي
            break
    doc.xref_set_key(doc.pdf_catalog(), "AcroForm/NeedAppearances", "true")
    doc.set_metadata({"title": "عقد تنفيذ وإنشاء كوخ خشبي — نموذج فاضي", "author": "مؤسسة وتد الأخشاب للصناعة"})
    doc.save(out, garbage=3, deflate=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", nargs="?", help="ملف بيانات العقد YAML")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--blank", action="store_true", help="نسخة فاضية بحقول قابلة للتعبئة")
    a = ap.parse_args()
    if a.blank:
        print(make_blank(a.out))
        return
    d = yaml.safe_load(open(a.data, encoding="utf-8"))
    pdf, _ = render(values(d))
    Path(a.out).write_bytes(pdf)
    print(a.out)


if __name__ == "__main__":
    main()
