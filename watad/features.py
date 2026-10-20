"""عناصر واجهة إضافية (مثل الكوخ الكلاسيكي في فيديو العميل):

  bays:     شباك بارز مضلع (نصف مثمن) بزجاج مقسّم بخشب، فوقه بلكونة الدور الأول عادةً
            {wall, offset, width, depth: 90, sill: 60, head: 250, top: 280, grid_rows: 5}
  porches:  مظلة مدخل بجملون صغير على عمودين قدام الباب
            {wall, offset, width, depth: 120, eave: 240, pitch: 40, overhang: 15, post: 12}
  pergolas: برجولة خشب فوق باب/شباك (عوارض للخارج + شرائح)
            {wall, offset, width, depth: 90, z: 245}   — z من أرضية دور الجدار
الإحداثيات على طول الجدار (offset من بداية محور الجدار)، والبروز للخارج من الوجه الخارجي.
"""
import math

from matplotlib.patches import Circle, Polygon, Rectangle

from .model import Wall, wall_thickness

WOOD_EL, GLASS_EL, LINE = "#e9d9c4", "#e8f0f7", "#5a3a22"


def _wall(P, name):
    return next(w for w in P.walls if w.name == name)


def _out(w, half):
    """نقطة على بعد t من بداية الجدار و d للخارج من الوجه الخارجي."""
    return lambda t, d: w.point(t, -half - d)


def bay_points(P, rules, b):
    w = _wall(P, b["wall"])
    half = wall_thickness(rules) / 2
    o = _out(w, half)
    a, L, d = b["offset"], b["width"], b.get("depth", 90)
    return w, [o(a, 0), o(a + d, d), o(a + L - d, d), o(a + L, 0)]


def hprism(S, mat, pts, z0, z1):
    """بلاطة أفقية بمضلع محدب في المسقط."""
    n = len(pts)
    V = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    F = [tuple(range(n)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    S.poly(mat, V, F)


def grid_glass(S, w, a, b, z0, z1, cols, rows, s0=-1, s1=1, bar=4):
    """زجاج بشبكة خشب (قوائم وعوارض) في إطار جدار."""
    S.wbox("glass", w, a, b, s0, s1, z0, z1)
    for k in range(1, cols):
        t = a + (b - a) * k / cols
        S.wbox("frame_wood", w, t - bar / 2, t + bar / 2, s0 - 2, s1 + 2, z0, z1)
    for k in range(1, rows):
        z = z0 + (z1 - z0) * k / rows
        S.wbox("frame_wood", w, a, b, s0 - 2, s1 + 2, z - bar / 2, z + bar / 2)


# ---------------------------------------------------------------- 3D
def add_3d(S, P, rules, style, cut=None):
    S.material("frame_wood", style["trim"])
    half = wall_thickness(rules) / 2
    sh = P.slab_height
    for b in P.bays:
        w, pts = bay_points(P, rules, b)
        lev = P.level(w.floor)
        S.zoff = lev
        sill, head, top = b.get("sill", 60), b.get("head", 250), b.get("top", 280)
        if cut:
            top = min(top, cut - lev)
        if w.floor == 0:
            hprism(S, "slab", pts, -sh, 0)
        hprism(S, "floor" if "floor" in S.colors else "wood", pts, 0, 1.2)
        for p, q in zip(pts, pts[1:]):
            fw = Wall("bay", p, q)
            Lf = fw.length
            S.wbox("wood", fw, 0, Lf, 0, 12, 0, min(sill, top))      # جلسة خشب تحت الزجاج
            if top > sill:
                zt = min(head, top)
                fr = 6
                for ta, tb, za, zb in ((0, fr, sill, zt), (Lf - fr, Lf, sill, zt), (0, Lf, sill, sill + fr),
                                       (0, Lf, zt - fr, zt)):
                    S.wbox("frame_wood", fw, ta, tb, -1, 8, za, zb)
                grid_glass(S, fw, fr, Lf - fr, sill + fr, zt - fr, max(1, round(Lf / 45)), b.get("grid_rows", 5),
                           s0=5, s1=6)
            if top > head:
                S.wbox("wood", fw, 0, Lf, 0, 12, head, top)            # حزام خشب فوق الزجاج
            S.wbox("trim", fw, -6, 6, -2, 10, 0, top)                  # قائم الزاوية
        if top >= b.get("top", 280) and not b.get("under_deck", True):
            hprism(S, "trim", pts, top, top + 15)
    for pc in P.porches:
        w = _wall(P, pc["wall"])
        S.zoff = P.level(w.floor)
        a, L = pc["offset"], pc["width"]
        dp, eave, ps = pc.get("depth", 120), pc.get("eave", 240), pc.get("post", 12)
        tp = math.tan(math.radians(pc.get("pitch", 40)))
        ov = pc.get("overhang", 15)
        rise = L / 2 * tp
        sF = -half - dp                      # الوجه الأمامي للمظلة (s سالب = للخارج)
        if cut and cut < eave:
            continue
        for t in (a, a + L - ps):            # عمودين
            S.wbox("trim", w, t, t + ps, sF, sF + ps, 0, eave)
        S.wbox("trim", w, a, a + L, sF, sF + ps, eave - 18, eave)         # جسر أمامي
        for t in (a, a + L - ps):
            S.wbox("trim", w, t, t + ps, sF, -half, eave - 18, eave)      # جسور جانبية للجدار
        S.wprism("wood", w, [(a, eave), (a + L, eave), (a + L / 2, eave + rise)], sF, sF + 3)   # مثلث أمامي
        tc = a + L / 2
        for sg in (-1, 1):                   # سطحين مائلين (قرميد) من الجدار للأمام
            te = tc + sg * (L / 2 + ov)
            ze = eave - ov * tp
            q = [(tc, eave + rise + 2), (te, ze + 2), (te, ze + 8), (tc, eave + rise + 8)]
            front = [(*w.point(t, sF - ov), z) for t, z in q]
            back = [(*w.point(t, -half), z) for t, z in q]
            S.poly("roof_tiles", front + back, [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
                                                (2, 3, 7, 6), (3, 0, 4, 7)])
        # لوح حافة أمامي
        for sg in (-1, 1):
            S.wdiag("trim", w, tc, eave + rise + 4, tc + sg * (L / 2 + ov), eave - ov * tp + 4, 14,
                    sF - ov - 2.5, sF - ov)
    for pg in P.pergolas:
        w = _wall(P, pg["wall"])
        lev = P.level(w.floor)
        if cut and cut <= lev:
            continue
        S.zoff = lev
        a, L, dp, z = pg["offset"], pg["width"], pg.get("depth", 90), pg.get("z", 245)
        for t in (a, a + L / 2 - 4, a + L - 8):                           # عوارض حاملة للخارج
            S.wbox("trim", w, t, t + 8, -half - dp, -half, z, z + 18)
        S.wbox("trim", w, a - 10, a + L + 10, -half - dp, -half - dp + 6, z + 18, z + 28)   # عارضة أمامية
        n = max(3, round(L / 14))
        for k in range(n + 1):                                             # شرائح
            t = a - 6 + (L + 6) * k / n
            S.wbox("trim", w, t, t + 5, -half - dp - 8, -half, z + 28, z + 36)
        for t in (a + 10, a + L - 18):                                     # كوابيل مائلة
            S.wdiag("trim", w, t, z - 40, t + 4, z, 6, -half - 30, -half)
    S.zoff = 0


# ---------------------------------------------------------------- المسقط
def draw_plan(ax, P, rules, floor):
    half = wall_thickness(rules) / 2
    for b in P.bays:
        w, pts = bay_points(P, rules, b)
        if w.floor != floor:
            continue
        ax.add_patch(Polygon(pts, closed=True, fc="white", ec="k", lw=1.2, zorder=3))
        for p, q in zip(pts, pts[1:]):
            fw = Wall("bay", p, q)
            for s in (3, 7):
                p1, q1 = fw.point(0, s), fw.point(fw.length, s)
                ax.plot([p1[0], q1[0]], [p1[1], q1[1]], color="#1f77b4", lw=0.8, zorder=4)
        cx = sum(x for x, _ in pts[1:3]) / 2
        cy = sum(y for _, y in pts[1:3]) / 2
        ax.text(cx, cy, "شباك بارز", ha="center", va="center", fontsize=6, color="#1f77b4", zorder=5,
                rotation=0)
    for pc in P.porches:
        w = _wall(P, pc["wall"])
        if w.floor != floor:
            continue
        a, L, dp, ps = pc["offset"], pc["width"], pc.get("depth", 120), pc.get("post", 12)
        o = _out(w, half)
        ov = pc.get("overhang", 15)
        roof = [o(a - ov, 0), o(a - ov, dp + ov), o(a + L + ov, dp + ov), o(a + L + ov, 0)]
        ax.add_patch(Polygon(roof, closed=True, fill=False, ec=LINE, lw=0.8, ls="--", zorder=3))
        for t in (a, a + L - ps):
            c = [o(t, dp - ps), o(t, dp), o(t + ps, dp), o(t + ps, dp - ps)]
            ax.add_patch(Polygon(c, closed=True, fc=LINE, ec="k", lw=0.5, zorder=4))
        m = o(a + L / 2, dp + ov + 14)
        ax.text(*m, "مظلة المدخل", ha="center", va="center", fontsize=6.5, color=LINE, zorder=5)
    for pg in P.pergolas:
        w = _wall(P, pg["wall"])
        if w.floor != floor:
            continue
        a, L, dp = pg["offset"], pg["width"], pg.get("depth", 90)
        o = _out(w, half)
        ax.add_patch(Polygon([o(a, 0), o(a, dp), o(a + L, dp), o(a + L, 0)], closed=True, fill=False,
                             ec=LINE, lw=0.7, ls=":", zorder=3))


# ---------------------------------------------------------------- الواجهة
def draw_elev(ax, P, rules, w, stack, gable_end=False):
    """يرسم العناصر اللي على هذي الواجهة (الجدار نفسه أو الجدار فوقه/تحته في نفس الخط)."""
    half = wall_thickness(rules) / 2
    names = {w2.name: lev for w2, lev in stack}
    X = lambda t: t + half                   # noqa: E731
    for b in P.bays:
        if b["wall"] not in names:
            continue
        lev = names[b["wall"]]
        a, L, d = b["offset"], b["width"], b.get("depth", 90)
        sill, head, top = b.get("sill", 60), b.get("head", 250), b.get("top", 280)
        xs = [X(a), X(a + d), X(a + L - d), X(a + L)]
        ax.add_patch(Rectangle((xs[0], lev), xs[3] - xs[0], top, fc=WOOD_EL, ec="k", lw=1, zorder=3))
        rows = b.get("grid_rows", 5)
        for x0, x1 in zip(xs, xs[1:]):
            ax.add_patch(Rectangle((x0 + 5, lev + sill), x1 - x0 - 10, head - sill, fc=GLASS_EL, ec="#1f77b4",
                                   lw=0.9, zorder=3))
            cols = max(1, round(math.hypot(x1 - x0, d if x0 in (xs[0], xs[2]) else 0) / 45))
            for k in range(1, cols):
                xx = x0 + 5 + (x1 - x0 - 10) * k / cols
                ax.plot([xx, xx], [lev + sill, lev + head], color=LINE, lw=0.6, zorder=4)
            for k in range(1, rows):
                zz = lev + sill + (head - sill) * k / rows
                ax.plot([x0 + 5, x1 - 5], [zz, zz], color=LINE, lw=0.6, zorder=4)
            ax.plot([x1, x1], [lev, lev + top], color="k", lw=0.8, zorder=4)
        ax.text((xs[1] + xs[2]) / 2, lev + top + 6, "شباك بارز", ha="center", va="bottom", fontsize=6.5,
                color="#1f77b4", zorder=5)
    for pc in P.porches:
        if pc["wall"] not in names:
            continue
        lev = names[pc["wall"]]
        a, L, eave = pc["offset"], pc["width"], pc.get("eave", 240)
        ps, ov = pc.get("post", 12), pc.get("overhang", 15)
        tp = math.tan(math.radians(pc.get("pitch", 40)))
        rise = L / 2 * tp
        x0 = X(a)
        for x in (x0, x0 + L - ps):
            ax.add_patch(Rectangle((x, lev), ps, eave, fc="#c9a27c", ec="k", lw=0.7, zorder=5))
        ax.add_patch(Rectangle((x0, lev + eave - 18), L, 18, fc="#c9a27c", ec="k", lw=0.7, zorder=5))
        ax.add_patch(Polygon([(x0, lev + eave), (x0 + L, lev + eave), (x0 + L / 2, lev + eave + rise)], closed=True,
                             fc=WOOD_EL, ec="k", lw=0.8, zorder=5))
        lower = [(x0 - ov, lev + eave - ov * tp), (x0 + L / 2, lev + eave + rise), (x0 + L + ov, lev + eave - ov * tp)]
        ax.add_patch(Polygon(lower + [(x, z + 10) for x, z in lower][::-1], closed=True, fc="#fff3e0", ec="#c56b1a",
                             lw=0.9, zorder=5))
        ax.text(x0 + L / 2, lev + eave + rise * 0.35, "مظلة", ha="center", fontsize=6, color=LINE, zorder=6)
    for pg in P.pergolas:
        if pg["wall"] not in names:
            continue
        lev = names[pg["wall"]]
        a, L, z = pg["offset"], pg["width"], pg.get("z", 245)
        x0 = X(a)
        ax.add_patch(Rectangle((x0 - 10, lev + z + 18), L + 20, 10, fc="#c9a27c", ec="k", lw=0.6, zorder=5))
        n = max(3, round(L / 14))
        for k in range(n + 1):
            xx = x0 - 6 + (L + 6) * k / n
            ax.add_patch(Rectangle((xx, lev + z + 28), 5, 8, fc="#c9a27c", ec="k", lw=0.4, zorder=5))
        for t in (x0 + 10, x0 + L - 18):
            ax.plot([t, t + 4], [lev + z - 40, lev + z], color=LINE, lw=1.4, zorder=5)


# ---------------------------------------------------------------- الميزانين (نص دور) + درج مستقيم
def stair_steps(st):
    """درج مستقيم: [(x0, y0, x1, y1, z_top)] — dir: E/W/N/S، يبدأ من start وينتهي بمنسوب rise."""
    n = max(2, round(st["rise"] / st.get("riser", 18)))
    r = st["rise"] / n
    tr, w = st.get("tread", 25), st.get("width", 80)
    sx, sy = st["start"]
    d = st.get("dir", "E")
    out = []
    for i in range(n - 1):                      # آخر قائمة تطلع على أرضية الميزانين
        a, b = i * tr, (i + 1) * tr
        if d == "E":
            out.append((sx + a, sy, sx + b, sy + w, (i + 1) * r))
        elif d == "W":
            out.append((sx - b, sy, sx - a, sy + w, (i + 1) * r))
        elif d == "N":
            out.append((sx, sy + a, sx + w, sy + b, (i + 1) * r))
        else:
            out.append((sx, sy - b, sx + w, sy - a, (i + 1) * r))
    return out, n, r


def _mezz_edges(m):
    x0, y0, x1, y1 = m["rect"]
    return {"S": ((x0, y0), (x1, y0)), "E": ((x1, y0), (x1, y1)), "N": ((x1, y1), (x0, y1)), "W": ((x0, y1), (x0, y0))}


def _slab_pieces(r, holes):
    """البلاطة ناقص الفتحات (مستطيلات)."""
    pieces = [r]
    for hx0, hy0, hx1, hy1 in holes:
        out = []
        for x0, y0, x1, y1 in pieces:
            if hx1 <= x0 or hx0 >= x1 or hy1 <= y0 or hy0 >= y1:
                out.append((x0, y0, x1, y1))
                continue
            if hy0 > y0:
                out.append((x0, y0, x1, hy0))
            if hy1 < y1:
                out.append((x0, hy1, x1, y1))
            if hx0 > x0:
                out.append((x0, max(y0, hy0), hx0, min(y1, hy1)))
            if hx1 < x1:
                out.append((hx1, max(y0, hy0), x1, min(y1, hy1)))
        pieces = out
    return pieces


def add_mezz_3d(S, P, rules, style, cut=None):
    import yaml
    from .model3d import railing_run
    from .style import PRESETS
    lib = yaml.safe_load(open(PRESETS, encoding="utf-8"))["railings"]
    S.material("stair", S.colors.get("trim", ("#8B5A2B", 1))[0])
    for m in P.mezzanines:
        lv = m["level"]
        if cut and cut < lv:
            continue
        x0, y0, x1, y1 = m["rect"]
        S.zoff = 0
        holes = [h["rect"] for h in m.get("holes", [])]                  # فتحة بالأرضية (درج حلزوني)
        for rx0, ry0, rx1, ry1 in _slab_pieces((x0, y0, x1, y1), holes):
            S.box("wood_in", rx0, ry0, lv - 4, rx1, ry1, lv)              # تطبيق الأرضية
        k = x0 + 30
        while k < x1 - 5:                                                 # مدادات 5×15 كل 60 (مكشوفة من تحت)
            cuts = [(h[1], h[3]) for h in holes if h[0] - 3 < k < h[2] + 3]
            from .model3d import _segments
            for ja, jb in _segments(y0, y1, cuts):
                S.box("joist", k - 2.5, ja, lv - 19, k + 2.5, jb, lv - 4)
            k += 60
        for h in holes:                                                   # إطار الفتحة + دربزين حولها
            hx0, hy0, hx1, hy1 = h
            S.box("joist", hx0 - 5, hy0, lv - 19, hx0, hy1, lv - 4)
            S.box("joist", hx1, hy0, lv - 19, hx1 + 5, hy1, lv - 4)
        for hd in m.get("holes", []):
            hx0, hy0, hx1, hy1 = hd["rect"]
            edges = {"S": ((hx0, hy0), (hx1, hy0)), "N": ((hx1, hy1), (hx0, hy1)),
                     "W": ((hx0, hy1), (hx0, hy0)), "E": ((hx1, hy0), (hx1, hy1))}
            hname = hd.get("railing_style", m.get("railing_style", "vertical_balusters"))
            from .model3d import _segments
            for side in hd.get("railing", ["S", "E", "W", "N"]):
                p0, p1 = edges[side]
                w = Wall("hole", p0, p1)
                gs = []
                for g0, g1 in hd.get("gaps", {}).get(side, []):         # مدى بالإحداثي (x للشمال/الجنوب، y للشرق/الغرب)
                    if side in "SN":
                        ta, tb = (g0 - hx0, g1 - hx0) if side == "S" else (hx1 - g1, hx1 - g0)
                    else:
                        ta, tb = (g0 - hy0, g1 - hy0) if side == "E" else (hy1 - g1, hy1 - g0)
                    gs.append((ta, tb))
                for a_, b_ in _segments(0, w.length, gs):
                    railing_run(S, w, a_, b_, lv, hname, lib[hname], height=100)
        S.box("joist", x0, y0, lv - 25, x1, y0 + 7, lv - 4)               # جسر الحافة
        name = m.get("railing_style", "vertical_balusters")
        spec = lib[name]
        for side in m.get("railing", ["S"]):
            p0, p1 = _mezz_edges(m)[side]
            w = Wall("mz", p0, p1)
            gaps = [(g0 - min(p0[0], p1[0]), g1 - min(p0[0], p1[0])) for g0, g1 in m.get("gaps", [])] \
                if side in "SN" else []
            if side == "N":
                gaps = [(w.length - b, w.length - a) for a, b in gaps]
            from .model3d import _segments
            lo, hi = 0, w.length
            if m.get("railing_span") and side in "SN":       # الدربزين بس تحت الجزء العالي من السقف المائل
                x_a, x_b = m["railing_span"]
                lo, hi = max(0, x_a - min(p0[0], p1[0])), min(w.length, x_b - min(p0[0], p1[0]))
            for a, b in _segments(lo, hi, gaps):
                railing_run(S, w, a, b, lv, name, spec, height=100)
    for st in P.straight_stairs:
        steps, n, r = stair_steps(st)
        S.zoff = st.get("z0", 0)
        for sx0, sy0, sx1, sy1, zt in steps:
            if cut and zt > cut:
                continue
            S.box("stair", sx0, sy0, zt - 4, sx1, sy1, zt)               # الدرجة
            S.box("stair", sx0, sy0, max(zt - r, 0), sx0 + 2, sy1, zt - 4) if st.get("dir", "E") == "E" else None
        if not cut:                                                       # الشاحط (كمرة مائلة) + دربزين على الجهة المفتوحة
            xs = [s_[0] for s_ in steps] + [s_[2] for s_ in steps]
            ys = [s_[1] for s_ in steps] + [s_[3] for s_ in steps]
            ax0, ax1, ay0, ay1 = min(xs), max(xs), min(ys), max(ys)
            top = steps[-1][4] + r
            for yy in ((ay0, ay0 + 5), (ay1 - 5, ay1)):
                S.hexa("stair", [(ax0, yy[0], 0), (ax0 + 8, yy[0], 0), (ax1, yy[0], top - 30), (ax1, yy[0], top - 30),
                                 (ax0, yy[0], 25), (ax0 + 8, yy[0], 25), (ax1, yy[0], top + 4), (ax1, yy[0], top + 4)]
                       if False else
                       [(ax0, yy[0], 0), (ax1, yy[0], top - 30), (ax1, yy[1], top - 30), (ax0, yy[1], 0),
                        (ax0, yy[0], 28), (ax1, yy[0], top + 4), (ax1, yy[1], top + 4), (ax0, yy[1], 28)])
            ry = ay0 if st.get("rail", "S") == "S" else ay1 - 5
            for k in range(0, len(steps), 2):                             # قوائم الدربزين
                s_ = steps[k]
                S.box("stair", s_[0] + 9, ry + 1, s_[4], s_[0] + 13, ry + 4, s_[4] + 90)
            S.hexa("stair", [(ax0, ry, 95), (ax1, ry, top + 95), (ax1, ry + 5, top + 95), (ax0, ry + 5, 95),
                             (ax0, ry, 100), (ax1, ry, top + 100), (ax1, ry + 5, top + 100), (ax0, ry + 5, 100)])
    S.zoff = 0
    add_spiral_3d(S, P, cut)


def spiral_steps(sp):
    """درج حلزوني: [(زاوية من، زاوية إلى، z_top)] بالدرجات — عكس عقارب الساعة (ccw) أو معها (cw).
    sp: {center, r, rise, riser, step_deg, end_deg, dir} — end_deg = زاوية آخر درجة (الوصول للميزانين)."""
    n = max(2, round(sp["rise"] / sp.get("riser", 19)))
    r = sp["rise"] / n
    stp = sp.get("step_deg", 30)
    sg = 1 if sp.get("dir", "ccw") == "ccw" else -1
    end = sp.get("end_deg", 90)
    start = end - sg * stp * (n - 1)
    out = []
    for i in range(n - 1):
        a0 = start + sg * stp * i
        out.append((a0, a0 + sg * stp, (i + 1) * r))
    return out, n, r


def _arc(c, rad, a0, a1, k=6):
    return [(c[0] + rad * math.cos(math.radians(a0 + (a1 - a0) * j / k)),
             c[1] + rad * math.sin(math.radians(a0 + (a1 - a0) * j / k))) for j in range(k + 1)]


def add_spiral_3d(S, P, cut=None):
    """درجات إسفين حول عمود وسطي + دربزين حلزوني على الحافة الخارجية."""
    for sp in P.spiral_stairs:
        steps, n, r = spiral_steps(sp)
        c, R = sp["center"], sp.get("r", 80)
        S.zoff = 0
        top = sp["rise"] + 95
        S.box("stair", c[0] - 6, c[1] - 6, 0, c[0] + 6, c[1] + 6, min(top, cut) if cut else top)    # العمود
        for a0, a1, zt in steps:
            if cut and zt > cut:
                continue
            pts = [tuple(c)] + _arc(c, R, a0, a1)
            m = len(pts)
            S.poly("stair", [(x, y, zt - 4) for x, y in pts] + [(x, y, zt) for x, y in pts],
                   [tuple(range(m)), tuple(range(m, 2 * m))] + [(i, (i + 1) % m, m + (i + 1) % m, m + i) for i in range(m)])
            if not cut:                                   # قائم دربزين بطرف كل درجة
                x, y = _arc(c, R - 4, a0, a0, 1)[0]
                S.box("stair", x - 2, y - 2, zt, x + 2, y + 2, zt + 90)
        if not cut:                                       # الدربزين الحلزوني (قطع قصيرة متصلة)
            for a0, a1, zt in steps:
                q = _arc(c, R - 4, a0, a1, 3)
                for j in range(3):
                    (xa, ya), (xb, yb) = q[j], q[j + 1]
                    za, zb = zt + 90 + r * j / 3, zt + 90 + r * (j + 1) / 3
                    S.hexa("stair", [(xa - 2, ya - 2, za), (xb - 2, yb - 2, zb), (xb + 2, yb + 2, zb), (xa + 2, ya + 2, za),
                                     (xa - 2, ya - 2, za + 5), (xb - 2, yb - 2, zb + 5), (xb + 2, yb + 2, zb + 5),
                                     (xa + 2, ya + 2, za + 5)])
    S.zoff = 0


def draw_spiral_plan(ax, P, upper=False):
    """مسقط الدرج الحلزوني: دائرة + خطوط الدرجات الشعاعية + سهم الصعود."""
    for sp in P.spiral_stairs:
        steps, n, r = spiral_steps(sp)
        c, R = sp["center"], sp.get("r", 80)
        ax.add_patch(Circle(c, R, fill=False, ec="#6b4f3a", lw=0.8, zorder=3))
        ax.add_patch(Circle(c, 6, fc="#6b4f3a", ec="none", zorder=3))
        for a0, a1, zt in steps + [(steps[-1][1], None, 0)]:
            x, y = _arc(c, R, a0, a0, 1)[0]
            dashed = (not upper) and zt > 120
            ax.plot([c[0], x], [c[1], y], color="#6b4f3a", lw=0.4 if dashed else 0.6, ls=(0, (4, 3)) if dashed else "-",
                    zorder=3)
        mid = [_arc(c, R * 0.62, a0 + (a1 - a0) / 2, a0 + (a1 - a0) / 2, 1)[0] for a0, a1, _ in steps]
        ax.plot([p[0] for p in mid[:-1]], [p[1] for p in mid[:-1]], color="#b04020", lw=0.8, zorder=4)
        ax.annotate("", mid[-1], mid[-2], arrowprops=dict(arrowstyle="->", color="#b04020", lw=0.9), zorder=4)
        ax.text(c[0], c[1] - R - 8, f"{sp.get('name', 'درج حلزوني')} Ø{2 * R / 100:.2f} م — {n} قائمة × {r:.1f} سم",
                ha="center", va="top", fontsize=6.5, color="#b04020", zorder=5)


def draw_mezz_on_ground(ax, P):
    """في المسقط الأرضي: حدود الميزانين (متقطع) + الدرج المستقيم."""
    for m in P.mezzanines:
        x0, y0, x1, y1 = m["rect"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="#6b4f3a", lw=0.8, ls=(0, (6, 4)), zorder=2))
        ax.text((x0 + x1) / 2, y0 + 10, f"حد الميزانين فوق (منسوب +{m['level'] / 100:.2f})", ha="center", va="bottom",
                fontsize=6.5, color="#6b4f3a", zorder=5)
    for st in P.straight_stairs:
        steps, n, r = stair_steps(st)
        for sx0, sy0, sx1, sy1, zt in steps:
            dashed = zt > 120
            ax.add_patch(Rectangle((sx0, sy0), sx1 - sx0, sy1 - sy0, fill=False, ec="#6b4f3a",
                                   lw=0.4 if dashed else 0.7, ls=(0, (4, 3)) if dashed else "-", zorder=3))
        a, b = steps[0], steps[-1]
        cy = (a[1] + a[3]) / 2
        ax.annotate("", ((b[0] + b[2]) / 2, cy), ((a[0] + a[2]) / 2, cy),
                    arrowprops=dict(arrowstyle="->", color="#b04020", lw=0.9), zorder=4)
        ax.text((a[0] + b[2]) / 2, a[3] + 6, f"{st.get('name', 'درج الميزانين')} {n} قائمة × {r:.1f} سم", ha="center", va="bottom",
                fontsize=6.5, color="#b04020", zorder=5)
    draw_spiral_plan(ax, P)


def mezz_sheet(ctx):
    """مسقط الميزانين (نص الدور): البلاطة + الفراغ المزدوج + الدرج + الفرش + البلكونة."""
    from .sheets import draw_furniture, drawing_ax, new_page, title, A3, dim, C_DOOR
    from .model import outer_bbox
    P, rules = ctx["project"], ctx["rules"]
    half = wall_thickness(rules) / 2
    x0, y0, x1, y1 = outer_bbox(P, rules)
    fig = new_page(A3)
    ax = drawing_ax(fig, [0.06, 0.08, 0.88, 0.84])
    lv = P.mezzanines[0]["level"] if P.mezzanines else 0
    title(ax, "مسقط الميزانين (نص الدور) — غرفة النوم", f"منسوب أرضية الميزانين +{lv / 100:.2f}  |  الأبعاد بالسنتيمتر")
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="white", ec="k", lw=1.6, zorder=0.3))
    ax.add_patch(Rectangle((x0 + 2 * half, y0 + 2 * half), x1 - x0 - 4 * half, y1 - y0 - 4 * half, fc="white", ec="k",
                           lw=0.8, zorder=0.4))
    for m in P.mezzanines:
        mx0, my0, mx1, my1 = m["rect"]
        ax.add_patch(Rectangle((mx0, my0), mx1 - mx0, my1 - my0, fc="#f6ecdf", ec="#8b5a2b", lw=1, zorder=0.5))
        yy = my0 + 14
        while yy < my1:
            ax.plot([mx0, mx1], [yy, yy], color="#e3cdb0", lw=0.4, zorder=0.6)
            yy += 14
        for side in m.get("railing", ["S"]):
            p0, p1 = _mezz_edges(m)[side]
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color="#8b5a2b", lw=2.4, zorder=4)
        for g0, g1 in m.get("gaps", []):
            ax.plot([g0, g1], [my0, my0], color="white", lw=3, zorder=5)
        for hd in m.get("holes", []):                 # فتحة الدرج بالأرضية + الدربزين حولها
            hx0, hy0, hx1, hy1 = hd["rect"]
            ax.add_patch(Rectangle((hx0, hy0), hx1 - hx0, hy1 - hy0, fc="white", ec="none", zorder=0.65))
            edges = {"S": ((hx0, hy0), (hx1, hy0)), "N": ((hx1, hy1), (hx0, hy1)),
                     "W": ((hx0, hy1), (hx0, hy0)), "E": ((hx1, hy0), (hx1, hy1))}
            for side in hd.get("railing", ["S", "E", "W", "N"]):
                (pa, pb) = edges[side]
                ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color="#8b5a2b", lw=2.4, zorder=4)
                for g0, g1 in hd.get("gaps", {}).get(side, []):
                    if side in "SN":
                        ax.plot([g0, g1], [pa[1], pa[1]], color="white", lw=3, zorder=5)
                    else:
                        ax.plot([pa[0], pa[0]], [g0, g1], color="white", lw=3, zorder=5)
            ax.text((hx0 + hx1) / 2, hy0 - 6, "فتحة الدرج + دربزين", ha="center", va="top", fontsize=6.5,
                    color="#8b5a2b", zorder=6)
        ax.text((mx0 + mx1) / 2, my1 - 20, f"{m.get('name', 'الميزانين')}  {(mx1 - mx0) / 100:.2f} × {(my1 - my0) / 100:.2f} م"
                f"  |  {(mx1 - mx0) * (my1 - my0) / 1e4:.1f} م²", ha="center", va="top", fontsize=10, color="#5a3a22", zorder=6)
        vy0 = y0 + 2 * half
        ax.add_patch(Rectangle((mx0, vy0), mx1 - mx0, my0 - vy0, fill=False, ec="#999", lw=0.6, hatch="..", zorder=0.5))
        ax.text((mx0 + mx1) / 2, vy0 + 60 if P.spiral_stairs else (vy0 + my0) / 2 + 40,
                "فراغ مزدوج الارتفاع (الصالة تحت)\nالواجهة زجاج كامل",
                ha="center", va="center", fontsize=9, color="#777", zorder=6)
        hb = m.get("headroom")
        if hb:                                     # خط ارتفاع 1.90 م تحت السقف المائل
            for xx in hb:
                ax.plot([xx, xx], [my0, my1], color="#c56b1a", lw=0.8, ls="--", zorder=5)
            ax.text((hb[0] + hb[1]) / 2, my0 + 12, "ارتفاع صافي ≥ 1.90 م بين الخطين", ha="center", fontsize=6.5,
                    color="#c56b1a", zorder=6)
        dim(ax, (mx0, my1), (mx1, my1), 40, fs=7)
        dim(ax, (mx1, my0), (mx1, my1), -40, fs=7)
    for st in P.straight_stairs:
        steps, n, r = stair_steps(st)
        for sx0, sy0, sx1, sy1, zt in steps:
            ax.add_patch(Rectangle((sx0, sy0), sx1 - sx0, sy1 - sy0, fill=False, ec="#6b4f3a", lw=0.6, zorder=3))
        a, b = steps[0], steps[-1]
        cy = (a[1] + a[3]) / 2
        ax.annotate("", ((b[0] + b[2]) / 2, cy), ((a[0] + a[2]) / 2, cy),
                    arrowprops=dict(arrowstyle="->", color="#b04020", lw=0.9), zorder=4)
        ax.text((a[0] + b[2]) / 2, a[1] - 6, "صعود", ha="center", va="top", fontsize=7, color="#b04020", zorder=5)
    draw_spiral_plan(ax, P, upper=True)
    import dataclasses
    PM = dataclasses.replace(P, furniture=[f for f in P.furniture if f.floor == -1])
    draw_furniture(ax, dataclasses.replace(PM, furniture=[dataclasses.replace(f, floor=0) for f in PM.furniture]))
    for w in P.walls:                              # فتحات الجملون (باب البلكونة)
        for go in w.gable_openings:
            p, q = w.point(go["offset"], -half), w.point(go["offset"] + go["width"], -half)
            ax.plot([p[0], q[0]], [p[1], q[1]], color="white", lw=4, zorder=5)
            ax.plot([p[0], q[0]], [p[1], q[1]], color=C_DOOR, lw=1.2, zorder=6)
            m_ = w.point(go["offset"] + go["width"] / 2, half + 14)
            ax.text(*m_, go.get("code", ""), ha="center", fontsize=8, color=C_DOOR, zorder=6)
    draw_bumps_plan(ax, P, rules, "mezz")
    for b in P.bumps:
        _w, _h, o_, a_, L_, d_ = bump_geom(P, rules, b)
        x0, y0 = min(x0, *(o_(t, d_)[0] for t in (a_, a_ + L_))), min(y0, *(o_(t, d_)[1] for t in (a_, a_ + L_)))
        x1, y1 = max(x1, *(o_(t, d_)[0] for t in (a_, a_ + L_))), max(y1, *(o_(t, d_)[1] for t in (a_, a_ + L_)))
    for d in P.decks:
        if d.level and P.mezzanines and abs(d.level - lv) < 1:
            dx0, dy0, dx1, dy1 = d.rect
            ax.add_patch(Rectangle((dx0, dy0), dx1 - dx0, dy1 - dy0, fc="#f6ecdf", ec="#8b5a2b", lw=0.9, zorder=2))
            ax.text((dx0 + dx1) / 2, (dy0 + dy1) / 2, f"{d.name}  {(dx1 - dx0) / 100:.2f} × {(dy1 - dy0) / 100:.2f} م",
                    ha="center", va="center", fontsize=9, color="#5a3a22", zorder=6)
            x0, y0, x1, y1 = min(x0, dx0), min(y0, dy0), max(x1, dx1), max(y1, dy1)
    ax.set_xlim(x0 - 120, x1 + 120)
    ax.set_ylim(y0 - 120, y1 + 120)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, "مسقط الميزانين"


# ---------------------------------------------------------------- بروز مقفل (دورة مياه الميزانين فوق + غرفة تفتيش تحت)
def bump_geom(P, rules, b):
    w = _wall(P, b["wall"])
    half = wall_thickness(rules) / 2
    o = _out(w, half)
    a, L, d = b["offset"], b["width"], b.get("depth", 150)
    return w, half, o, a, L, d


def add_bumps_3d(S, P, rules, style, cut=None):
    for b in P.bumps:
        w, half, o, a, L, d = bump_geom(P, rules, b)
        if cut:                                      # المقطع: جدران البروز لين منسوب القطع (عشان قطع الحمام ما تطيح برا)
            S.zoff = 0
            z0, zc = b.get("base", -P.slab_height), min(cut, b.get("eave", 445))
            S.wbox("wood", w, a, a + 12, -half - d, -half, z0, zc)
            S.wbox("wood", w, a + L - 12, a + L, -half - d, -half, z0, zc)
            S.wbox("wood", w, a, a + L, -half - d, -half - d + 12, z0, zc)
            S.material("tiles", "#D5D9DC")
            S.wbox("tiles", w, a + 12, a + L - 12, -half - d + 12, -half, z0, 1.2)
            continue
        S.zoff = 0
        z0, ze = b.get("base", -P.slab_height), b.get("eave", 445)
        tp = math.tan(math.radians(b.get("pitch", 40)))
        rise = L / 2 * tp
        ov = b.get("overhang", 12)
        # الجدران (صندوق مقفل من الأرض لين الرفرف)
        S.wbox("wood", w, a, a + L, -half - d, -half, z0, ze)
        # جملون البروز (مثلث أمامي) + سطحين قرميد يصرّفون للجنبين
        S.wprism("wood", w, [(a, ze), (a + L, ze), (a + L / 2, ze + rise)], -half - d, -half - d + 12)
        tc = a + L / 2
        for sg in (-1, 1):
            te = tc + sg * (L / 2 + ov)
            zl = ze - ov * tp
            q = [(tc, ze + rise + 2), (te, zl + 2), (te, zl + 8), (tc, ze + rise + 8)]
            front = [(*w.point(t, -half - d - ov), z) for t, z in q]
            back = [(*w.point(t, -half), z) for t, z in q]
            S.poly("roof_tiles", front + back, [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
                                                (2, 3, 7, 6), (3, 0, 4, 7)])
            S.wdiag("trim", w, tc, ze + rise + 4, te, zl + 4, 14, -half - d - ov - 2.5, -half - d - ov)
        # حزام بين الدورين (منسوب أرضية الحمام) + شباك تهوية + باب غرفة التفتيش
        fz = b.get("floor_z", 245)
        S.wbox("trim", w, a - 2, a + L + 2, -half - d - 3, -half, fz - 20, fz)
        wv = Wall("bmp", o(a + L / 2 - 30, d + 0.5), o(a + L / 2 + 30, d + 0.5))
        S.wbox("frame", wv, 0, 60, -2, 2, fz + 140, fz + 180)
        S.wbox("glass", wv, 4, 56, -1, 1, fz + 144, fz + 176)
        if b.get("door_h", 120):                     # باب خارجي للمخزن/غرفة التفتيش
            S.wbox("door", wv, -5, 65, -2, 2, z0 + 45, min(fz - 25, z0 + 45 + b.get("door_h", 120)))
        else:                                        # تحت دورة مياه داخلية: شباك تهوية بدل الباب
            S.wbox("frame", wv, 0, 60, -2, 2, 150, 190)
            S.wbox("glass", wv, 4, 56, -1, 1, 154, 186)
    S.zoff = 0


def draw_bumps_plan(ax, P, rules, which):
    """which = 'ground' (غرفة التفتيش) أو 'mezz' (دورة المياه)."""
    for b in P.bumps:
        w, half, o, a, L, d = bump_geom(P, rules, b)
        outer = [o(a, 0), o(a, d), o(a + L, d), o(a + L, 0)]
        inner = [o(a + 12, 0), o(a + 12, d - 12), o(a + L - 12, d - 12), o(a + L - 12, 0)]
        ax.add_patch(Polygon(outer, closed=True, fc="#eeeeee", ec="k", lw=1.2, hatch="////", zorder=0.7))
        wet_down = not b.get("door_h", 120)          # الدور الأرضي للبروز دورة مياه (بابها من داخل الكوخ)
        ax.add_patch(Polygon(inner, closed=True, fc="#eef6ff" if which == "mezz" or wet_down else "white", ec="k",
                             lw=0.8, zorder=0.8))
        c = o(a + L / 2, d / 2)
        if which == "ground":
            ax.text(*c, b.get("name_down", "غرفة تفتيش"), ha="center", va="center", fontsize=6.5, zorder=5)
            p0, p1 = o(a + L / 2 - 30, d), o(a + L / 2 + 30, d)
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color="white", lw=3, zorder=4)
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color="#1f3fff" if wet_down else "#10a010", lw=1.2, zorder=5)
        else:
            ax.text(c[0], c[1] + 10, b.get("name_up", "دورة مياه"), ha="center", va="center", fontsize=7, zorder=5)
            ax.text(c[0], c[1] - 8, f"{(L - 24) / 100:.2f} × {(d - 12) / 100:.2f} م", ha="center", va="center",
                    fontsize=6, zorder=5)


def draw_bumps_elev(ax, P, rules, w, stack):
    """البروز في الواجهة الخلفية (وجه) والجانبية (مقطع جانبي)."""
    names = {w2.name for w2, _l in stack}
    for b in P.bumps:
        bw, half, o, a, L, d = bump_geom(P, rules, b)
        z0, ze = b.get("base", -P.slab_height), b.get("eave", 445)
        tp = math.tan(math.radians(b.get("pitch", 40)))
        rise = L / 2 * tp
        fz = b.get("floor_z", 245)
        par = abs(bw.u[0] * w.u[0] + bw.u[1] * w.u[1]) > 0.9
        if par and b["wall"] != w.name:  # الواجهة المقابلة: البروز وراء المبنى (ما يبان)
            continue
        if b["wall"] in names:           # الوجه
            x0 = a + half
            ax.add_patch(Rectangle((x0, z0), L, ze - z0, fc="#f3e7d6", ec="k", lw=1, zorder=5))
            ax.add_patch(Polygon([(x0 - 12, ze - 10), (x0 + L / 2, ze + rise), (x0 + L + 12, ze - 10)], closed=True,
                                 fc="#fff3e0", ec="#c56b1a", lw=0.9, zorder=5))
            ax.add_patch(Rectangle((x0, fz - 20), L, 20, fc="#c9a27c", ec="k", lw=0.5, zorder=6))
            ax.add_patch(Rectangle((x0 + L / 2 - 30, fz + 140), 60, 40, fc="white", ec="#1f3fff", lw=0.8, zorder=6))
            if b.get("door_h", 120):
                ax.add_patch(Rectangle((x0 + L / 2 - 30, z0 + 45), 60, min(fz - 25 - z0 - 45, b.get("door_h", 120)),
                                       fc="white", ec="#10a010", lw=0.8, zorder=6))
            else:
                ax.add_patch(Rectangle((x0 + L / 2 - 30, 150), 60, 40, fc="white", ec="#1f3fff", lw=0.8, zorder=6))
            ax.text(x0 + L / 2, fz + 60, b.get("name_up", "دورة مياه"), ha="center", fontsize=6, zorder=7)
            ax.text(x0 + L / 2, fz - 45, b.get("name_down", "غرفة تفتيش"), ha="center", fontsize=6, zorder=7)
        else:                            # جانبي: البروز يطلع من الجدار
            ux, uy = w.u
            pts = [o(a, 0), o(a, d), o(a + L, d), o(a + L, 0)]
            ts = [(px - w.start[0]) * ux + (py - w.start[1]) * uy + half for px, py in pts]
            nx_, ny_ = w.n
            sds = [(px - w.start[0]) * nx_ + (py - w.start[1]) * ny_ for px, py in pts]
            if max(abs(v) for v in sds) > 3000:
                continue
            t0, t1 = min(ts), max(ts)
            if t1 - t0 < 5 or t1 - t0 > d + 5:
                continue                  # الوجه الأمامي/الخلفي يرسم فوق
            ax.add_patch(Rectangle((t0, z0), t1 - t0, ze - z0, fc="#f3e7d6", ec="k", lw=1, zorder=5))
            ax.add_patch(Rectangle((t0 - 12, ze), t1 - t0 + 12, rise + 10, fc="#fff3e0", ec="#c56b1a", lw=0.9,
                                   zorder=5))
            ax.add_patch(Rectangle((t0, fz - 20), t1 - t0, 20, fc="#c9a27c", ec="k", lw=0.5, zorder=6))
