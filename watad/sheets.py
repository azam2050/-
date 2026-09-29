"""لوحات المشروع PDF بالعربي — نفس ترتيب المكتب الهندسي + لوحات الورشة.

1 المسقط مع الفرش والأبعاد | 2-3 الواجهات | 4 السقف والقطاع | 5 جدول الفتحات
6 المساحات والتسعير | 7.. تأطير الجدران | كميات وخطة الطبليات | مراجعة التصميم
"""
import math

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Arc, Ellipse, FancyBboxPatch, Polygon, Rectangle
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from .model import outer_bbox, wall_thickness
from .roof import cross_gables, rafter_positions, roof_geometry

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["pdf.fonttype"] = 42      # خطوط TrueType مضمّنة — تفتح في كل برامج PDF والجوالات
plt.rcParams["hatch.linewidth"] = 0.5
A3 = (16.54, 11.69)
BROWN = "#5a3a22"
C_WIN, C_DOOR, C_FURN, C_ROOF, C_LVL, C_DIM = "#1f3fff", "#10a010", "#e000e0", "#f08000", "#10b010", "#222"
FRAME_COLORS = {"bottom_plate": "#b5651d", "top_plate": "#b5651d", "stud": "#d2a679",
                "corner_stud": "#8b5a2b", "jamb": "#5b7fa6", "header": "#5b7fa6",
                "sill": "#5b7fa6", "cripple": "#9c6fb0"}
KIND_AR = {"bottom_plate": "قاعدة سفلية", "top_plate": "علوي", "stud": "عمود",
           "corner_stud": "عمود زاوية", "jamb": "جنب فتحة", "header": "رأس فتحة",
           "sill": "جلسة شباك", "cripple": "عمود قصير"}


# ---------------------------------------------------------------- أدوات رسم عامة
def new_page(size=A3):
    fig = plt.figure(figsize=size)
    fig.patches.append(Rectangle((0.02, 0.025), 0.96, 0.955, transform=fig.transFigure,
                                 fill=False, lw=1.2, ec="k"))
    return fig


def drawing_ax(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


def footer(fig, ctx, sheet, i, n):
    P = ctx["project"]
    fig.text(0.5, 0.04, f"مصنع وتد الأخشاب  |  {P.title}  |  {sheet}  |  صفحة {i} / {n}",
             ha="center", fontsize=10)
    fig.text(0.035, 0.04, "WATAD", fontsize=11, weight="bold", color=BROWN)


def title(ax, text, sub=""):
    ax.set_title(text + (f"\n{sub}" if sub else ""), fontsize=15, pad=12)


def dim(ax, a, b, off, text=None, fs=7, color=C_DIM, ext=True):
    """خط بُعد بين a و b مُزاح off على يسار الاتجاه a→b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return
    nx, ny = -dy / L, dx / L
    pa = (a[0] + nx * off, a[1] + ny * off)
    pb = (b[0] + nx * off, b[1] + ny * off)
    ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color=color, lw=0.6)
    k = 6 if off >= 0 else -6
    for p, q in ((a, pa), (b, pb)):
        if ext:
            ax.plot([p[0] + nx * k * 0.6, q[0] + nx * k], [p[1] + ny * k * 0.6, q[1] + ny * k],
                    color=color, lw=0.35)
        s = 5
        ax.plot([q[0] - (dx / L + nx) * s, q[0] + (dx / L + nx) * s],
                [q[1] - (dy / L + ny) * s, q[1] + (dy / L + ny) * s], color=color, lw=0.9)
    ang = math.degrees(math.atan2(dy, dx))
    if ang > 90.1 or ang < -89.9:
        ang -= 180
    t = f"{L:.0f}" if text is None else text
    sgn = 1 if off >= 0 else -1
    mx, my = (pa[0] + pb[0]) / 2 + nx * 9 * sgn, (pa[1] + pb[1]) / 2 + ny * 9 * sgn
    ax.text(mx, my, t, rotation=ang, ha="center", va="center", fontsize=fs, color=color,
            rotation_mode="anchor")


def chain(ax, pts, off, fs=7):
    """سلسلة أبعاد على نقاط متتالية على خط واحد."""
    for a, b in zip(pts, pts[1:]):
        dim(ax, a, b, off, fs=fs)


def level(ax, x, y, value, label, below=False):
    ax.plot([x - 45, x + 45], [y, y], color=C_LVL, lw=0.7)
    if below:
        ax.add_patch(Polygon([(x - 7, y - 11), (x + 7, y - 11), (x, y)], closed=True, fill=False,
                             ec=C_LVL, lw=0.7))
        ax.text(x, y - 14, f"{value:+.2f}", ha="center", va="top", fontsize=8, color=C_LVL)
        ax.text(x, y - 32, label, ha="center", va="top", fontsize=6.5, color=C_LVL)
        return
    ax.add_patch(Polygon([(x - 7, y + 11), (x + 7, y + 11), (x, y)], closed=True, fill=False,
                         ec=C_LVL, lw=0.7))
    ax.text(x, y + 15, f"{value:+.2f}" if abs(value) > 0.001 else "0.00", ha="center", va="bottom",
            fontsize=8, color=C_LVL)
    ax.text(x, y + 33, label, ha="center", va="bottom", fontsize=6.5, color=C_LVL)


BRAND = "#3A2314"          # بني الشعار
BRAND_SOFT = "#F4EEE7"
RULE = "#B9AEA3"
OFFER = "#0B6B3A"          # أخضر اليوم الوطني


def table(ax, headers, rows, col_w, fs=9, row_h=1.0, head_fc=None, bold_last=0, wrap=None, zebra=True):
    """جدول من اليمين لليسار بطابع المكاتب الهندسية: رأس بلون الشعار، صفوف متناوبة، إجماليات مظللة.
    col_w بنفس ترتيب headers (من اليمين). wrap: حروف لكل وحدة عرض لتلفيف النص الطويل."""
    import textwrap
    total = sum(col_w)
    allrows = [headers] + rows
    if wrap:
        allrows = [[textwrap.fill(str(v), max(4, int(col_w[c] * wrap))) for c, v in enumerate(r)]
                   for r in allrows]
    heights = [row_h * max(1, max(str(v).count("\n") + 1 for v in r) * 0.8 + 0.2) for r in allrows]
    ax.set_xlim(-0.02, total + 0.02)
    ax.set_ylim(-sum(heights) - 0.02, 0.02)
    ax.axis("off")
    xs = [total]
    for w in col_w:
        xs.append(xs[-1] - w)
    y = 0
    n = len(allrows)
    for r, cells in enumerate(allrows):
        h = heights[r]
        y -= h
        head = r == 0
        bold = bool(bold_last) and r >= n - bold_last
        fc = BRAND if head else (BRAND_SOFT if bold else ("#FAF8F5" if zebra and r % 2 == 0 else "white"))
        tc = "white" if head else "#1E1E1E"
        ax.add_patch(Rectangle((0, y), total, h, fc=fc, ec="none"))
        for c, val in enumerate(cells):
            if c:
                ax.plot([xs[c], xs[c]], [y, y + h], color="white" if head else RULE, lw=0.5)
            ax.text((xs[c] + xs[c + 1]) / 2, y + h / 2, str(val), ha="center", va="center", color=tc,
                    fontsize=fs, weight="bold" if (bold or head) else "normal", linespacing=1.3)
        ax.plot([0, total], [y, y], color=BRAND if bold and r == n - bold_last else RULE,
                lw=1.0 if bold and r == n - bold_last else 0.5)
    ax.add_patch(Rectangle((0, y), total, -y, fill=False, ec=BRAND, lw=1.3))


# ---------------------------------------------------------------- الشعار وإطار اللوحة
_LOGO = None


def logo_polys():
    global _LOGO
    if _LOGO is None:
        import json
        from pathlib import Path
        f = Path(__file__).resolve().parent.parent / "assets" / "watad_logo.json"
        _LOGO = json.loads(f.read_text()) if f.exists() else {"polys": [], "color": BRAND}
    return _LOGO


def draw_logo(fig, cx, cy, size_in):
    """يرسم الشعار (متجه) في إحداثيات الشكل: المركز cx,cy وحجم بالإنش."""
    W, H = fig.get_size_inches()
    w, h = size_in / W, size_in / H
    ax = fig.add_axes([cx - w / 2, cy - h / 2, w, h])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    L = logo_polys()
    for pl in L["polys"]:
        ax.add_patch(Polygon(pl, closed=True, fc=L["color"], ec="none"))
    ax._watad_fixed = True
    ax.set_zorder(20)
    ax.patch.set_alpha(0)
    return ax


def title_block(fig, ctx, sheet, code, i, n, scale="1:50"):
    """إطار عنوان اللوحة بطابع المكاتب الهندسية أسفل كل صفحة."""
    P = ctx["project"]
    m = P.meta
    x0, x1, y0, y1 = 0.022, 0.978, 0.026, 0.084
    W = x1 - x0
    fig.patches.append(Rectangle((x0, y0), W, y1 - y0, transform=fig.transFigure, fc="white", ec=BRAND, lw=1.3))
    cols = [(0.22, "brand"), (0.27, "المشروع / العميل"), (0.2, "عنوان اللوحة"), (0.08, "المقياس"),
            (0.1, "التاريخ"), (0.13, "رقم اللوحة")]
    tot = sum(c for c, _ in cols)
    x = x1
    for frac, key in cols:
        w = W * frac / tot
        xa = x - w
        if x != x1:
            fig.lines.append(plt.Line2D([x, x], [y0, y1], transform=fig.transFigure, color=BRAND, lw=0.8))
        cx = (xa + x) / 2
        if key == "brand":
            fig.patches.append(Rectangle((xa, y0), w, y1 - y0, transform=fig.transFigure, fc=BRAND_SOFT,
                                         ec="none"))
            FW, FH = fig.get_size_inches()
            lg = min((y1 - y0) * FH * 0.78, 0.55)          # حجم الشعار بالإنش (ثابت في الطولي والعرضي)
            pad = 0.12 / FW
            draw_logo(fig, x - pad - lg / FW / 2, (y0 + y1) / 2, lg)
            tx = x - 2 * pad - lg / FW
            fig.text(tx, (y0 + y1) / 2 + 0.1 / FH, "مصنع وتد الأخشاب", ha="right", va="center",
                     fontsize=12, weight="bold", color=BRAND)
            fig.text(tx, (y0 + y1) / 2 - 0.13 / FH, "Watad Wood Factory", ha="right", va="center",
                     fontsize=8.5, color="#6B5A4C")
        else:
            val = {"المشروع / العميل": f"{P.title}\n{P.client}", "عنوان اللوحة": sheet, "المقياس": scale,
                   "التاريخ": str(m.get("date", "")), "رقم اللوحة": f"{code}   ({i}/{n})"}[key]
            fig.text(x - 0.006, y1 - 0.006, key, ha="right", va="top", fontsize=7, color="#7A6A5C")
            fig.text(cx, (y0 + y1) / 2 - 0.006, val, ha="center", va="center", fontsize=10 if "\n" not in val else 8.5,
                     weight="bold", color="#1E1E1E", linespacing=1.4)
        x = xa


def lift_content(fig, bottom=0.095):
    """يرفع محتوى الصفحة فوق إطار العنوان."""
    k = (0.975 - bottom) / 0.975
    for ax in fig.axes:
        if getattr(ax, "_watad_fixed", False):
            continue
        b = ax.get_position()
        ax.set_position([b.x0, bottom + b.y0 * k, b.width, b.height * k])
    for t in fig.texts:
        x, y = t.get_position()
        t.set_position((x, bottom + y * k))


# ---------------------------------------------------------------- المسقط
def wall_shapes(P, rules):
    half = wall_thickness(rules) / 2
    polys, holes = [], []
    for w in P.walls:
        polys.append(LineString([w.start, w.end]).buffer(half, cap_style="square"))
        for o in w.openings:
            a, b = w.point(o.offset, -half - 1), w.point(o.offset + o.width, half + 1)
            c, d = w.point(o.offset, half + 1), w.point(o.offset + o.width, -half - 1)
            from shapely.geometry import Polygon as SP
            holes.append(SP([a, d, b, c]))
    return unary_union(polys).difference(unary_union(holes))


def _draw_shape(ax, geom, **kw):
    geoms = getattr(geom, "geoms", [geom])
    for g in geoms:
        ax.add_patch(Polygon(list(g.exterior.coords), closed=True, **kw))
        for hole in g.interiors:
            ax.add_patch(Polygon(list(hole.coords), closed=True, fc="white", ec=kw.get("ec", "k"),
                                 lw=kw.get("lw", 0.8)))


def draw_openings_plan(ax, P, rules):
    half = wall_thickness(rules) / 2
    for w in P.walls:
        nx, ny = w.n
        for o in w.openings:
            a, b = o.offset, o.offset + o.width
            if o.kind == "door" and o.leaves == 0:
                continue
            if o.kind == "window" or o.style in ("sliding", "fixed"):
                for s in (-half, 0, half):
                    p, q = w.point(a, s), w.point(b, s)
                    ax.plot([p[0], q[0]], [p[1], q[1]], color=C_WIN, lw=0.9 if s else 0.6)
                for t in (a, b):
                    p, q = w.point(t, -half), w.point(t, half)
                    ax.plot([p[0], q[0]], [p[1], q[1]], color=C_WIN, lw=0.6)
            else:
                side = half if o.swing == "left" else -half
                sg = 1 if o.swing == "left" else -1
                leaves = [(a, 1, o.width / o.leaves)]
                if o.leaves == 2:
                    leaves.append((b, -1, o.width / 2))
                for hinge_t, dirn, lw_ in leaves:
                    h = w.point(hinge_t, side)
                    tip = w.point(hinge_t, side + sg * lw_)
                    ax.plot([h[0], tip[0]], [h[1], tip[1]], color=C_DOOR, lw=1)
                    ux, uy = w.u
                    ang_u = math.degrees(math.atan2(uy * dirn, ux * dirn))
                    ang_n = math.degrees(math.atan2(ny * sg, nx * sg))
                    lo, hi = sorted((ang_u, ang_n))
                    if hi - lo > 180:
                        lo, hi = hi, lo + 360
                    ax.add_patch(Arc(h, 2 * lw_, 2 * lw_, theta1=lo, theta2=hi, color=C_DOOR, lw=0.7))


def draw_furniture(ax, P):
    for f in P.furniture:
        x0, y0, x1, y1 = f.rect
        w, h = x1 - x0, y1 - y0
        if f.shape == "wc":
            ax.add_patch(Ellipse(((x0 + x1) / 2, (y0 + y1) / 2), w, h, fill=False, ec=C_FURN, lw=0.6))
        elif f.shape == "basin":
            ax.add_patch(Rectangle((x0, y0), w, h, fill=False, ec=C_FURN, lw=0.6))
            ax.add_patch(Ellipse(((x0 + x1) / 2, (y0 + y1) / 2), w * .6, h * .6, fill=False,
                                 ec=C_FURN, lw=0.5))
        else:
            ax.add_patch(Rectangle((x0, y0), w, h, fill=False, ec=C_FURN, lw=0.6))
            if f.shape == "shower":
                ax.plot([x0, x1], [y0, y1], color=C_FURN, lw=0.4)
                ax.plot([x0, x1], [y1, y0], color=C_FURN, lw=0.4)
        if f.name:
            rot = 90 if h > w * 1.6 and w < 100 else 0
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, f.name, ha="center", va="center", fontsize=7,
                    rotation=rot)


def floor_view(P, f):
    """نسخة من المشروع فيها عناصر دور واحد فقط (للمسقط)."""
    import dataclasses
    lev = P.level(f)
    return dataclasses.replace(
        P, walls=[w for w in P.walls if w.floor == f], rooms=[r for r in P.rooms if r.floor == f],
        furniture=[x for x in P.furniture if x.floor == f],
        decks=[d for d in P.decks if (d.level == 0 and f == 0) or (d.level and abs(d.level - lev) < 1)])


def draw_stairs_plan(ax, P_full, f):
    from .model3d import stair_geometry
    for st in P_full.stairs:
        base = st.get("from", 0)
        if f not in (base, base + 1):
            continue
        steps, landing, r, n = stair_geometry(P_full, st)
        cut_z = 120
        for x0, y0, x1, y1, zt in steps + [landing]:
            dashed = f == base and zt > cut_z
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="#6b4f3a",
                                   lw=0.4 if dashed else 0.7, ls=(0, (4, 3)) if dashed else "-"))
        x0, y0, x1, y1 = st["rect"]
        fw = st.get("flight_w", 90)
        first_east = st.get("first", "east") == "east"
        fa = (x1 - fw / 2) if first_east else (x0 + fw / 2)
        fb = (x0 + fw / 2) if first_east else (x1 - fw / 2)
        ly = landing[1]
        if f == base:
            ax.annotate("", (fa, ly - 10), (fa, y0 + 8), arrowprops=dict(arrowstyle="->", color="#b04020", lw=0.9))
            ax.text(fa, y0 + 20, "صعود", ha="center", va="bottom", fontsize=7, color="#b04020", rotation=90)
            ax.plot([fa - fw / 2, fa + fw / 2], [y0 + 4 * 27 + 10, y0 + 4 * 27 - 10], color="k", lw=0.8)
        else:
            ax.annotate("", (fb, y0 + 30), (fb, ly - 10), arrowprops=dict(arrowstyle="->", color="#b04020", lw=0.9))
            ax.text(fb, ly - 30, "نزول", ha="center", va="top", fontsize=7, color="#b04020", rotation=90)
            a, b = (x0 + fw, x1) if first_east else (x0, x1 - fw)
            ax.plot([a, b], [y0, y0], color="#6b4f3a", lw=2.2)
        ax.text((x0 + x1) / 2, landing[1] + (landing[3] - landing[1]) / 2,
                f"{n} قائمة × {r:.1f} سم", ha="center", va="center", fontsize=6.5, color="#6b4f3a")


def plan_sheet(ctx, floor=0):
    P_full = ctx["project"]
    P, rules = floor_view(P_full, floor), ctx["rules"]
    fname = P_full.floor_list[floor]["name"]
    half = wall_thickness(rules) / 2
    x0, y0, x1, y1 = outer_bbox(P, rules)
    ey0 = min([y0] + [d.rect[1] - (120 if d.stairs else 0) for d in P.decks])
    ex1 = max([x1] + [d.rect[2] for d in P.decks])
    portrait = (y1 - ey0) >= (ex1 - x0) * 0.95
    fig = new_page((A3[1], A3[0]) if portrait else A3)
    ax = drawing_ax(fig, [0.06, 0.08, 0.88, 0.84])
    multi = len(P_full.floor_list) > 1
    title(ax, "المسقط الأفقي مع الفرش" + (f" — {fname}" if multi else ""),
          "الأبعاد بالسنتيمتر - الجدران: قوائم 7×5 + تلبيس 2.5 من الجهتين (12 سم)"
          + (f"  |  منسوب الأرضية {P_full.level(floor) / 100:+.2f}" if multi else ""))

    for r in P.rooms:
        if r.wet:
            ax.add_patch(Rectangle((r.rect[0], r.rect[1]), r.w, r.h, fc="#eef6ff", ec="none"))
    for d in P.decks:      # التراس / الدكة
        dx0, dy0, dx1, dy1 = d.rect
        ax.add_patch(Rectangle((dx0, dy0), dx1 - dx0, dy1 - dy0, fc="#f6ecdf", ec="#8b5a2b", lw=0.8))
        yy = dy0 + 14
        while yy < dy1:
            ax.plot([dx0, dx1], [yy, yy], color="#d9c2a5", lw=0.4)
            yy += 14
        ax.text((dx0 + dx1) / 2, (dy0 + dy1) / 2, f"{d.name}  {(dx1 - dx0) / 100:.2f} × {(dy1 - dy0) / 100:.2f} م",
                ha="center", va="center", fontsize=10, color="#5a3a22")
        if d.stairs and d.stairs.get("side") == "S":
            n = max(1, math.ceil(d.height / 15))
            a, b = dx0 + d.stairs["offset"], dx0 + d.stairs["offset"] + d.stairs["width"]
            for k in range(n):
                ax.add_patch(Rectangle((a, dy0 - 30 * (k + 1)), b - a, 30, fc="white", ec="#8b5a2b", lw=0.6))
            ax.text((a + b) / 2, dy0 - 30 * n - 12, f"{n} درجات × {d.height / n:.0f} سم", ha="center",
                    va="top", fontsize=8)
            y0 = min(y0, dy0 - 30 * n - 30)
        x0, x1, y0 = min(x0, dx0), max(x1, dx1), min(y0, dy0)
    for pt in P.posts:
        ax.add_patch(Rectangle((pt["at"][0] - 8, pt["at"][1] - 8), 16, 16, fc="#8b5a2b", ec="k", lw=0.6))
    _draw_shape(ax, wall_shapes(P, rules), fc="white", ec="k", lw=0.9, hatch="////")
    draw_openings_plan(ax, P, rules)
    draw_furniture(ax, P)
    draw_stairs_plan(ax, P_full, floor)
    for r in P.rooms:
        cx, cy = r.label or ((r.rect[0] + r.rect[2]) / 2, (r.rect[1] + r.rect[3]) / 2)
        big = r.area_m2 > 4 and r.kind != "stair"
        rot = 90 if r.h > 2 * r.w and r.w < 100 else 0
        ax.text(cx, cy + (8 if big else 0), r.name, ha="center", va="bottom", fontsize=12 if big else 8,
                rotation=rot)
        if big:
            ax.text(cx, cy, f"{r.w / 100:.2f} × {r.h / 100:.2f} م  |  {r.area_m2:.1f} م2",
                    ha="center", va="top", fontsize=8)
    # رموز الفتحات
    for w in P.walls:
        for o in w.openings:
            p = w.point(o.offset + o.width / 2, -(half + 14) if w.exterior else half + 14)
            ax.text(*p, o.code, ha="center", va="center", fontsize=8,
                    color=C_WIN if o.kind == "window" else C_DOOR)
    # سلاسل الأبعاد الخارجية
    for w in P.exterior_walls:
        ts = [-half] + sorted(t for o in w.openings for t in (o.offset, o.offset + o.width)) \
            + [w.length + half]
        pts = [w.point(t, -half) for t in ts]
        # dim() يزيح لليسار؛ الخارج على يمين الجدار → نعكس الاتجاه
        chain(ax, pts[::-1], 45)
        dim(ax, pts[-1], pts[0], 90, fs=8)
    # محاور الشبكة (أرقام للجدران الرأسية، حروف للأفقية) مثل لوحات المكتب
    xs = sorted({round(w.start[0]) for w in P.walls if abs(w.u[0]) < 1e-6})
    ys = sorted({round(w.start[1]) for w in P.walls if abs(w.u[1]) < 1e-6})
    def _thin(v, gap=45):
        out = []
        for a in v:
            if not out or a - out[-1] >= gap:
                out.append(a)
        return out
    xs, ys = _thin(xs), _thin(ys)
    letters = "أبجدهوزحطيكلمن"
    bx0, by0, bx1, by1 = outer_bbox(P, rules)
    for i, x in enumerate(xs):
        yb = by1 + 125
        ax.plot([x, x], [by1 + 8, yb - 16], color="#999", lw=0.5, ls=(0, (6, 3)))
        ax.add_patch(Ellipse((x, yb), 32, 32, fill=False, ec="#777", lw=0.8))
        ax.text(x, yb, str(i + 1), ha="center", va="center", fontsize=9, color="#555")
    for i, y in enumerate(ys):
        xb = bx1 + 125
        ax.plot([bx1 + 8, xb - 16], [y, y], color="#999", lw=0.5, ls=(0, (6, 3)))
        ax.add_patch(Ellipse((xb, y), 32, 32, fill=False, ec="#777", lw=0.8))
        ax.text(xb, y, letters[i], ha="center", va="center", fontsize=9, color="#555")
    y1 = max(y1, by1 + 60)
    x1 = max(x1, bx1 + 60)
    # سهم الشمال
    nx_, ny_ = x1 + 120, y1 - 60
    ax.add_patch(Polygon([(nx_ - 18, ny_ - 40), (nx_, ny_ + 30), (nx_ + 18, ny_ - 40), (nx_, ny_ - 25)],
                         closed=True, fc="k"))
    ax.text(nx_, ny_ + 42, "ش", ha="center", fontsize=14)
    ax.set_xlim(x0 - 160, x1 + 170)
    ax.set_ylim(y0 - 160, y1 + 170)
    return fig, "المسقط الأفقي" + (f" — {fname}" if multi else "")


# ---------------------------------------------------------------- الواجهات
def elevation(ax, ctx, w):
    P, rules = ctx["project"], ctx["rules"]
    half = wall_thickness(rules) / 2
    H = P.roof_base                    # ارتفاع الجدار الكلي (كل الأدوار)
    L = w.length + 2 * half
    stack = [(w2, P.level(w2.floor)) for w2 in P.walls
             if w2.exterior and tuple(w2.start) == tuple(w.start) and tuple(w2.end) == tuple(w.end)]
    g = roof_geometry(P, rules)
    ov, p = P.roof.overhang, g["pitch"]
    rise = g["rise"]
    depth = rules["members"]["rafter"]["w"] / math.cos(p)
    cover = rules["cladding"]["effective_cover"]
    ux, uy = w.u
    gable_end = (P.roof.ridge_axis == "y") == (abs(uy) < 1e-6)
    sh = P.slab_height
    # امتداد السقف على جانب الجملون (تراس مسقوف) يظهر في واجهات الرفرف
    along = (w.start[1], w.end[1]) if P.roof.ridge_axis == "y" else (w.start[0], w.end[0])
    ext_l, ext_r = (P.roof.ext_start, P.roof.ext_end) if along[0] <= along[1] else (P.roof.ext_end, P.roof.ext_start)

    ax.plot([-170 - ext_l, L + 170 + ext_r], [-sh, -sh], color="k", lw=1)
    ax.add_patch(Rectangle((-10, -sh), L + 20, sh, fc="#f2f2f2", ec="#888", lw=0.6))
    ax.add_patch(Rectangle((0, 0), L, H, fc="white", ec="k", lw=1))
    y = cover
    while y < H - 1:
        ax.plot([0, L], [y, y], color="#999", lw=0.4)
        y += cover
    top = H + rise
    gglass = any(w2.gable_glass for w2, _l in stack)
    if gable_end and gglass:
        from .model3d import gable_glass_geometry
        inner, posts, zin, bv, tl = gable_glass_geometry(L, H, rise, math.tan(p))
        ax.add_patch(Polygon([(0, H), (L / 2, top), (L, H)], closed=True, fc="#e9d9c4", ec="k", lw=1))
        ax.add_patch(Polygon(inner, closed=True, fc="#e8f0f7", ec=C_WIN, lw=1.1))
        for t in posts:
            ax.add_patch(Rectangle((t - 5, inner[0][1]), 10, zin(t) - inner[0][1], fc="#e9d9c4", ec="k", lw=0.5))
        from .model3d import gable_transom
        zh = gable_transom(H, rise, 20, bv)
        ta = (zh - H + bv) / math.tan(p)
        if L - 2 * ta > 60:
            ax.add_patch(Rectangle((ta, zh - 5), L - 2 * ta, 10, fc="#e9d9c4", ec="k", lw=0.5))
        ax.text(L / 2, H + 32, "زجاج مقسّم بإطار خشب 20 سم + قوائم وعارضة 10 سم", ha="center", fontsize=7, color=C_WIN)
    if gable_end:
        if not gglass:
            ax.add_patch(Polygon([(0, H), (L / 2, top), (L, H)], closed=True, fc="white", ec="k", lw=1))
        y = H + cover if not gglass else top
        while y < top - 5:
            dxg = (top - y) / math.tan(p)
            ax.plot([L / 2 - dxg, L / 2 + dxg], [y, y], color="#999", lw=0.4)
            y += cover
        e = ov * math.tan(p)
        lower = [(-ov, H - e), (L / 2, top), (L + ov, H - e)]
        upper = [(x, yy + depth) for x, yy in lower]
        ax.add_patch(Polygon(lower + upper[::-1], closed=True, fc="#fff3e0", ec=C_ROOF, lw=0.9))
        roof_top = top + depth
    else:
        e = ov * math.tan(p)
        x_l, x_r = -ov - ext_l, L + ov + ext_r
        ax.add_patch(Rectangle((x_l, H - e), x_r - x_l, rise + e + depth, fc="#fff3e0", ec=C_ROOF,
                               lw=0.9))
        yy = H - e + 12
        while yy < top + depth - 5:
            ax.plot([x_l, x_r], [yy, yy], color=C_ROOF, lw=0.3)
            yy += 12
        ax.plot([x_l, x_r], [H - e + depth, H - e + depth], color=C_ROOF, lw=0.7)
        for pt in P.posts:   # أعمدة التراس الظاهرة في هذي الواجهة
            px, py = pt["at"]
            tpos = (px - w.start[0]) * ux + (py - w.start[1]) * uy + half
            if tpos < -5 or tpos > L + 5:
                ax.add_patch(Rectangle((tpos - 7, 0), 14, H, fc="#f3e3d3", ec="k", lw=0.6))
        roof_top = top + depth
    # المثلثات البارزة (جملون متقاطع)
    from .roof import cross_gables
    for g in cross_gables(P, rules):
        kd = (rules["members"]["rafter"]["w"] + 6.5) / math.cos(math.radians(g["pitch"]))
        tt = lambda x, y: (x - w.start[0]) * ux + (y - w.start[1]) * uy + half  # noqa: E731
        P_ = (lambda a, b: (a, b)) if g["axis"] == "y" else (lambda a, b: (b, a))
        facing = (abs(ux) < 1e-6) == (g["axis"] == "y") and \
            abs(((w.start[0] if g["axis"] == "y" else w.start[1]) + g["sg"] * half) - g["wall"]) < 2
        if facing:                 # المثلث مواجه لنا: حشوة + سقفه + شباك
            ta, tc, tb = (tt(*P_(g["wall"], g["c"] + d_)) for d_ in (-g["hw"], 0, g["hw"]))
            ta, tb = min(ta, tb), max(ta, tb)
            ax.add_patch(Polygon([(ta, H), (tc, g["zr"]), (tb, H)], closed=True, fc="white", ec="k", lw=1, zorder=3))
            yy = H + cover
            while yy < g["zr"] - 5:
                dxg = (g["zr"] - yy) / g["t"]
                ax.plot([tc - dxg, tc + dxg], [yy, yy], color="#999", lw=0.4, zorder=3)
                yy += cover
            e2 = g["ov"] * g["t"]
            lower = [(ta - g["ov"], H - e2), (tc, g["zr"]), (tb + g["ov"], H - e2)]
            ax.add_patch(Polygon(lower + [(x, z + kd) for x, z in lower][::-1], closed=True, fc="#fff3e0",
                                 ec=C_ROOF, lw=0.9, zorder=3))
            cgd = next(x for x in P.roof.cross_gables if x.get("side", "W") == g["side"])
            ww = cgd.get("window_width", 110)
            wz1 = min(H + cgd.get("window_height", 140), g["zr"] - ww / 2 * g["t"] - 25)
            ax.add_patch(Rectangle((tc - ww / 2, H + 15), ww, wz1 - H - 15, fc="white", ec=C_WIN, lw=1, zorder=3))
            ax.text(tc, H + 18 + (wz1 - H) / 2, "مثلث بارز", ha="center", fontsize=6, color=C_WIN, zorder=4)
            level(ax, L + g["ov"] + 30 + ext_r, g["zr"], g["zr"] / 100, "قمة المثلث")
        elif (abs(uy) < 1e-6) == (g["axis"] == "y"):   # واجهة الجملون: بروز المثلث من الجنب
            xo = g["wall"] + g["sg"] * g["ov"]
            xi = g["wall"] - g["sg"] * g["reach"]
            a0 = tt(*P_(xo, g["c"]))
            a1 = tt(*P_(xi, g["c"]))
            ax.add_patch(Polygon([(a0, g["ze"]), (a0, g["zr"] + kd), (a1, g["zr"] + kd), (a1, g["zr"])], closed=True,
                                 fc="#f3e7d6", ec=C_ROOF, lw=0.8, zorder=0.5))
    # التراس والأعمدة أمام هذي الواجهة
    late_rails = []
    nx_, ny_ = w.n
    front_posts = []
    for pt in P.posts:
        px, py = pt["at"]
        sd = (px - w.start[0]) * nx_ + (py - w.start[1]) * ny_
        tpos = (px - w.start[0]) * ux + (py - w.start[1]) * uy + half
        if sd < -half - 20 and -20 <= tpos <= L + 20:
            front_posts.append(tpos)
    for d in P.decks:
        dx0, dy0, dx1, dy1 = d.rect
        cs = [((cx - w.start[0]) * nx_ + (cy - w.start[1]) * ny_,
               (cx - w.start[0]) * ux + (cy - w.start[1]) * uy + half)
              for cx in (dx0, dx1) for cy in (dy0, dy1)]
        if min(c[0] for c in cs) < -half - 20:
            t0, t1 = min(c[1] for c in cs), max(c[1] for c in cs)
            if d.level > 0:      # بلكونة الدور العلوي
                top_d = d.level
                ax.add_patch(Rectangle((t0, top_d - 25), t1 - t0, 25, fc="#e9d9c4", ec="#8b5a2b", lw=0.7))
                if "S" in d.railing or not gable_end:
                    late_rails.append((t0, t1, top_d))
                continue
            top_d = d.height - sh
            ax.add_patch(Rectangle((t0, -sh), t1 - t0, sh + top_d, fc="#e9d9c4", ec="#8b5a2b", lw=0.7))
            if d.stairs and gable_end:
                n = max(1, math.ceil(d.height / 15))
                a = t0 + d.stairs["offset"]
                for k in range(1, n):
                    ax.add_patch(Rectangle((a, -sh), d.stairs["width"], d.height * k / n, fill=False,
                                           ec="#8b5a2b", lw=0.6))
            rh = 95
            for tt in (t0, t1):
                ax.add_patch(Rectangle((tt - 5 if tt == t1 else tt, top_d), 5, rh, fc="#8b5a2b", ec="none"))
    for tp_ in front_posts:
        ax.add_patch(Rectangle((tp_ - 8, 0), 16, H, fc="#c9a27c", ec="k", lw=0.7))
    if len(front_posts) >= 2:
        ax.add_patch(Rectangle((min(front_posts) - 8, H - 22), max(front_posts) - min(front_posts) + 16, 22,
                               fc="#c9a27c", ec="k", lw=0.7))
    # أحزمة الأدوار (أرضية الدور العلوي)
    for f_ in range(1, len(P.floor_list)):
        lv = P.level(f_)
        ax.add_patch(Rectangle((0, lv - 25), L, 25, fc="#e9d9c4", ec="k", lw=0.6))
    # الفتحات (لكل دور على منسوبه)
    for w2, lev in stack:
        for o in w2.openings:
            ex = o.offset + half
            b = lev + (o.sill if o.kind == "window" else 0)
            col = C_WIN if o.kind == "window" else C_DOOR
            ax.add_patch(Rectangle((ex, b), o.width, o.height, fc="white", ec=col, lw=1))
            ax.add_patch(Rectangle((ex + 4, b + 4), o.width - 8, o.height - (8 if o.kind == "window" else 4),
                                   fill=False, ec=col, lw=0.6))
            if o.kind == "window" and o.width >= 90 and not o.style:
                ax.plot([ex + o.width / 2] * 2, [b + 4, b + o.height - 4], color=col, lw=0.6)
            if o.transom:
                ax.plot([ex, ex + o.width], [lev + o.transom] * 2, color=col, lw=0.8)
            if o.kind == "door" and o.style in ("sliding", "fixed"):
                n = max(2, round(o.width / 100))
                for k in range(1, n):
                    ax.plot([ex + o.width * k / n] * 2, [lev, lev + o.height], color=col, lw=0.7)
                if o.style == "sliding":
                    ax.annotate("", (ex + o.width * 0.35, lev + 100), (ex + o.width * 0.15, lev + 100),
                                arrowprops=dict(arrowstyle="->", color=col, lw=0.6))
            elif o.kind == "door" and o.leaves:
                n = o.leaves
                lw_ = o.width / n
                for k in range(n):
                    xx = ex + k * lw_
                    ax.add_patch(Rectangle((xx + 8, lev + 10), lw_ - 16, o.height - 20, fill=False, ec=col, lw=0.5))
                    hx = xx + (lw_ - 12 if k == 0 else 12)
                    ax.add_patch(Ellipse((hx, lev + 105), 5, 5, fill=False, ec=col, lw=0.5))
            ax.text(ex + o.width / 2, b + o.height + 8, o.code, ha="center", va="bottom", fontsize=8,
                    color=col)
    for t0, t1, top_d in late_rails:        # دربزين البلكونة فوق الفتحات
        ax.add_patch(Rectangle((t0, top_d), t1 - t0, 105, fc="#fbf6ef", ec="#8b5a2b", lw=0.9, alpha=0.85))
        for yy in range(12, 105, 13):
            ax.plot([t0, t1], [top_d + yy] * 2, color="#8b5a2b", lw=0.5)
        for tt in np.linspace(t0, t1, 7):
            ax.plot([tt, tt], [top_d, top_d + 110], color="#8b5a2b", lw=1.2)
    # المناسيب
    lx = -110
    level(ax, lx - ext_l, -sh, -sh / 100, "منسوب الأرض", below=True)
    level(ax, lx - ext_l, 0, 0.0001, "وجه الصبة")
    for f_ in range(1, len(P.floor_list)):
        lv = P.level(f_)
        level(ax, lx - ext_l, lv, lv / 100, "أرضية " + P.floor_list[f_]["name"])
    level(ax, lx - ext_l, H, H / 100, "أعلى الجدار")
    level(ax, lx - ext_l, top, top / 100, "قمة الجملون")
    # الأبعاد
    ts = [0] + sorted(t + half for o in w.openings for t in (o.offset, o.offset + o.width)) + [L]
    chain(ax, [(t, -sh) for t in ts], -35)
    dim(ax, (0, -sh), (L, -sh), -75, fs=8)
    dim(ax, (L, 0), (L, H), -(ov + 50))
    dim(ax, (L, H), (L, top), -(ov + 50))
    dim(ax, (L, -sh), (L, top), -(ov + 95 + ext_r), fs=8)
    for o in w.openings:
        if o.kind == "window":
            dim(ax, (o.offset + half, 0), (o.offset + half, o.sill), 12, fs=6)
    ax.set_xlim(-170 - ext_l, L + ov + 140 + ext_r)
    ax.set_ylim(-120 - sh, roof_top + 30)


def elevation_sheets(ctx):
    P = ctx["project"]
    ext = [w for w in P.exterior_walls if w.floor == 0]
    out = []
    for i in range(0, len(ext), 2):
        fig = new_page((A3[1], A3[0]))
        pair = ext[i:i + 2]
        for k, w in enumerate(pair):
            ax = drawing_ax(fig, [0.05, 0.53 - 0.45 * k, 0.9, 0.4])
            elevation(ax, ctx, w)
            ax.text(0.5, -0.02, w.title or w.name, transform=ax.transAxes, ha="center", va="top",
                    fontsize=15)
            ax.text(0.5, -0.075, "مقياس 1:50  |  الوحدة: سم", transform=ax.transAxes, ha="center",
                    va="top", fontsize=8)
        out.append((fig, " و".join((w.title or w.name) for w in pair)))
    return out


# ---------------------------------------------------------------- السقف والقطاع
def roof_sheet(ctx):
    P, rules, R = ctx["project"], ctx["rules"], ctx["q"]["pallets"]["roof"]
    g = roof_geometry(P, rules)
    x0, y0, x1, y1 = g["bbox"]
    ov = P.roof.overhang
    fig = new_page()
    ax = drawing_ax(fig, [0.05, 0.1, 0.42, 0.8])
    title(ax, "مسقط السقف (جملون)", f"رفرف {ov:.0f} سم من كل جهة  |  مقياس 1:50")
    es, ee = P.roof.ext_start, P.roof.ext_end
    if P.roof.ridge_axis == "y":
        rx0, ry0, rx1, ry1 = x0 - ov, y0 - ov - es, x1 + ov, y1 + ov + ee
    else:
        rx0, ry0, rx1, ry1 = x0 - ov - es, y0 - ov, x1 + ov + ee, y1 + ov
    ax.add_patch(Rectangle((rx0, ry0), rx1 - rx0, ry1 - ry0, fc="#fff8ee", ec=C_ROOF, lw=1))
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="#555", ls="--", lw=0.7))
    ridge_y = P.roof.ridge_axis == "y"
    for pos in rafter_positions(P, rules):
        if ridge_y:
            ax.plot([x0 - ov, x1 + ov], [pos, pos], color="#777", lw=0.5)
        else:
            ax.plot([pos, pos], [y0 - ov, y1 + ov], color="#777", lw=0.5)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if ridge_y:
        ax.plot([cx, cx], [y0 - ov - 20, y1 + ov + 20], color=C_ROOF, lw=1.2)
        ax.text(cx + 8, y1 - 40, "خط الحرف (رأس الجملون)", ha="left", fontsize=8, color=C_ROOF,
                rotation=90, va="top")
        for s in (-1, 1):
            ax.annotate("", (cx + s * (x1 - x0) * 0.35, cy), (cx + s * 40, cy),
                        arrowprops=dict(arrowstyle="->", color="red"))
            ax.text(cx + s * (x1 - x0) * 0.22, cy + 12, f"ميل {P.roof.pitch_deg}°", ha="center",
                    fontsize=9, color="red")
    else:
        ax.plot([x0 - ov - 20, x1 + ov + 20], [cy, cy], color=C_ROOF, lw=1.2)
        for s in (-1, 1):
            ax.annotate("", (cx, cy + s * (y1 - y0) * 0.35), (cx, cy + s * 40),
                        arrowprops=dict(arrowstyle="->", color="red"))
            ax.text(cx + 15, cy + s * (y1 - y0) * 0.22, f"ميل {P.roof.pitch_deg}°", fontsize=9, color="red")
    ax.text(cx, y0 + 30, f"مدادات 5×15 كل 60 سم — {R['rafter_count']} مداد", ha="center", fontsize=9,
            bbox=dict(fc="white", ec="none"))
    dim(ax, (rx0, ry1), (rx1, ry1), 40)
    dim(ax, (x0, ry1), (x1, ry1), 15, fs=6)
    dim(ax, (rx1, ry1), (rx1, ry0), 40)
    for pt in P.posts:
        ax.add_patch(Rectangle((pt["at"][0] - 8, pt["at"][1] - 8), 16, 16, fc="#8b5a2b", ec="k"))
    from .roof import cross_gables, cross_planes
    for gc in cross_gables(P, rules):               # المثلثات البارزة: سطحين + قمة + وادي
        for tri in cross_planes(gc):
            ax.add_patch(Polygon([(x, y) for x, y, _ in tri], closed=True, fc="#ffe9cc", ec=C_ROOF, lw=0.9))
        (ax_, ay_, _), (bx_, by_, _) = cross_planes(gc)[0][2], cross_planes(gc)[0][1]
        ax.plot([ax_, bx_], [ay_, by_], color=C_ROOF, lw=1.2)
        for tri in cross_planes(gc):
            ax.plot([tri[0][0], tri[1 if tri is cross_planes(gc)[0] else 2][0]],
                    [tri[0][1], tri[1 if tri is cross_planes(gc)[0] else 2][1]], color="#1f5fa8", lw=1, ls="--")
        mx, my = (ax_ + bx_) / 2, (ay_ + by_) / 2
        ax.text(mx, my + 14, f"مثلث بارز {gc['pitch']}°", ha="center", fontsize=7, color="red")
    if P.roof.cross_gables:
        ax.text(cx, y0 + 60, "--- وادي: ينزل للرفرف (تصريف لبرا)", ha="center", fontsize=7, color="#1f5fa8")
    ax.set_xlim(rx0 - 60 - max([g["ov"] for g in cross_gables(P, rules)] + [0]), rx1 + 90 + max([g["ov"] for g in cross_gables(P, rules)] + [0]))
    ax.set_ylim(ry0 - 40, ry1 + 90)

    # القطاع العرضي عمودي على الجملون، يمر بأكبر غرفة
    ax2 = drawing_ax(fig, [0.52, 0.33, 0.44, 0.52])
    title(ax2, "قطاع عرضي أ-أ", "مقياس 1:50  |  الوحدة: سم")
    half = wall_thickness(rules) / 2
    H = P.roof_base
    big = max((r for r in P.rooms if r.floor == 0), key=lambda r: r.area_m2) if P.rooms else None
    cut = ((big.rect[1] + big.rect[3]) / 2 if ridge_y else (big.rect[0] + big.rect[2]) / 2) if big \
        else (cy if ridge_y else cx)
    lo, hi = (x0, x1) if ridge_y else (y0, y1)
    walls_cut = []   # (الموقع، منسوب الأسفل، الارتفاع)
    for w in P.walls:
        ux, uy = w.u
        lv, hh = P.level(w.floor), ctx["heights"][w.name]
        if ridge_y and abs(ux) < 1e-6 and min(w.start[1], w.end[1]) <= cut <= max(w.start[1], w.end[1]):
            walls_cut.append((w.start[0] - lo, lv, hh))
        if not ridge_y and abs(uy) < 1e-6 and min(w.start[0], w.end[0]) <= cut <= max(w.start[0], w.end[0]):
            walls_cut.append((w.start[1] - lo, lv, hh))
    S = hi - lo
    p = g["pitch"]
    rise = g["rise"]
    depth = rules["members"]["rafter"]["w"] / math.cos(p)
    sh = P.slab_height
    ax2.plot([-120, S + 120], [-sh, -sh], color="k", lw=1)
    ax2.add_patch(Rectangle((-10, -sh), S + 20, sh, fc="#f2f2f2", ec="#888", lw=0.6))
    for c, lv, hh in walls_cut:
        ax2.add_patch(Rectangle((c - half, lv), 2 * half, hh, fc="white", ec="k", lw=0.8, hatch="////"))
    for f_ in range(1, len(P.floor_list)):      # أرضية الدور العلوي: جسور 5×15 + تطبيق
        lv = P.level(f_)
        ax2.add_patch(Rectangle((0, lv - 25), S, 25, fc="#e9d9c4", ec="k", lw=0.7, hatch=".."))
        ax2.text(S / 2, lv - 12, "أرضية: جسور 5×15 + تطبيق خشب", ha="center", va="center", fontsize=7)
        level(ax2, -80, lv, lv / 100, "أرضية " + P.floor_list[f_]["name"])
    e = ov * math.tan(p)
    lower = [(-ov, H - e), (S / 2, H + rise), (S + ov, H - e)]
    upper = [(x, yy + depth) for x, yy in lower]
    ax2.add_patch(Polygon(lower + upper[::-1], closed=True, fc="#fff3e0", ec=C_ROOF, lw=1))
    for gc in cross_gables(P, rules):               # المثلث البارز إذا القطاع يمر فيه
        if ridge_y == (gc["axis"] == "y") and abs(cut - gc["c"]) < gc["hw"] + gc["ov"]:
            zc = gc["zr"] - abs(cut - gc["c"]) * gc["t"]
            xo = gc["wall"] + gc["sg"] * gc["ov"] - lo
            xi = gc["wall"] - lo - gc["sg"] * (zc - H) / math.tan(p)
            kd = depth
            ax2.add_patch(Rectangle((min(xo, xi), zc), abs(xi - xo), kd, fc="#ffe9cc", ec=C_ROOF, lw=0.9))
            if abs(cut - gc["c"]) < gc["hw"]:
                wx = gc["wall"] - lo - gc["sg"] * half
                ax2.add_patch(Rectangle((wx - half, H), 2 * half, zc - H, fc="white", ec="k", lw=0.8, hatch="////"))
    ax2.text(S / 2, H + rise + depth + 15, "مداد 5×15 بخلعة على العمود العلوي، مثبت ببراغي",
             ha="center", fontsize=8)
    ax2.text(S / 2, P.floor_list[0]["height"] / 2, "قوائم 7×5 + تلبيس 2.5 من الجهتين", ha="center", fontsize=8)
    level(ax2, -80, 0, 0.0001, "وجه الصبة")
    level(ax2, -80, H, H / 100, "أعلى الجدار")
    level(ax2, -80, H + rise, (H + rise) / 100, "قمة الجملون")
    dim(ax2, (0, -sh), (S, -sh), -35)
    dim(ax2, (-ov, -sh), (S + ov, -sh), -75, fs=6)
    dim(ax2, (S + ov, 0), (S + ov, H), -40)
    dim(ax2, (S + ov, H), (S + ov, H + rise), -40)
    ax2.set_xlim(-140, S + ov + 90)
    ax2.set_ylim(-100 - sh, H + rise + depth + 40)

    # تفصيلة الخلعة 1:5
    ax3 = drawing_ax(fig, [0.60, 0.08, 0.25, 0.22])
    ax3.set_title("تفصيلة جلوس المداد على العلوي (1:5)", fontsize=10)
    ax3.add_patch(Rectangle((0, -40), 7, 40, fc="#d2a679", ec="k", lw=0.8))           # عمود
    ax3.add_patch(Rectangle((0, 0), 7, 5, fc="#b5651d", ec="k", lw=0.8))              # علوي
    ax3.add_patch(Rectangle((-2.5, -40), 2.5, 45, fc="#eee", ec="k", lw=0.5))          # تلبيس
    ax3.add_patch(Rectangle((7, -40), 2.5, 45, fc="#eee", ec="k", lw=0.5))
    d = rules["members"]["rafter"]["w"]
    ca, sa = math.cos(p), math.sin(p)
    # خلعة: قطع أفقي بعرض العلوي + قطع رأسي عند الوجه الخارجي
    tp = math.tan(p)
    yb = lambda x: 5 + (x - 7) * tp  # noqa: E731  خط أسفل المداد يمر بالركن الداخلي للعلوي
    xl, xr = -40, 30
    pts = [(xl, yb(xl)), (0, yb(0)), (0, 5), (7, 5), (xr, yb(xr)),
           (xr - d * sa, yb(xr) + d * ca), (xl - d * sa, yb(xl) + d * ca)]
    ax3.add_patch(Polygon(pts, closed=True, fc="#fff3e0", ec=C_ROOF, lw=1))
    ax3.plot([3.5, 3.5 + 12 * sa], [5 + 9, 5 - 6], color="k", lw=1.2)
    ax3.text(14, -12, "برغي", fontsize=7)
    ax3.text(-3, 9, "خلعة", fontsize=7, ha="right")
    ax3.text(-5, -48, "علوي 7×5 على قائم 7×5", fontsize=7, ha="center")
    ax3.set_xlim(-45, 45)
    ax3.set_ylim(-55, 40)
    return fig, "مسقط السقف والقطاع"


# ---------------------------------------------------------------- الجداول
def schedule_sheet(ctx):
    P = ctx["project"]
    groups = {}
    for w in P.walls:
        for o in w.openings:
            key = (o.code, o.kind, o.width, o.height, o.sill if o.kind == "window" else None, o.leaves)
            where = (w.title or w.name).replace("الواجهة ", "") if w.exterior else o.name.replace(o.code, "").strip()
            groups.setdefault(key, []).append(where)
    rows = []
    kinds = {"window": "شباك", "door": "باب"}
    for (code, kind, wd, ht, sill, leaves), where in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        typ = kinds[kind] + (" مزدوج" if leaves == 2 else "")
        cnt = {}
        for x in where:
            cnt[x] = cnt.get(x, 0) + 1
        loc = " - ".join(f"{k} {v}" if v > 1 else k for k, v in cnt.items())
        rows.append([code, typ, f"{wd:.0f}", f"{ht:.0f}", "-" if sill is None else f"{sill:.0f}",
                     len(where), loc])
    fig = new_page()
    ax = fig.add_axes([0.08, 0.35, 0.84, 0.5])
    table(ax, ["الرمز", "النوع", "العرض (سم)", "الارتفاع (سم)", "ارتفاع الجلسة (سم)", "العدد", "الموقع"],
          rows, [1.2, 1.8, 1.3, 1.3, 1.6, 0.9, 6.0], fs=10, row_h=1)
    ax.set_title("جدول مقاسات الأبواب والشبابيك\nمقاس الفتحة الصافي في الجدار - الوحدة: سم", fontsize=15)
    nd = sum(r[5] for r in rows if "باب" in r[1])
    nw = sum(r[5] for r in rows if "شباك" in r[1])
    fig.text(0.5, 0.3, f"الإجمالي: أبواب {nd} - شبابيك {nw}", ha="center", fontsize=13)
    return fig, "جدول الأبواب والشبابيك"


def areas_sheet(ctx):
    P, rules = ctx["project"], ctx["rules"]
    x0, y0, x1, y1 = outer_bbox(P, rules)
    nfl = len(P.floor_list)
    gross = (x1 - x0) * (y1 - y0) / 1e4 * nfl
    net = sum(r.area_m2 for r in P.rooms if r.kind != "stair" or r.floor == 0)
    terrace = sum((d.rect[2] - d.rect[0]) * (d.rect[3] - d.rect[1]) for d in P.decks) / 1e4
    fig = new_page()
    hide_price = bool(P.meta.get("hide_pricing"))
    fig.text(0.5, 0.945, "جدول المساحات وبيانات المشروع" + ("" if hide_price else " والتسعير"), ha="center",
             fontsize=18, weight="bold", color=BRAND)
    # جدول المساحات
    ax = fig.add_axes([0.04, 0.3, 0.5, 0.58])
    short = {0: "أرضي", 1: "أول", 2: "ثاني"}
    rooms_ = [r for r in P.rooms if not (r.kind == "stair" and r.floor > 0)]
    rows = [[i + 1, (f"{short.get(r.floor, r.floor)} — " if nfl > 1 else "") + r.name,
             f"{r.w / 100:.2f} × {r.h / 100:.2f}", f"{r.area_m2:.2f}"] for i, r in enumerate(rooms_)]
    rows.append(["", "المساحة الصافية الداخلية", "", f"{net:.2f}"])
    if terrace:
        rows.append(["", "التراس المسقوف" + (" + تراس الدور الأول" if len(P.decks) > 1 else "")
                     + (" (مجاناً)" if P.meta.get("price_scope") == "building" else ""),
                     " × ".join(f"{(d.rect[k + 2] - d.rect[k]) / 100:.2f}" for d in P.decks[:1] for k in (0, 1))
                     + (f" × {len(P.decks)}" if len(P.decks) > 1 else ""), f"{terrace:.2f}"])
    rows.append(["", "المساحة الإجمالية المبنية",
                 f"{(x1 - x0) / 100:.2f} × {(y1 - y0) / 100:.2f}" + (f" × {nfl} دور" if nfl > 1 else ""), f"{gross:.2f}"])
    table(ax, ["م", "الفراغ", "الأبعاد (م)", "المساحة (م2)"], rows, [0.7, 3.6, 2.8, 2.1], fs=10.5 if len(rows) < 12 else 9,
          bold_last=3 if terrace else 2)
    ax.set_title("جدول المساحات", fontsize=14, weight="bold", color=BRAND, loc="right")
    # بيانات المشروع
    m = P.meta
    info = [["المشروع", P.title], ["العميل", P.client], ["الموقع", m.get("location", "")],
            ["الاستخدام", m.get("usage", "")], ["التاريخ", str(m.get("date", ""))],
            ["نظام البناء", "هيكل خشب 7×5 + تلبيس 2.5 سم من الجهتين"],
            ["السقف", f"جملون {P.roof.pitch_deg}° — قرميد معدني"
             + (f" + {len(P.roof.cross_gables)} مثلث بارز" if P.roof.cross_gables else "")]]
    ax2 = fig.add_axes([0.58, 0.52, 0.38, 0.36])
    table(ax2, ["البند", "البيان"], info, [1.5, 4.0], fs=10)
    ax2.set_title("بيانات المشروع", fontsize=14, weight="bold", color=BRAND, loc="right")
    if hide_price:           # بدون تسعير لهذا العميل
        return fig, "المساحات وبيانات المشروع"
    # التسعير
    ax3 = fig.add_axes([0.58, 0.2, 0.38, 0.25])
    price = P.price_per_m2
    note = P.meta.get("price_note", "")
    all_in = P.meta.get("price_scope") == "all" and terrace
    area_p = gross + terrace if all_in else gross
    area_lbl = "المساحة الكلية — الكوخ + التراس (م2)" if all_in else "المساحة المبنية (م2)"
    if price:
        total = round(area_p, 2) * price
        prow = [[area_lbl, f"{area_p:.2f}"],
                ["سعر المتر المربع" + (f" — {note}" if note else ""), f"{price:,.0f} ريال"],
                ["الإجمالي", f"{total:,.0f} ريال"]]
    else:
        prow = [[area_lbl, f"{area_p:.2f}"], ["سعر المتر المربع", "يُحدد بعد الاعتماد"],
                ["الإجمالي", "—"]]
    table(ax3, ["البند", "القيمة"], prow, [3.2, 2.3], fs=11, bold_last=1, row_h=1.15)
    ax3.set_title("التسعير", fontsize=14, weight="bold", color=BRAND, loc="right")
    if price and note:
        ax3.text(0.0, 1.035, f"  {note}  ", transform=ax3.transAxes, ha="left", va="bottom", fontsize=11,
                 weight="bold", color="white",
                 bbox=dict(boxstyle="round,pad=0.35", fc=OFFER, ec="none"))
    terms = P.meta.get("terms") or [("السعر لكامل المساحة (الكوخ + التراس المسقوف) حسب المخطط المعتمد."
                                     if all_in else "السعر للمساحة المبنية حسب المخطط المعتمد."),
                                    "الصبة والتمديدات الخارجية على العميل ما لم يُذكر غير ذلك."]
    fig.text(0.96, 0.175, "ملاحظات:", ha="right", fontsize=9.5, weight="bold", color=BRAND)
    for k, t in enumerate(terms):
        fig.text(0.96, 0.152 - k * 0.02, "• " + t, ha="right", fontsize=9, color="#444")
    return fig, "المساحات والتسعير"


# ---------------------------------------------------------------- لقطات 3D
def _grid_page(title, shots, note=None):
    fig = new_page()
    fig.text(0.5, 0.945, title, ha="center", fontsize=18, weight="bold", color=BRAND)
    n = len(shots)
    cols = 2 if n <= 4 else 3
    rows = math.ceil(n / cols)
    w, h = 0.94 / cols, 0.80 / rows
    for q, (pth, name) in enumerate(shots):
        r, c = divmod(q, cols)
        ax = fig.add_axes([0.97 - (c + 1) * w + 0.006, 0.9 - (r + 1) * h + 0.01, w - 0.012, h - 0.045])
        ax.imshow(plt.imread(pth))
        ax.axis("off")
        ax.set_title(name, fontsize=11, color=BRAND, loc="right")
    if note:
        fig.text(0.955, 0.12, note, ha="right", fontsize=9, color="#555")
    return fig


def real_sheets(ctx):
    """الصور الواقعية (Blender Cycles): الخارج نهاراً، وقت الغروب، ثم الداخل بالأثاث."""
    shots = ctx.get("real_shots") or {}
    if isinstance(shots, list):          # توافق مع الصيغة القديمة
        shots = {"exterior": shots}
    pages = []
    ext = shots.get("exterior") or []
    if ext:
        fig = new_page()
        fig.text(0.5, 0.945, "الصور الواقعية — الخارج", ha="center", fontsize=18, weight="bold", color=BRAND)
        main, rest = ext[0], ext[1:4]
        ax = fig.add_axes([0.3, 0.3, 0.68, 0.6])
        ax.imshow(plt.imread(main[0]))
        ax.axis("off")
        ax.set_title(main[1], fontsize=12, color=BRAND, loc="right")
        for q, (pth, name) in enumerate(rest):
            a2 = fig.add_axes([0.02, 0.64 - q * 0.29, 0.26, 0.25])
            a2.imshow(plt.imread(pth))
            a2.axis("off")
            a2.set_title(name, fontsize=10, color=BRAND, loc="right")
        fig.text(0.955, 0.25, "رندر واقعي بخامات حقيقية وإضاءة طبيعية — الألوان النهائية حسب عينات المورد",
                 ha="right", fontsize=9, color="#555")
        pages.append((fig, "الصور الواقعية — الخارج"))
    if shots.get("dusk"):
        pages.append((_grid_page("الصور الواقعية — وقت الغروب", shots["dusk"]), "الصور الواقعية — الغروب"))
    if shots.get("interior"):
        pages.append((_grid_page("الصور الواقعية — الداخل", shots["interior"],
                                 "الأثاث للتوضيح فقط — مواقع القطع ومقاساتها حسب المسقط"), "الصور الواقعية — الداخل"))
    return pages


def renders_sheets(ctx):
    shots = ctx.get("renders") or []
    if not shots:
        return []
    out = []
    ext = [s_ for s_ in shots if not s_[2]]
    cut = [s_ for s_ in shots if s_[2]]
    for k in range(0, len(ext), 6):
        fig = new_page()
        fig.text(0.5, 0.945, "لقطات المنظور الخارجي", ha="center", fontsize=18, weight="bold", color=BRAND)
        for q, (pth, name, _c) in enumerate(ext[k:k + 6]):
            r, c = divmod(q, 3)
            ax = fig.add_axes([0.665 - c * 0.315, 0.49 - r * 0.43, 0.3, 0.39])
            ax.imshow(plt.imread(pth))
            ax.axis("off")
            ax.set_title(name, fontsize=12, color=BRAND, loc="right")
        out.append((fig, "لقطات المنظور"))
    for pth, name, _c in cut:
        fig = new_page()
        fig.text(0.5, 0.945, name, ha="center", fontsize=18, weight="bold", color=BRAND)
        fig.text(0.5, 0.915, "مقطع أفقي على ارتفاع 1.90 م — توزيع الفرش ومسار الحركة", ha="center", fontsize=10,
                 color="#555")
        ax = fig.add_axes([0.1, 0.06, 0.8, 0.84])
        ax.imshow(plt.imread(pth))
        ax.axis("off")
        out.append((fig, name))
    return out


# ---------------------------------------------------------------- المنظور والمواد
def perspective_sheet(ctx):
    st = ctx["style"]
    fig = new_page()
    fig.text(0.5, 0.93, "المنظور ثلاثي الأبعاد والمواد", ha="center", fontsize=18)
    fig.text(0.5, 0.905, f"النمط: {st['ar']}  —  رندر واقعي بخامات حقيقية",
             ha="center", fontsize=10, color="#555")
    ax = fig.add_axes([0.03, 0.3, 0.64, 0.58])
    real = (ctx.get("real_shots") or {}) if isinstance(ctx.get("real_shots"), dict) else {}
    ext = real.get("exterior") or []
    if len(ext) >= 2:      # الصور الواقعية بدل المعاينة المبسطة (أدق للسقف والمواد)
        import numpy as _np
        a, b = plt.imread(ext[0][0]), plt.imread(ext[3 if len(ext) > 3 else 1][0])
        h = min(a.shape[0], b.shape[0])
        ax.imshow(_np.concatenate([a[:h, :, :3], _np.full((h, 30, 3), 255, a.dtype), b[:h, :, :3]], axis=1))
    else:
        ax.imshow(plt.imread(ctx["preview"]))
    ax.axis("off")
    rows = [("الخشب / الصبغة", st["wood_ar"], st["wood"]),
            ("القرميد", st["roof_ar"], st["roof"]),
            ("الزجاج", st["glass_ar"], st["glass"]),
            ("إطارات الشبابيك والأبواب", st["frame_ar"], st["frame"]),
            ("الكنار والزوايا", "نفس الصبغة أغمق درجة", st["trim"]),
            ("الصبة", f"خرسانة {ctx['project'].slab_height:.0f} سم", st["slab"])]
    y = 0.84
    fig.text(0.95, y + 0.02, "جدول المواد والألوان", ha="right", fontsize=13, weight="bold")
    for k, v, c in rows:
        y -= 0.065
        fig.patches.append(Rectangle((0.70, y - 0.012), 0.035, 0.045, transform=fig.transFigure,
                                     fc=c, ec="k", lw=0.6))
        fig.text(0.95, y + 0.018, k, ha="right", fontsize=10, weight="bold")
        fig.text(0.95, y - 0.008, v, ha="right", fontsize=9, color="#444")
    y -= 0.07
    fig.text(0.95, y, f"الدربزين: {st['railing_ar']}", ha="right", fontsize=10)
    grid_ar = {"none": "بدون", "mullion": "قاطع رأسي", "grid": "شبكة"}[st["window_grid"]]
    door_ar = {"panel": "خشب مصمت", "french": "زجاج بتقسيمات (فرنسي)"}[st["door_style"]]
    ext_doors = [o for w in ctx["project"].exterior_walls for o in w.openings if o.kind == "door"]
    if ext_doors and ext_doors[0].style == "sliding":
        door_ar = "سحاب زجاج"
    fig.text(0.95, y - 0.03, f"تقسيم الشبابيك: {grid_ar}  |  الباب الرئيسي: {door_ar}",
             ha="right", fontsize=9, color="#444")
    fig.text(0.5, 0.29, "أنواع الدربزين المعتمدة (من مشاريع المصنع)", ha="center", fontsize=12)
    for i, (pth, name) in enumerate(ctx["railings"]):
        ax2 = fig.add_axes([0.06 + i * 0.3, 0.09, 0.28, 0.18])
        ax2.imshow(plt.imread(pth))
        ax2.axis("off")
        ax2.text(0.5, -0.04, name, transform=ax2.transAxes, ha="center", va="top", fontsize=9)
    return fig, "المنظور والمواد"


# ---------------------------------------------------------------- لوحات الورشة
def framing_ax(ax, ctx, w):
    rules = ctx["rules"]
    H = ctx["heights"][w.name]
    members = ctx["members"][w.name]
    for m in members:
        ax.add_patch(Rectangle((m.x0, m.y0), m.x1 - m.x0, m.y1 - m.y0, fc=FRAME_COLORS[m.kind],
                               ec="k", lw=.4))
    yb = rules["members"]["stud"]["t"]
    for o in w.openings:
        b = yb + (o.sill if o.kind == "window" else 0)
        ax.add_patch(Rectangle((o.offset, b), o.width, o.height, fill=False, ec="#1f77b4", ls="--", lw=.8))
        ax.plot([o.offset, o.offset + o.width], [b, b + o.height], color="#1f77b4", lw=.4)
        ax.plot([o.offset, o.offset + o.width], [b + o.height, b], color="#1f77b4", lw=.4)
        ax.text(o.offset + o.width / 2, b + o.height + 10, f"{o.code} {o.width:.0f}×{o.height:.0f}",
                ha="center", fontsize=7)
    for m in members:
        if m.note:
            ax.text((m.x0 + m.x1) / 2, m.y0 - 16, m.note, ha="center", fontsize=7, color="#a33")
    xs = sorted({round((m.x0 + m.x1) / 2, 1) for m in members if m.kind in ("stud", "corner_stud", "jamb")})
    for a, b in zip(xs, xs[1:]):
        dim(ax, (a, H), (b, H), 15, fs=5.5, ext=False)
    dim(ax, (0, 0), (w.length, 0), -40, fs=7)
    dim(ax, (w.length, 0), (w.length, H), -25, fs=7)
    ax.set_xlim(-30, w.length + 60)
    ax.set_ylim(-70, H + 45)
    ax.set_title(f"تأطير جدار {w.name}  —  الطول {w.length:.0f} سم، الارتفاع {H:.0f} سم"
                 + ("" if w.exterior else "  (داخلي)"), fontsize=11)


def framing_sheets(ctx):
    P = ctx["project"]
    out = []
    walls = P.walls
    for i in range(0, len(walls), 2):
        fig = new_page()
        for k, w in enumerate(walls[i:i + 2]):
            ax = drawing_ax(fig, [0.04, 0.53 - 0.44 * k, 0.92, 0.38])
            framing_ax(ax, ctx, w)
        handles = [Rectangle((0, 0), 1, 1, fc=c) for c in FRAME_COLORS.values()]
        fig.legend(handles, [KIND_AR[k] for k in FRAME_COLORS], loc="lower center", ncol=8, fontsize=8,
                   frameon=False, bbox_to_anchor=(0.5, 0.1))
        out.append((fig, "لوحات التأطير (للورشة)"))
    return out


def text_table_sheet(ctx, heading, rows, sheet):
    """جدول نصي من عمودين/ثلاثة على صفحات متتالية."""
    figs = []
    per_page = 14
    for i in range(0, max(len(rows), 1), per_page):
        fig = new_page()
        ax = fig.add_axes([0.06, 0.1, 0.88, 0.78])
        chunk = rows[i:i + per_page]
        ncol = max(len(r) for r in rows) if rows else 2
        widths = {2: [4, 8], 3: [1.2, 3.5, 9], 4: [1.2, 3, 5, 5]}[ncol]
        heads = {2: ["البند", "القيمة"], 3: ["النوع", "البند", "التفاصيل"],
                 4: ["النوع", "البند", "التفاصيل", "المقترح"]}[ncol]
        table(ax, heads, [r + [""] * (ncol - len(r)) for r in chunk], widths, fs=8.5, wrap=11)
        ax.set_title(heading, fontsize=15)
        figs.append((fig, sheet))
    return figs


def bom_rows(ctx):
    q, hi = ctx["q"], ctx["height"]
    p, c, roof = q["pallets"], q["cladding"], q["pallets"]["roof"]
    rows = [["الارتفاع المطلوب / المعتمد", f"{hi['requested']:.0f} / {hi['suggested']:.0f} سم"],
            ["السقف", f"جملون {roof['pitch_deg']}° — قمة {roof['ridge_level']:.0f} سم من وجه الصبة"],
            ["المدادات 5×15", f"{roof['rafter_count']} مداد ({roof['rafters_per_side']} لكل جهة) × "
                              f"{roof['rafter_length']:.0f} سم — من طبلية {roof['stock_length']}"],
            ["طبليات الطريقة الأولى (مداد + عمود)",
             f"{p['method1_pallets']['count']} طبلية × {p['method1_pallets']['length']} سم"],
            ["طبليات الطريقة الثانية (3 أعمدة)",
             f"{p['method2_pallets']['count']} طبلية × {p['method2_pallets']['length']} سم"]]
    if p["method2_long_pallets"]["count"]:
        rows.append(["طبليات الطريقة الثانية (طويلة)",
                     f"{p['method2_long_pallets']['count']} طبلية × {p['method2_long_pallets']['length']} سم"])
    fj = p.get("floor_joists") or {}
    if fj.get("count"):
        mj = ctx["rules"]["members"].get("floor_joist", {"w": 15, "t": 5, "spacing": 60})
        rows.append([f"مدادات أرضية الدور العلوي {mj['t']}×{mj['w']} كل {mj['spacing']} سم",
                     f"{fj['count']} مداد — " + "، ".join(f"{L}سم×{n}" for L, n in fj["lengths"])
                     + f" (طبلية {fj['stock']} بالطريقة الأولى)"])
    cr = p.get("cross_rafters") or {}
    for cx_ in cr.get("items", []):
        rows.append([f"مدادات المثلث البارز ({'الغربي' if cx_['side'] == 'W' else 'الشرقي' if cx_['side'] == 'E' else cx_['side']}) {cx_['pitch']}°",
                     f"{cx_['rafters']} مداد حتى {cx_['rafter_length']:.0f} سم (طبلية {cx_['stock']}) + 2 مداد وادي "
                     f"{cx_['valley_length']:.0f} سم" + (" — وصلة" if not cx_["valley_stock"] else "")])
    rows += [["إجمالي الطبليات 5×22.5", str(p["total_pallets"])],
             ["إجمالي قطع 7×5", str(p["stud_pieces_total"])],
             ["قائمة تقطيع 7×5", "  |  ".join(f"{L}سم×{n}" for L, n in p["stud_cut_list"][:9])]]
    if len(p["stud_cut_list"]) > 9:
        rows.append(["", "  |  ".join(f"{L}سم×{n}" for L, n in p["stud_cut_list"][9:18])])
    rows += [["ألواح تلبيس 2.5 سم", f"{c['boards']} لوح × {c['board_length']} سم "
                                     f"(مجموع الصفوف {c['total_run_m']} م، {c['faces']} وجه)"],
             ["أسمنت بورد 12 مم (122×244)", f"{c['cement_board_sheets']} لوح (داخل دورات المياه)"],
             ["العزل", f"{q['insulation']['panels']} لوح فوم صخري 80" if q["insulation"] else "بدون (غير مطلوب)"],
             ["الصبة", "يجهزها العميل — 20 سم، مفرغة تحت دورات المياه"]]
    return rows


def build_client_pdf(ctx, path, with_perspective=True):
    """نسخة العميل بطابع مكتب هندسي: إطار عنوان بالشعار، مسقط، واجهات، سقف وقطاع، جداول، لقطات 3D."""
    pages = [(plan_sheet(ctx, f), "1:50") for f in range(len(ctx["project"].floor_list))] + \
        [(e, "1:50") for e in elevation_sheets(ctx)] + \
        [(roof_sheet(ctx), "1:50"), (schedule_sheet(ctx), "—"), (areas_sheet(ctx), "—")]
    pages += [(r, "—") for r in real_sheets(ctx)]
    # المعاينة المبسطة للخارج تنشال إذا فيه صور واقعية (السقف فيها تقريبي) — يبقى المقطع بالفرش
    rs = renders_sheets(ctx)
    if isinstance(ctx.get("real_shots"), dict) and ctx["real_shots"].get("exterior"):
        rs = [r for r in rs if r[1] != "لقطات المنظور"]
    pages += [(r, "—") for r in rs]
    if with_perspective:
        pages.append((perspective_sheet(ctx), "—"))
    n = len(pages)
    with PdfPages(path) as pdf:
        for i, ((fig, sheet), scale) in enumerate(pages, 1):
            lift_content(fig)
            title_block(fig, ctx, sheet, f"A-{i:02d}", i, n, scale)
            pdf.savefig(fig)
            plt.close(fig)
    return n


def build_pdf(ctx, path):
    pages = [perspective_sheet(ctx)] + [plan_sheet(ctx, f) for f in range(len(ctx["project"].floor_list))] + \
        elevation_sheets(ctx) + [roof_sheet(ctx), schedule_sheet(ctx),
                                                         areas_sheet(ctx)]
    pages += framing_sheets(ctx)
    pages += text_table_sheet(ctx, "جدول الكميات وخطة تقطيع الطبليات", bom_rows(ctx), "الكميات")
    rv = [[i["level"], i["title"], i["detail"], i["fix"]] for i in ctx["issues"]]
    rv += [["سؤال", "يحتاج تأكيد", qq, ""] for qq in ctx["questions"]]
    pages += text_table_sheet(ctx, "مراجعة التصميم مقابل قواعد المصنع", rv, "مراجعة التصميم")
    n = len(pages)
    with PdfPages(path) as pdf:
        for i, (fig, sheet) in enumerate(pages, 1):
            lift_content(fig)
            title_block(fig, ctx, sheet, f"W-{i:02d}", i, n, "1:50" if i <= 5 else "—")
            pdf.savefig(fig)
            plt.close(fig)
    return n
