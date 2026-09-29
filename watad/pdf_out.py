"""ملف PDF للعميل/الورشة: مسقط، واجهات تأطير، جدول كميات — بالعربي."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon, Rectangle

plt.rcParams["font.family"] = "DejaVu Sans"
COLORS = {"bottom_plate": "#b5651d", "top_plate": "#b5651d", "stud": "#d2a679",
          "corner_stud": "#8b5a2b", "jamb": "#5b7fa6", "header": "#5b7fa6",
          "sill": "#5b7fa6", "cripple": "#9c6fb0"}
KIND_AR = {"bottom_plate": "قاعدة سفلية", "top_plate": "علوي", "stud": "عمود",
           "corner_stud": "عمود زاوية", "jamb": "جنب فتحة", "header": "رأس فتحة",
           "sill": "جلسة شباك", "cripple": "عمود قصير"}


def ar(s):
    # matplotlib >= 3.11 يشكّل العربي ويتعامل مع الاتجاه بنفسه
    return str(s)


def _title(fig, project, sub):
    fig.text(0.97, 0.96, ar(f"مصنع وتد الأخشاب — {project.name}"), ha="right", fontsize=14,
             weight="bold")
    fig.text(0.97, 0.925, ar(f"العميل: {project.client}  |  {sub}"), ha="right", fontsize=10)


def _plan(pdf, project, rules):
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    _title(fig, project, "المسقط الأفقي")
    thick = rules["members"]["stud"]["w"] + 2 * rules["cladding"]["thickness"]
    for w in project.walls:
        (x0, y0), (x1, y1) = w.start, w.end
        L = w.length
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        nx, ny = -uy * thick / 2, ux * thick / 2
        ax.add_patch(Polygon([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny),
                              (x0 - nx, y0 - ny)], closed=True, fc="#6b4f3a", ec="k", lw=.5))
        for o in w.openings:
            a, b = o.offset, o.offset + o.width
            ax.add_patch(Polygon([(x0 + ux * a + nx * 1.4, y0 + uy * a + ny * 1.4),
                                  (x0 + ux * b + nx * 1.4, y0 + uy * b + ny * 1.4),
                                  (x0 + ux * b - nx * 1.4, y0 + uy * b - ny * 1.4),
                                  (x0 + ux * a - nx * 1.4, y0 + uy * a - ny * 1.4)],
                                 closed=True, fc="white", ec="#1f77b4", lw=1))
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ax.annotate(f"{L:.0f}", (mx, my), xytext=(-ny * 6, nx * 6), textcoords="offset points",
                    ha="center", va="center", fontsize=8, color="#555")
        ax.text(mx - nx * 8, my - ny * 8, w.name, ha="center", va="center", fontsize=8,
                color="#a33")
    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.15)
    ax.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def _elevation(pdf, project, w, members, H, rules):
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    _title(fig, project, f"واجهة تأطير الجدار {w.name} — الطول {w.length:.0f} سم، الارتفاع {H:.0f} سم")
    for m in members:
        ax.add_patch(Rectangle((m.x0, m.y0), m.x1 - m.x0, m.y1 - m.y0, fc=COLORS[m.kind],
                               ec="k", lw=.4))
    yb = rules["members"]["stud"]["t"]
    for o in w.openings:
        b = yb + (o.sill if o.kind == "window" else 0)
        ax.add_patch(Rectangle((o.offset, b), o.width, o.height, fill=False, ec="#1f77b4",
                               ls="--", lw=1))
        ax.plot([o.offset, o.offset + o.width], [b, b + o.height], color="#1f77b4", lw=.5)
        ax.plot([o.offset, o.offset + o.width], [b + o.height, b], color="#1f77b4", lw=.5)
        ax.text(o.offset + o.width / 2, b + o.height + 12,
                ar(f"{o.name} {o.width:.0f}×{o.height:.0f}"), ha="center", fontsize=7)
    for m in members:
        if m.note:
            ax.text((m.x0 + m.x1) / 2, m.y0 - 18, ar(m.note), ha="center", fontsize=7, color="#a33")
    studs = sorted((m.x0 + m.x1) / 2 for m in members if m.kind in ("stud", "corner_stud", "jamb"))
    for a, b in zip(studs, studs[1:]):
        ax.annotate("", (a, H + 25), (b, H + 25), arrowprops=dict(arrowstyle="<->", lw=.4))
        ax.text((a + b) / 2, H + 30, f"{b - a:.0f}", ha="center", fontsize=6)
    handles = [Rectangle((0, 0), 1, 1, fc=c) for c in COLORS.values()]
    ax.legend(handles, [ar(KIND_AR[k]) for k in COLORS], loc="upper center",
              bbox_to_anchor=(0.5, -0.02), ncol=8, fontsize=7, frameon=False)
    ax.set_xlim(-30, w.length + 30)
    ax.set_ylim(-40, H + 60)
    ax.set_aspect("equal")
    ax.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def _table(pdf, project, title, rows):
    fig = plt.figure(figsize=(8.27, 11.69))
    _title(fig, project, title)
    y = 0.88
    for k, v in rows:
        if k is None:
            y -= 0.015
            fig.text(0.94, y, ar(v), ha="right", fontsize=11, weight="bold", color="#6b4f3a")
        else:
            fig.text(0.94, y, ar(k), ha="right", fontsize=9)
            fig.text(0.45, y, ar(v), ha="right", fontsize=9)
        y -= 0.024
        if y < 0.05:
            pdf.savefig(fig)
            plt.close(fig)
            fig = plt.figure(figsize=(8.27, 11.69))
            y = 0.92
    pdf.savefig(fig)
    plt.close(fig)


def write_pdf(project, rules, members, heights, q, height_info, open_questions, path):
    p, c, roof = q["pallets"], q["cladding"], q["pallets"]["roof"]
    rows = [(None, "الارتفاع")]
    hi = height_info
    rows.append(("الارتفاع المطلوب / المعتمد", f"{hi['requested']:.0f} / {hi['suggested']:.0f} سم"))
    if hi["changed"]:
        rows.append(("سبب التعديل", hi["reason"]))
    rows += [(None, "السقف (جملون)"),
             ("الميل", f"{roof['pitch_deg']}°  (ارتفاع القمة {roof['rise']:.0f} سم)"),
             ("البحر / طول الجملون", f"{roof['span']:.0f} / {roof['ridge_length']:.0f} سم"),
             ("عدد المدادات 5×15", f"{roof['rafter_count']} ({roof['rafters_per_side']} لكل جهة)"),
             ("طول المداد", f"{roof['rafter_length']:.0f} سم — من طبلية {roof['stock_length']}")]
    if roof["warning"]:
        rows.append(("تنبيه", roof["warning"]))
    rows += [(None, "خطة تقطيع الطبليات 5×22.5"),
             ("الطريقة الأولى (مداد + عمود)",
              f"{p['method1_pallets']['count']} طبلية × {p['method1_pallets']['length']} سم"),
             ("الطريقة الثانية (3 أعمدة)",
              f"{p['method2_pallets']['count']} طبلية × {p['method2_pallets']['length']} سم")]
    if p["method2_long_pallets"]["count"]:
        rows.append(("الطريقة الثانية (طويلة)",
                     f"{p['method2_long_pallets']['count']} طبلية × {p['method2_long_pallets']['length']} سم"))
    rows += [("إجمالي الطبليات", str(p["total_pallets"])),
             ("إجمالي قطع 7×5", str(p["stud_pieces_total"]))]
    rows += [(None, "قائمة تقطيع 7×5 (الطول سم : العدد)")]
    rows += [(f"{L} سم", f"{n} قطعة") for L, n in p["stud_cut_list"]]
    rows += [(None, "التلبيس والكسوة"),
             ("ألواح تلبيس 2.5 سم", f"{c['boards']} لوح × {c['board_length']} سم"),
             ("مجموع طول الصفوف", f"{c['total_run_m']} م  ({c['faces']} وجه)"),
             ("أسمنت بورد 12 مم (122×244)", f"{c['cement_board_sheets']} لوح")]
    if q["insulation"]:
        rows.append(("فوم صخري 80 (120×60)", f"{q['insulation']['panels']} لوح"))
    else:
        rows.append(("العزل", "بدون (غير مطلوب)"))
    if project.notes:
        rows.append((None, "ملاحظات المشروع"))
        rows += [("•", n) for n in project.notes]
    if open_questions:
        rows.append((None, "نقاط تحتاج تأكيد من المصنع"))
        rows += [("؟", qq) for qq in open_questions]

    with PdfPages(path) as pdf:
        _plan(pdf, project, rules)
        for w in project.walls:
            _elevation(pdf, project, w, members[w.name], heights[w.name], rules)
        _table(pdf, project, "جدول الكميات", rows)
