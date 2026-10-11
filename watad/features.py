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

from matplotlib.patches import Polygon, Rectangle

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
