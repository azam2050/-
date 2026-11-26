"""تقسيم أرض مشروع شاليهات بلجرشي (أرض غير منتظمة 6 أضلاع) — 6 شاليهات بنفس التصميم (80 م² دورين)
كل شاليه بحوش خاص مقفل بسواتر خشب 2.50 م + بوابة سيارة وباب مشاة على الممر الداخلي، ومدخل واحد من الشارع.
الإحداثيات بالمتر في إطار مدوّر: u على الضلع الجنوبي (E→D)، v عمودي عليه."""
import sys, math
sys.path.insert(0, ".")
import watad.sheets  # noqa: F401  (الخطوط والإعدادات)
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP, Rectangle, Circle, FancyArrow
from shapely.geometry import Polygon, LineString, box
from shapely.affinity import translate, rotate
from watad.sheets import new_page, BRAND, BRAND_SOFT, draw_logo

out = sys.argv[1]
# ---- حدود الأرض (من المخطط المساحي، مقاسة على الرسم بمقياس الضلع 47.50 م)
E, D, C, B, A, F = (0, 0), (47.59, 0), (42.88, 17.75), (34.70, 29.10), (19.85, 41.73), (-3.80, 39.25)
plot = Polygon([E, D, C, B, A, F])
road_line = LineString([A, B, C, D])
flood_line = LineString([F, A])
SB = 2.0                                        # ارتداد الشارع (المقتطع المخطط) + ارتداد مجرى السيل
setback = road_line.buffer(SB, cap_style=2, join_style=2).union(flood_line.buffer(SB, cap_style=2, join_style=2))
net = plot.difference(setback)
DRV = (15.0, 21.0)                               # الممر الداخلي (عرض 6.00 م)
drive = net.intersection(box(-10, DRV[0], 60, DRV[1]))
units = []
row1 = [(-5, 10.9), (10.9, 21.6), (21.6, 32.3), (32.3, 60)]
for k, (u0, u1) in enumerate(row1, 1):
    units.append((k, net.intersection(box(u0, 0, u1, DRV[0])), "S"))
row2 = [(-6, 11.9), (11.9, 24.2)]
for k, (u0, u1) in enumerate(row2, 5):
    units.append((k, net.intersection(box(u0, DRV[1], u1, 45)), "N"))
plaza = net.intersection(box(24.2, DRV[1], 60, 45))
# ---- بصمة الشاليه (من مخطط التصميم: 9.15 × 5.50 + بروز الشباك المضلع 0.50 + 0.75)
fp = [(0, 0), (9.15, 0), (9.15, 3.35), (7.75, 3.35), (7.75, 5.28), (7.015, 6.015), (5.765, 6.015),
      (5.015, 5.265), (5.015, 4.765), (3.215, 4.765), (3.215, 5.50), (0, 5.50)]


def chalet(u_c, v_back, facing):
    """facing S: الواجهة (البروز) لجهة +v (الممر) والظهر على الجدار الجنوبي. N: العكس."""
    pts = [(x - 4.575, y) for x, y in fp]
    if facing == "S":
        return [(u_c + x, v_back + y) for x, y in pts]
    return [(u_c - x, v_back - y) for x, y in pts]


fig = new_page((16.54, 11.69))
ax = fig.add_axes([0.03, 0.10, 0.66, 0.84]); ax.set_aspect("equal"); ax.axis("off")
WOOD, SCR = "#C8A27A", "#7A5230"
# خارج الأرض: الشارع ومجرى السيل والجيران
rd = Polygon([A, B, C, D, (D[0] + 6 * 0.778, D[1] + 6 * 0.628), (C[0] + 6 * 0.89, C[1] + 6 * 0.46),
              (B[0] + 6 * 0.65, B[1] + 6 * 0.76), (A[0] + 6 * 0.16, A[1] + 6 * 0.99)])
ax.add_patch(MP(list(rd.exterior.coords), fc="#D9D9D9", ec="#888", lw=0.8))
ax.text(44.5, 32.0, "شارع / خط سيارات عرض 6.00 م", rotation=-50, ha="center", va="center", fontsize=11, color="#444")
fl = Polygon([F, A, (A[0] - 0.9, A[1] + 9), (F[0] - 0.9, F[1] + 9)])
ax.add_patch(MP(list(fl.exterior.coords), fc="#DCEBF5", ec="#7FA7C4", lw=0.8, hatch="..."))
ax.text(7.5, 45.0, "مجرى السيل عرض 9.00 م", rotation=6, ha="center", fontsize=10, color="#3D6E91")
ax.text(23.8, -3.9, "جار — ملك خاص", ha="center", fontsize=9, color="#777")
ax.text(-5.6, 19.5, "جار — ملك خاص", rotation=84.5, ha="center", fontsize=9, color="#777")
# الأرض + الارتداد
ax.add_patch(MP(list(plot.exterior.coords), fc="#EEF3E6", ec="k", lw=2.2, zorder=1))
sbp = plot.intersection(setback)
for g in getattr(sbp, "geoms", [sbp]):
    ax.add_patch(MP(list(g.exterior.coords), fc="none", ec="#A0559C", lw=0.4, hatch="////", zorder=1.1))
# الممر الداخلي + ساحة المدخل ومواقف الزوار
for g in [drive, plaza]:
    ax.add_patch(MP(list(g.exterior.coords), fc="#CFCFCF", ec="#777", lw=0.8, zorder=2))
ax.plot([-1.5, 39], [18, 18], color="white", lw=1.2, ls=(0, (6, 5)), zorder=2.1)
ax.text(14, 18.35, "ممر داخلي للسيارات عرض 6.00 م", ha="center", fontsize=9.5, color="#333", zorder=3)
for k in range(4):                                   # مواقف زوار بالساحة
    x0 = 26.0 + k * 2.6
    ax.add_patch(Rectangle((x0, 21.4), 2.5, 5.0, fc="#E3E3E3", ec="#666", lw=0.6, zorder=2.2))
ax.text(31.2, 27.0, "مواقف زوار", ha="center", fontsize=8.5, zorder=3)
ax.add_patch(Rectangle((35.8, 21.6), 3.0, 3.0, fc="#F4E7D3", ec=SCR, lw=0.9, zorder=2.2))
ax.text(37.3, 23.1, "استقبال\nوحارس", ha="center", va="center", fontsize=7, zorder=3)
# البوابة الرئيسية على الشارع
gx, gy = 39.6, 18.0
ax.add_patch(FancyArrow(gx + 4.5, gy, -3.2, 0, width=0.25, head_width=1.1, color="#2E7D32", zorder=4))
ax.text(gx + 3.0, gy + 1.4, "المدخل الرئيسي", fontsize=9, color="#2E7D32", weight="bold", ha="center", zorder=4)
# الوحدات
total_unit = 0
rows = []
for k, poly, facing in units:
    total_unit += poly.area
    ax.add_patch(MP(list(poly.exterior.coords), fc="#F7F9F2", ec="none", zorder=1.5))
    (u0, v0, u1, v1) = poly.bounds
    if facing == "S":
        uc = (max(u0, -1.0) + min(u1, 43.0)) / 2 if k == 4 else (u0 + u1) / 2
        if k == 1:
            uc = 5.45
        cp = chalet(uc, 1.0, "S")
        park = (uc + 4.575 - 2.8, 9.4, 2.8, 5.4); seat = (uc - 4.4, 9.6, 3.6, 3.2)
        gate_v = DRV[0]
    else:
        uc = (max(u0, -1.6) + u1) / 2 if k == 5 else 17.6
        vb = 37.3 if k == 5 else 35.6
        cp = chalet(uc, vb, "N")
        park = (uc - 4.575, DRV[1] + 0.2, 2.8, 5.4); seat = (uc + 0.9, DRV[1] + 0.8, 3.6, 3.0)
        gate_v = DRV[1]
    # الحديقة + الموقف + الجلسة
    ax.add_patch(Rectangle(park[:2], park[2], park[3], fc="#E3E3E3", ec="#666", lw=0.6, zorder=2.3))
    ax.text(park[0] + park[2] / 2, park[1] + park[3] / 2, "موقف", rotation=90, ha="center", va="center", fontsize=6.5, zorder=3)
    ax.add_patch(Rectangle(seat[:2], seat[2], seat[3], fc="#F1E2C8", ec=SCR, lw=0.6, zorder=2.3))
    ax.text(seat[0] + seat[2] / 2, seat[1] + seat[3] / 2, "جلسة\nخارجية", ha="center", va="center", fontsize=6.3, zorder=3)
    for t in (0.25, 0.75):
        ax.add_patch(Circle((seat[0] + seat[2] * t, (seat[1] + seat[3] + 1.0) if facing == "S" else (seat[1] - 1.0)),
                            0.7, fc="#8DBF6A", ec="#4F7A2A", lw=0.5, zorder=2.4))
    # الشاليه
    ax.add_patch(MP(cp, fc="#B5835A", ec="k", lw=1.0, zorder=3))
    cx = sum(p[0] for p in cp) / len(cp); cy = sum(p[1] for p in cp) / len(cp)
    ax.text(cx, cy, f"شاليه {k}", ha="center", va="center", fontsize=10, color="white", weight="bold", zorder=4)
    # السواتر: حدود الوحدة (خشب 2.50 م) — والضلع على الممر ساتر ببوابة سيارة + باب مشاة
    ax.add_patch(MP(list(poly.exterior.coords), fill=False, ec=SCR, lw=2.6, zorder=3.5))
    g0 = park[0] - 0.1
    ax.plot([g0, g0 + 3.0], [gate_v, gate_v], color="#EEF3E6", lw=3.4, zorder=3.6)
    ax.plot([g0, g0 + 3.0], [gate_v, gate_v], color="#2E7D32", lw=1.2, zorder=3.7)
    pg = (seat[0] + 0.3) if facing == "S" else (uc + 3.2)
    ax.plot([pg, pg + 1.0], [gate_v, gate_v], color="#EEF3E6", lw=3.4, zorder=3.6)
    ax.plot([pg, pg + 1.0], [gate_v, gate_v], color="#1565C0", lw=1.2, zorder=3.7)
    lab_v = (v0 + 0.5) if facing == "N" and False else (v1 - 1.2 if facing == "S" else v0 + 7.5)
    rows.append((k, poly.area))
# حدود الأرض فوق كل شي
ax.add_patch(MP(list(plot.exterior.coords), fill=False, ec="k", lw=2.4, zorder=5))
# أطوال الأضلاع
L = [(E, D, "47.50"), (D, C, "18.40"), (C, B, "14.00"), (B, A, "19.50"), (A, F, "23.80"), (F, E, "39.40")]
for p, q, t in L:
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
    if ang > 90 or ang < -90:
        ang += 180
    nx, ny = -(q[1] - p[1]), q[0] - p[0]; nn = math.hypot(nx, ny)
    off = -1.6
    ax.text(mx + nx / nn * off, my + ny / nn * off, f"{t} م", rotation=ang, ha="center", va="center", fontsize=10.5,
            color="#B00000", weight="bold", zorder=6)
for n, P_ in zip("123456", [D, E, F, A, B, C]):
    ax.add_patch(Circle(P_, 0.9, fc="white", ec="#C2185B", lw=1.2, zorder=6))
    ax.text(*P_, n, ha="center", va="center", fontsize=8, color="#C2185B", zorder=7)
# سهم الشمال (اتجاه الشمال بالمخطط المساحي)
nx0, ny0 = 50.5, 38.0
a = math.radians(46.7)
ax.add_patch(FancyArrow(nx0, ny0, 4 * math.cos(a), 4 * math.sin(a), width=0.35, head_width=1.4, color="k"))
ax.text(nx0 + 6.8 * math.cos(a), ny0 + 6.8 * math.sin(a), "ش", fontsize=14, ha="center", va="center")
ax.set_xlim(-8, 58); ax.set_ylim(-5, 51)
# ---- اللوحة الجانبية: الجدول والملاحظات
fig.text(0.86, 0.93, "تقسيم الأرض — مشروع 6 شاليهات", ha="center", fontsize=17, weight="bold", color=BRAND)
fig.text(0.86, 0.905, "بلجرشي — كل شاليه 80 م² (دورين) بحوش خاص وسواتر", ha="center", fontsize=10.5, color="#555")
tab = fig.add_axes([0.705, 0.47, 0.26, 0.40]); tab.axis("off")
data = [["البند", "المساحة (م²)"], ["مساحة الأرض", f"{plot.area:,.0f}"],
        ["ارتداد الشارع ومجرى السيل", f"{plot.intersection(setback).area:,.0f}"],
        ["الممر الداخلي + ساحة المدخل والمواقف", f"{(drive.area + plaza.area):,.0f}"]]
data += [[f"حوش شاليه {k} (مع الشاليه)", f"{a_:,.0f}"] for k, a_ in rows]
data += [["بصمة الشاليه (أرضي)", "40 × 6 = 240"], ["مسطح البناء (6 × 80)", "480"]]
t = tab.table(cellText=data, loc="upper center", cellLoc="center", colWidths=[0.66, 0.34])
t.auto_set_font_size(False); t.set_fontsize(9.5); t.scale(1, 1.55)
for (r, c), cell in t.get_celld().items():
    cell.set_edgecolor("#999")
    if r == 0:
        cell.set_facecolor(BRAND); cell.get_text().set_color("white"); cell.get_text().set_weight("bold")
notes = ["• حدود الأرض من المخطط المساحي (6 أضلاع) — تُعتمد الأطوال بعد الرفع المساحي.",
         "• مدخل واحد من الشارع + ممر داخلي 6.00 م يخدم كل الشاليهات.",
         "• كل شاليه بحوش خاص مقفل بسواتر خشب 2.50 م (خصوصية كاملة بين الشاليهات).",
         "• لكل حوش بوابة سيارة 3.00 م + باب مشاة على الممر، وموقف خاص وجلسة خارجية وتشجير.",
         "• الشاليه بنفس التصميم المعتمد بالضبط: 9.15 × 5.50 م + بروز الشباك، 80 م² دورين.",
         "• ساحة المدخل: مواقف زوار + غرفة استقبال/حارس."]
fig.text(0.965, 0.44, "\n".join(notes), ha="right", va="top", fontsize=9.2, linespacing=1.75)
# مفتاح
ky = 0.165
for i, (fc, ec, lw, txt) in enumerate([("none", SCR, 2.6, "ساتر خشب 2.50 م"), ("#B5835A", "k", 1, "الشاليه"),
                                       ("#CFCFCF", "#777", 0.8, "ممر / مواقف"), ("none", "#A0559C", 0.4, "ارتداد")]):
    fig.patches.append(Rectangle((0.72 + (i % 2) * 0.13, ky - (i // 2) * 0.03), 0.022, 0.016, transform=fig.transFigure,
                                 fc=fc, ec=ec, lw=lw, hatch="////" if txt == "ارتداد" else None))
    fig.text(0.746 + (i % 2) * 0.13, ky + 0.008 - (i // 2) * 0.03, txt, fontsize=8.5, va="center")
# إطار عنوان مبسط
fig.patches.append(Rectangle((0.022, 0.026), 0.956, 0.058, transform=fig.transFigure, fc="white", ec=BRAND, lw=1.3))
fig.patches.append(Rectangle((0.80, 0.026), 0.178, 0.058, transform=fig.transFigure, fc=BRAND_SOFT, ec=BRAND, lw=1.0))
FW, FH = fig.get_size_inches()
draw_logo(fig, 0.958, 0.055, 0.5)
fig.text(0.935, 0.063, "مصنع وتد الأخشاب", ha="right", fontsize=12, weight="bold", color=BRAND)
fig.text(0.935, 0.040, "Watad Wood Factory", ha="right", fontsize=8.5, color="#6B5A4C")
for x, h, v in [(0.70, "المشروع / العميل", "مشروع شاليهات استثمارية — بلجرشي\nعميل — بلجرشي"),
                (0.46, "عنوان اللوحة", "تقسيم الأرض والموقع العام"), (0.30, "المقياس", "1:300"),
                (0.18, "التاريخ", "2026-11-26"), (0.07, "رقم اللوحة", "S-01")]:
    fig.text(x, 0.073, h, ha="center", fontsize=7.5, color="#888")
    fig.text(x, 0.045, v, ha="center", fontsize=10.5, weight="bold", va="center")
fig.savefig(out, dpi=150)
fig.savefig(out.replace(".png", ".pdf"))
print("ok", round(plot.area), [round(a_) for _, a_ in rows], round(drive.area + plaza.area))
