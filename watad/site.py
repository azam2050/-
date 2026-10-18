"""الموقع العام (Landscape): الأرض، السور والبوابات، المسبح، الجلسات، المواقف، الممرات، المسطحات الخضراء والأشجار.

في ملف المشروع:
  site:
    plot: [x0, y0, x1, y1]          # حدود الأرض (نفس إحداثيات الكوخ، سم) — الشارع على جهة street
    street: S                       # جهة الشارع
    street_width: 1600
    wall: {t: 20, h: 250}           # سور بلك
    gates: [{x: 444, width: 400, kind: car}, {x: -56, width: 110, kind: person}]   # على ضلع الشارع
    zones:                           # مستطيلات: kind = pool | deck | paving | parking | seating | path | lawn | planter
      - {kind: pool, rect: [...], name: المسبح, depth: 140}
    pergolas: [{rect: [...], name: ...}]
    trees: [{at: [x, y], kind: palm|tree|shrub, r: 150}]
"""
import math

from matplotlib.patches import Circle, Polygon, Rectangle

COL = {"pool": ("#bfe6f5", "#2b8cbe"), "deck": ("#ead2b0", "#8b5a2b"), "paving": ("#e6e1d8", "#8a8478"),
       "parking": ("#dcdcdc", "#777777"), "seating": ("#f1e3cc", "#8b5a2b"), "path": ("#eee8dc", "#8a8478"),
       "lawn": ("#d6ebc3", "#6a9a3a"), "planter": ("#c9dfb0", "#4f7a2a")}
AR = {"pool": "مسبح", "deck": "ديك خشب", "paving": "بلاط", "parking": "موقف سيارة", "seating": "جلسة خارجية",
      "path": "ممر", "lawn": "مسطح أخضر", "planter": "أحواض زراعة"}


def _area(r):
    return (r[2] - r[0]) * (r[3] - r[1]) / 1e4


def site_rows(P, rules):
    """جدول المساحات للموقع."""
    from .model import outer_bbox
    st = P.site
    x0, y0, x1, y1 = st["plot"]
    plot = _area(st["plot"])
    bx0, by0, bx1, by1 = outer_bbox(P, rules)
    fp = (bx1 - bx0) * (by1 - by0) / 1e4
    sums = {}
    zones = st.get("zones", [])
    for z in zones:
        a = _area(z["rect"])
        if z["kind"] == "paving":                  # البلاط حول المسبح: يُخصم منه المسبح والجلسة اللي داخله
            for o in zones:
                if o is not z and o["kind"] != "paving":
                    r, q = z["rect"], o["rect"]
                    ix = min(r[2], q[2]) - max(r[0], q[0])
                    iy = min(r[3], q[3]) - max(r[1], q[1])
                    if ix > 0 and iy > 0:
                        a -= ix * iy / 1e4
        sums.setdefault(z["kind"], 0)
        sums[z["kind"]] += a
    deck = sum(_area(d.rect) for d in P.decks if not d.level)
    used = fp + deck + sum(v for k, v in sums.items() if k != "lawn")
    rows = [["مساحة الأرض", f"{(x1 - x0) / 100:.2f} × {(y1 - y0) / 100:.2f} م", f"{plot:.1f}"],
            ["مسطح الكوخ (البصمة)", f"{(bx1 - bx0) / 100:.2f} × {(by1 - by0) / 100:.2f} م", f"{fp:.1f}"]]
    if deck:
        rows.append(["تراس الكوخ", "", f"{deck:.1f}"])
    for k in ("pool", "deck", "seating", "paving", "parking", "path", "planter"):
        if k in sums:
            zs = [z["rect"] for z in st.get("zones", []) if z["kind"] == k]
            size = f"{(zs[0][2] - zs[0][0]) / 100:.2f} × {(zs[0][3] - zs[0][1]) / 100:.2f} م" \
                if len(zs) == 1 and k != "paving" else ""
            rows.append([AR[k], size, f"{sums[k]:.1f}"])
    rows.append(["المسطحات الخضراء (حديقة)", "الباقي", f"{plot - used:.1f}"])
    return rows, plot, plot - used


def site_sheet(ctx):
    from .model import outer_bbox, wall_thickness
    from .sheets import A3, BROWN, chain, dim, drawing_ax, new_page, table, title
    P, rules = ctx["project"], ctx["rules"]
    st = P.site
    x0, y0, x1, y1 = st["plot"]
    t = st.get("wall", {}).get("t", 20)
    fig = new_page((A3[1], A3[0]))
    ax = drawing_ax(fig, [0.05, 0.06, 0.58, 0.86])
    title(ax, "الموقع العام وتنسيق الحديقة (لاندسكيب)",
          f"الأرض {(x1 - x0) / 100:.0f} × {(y1 - y0) / 100:.0f} م = {_area(st['plot']):.0f} م²  |  الأبعاد بالسنتيمتر")
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#e8f2dc", ec="none", zorder=0))
    for z in st.get("zones", []):                              # المناطق
        r = z["rect"]
        fc, ec = COL.get(z["kind"], ("#eee", "#999"))
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=fc, ec=ec, lw=0.9, zorder=1,
                               hatch="...." if z["kind"] == "paving" else None))
        if z["kind"] == "pool":
            ax.add_patch(Rectangle((r[0] + 15, r[1] + 15), r[2] - r[0] - 30, r[3] - r[1] - 30, fc="#8fd3f0", ec="#2b8cbe",
                                   lw=0.6, zorder=1.1))
            for k in range(1, 4):                              # درج نزول المسبح
                ax.plot([r[0] + 15, r[0] + 75], [r[1] + 15 + 30 * k] * 2, color="#2b8cbe", lw=0.5, zorder=1.2)
        if z["kind"] == "deck":
            yy = r[1] + 15
            while yy < r[3]:
                ax.plot([r[0], r[2]], [yy, yy], color="#cfae84", lw=0.4, zorder=1.1)
                yy += 15
        if z["kind"] == "parking":
            ax.plot([r[0] + 40, r[2] - 40, r[2] - 40, r[0] + 40, r[0] + 40],
                    [r[1] + 60, r[1] + 60, r[3] - 40, r[3] - 40, r[1] + 60], color="#999", lw=0.5, ls="--", zorder=1.2)
        name = z.get("name", AR.get(z["kind"], ""))
        if not name:
            continue
        w, h = r[2] - r[0], r[3] - r[1]
        txt = f"{name}\n{w / 100:.2f} × {h / 100:.2f} م"
        if z.get("depth"):
            txt += f"\nعمق {z['depth'] / 100:.2f} م"
        lx, ly = z.get("label") or ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        ax.text(lx, ly, txt, ha="center", va="center", fontsize=7, color=BROWN, zorder=8.5,
                rotation=90 if w < 200 and h > 2 * w else 0, linespacing=1.3,
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.2))
    for pg in st.get("pergolas", []):                         # برجولة الجلسة
        r = pg["rect"]
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ec="#8b5a2b", lw=1, ls="--",
                               zorder=3))
        n = max(3, round((r[2] - r[0]) / 40))
        for k in range(n + 1):
            xx = r[0] + (r[2] - r[0]) * k / n
            ax.plot([xx, xx], [r[1], r[3]], color="#b08a5a", lw=0.4, zorder=3)
        for cx, cy in ((r[0], r[1]), (r[2], r[1]), (r[0], r[3]), (r[2], r[3])):
            ax.add_patch(Rectangle((cx - 8, cy - 8), 16, 16, fc="#6b4f3a", ec="k", lw=0.4, zorder=4))
        for f in pg.get("furniture", []):
            fr = f["rect"]
            ax.add_patch(Rectangle((fr[0], fr[1]), fr[2] - fr[0], fr[3] - fr[1], fc="#d8c3a5", ec="#6b4f3a", lw=0.6,
                                   zorder=4))
    for f in st.get("furniture", []):                         # كراسي استلقاء المسبح…
        fr = f["rect"]
        ax.add_patch(Rectangle((fr[0], fr[1]), fr[2] - fr[0], fr[3] - fr[1], fc="#f4ead8", ec="#6b4f3a", lw=0.6, zorder=4))
    # الكوخ (البصمة + المسقط الأرضي مبسّط)
    from .sheets import draw_openings_plan, wall_shapes, _draw_shape, floor_view
    bx0, by0, bx1, by1 = outer_bbox(P, rules)
    ax.add_patch(Rectangle((bx0, by0), bx1 - bx0, by1 - by0, fc="white", ec="k", lw=1.2, zorder=5))
    G = floor_view(P, 0)
    _draw_shape(ax, wall_shapes(G, rules), fc="#d9c7ae", ec="k", lw=0.6, zorder=6)
    for d in P.decks:
        if d.level:
            continue
        r = d.rect
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#ead2b0", ec="#8b5a2b", lw=0.8, zorder=5))
        ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, d.name, ha="center", va="center", fontsize=7, color=BROWN, zorder=6)
    ax.text((bx0 + bx1) / 2, (by0 + by1) / 2, f"الكوخ\n{(bx1 - bx0) / 100:.2f} × {(by1 - by0) / 100:.2f} م\nدورين",
            ha="center", va="center", fontsize=10, weight="bold", color=BROWN, zorder=7)
    # الأشجار
    for tr in st.get("trees", []):
        cx, cy = tr["at"]
        r = tr.get("r", 150 if tr.get("kind") != "shrub" else 50)
        if tr.get("kind") == "palm":
            ax.add_patch(Circle((cx, cy), r, fc="#9cc27a", ec="#4f7a2a", lw=0.6, alpha=0.8, zorder=8))
            for k in range(8):
                a = k * math.pi / 4
                ax.plot([cx, cx + r * math.cos(a)], [cy, cy + r * math.sin(a)], color="#4f7a2a", lw=0.6, zorder=8)
        else:
            ax.add_patch(Circle((cx, cy), r, fc="#7fb069" if tr.get("kind") != "shrub" else "#a7c98a", ec="#4f7a2a",
                                lw=0.6, alpha=0.75, zorder=8))
            ax.add_patch(Circle((cx, cy), 6, fc="#6b4f3a", ec="none", zorder=8))
    # السور والبوابات
    side = st.get("street", "S")
    gates = st.get("gates", [])
    ax.add_patch(Rectangle((x0 - t, y0 - t), x1 - x0 + 2 * t, y1 - y0 + 2 * t, fill=False, ec="#444", lw=0, zorder=9))
    for (ax0, ay0, ax1, ay1, edge) in ((x0 - t, y0 - t, x1 + t, y0, "S"), (x0 - t, y1, x1 + t, y1 + t, "N"),
                                        (x0 - t, y0, x0, y1, "W"), (x1, y0, x1 + t, y1, "E")):
        cuts = sorted((g["x"], g["x"] + g["width"]) for g in gates) if edge == side else []
        a = ax0
        for c0, c1 in cuts + [(ax1, ax1)]:
            if c0 > a:
                ax.add_patch(Rectangle((a, ay0), c0 - a, ay1 - ay0, fc="#6e6e6e", ec="k", lw=0.5, zorder=9)) \
                    if edge in "SN" else None
            a = c1
        if edge in "WE":
            ax.add_patch(Rectangle((ax0, ay0), ax1 - ax0, ay1 - ay0, fc="#6e6e6e", ec="k", lw=0.5, zorder=9))
    for g in gates:
        gx = g["x"]
        ax.plot([gx, gx + g["width"]], [y0 - t / 2] * 2, color="#10a010", lw=2.4, zorder=10)
        ax.text(gx + g["width"] / 2, y0 - t - 22, "بوابة سيارة" if g.get("kind") == "car" else "باب مشاة",
                ha="center", va="top", fontsize=7, color="#10a010", zorder=10)
    sw = st.get("street_width", 1600)
    ax.add_patch(Rectangle((x0 - 300, y0 - t - 120 - 160), x1 - x0 + 600, 160, fc="#cfcfcf", ec="none", zorder=0))
    ax.text((x0 + x1) / 2, y0 - t - 200, f"شارع عرض {sw / 100:.0f} م", ha="center", va="center", fontsize=9,
            color="#333", zorder=1)
    # الأبعاد: الإجمالي ثم التقسيمات (قاعدة المصنع)
    dim(ax, (x0, y0), (x0, y1), 120, fs=9)
    ys = sorted({y0, y1, by0, by1} | {r for z in st.get("zones", []) if z["kind"] in ("pool",)
                                      for r in (z["rect"][1], z["rect"][3])})
    chain(ax, [(x0, v) for v in ys], 60, fs=7)
    dim(ax, (x0, y1), (x1, y1), 120, fs=9)
    xs = sorted({x0, x1, bx0, bx1})
    chain(ax, [(v, y1) for v in xs], 60, fs=7)
    # سهم الشمال
    nx, ny = x1 + 160, y1 - 200
    ax.add_patch(Polygon([(nx, ny), (nx - 25, ny - 90), (nx, ny - 65), (nx + 25, ny - 90)], closed=True, fc="k"))
    ax.text(nx, ny + 15, "ش", ha="center", va="bottom", fontsize=12)
    ax.set_xlim(x0 - 330, x1 + 260)
    ax.set_ylim(y0 - 330, y1 + 200)
    # جدول المساحات + ملاحظات
    rows, plot, green = site_rows(P, rules)
    ax2 = fig.add_axes([0.66, 0.42, 0.31, 0.46])
    table(ax2, ["البند", "المقاس", "المساحة (م²)"], rows, [3.0, 2.2, 1.6], fs=9)
    ax2.set_title("جدول مساحات الموقع", fontsize=13, weight="bold", color=BROWN, loc="right")
    notes = st.get("notes", [])
    fig.text(0.965, 0.38, "\n".join("• " + n for n in notes), ha="right", va="top", fontsize=8.5, color="#333",
             linespacing=1.6)
    return fig, "الموقع العام واللاندسكيب"


# ---------------------------------------------------------------- 3D
def add_site_3d(S, P, rules, style, cut=None):
    st = P.site
    if not st or cut:
        return
    S.material("site_wall", "#E9E4DA")
    S.material("paver", "#CFC8BB")
    S.material("pool_edge", "#EDEAE4")
    S.material("water", "#3DA5C9", 0.75)
    S.material("lawn_bed", "#7C9A4A")
    S.material("gate", "#2B2B2B")
    x0, y0, x1, y1 = st["plot"]
    w = st.get("wall", {})
    t, h = w.get("t", 20), w.get("h", 250)
    gz = -P.slab_height
    S.zoff = 0
    side = st.get("street", "S")
    gates = sorted((g["x"], g["x"] + g["width"], g) for g in st.get("gates", []))
    a = x0 - t
    for g0, g1, g in gates + [(x1 + t, x1 + t, None)]:          # السور الأمامي مع البوابات
        if g0 > a:
            S.box("site_wall", a, y0 - t, gz, g0, y0, gz + h)
            S.box("trim", a, y0 - t - 2, gz + h - 12, g0, y0 + 2, gz + h)       # كاب خشب أعلى السور
        if g:
            n = max(4, round(g["width"] / 12))                   # بوابة شرائح خشب حديثة
            for k in range(n):
                xa = g0 + (g1 - g0) * k / n
                S.box("trim", xa + 1, y0 - t / 2 - 3, gz + 5, xa + (g1 - g0) / n - 2, y0 - t / 2 + 3, gz + h - 20)
            S.box("gate", g0, y0 - t / 2 - 4, gz + h - 20, g1, y0 - t / 2 + 4, gz + h - 12)
        a = g1
    S.box("site_wall", x0 - t, y1, gz, x1 + t, y1 + t, gz + h)
    S.box("site_wall", x0 - t, y0, gz, x0, y1, gz + h)
    S.box("site_wall", x1, y0, gz, x1 + t, y1, gz + h)
    for z in st.get("zones", []):
        r = z["rect"]
        k = z["kind"]
        if k == "pool":
            d = z.get("depth", 140)
            S.box("pool_edge", r[0], r[1], gz, r[2], r[1] + 15, gz + 8)
            S.box("pool_edge", r[0], r[3] - 15, gz, r[2], r[3], gz + 8)
            S.box("pool_edge", r[0], r[1], gz, r[0] + 15, r[3], gz + 8)
            S.box("pool_edge", r[2] - 15, r[1], gz, r[2], r[3], gz + 8)
            S.box("water", r[0] + 15, r[1] + 15, gz - d, r[2] - 15, r[3] - 15, gz - 6)
        elif k in ("paving", "parking", "path", "seating"):
            S.box("paver", r[0], r[1], gz, r[2], r[3], gz + 3)
        elif k == "deck":
            S.box("wood", r[0], r[1], gz, r[2], r[3], gz + 15)
        elif k == "planter":
            S.box("site_wall", r[0], r[1], gz, r[2], r[3], gz + 45)
            S.box("lawn_bed", r[0] + 8, r[1] + 8, gz + 40, r[2] - 8, r[3] - 8, gz + 46)
    for pg in st.get("pergolas", []):
        r = pg["rect"]
        ph = pg.get("h", 270)
        for cx, cy in ((r[0], r[1]), (r[2], r[1]), (r[0], r[3]), (r[2], r[3])):
            S.box("trim", cx - 8, cy - 8, gz, cx + 8, cy + 8, gz + ph)
        for yy in (r[1], r[3]):
            S.box("trim", r[0] - 20, yy - 6, gz + ph - 25, r[2] + 20, yy + 6, gz + ph)
        n = max(3, round((r[2] - r[0]) / 30))
        for k in range(n + 1):
            xx = r[0] + (r[2] - r[0]) * k / n
            S.box("trim", xx - 3, r[1] - 20, gz + ph, xx + 3, r[3] + 20, gz + ph + 12)
    S.zoff = 0
