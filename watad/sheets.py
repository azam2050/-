"""لوحات المشروع PDF بالعربي — نفس ترتيب المكتب الهندسي + لوحات الورشة.

1 المسقط مع الفرش والأبعاد | 2-3 الواجهات | 4 السقف والقطاع | 5 جدول الفتحات
6 المساحات والتسعير | 7.. تأطير الجدران | كميات وخطة الطبليات | مراجعة التصميم
"""
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Arc, Ellipse, Polygon, Rectangle
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from .model import outer_bbox, wall_thickness
from .roof import rafter_positions, roof_geometry

plt.rcParams["font.family"] = "DejaVu Sans"
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


def table(ax, headers, rows, col_w, fs=9, row_h=1.0, head_fc="#e8e8e8", bold_last=0, wrap=None):
    """جدول من اليمين لليسار. col_w بنفس ترتيب headers (من اليمين).
    wrap: عدد الحروف لكل وحدة عرض — يلف النص الطويل ويكبّر ارتفاع الصف."""
    import textwrap
    total = sum(col_w)
    allrows = [headers] + rows
    if wrap:
        allrows = [[textwrap.fill(str(v), max(4, int(col_w[c] * wrap))) for c, v in enumerate(r)]
                   for r in allrows]
    heights = [row_h * max(1, max(str(v).count("\n") + 1 for v in r) * 0.8 + 0.2) for r in allrows]
    ax.set_xlim(0, total)
    ax.set_ylim(-sum(heights), 0)
    ax.axis("off")
    xs = [total]
    for w in col_w:
        xs.append(xs[-1] - w)
    y = 0
    n = len(allrows)
    for r, cells in enumerate(allrows):
        h = heights[r]
        y -= h
        bold = bold_last and r >= n - bold_last
        fc = head_fc if (r == 0 or bold) else "white"
        for c, val in enumerate(cells):
            ax.add_patch(Rectangle((xs[c + 1], y), col_w[c], h, fc=fc, ec="k", lw=0.6))
            ax.text((xs[c] + xs[c + 1]) / 2, y + h / 2, str(val), ha="center", va="center",
                    fontsize=fs, weight="bold" if bold else "normal", linespacing=1.3)


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
            if o.kind == "window":
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


def plan_sheet(ctx):
    P, rules = ctx["project"], ctx["rules"]
    half = wall_thickness(rules) / 2
    x0, y0, x1, y1 = outer_bbox(P, rules)
    portrait = (y1 - y0) > (x1 - x0)
    fig = new_page((A3[1], A3[0]) if portrait else A3)
    ax = drawing_ax(fig, [0.06, 0.08, 0.88, 0.84])
    title(ax, "المسقط الأفقي مع الفرش", "الأبعاد بالسنتيمتر - الجدران: قوائم 7×5 + تلبيس 2.5 من الجهتين (12 سم)")

    for r in P.rooms:
        if r.wet:
            ax.add_patch(Rectangle((r.rect[0], r.rect[1]), r.w, r.h, fc="#eef6ff", ec="none"))
    _draw_shape(ax, wall_shapes(P, rules), fc="white", ec="k", lw=0.9, hatch="////")
    draw_openings_plan(ax, P, rules)
    draw_furniture(ax, P)
    for r in P.rooms:
        cx, cy = (r.rect[0] + r.rect[2]) / 2, (r.rect[1] + r.rect[3]) / 2
        big = r.area_m2 > 4
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
    # سهم الشمال
    nx_, ny_ = x1 + 120, y1 - 60
    ax.add_patch(Polygon([(nx_ - 18, ny_ - 40), (nx_, ny_ + 30), (nx_ + 18, ny_ - 40), (nx_, ny_ - 25)],
                         closed=True, fc="k"))
    ax.text(nx_, ny_ + 42, "ش", ha="center", fontsize=14)
    ax.set_xlim(x0 - 160, x1 + 170)
    ax.set_ylim(y0 - 160, y1 + 130)
    return fig, "المسقط الأفقي"


# ---------------------------------------------------------------- الواجهات
def elevation(ax, ctx, w):
    P, rules = ctx["project"], ctx["rules"]
    half = wall_thickness(rules) / 2
    H = ctx["heights"][w.name]
    L = w.length + 2 * half
    g = roof_geometry(P, rules)
    ov, p = P.roof.overhang, g["pitch"]
    rise = g["rise"]
    depth = rules["members"]["rafter"]["w"] / math.cos(p)
    cover = rules["cladding"]["effective_cover"]
    ux, uy = w.u
    gable_end = (P.roof.ridge_axis == "y") == (abs(uy) < 1e-6)

    ax.plot([-170, L + 170], [-20, -20], color="k", lw=1)
    ax.add_patch(Rectangle((-10, -20), L + 20, 20, fc="#f2f2f2", ec="#888", lw=0.6))
    ax.add_patch(Rectangle((0, 0), L, H, fc="white", ec="k", lw=1))
    y = cover
    while y < H - 1:
        ax.plot([0, L], [y, y], color="#999", lw=0.4)
        y += cover
    top = H + rise
    if gable_end:
        ax.add_patch(Polygon([(0, H), (L / 2, top), (L, H)], closed=True, fc="white", ec="k", lw=1))
        y = H + cover
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
        ax.add_patch(Rectangle((-ov, H - e), L + 2 * ov, rise + e + depth, fc="#fff3e0", ec=C_ROOF,
                               lw=0.9))
        yy = H - e + 12
        while yy < top + depth - 5:
            ax.plot([-ov, L + ov], [yy, yy], color=C_ROOF, lw=0.3)
            yy += 12
        ax.plot([-ov, L + ov], [H - e + depth, H - e + depth], color=C_ROOF, lw=0.7)
        roof_top = top + depth
    # الفتحات
    for o in w.openings:
        ex = o.offset + half
        b = o.sill if o.kind == "window" else 0
        col = C_WIN if o.kind == "window" else C_DOOR
        ax.add_patch(Rectangle((ex, b), o.width, o.height, fc="white", ec=col, lw=1))
        ax.add_patch(Rectangle((ex + 4, b + 4), o.width - 8, o.height - (8 if o.kind == "window" else 4),
                               fill=False, ec=col, lw=0.6))
        if o.kind == "window" and o.width >= 90:
            ax.plot([ex + o.width / 2] * 2, [b + 4, b + o.height - 4], color=col, lw=0.6)
        if o.kind == "door":
            n = o.leaves
            lw_ = o.width / n
            for k in range(n):
                xx = ex + k * lw_
                ax.add_patch(Rectangle((xx + 8, 10), lw_ - 16, o.height - 20, fill=False, ec=col, lw=0.5))
                hx = xx + (lw_ - 12 if k == 0 else 12)
                ax.add_patch(Ellipse((hx, 105), 5, 5, fill=False, ec=col, lw=0.5))
        ax.text(ex + o.width / 2, b + o.height + 8, o.code, ha="center", va="bottom", fontsize=8,
                color=col)
    # المناسيب
    lx = -110
    level(ax, lx, -20, -0.20, "منسوب الأرض", below=True)
    level(ax, lx, 0, 0.0001, "وجه الصبة")
    level(ax, lx, H, H / 100, "أعلى الجدار")
    level(ax, lx, top, top / 100, "قمة الجملون")
    # الأبعاد
    ts = [0] + sorted(t + half for o in w.openings for t in (o.offset, o.offset + o.width)) + [L]
    chain(ax, [(t, -20) for t in ts], -35)
    dim(ax, (0, -20), (L, -20), -75, fs=8)
    dim(ax, (L, 0), (L, H), -(ov + 50))
    dim(ax, (L, H), (L, top), -(ov + 50))
    dim(ax, (L, -20), (L, top), -(ov + 95), fs=8)
    for o in w.openings:
        if o.kind == "window":
            dim(ax, (o.offset + half, 0), (o.offset + half, o.sill), 12, fs=6)
    ax.set_xlim(-170, L + ov + 140)
    ax.set_ylim(-140, roof_top + 30)


def elevation_sheets(ctx):
    P = ctx["project"]
    ext = P.exterior_walls
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
    ax.add_patch(Rectangle((x0 - ov, y0 - ov), x1 - x0 + 2 * ov, y1 - y0 + 2 * ov, fc="#fff8ee",
                           ec=C_ROOF, lw=1))
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
    dim(ax, (x0 - ov, y1 + ov), (x1 + ov, y1 + ov), 40)
    dim(ax, (x0, y1 + ov), (x1, y1 + ov), 15, fs=6)
    dim(ax, (x1 + ov, y1 + ov), (x1 + ov, y0 - ov), 40)
    ax.set_xlim(x0 - ov - 60, x1 + ov + 90)
    ax.set_ylim(y0 - ov - 40, y1 + ov + 90)

    # القطاع العرضي عمودي على الجملون، يمر بأكبر غرفة
    ax2 = drawing_ax(fig, [0.52, 0.33, 0.44, 0.52])
    title(ax2, "قطاع عرضي أ-أ", "مقياس 1:50  |  الوحدة: سم")
    half = wall_thickness(rules) / 2
    H = P.wall_height
    big = max(P.rooms, key=lambda r: r.area_m2) if P.rooms else None
    cut = ((big.rect[1] + big.rect[3]) / 2 if ridge_y else (big.rect[0] + big.rect[2]) / 2) if big \
        else (cy if ridge_y else cx)
    lo, hi = (x0, x1) if ridge_y else (y0, y1)
    walls_cut = []
    for w in P.walls:
        ux, uy = w.u
        if ridge_y and abs(ux) < 1e-6 and min(w.start[1], w.end[1]) <= cut <= max(w.start[1], w.end[1]):
            walls_cut.append(w.start[0] - lo)
        if not ridge_y and abs(uy) < 1e-6 and min(w.start[0], w.end[0]) <= cut <= max(w.start[0], w.end[0]):
            walls_cut.append(w.start[1] - lo)
    S = hi - lo
    p = g["pitch"]
    rise = g["rise"]
    depth = rules["members"]["rafter"]["w"] / math.cos(p)
    ax2.plot([-120, S + 120], [-20, -20], color="k", lw=1)
    ax2.add_patch(Rectangle((-10, -20), S + 20, 20, fc="#f2f2f2", ec="#888", lw=0.6))
    for c in walls_cut:
        ax2.add_patch(Rectangle((c - half, 0), 2 * half, H, fc="white", ec="k", lw=0.8, hatch="////"))
    e = ov * math.tan(p)
    lower = [(-ov, H - e), (S / 2, H + rise), (S + ov, H - e)]
    upper = [(x, yy + depth) for x, yy in lower]
    ax2.add_patch(Polygon(lower + upper[::-1], closed=True, fc="#fff3e0", ec=C_ROOF, lw=1))
    ax2.text(S / 2, H + rise + depth + 15, "مداد 5×15 بخلعة على العمود العلوي، مثبت ببراغي",
             ha="center", fontsize=8)
    ax2.text(S / 2, H / 2, "قوائم 7×5 + تلبيس 2.5 من الجهتين", ha="center", fontsize=8)
    level(ax2, -80, 0, 0.0001, "وجه الصبة")
    level(ax2, -80, H, H / 100, "أعلى الجدار")
    level(ax2, -80, H + rise, (H + rise) / 100, "قمة الجملون")
    dim(ax2, (0, -20), (S, -20), -35)
    dim(ax2, (-ov, -20), (S + ov, -20), -75, fs=6)
    dim(ax2, (S + ov, 0), (S + ov, H), -40)
    dim(ax2, (S + ov, H), (S + ov, H + rise), -40)
    ax2.set_xlim(-140, S + ov + 90)
    ax2.set_ylim(-120, H + rise + depth + 40)

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
    gross = (x1 - x0) * (y1 - y0) / 1e4
    net = sum(r.area_m2 for r in P.rooms)
    fig = new_page()
    ax = fig.add_axes([0.06, 0.3, 0.5, 0.55])
    rows = [[i + 1, r.name, f"{r.w / 100:.2f} × {r.h / 100:.2f}", f"{r.area_m2:.2f}"]
            for i, r in enumerate(P.rooms)]
    rows.append(["", "المساحة الصافية الداخلية", "", f"{net:.2f}"])
    rows.append(["", "المساحة الإجمالية الخارجية", f"{(x1 - x0) / 100:.2f} × {(y1 - y0) / 100:.2f}",
                 f"{gross:.2f}"])
    table(ax, ["م", "الفراغ", "الأبعاد الداخلية (م)", "المساحة (م2)"], rows, [0.8, 3.5, 3, 2.2],
          fs=10, bold_last=2)
    ax.set_title("جدول المساحات", fontsize=15)
    m = P.meta
    info = [["المشروع", P.title], ["العميل", P.client], ["الموقع", m.get("location", "")],
            ["الاستخدام", m.get("usage", "")], ["المدير", m.get("manager", "")],
            ["التاريخ", str(m.get("date", ""))], ["المقياس", "1:50"], ["الوحدة", "سم"]]
    ax2 = fig.add_axes([0.6, 0.45, 0.35, 0.4])
    table(ax2, ["البند", "القيمة"], info, [1.5, 3.5], fs=10)
    ax2.set_title("مصنع وتد الأخشاب\nWatad Wood Factory", fontsize=14)
    if P.price_per_m2:
        ax3 = fig.add_axes([0.6, 0.2, 0.35, 0.18])
        total = round(gross, 2) * P.price_per_m2
        table(ax3, ["البند", "القيمة"], [["المساحة الإجمالية (م2)", f"{gross:.2f}"],
                                          ["سعر المتر (ريال)", f"{P.price_per_m2:,.0f}"],
                                          ["الإجمالي (ريال)", f"{total:,.0f}"]], [2.5, 2.5], fs=10,
              bold_last=1)
        ax3.set_title("التسعير", fontsize=14)
    return fig, "المساحات والتسعير"


# ---------------------------------------------------------------- المنظور والمواد
def perspective_sheet(ctx):
    st = ctx["style"]
    fig = new_page()
    fig.text(0.5, 0.93, "المنظور ثلاثي الأبعاد والمواد", ha="center", fontsize=18)
    fig.text(0.5, 0.905, f"النمط: {st['ar']}  —  معاينة تقريبية، الإخراج النهائي من 3ds Max",
             ha="center", fontsize=10, color="#555")
    ax = fig.add_axes([0.03, 0.3, 0.64, 0.58])
    ax.imshow(plt.imread(ctx["preview"]))
    ax.axis("off")
    rows = [("الخشب / الصبغة", st["wood_ar"], st["wood"]),
            ("القرميد", st["roof_ar"], st["roof"]),
            ("الزجاج", st["glass_ar"], st["glass"]),
            ("إطارات الشبابيك والأبواب", st["frame_ar"], st["frame"]),
            ("الكنار والزوايا", "نفس الصبغة أغمق درجة", st["trim"]),
            ("الصبة", "خرسانة 20 سم", st["slab"])]
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
                   frameon=False, bbox_to_anchor=(0.5, 0.06))
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


def build_pdf(ctx, path):
    pages = [perspective_sheet(ctx), plan_sheet(ctx)] + elevation_sheets(ctx) + [roof_sheet(ctx), schedule_sheet(ctx),
                                                         areas_sheet(ctx)]
    pages += framing_sheets(ctx)
    pages += text_table_sheet(ctx, "جدول الكميات وخطة تقطيع الطبليات", bom_rows(ctx), "الكميات")
    rv = [[i["level"], i["title"], i["detail"], i["fix"]] for i in ctx["issues"]]
    rv += [["سؤال", "يحتاج تأكيد", qq, ""] for qq in ctx["questions"]]
    pages += text_table_sheet(ctx, "مراجعة التصميم مقابل قواعد المصنع", rv, "مراجعة التصميم")
    n = len(pages)
    with PdfPages(path) as pdf:
        for i, (fig, sheet) in enumerate(pages, 1):
            footer(fig, ctx, sheet, i, n)
            pdf.savefig(fig)
            plt.close(fig)
    return n
