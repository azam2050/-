"""عرض سعر تسليم مفتاح — مؤسسة وتد الأخشاب للصناعة (نفس ترويسة العقود).

  python tools/quote.py contracts/quotes/X.yaml -o عرض.pdf
  python tools/quote.py contracts/quotes/X.yaml --internal   ← ملخص التكلفة والهامش للمصنع (ما يدخل الـPDF)

البيانات: أقسام فيها بنود (item, qty, unit, base = تكلفة المصنع للوحدة، photo اختياري)، وهامش القسم markup (افتراضي 15%).
سعر الوحدة للعميل = base × (1 + markup) مقرّب لـ round_to. العميل يشوف سعر الوحدة والإجمالي فقط.
القالب: contracts/quote_template.html — الصور من contracts/assets/products/.
"""
import argparse
import datetime as dt
import math
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import money, riyal_words  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "contracts" / "quote_template.html"
DEFAULT_MARKUP = 15


def priced(d):
    """يحسب أسعار العميل لكل بند وقسم + ملخص التكلفة الداخلي."""
    step = d.get("round_to", 50)
    secs, base_total, total = [], 0.0, 0.0
    n = 0
    for s in d["sections"]:
        mk = s.get("markup", DEFAULT_MARKUP)
        rows, s_base, s_total = [], 0.0, 0.0
        for it in s["items"]:
            m = it.get("markup", mk)
            unit = it["base"] * (1 + m / 100)
            if m:   # التقريب يتناسب مع السعر: الأسعار الصغيرة (م²، م.ط) ما تنتفخ بالتقريب
                st = 5 if unit < 500 else 10 if unit < 5000 else step
                unit = math.ceil(unit / st) * st
            n += 1
            amt = unit * it["qty"]
            rows.append(dict(it, n=n, unit_price=money(unit), amount=money(amt), qty_s=f"{it['qty']:g}"))
            s_base += it["base"] * it["qty"]
            s_total += amt
        secs.append(dict(name=s["name"], rows=rows, total=money(s_total), base=s_base, value=s_total))
        base_total += s_base
        total += s_total
    return secs, base_total, total


def payments(d, total):
    out, acc = [], 0
    pays = d["payments"]
    if abs(sum(p for p, _ in pays) - 100) > 1e-6:
        sys.exit("نسب الدفعات لازم مجموعها 100%")
    for i, (p, label) in enumerate(pays):
        a = round(total * p / 100) if i < len(pays) - 1 else round(total) - acc
        acc += a
        out.append(dict(pct=f"{p:g}", label=label, amount=money(a)))
    return out


def render(d):
    import jinja2
    from weasyprint import HTML
    secs, _base, total = priced(d)
    date = d["date"]
    if isinstance(date, str):
        date = dt.date.fromisoformat(date)
    v = dict(d, sections=secs, total=money(total), total_words=riyal_words(total),
             vat=money(total * 15 / 115) if d.get("vat_included", True) else None,
             pays=payments(d, total), date=date.strftime("%Y/%m/%d"),
             valid_until=(date + dt.timedelta(days=d.get("validity_days", 15))).strftime("%Y/%m/%d"))
    env = jinja2.Environment(autoescape=True)
    src = env.from_string(TPL.read_text(encoding="utf-8")).render(**v)
    return HTML(string=src, base_url=str(TPL)).write_pdf()


def internal(d):
    secs, base, total = priced(d)
    print(f"{'القسم':<44}{'التكلفة':>12}{'سعر العميل':>12}{'الربح':>10}")
    for s in secs:
        print(f"{s['name']:<44}{s['base']:>12,.0f}{s['value']:>12,.0f}{s['value'] - s['base']:>10,.0f}")
    print(f"{'الإجمالي':<44}{base:>12,.0f}{total:>12,.0f}{total - base:>10,.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("-o", "--out")
    ap.add_argument("--internal", action="store_true", help="ملخص التكلفة والهامش (للمصنع فقط)")
    a = ap.parse_args()
    d = yaml.safe_load(open(a.data, encoding="utf-8"))
    if a.internal:
        internal(d)
    if a.out:
        Path(a.out).write_bytes(render(d))
        print(a.out)


if __name__ == "__main__":
    main()
