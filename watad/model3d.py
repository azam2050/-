"""نموذج 3D كامل للكوخ بالمواد والألوان — OBJ+MTL (3ds Max) و GLB.

المحاور: x,y المسقط، z للأعلى، z=0 وجه الصبة، الأرض الطبيعية z=-20. الوحدة سم في OBJ، متر في GLB.
"""
import math

import numpy as np

from .model import Wall, outer_bbox, wall_thickness
from .roof import cross_gables, cross_planes, rafter_positions, roof_geometry


class Scene:
    def __init__(self):
        self.parts = {}     # material -> [verts, faces]
        self.colors = {}    # material -> (hex, alpha)
        self.zoff = 0.0     # إزاحة رأسية (منسوب الدور الحالي)

    def material(self, name, color, alpha=1.0):
        self.colors[name] = (color, alpha)

    def poly(self, mat, verts, faces, center=None):
        """يضيف مجسم محدب؛ يضبط اتجاه الأوجه للخارج."""
        V, F = self.parts.setdefault(mat, [[], []])
        base = len(V)
        verts = [(float(v[0]), float(v[1]), float(v[2]) + self.zoff) for v in verts]
        c = np.mean(verts, axis=0) if center is None else center
        for f in faces:
            pts = np.array([verts[i] for i in f])
            n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            if np.linalg.norm(n) < 1e-9 and len(f) > 3:
                n = np.cross(pts[2] - pts[0], pts[3] - pts[0])
            if np.dot(n, pts.mean(axis=0) - c) < 0:
                f = f[::-1]
            F.append([base + i for i in f])
        V.extend(verts)

    def hexa(self, mat, c):
        """8 نقاط: 4 سفلية ثم 4 علوية بنفس الترتيب."""
        self.poly(mat, c, [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])

    def box(self, mat, x0, y0, z0, x1, y1, z1):
        self.hexa(mat, [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])

    def wbox(self, mat, w, t0, t1, s0, s1, z0, z1):
        """صندوق في إطار جدار: t على طوله، s عمودي (يسار +)، z ارتفاع."""
        b = [w.point(t0, s0), w.point(t1, s0), w.point(t1, s1), w.point(t0, s1)]
        self.hexa(mat, [(*p, z0) for p in b] + [(*p, z1) for p in b])

    def wprism(self, mat, w, pts_tz, s0, s1):
        """بثق مضلع محدب (t,z) بسماكة s0..s1."""
        n = len(pts_tz)
        front = [(*w.point(t, s0), z) for t, z in pts_tz]
        back = [(*w.point(t, s1), z) for t, z in pts_tz]
        faces = [tuple(range(n)), tuple(range(n, 2 * n))]
        faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.poly(mat, front + back, faces)

    def wdiag(self, mat, w, t0, z0, t1, z1, width, s0, s1):
        """قطعة مائلة (دياغونال) في مستوى الجدار."""
        dt, dz = t1 - t0, z1 - z0
        L = math.hypot(dt, dz)
        nt, nz = -dz / L * width / 2, dt / L * width / 2
        self.wprism(mat, w, [(t0 + nt, z0 + nz), (t1 + nt, z1 + nz), (t1 - nt, z1 - nz), (t0 - nt, z0 - nz)],
                    s0, s1)

    # ------------------------------------------------------------ تصدير
    def write_obj(self, path, title=""):
        mtl = path.with_suffix(".mtl")
        lines = [f"# {title} — Watad Wood Factory (units: cm, Z-up)", f"mtllib {mtl.name}"]
        off = 1
        for mat, (V, F) in self.parts.items():
            lines.append(f"o {mat}")
            lines += ["v {:.2f} {:.2f} {:.2f}".format(*v) for v in V]
            lines.append(f"usemtl {mat}")
            lines += ["f " + " ".join(str(i + off) for i in f) for f in F]
            off += len(V)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        m = []
        for mat, (col, a) in self.colors.items():
            r, g, b = (int(col.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
            m += [f"newmtl {mat}", f"Kd {r:.3f} {g:.3f} {b:.3f}", f"Ka {r * .2:.3f} {g * .2:.3f} {b * .2:.3f}",
                  f"d {a:.2f}", "illum 2", ""]
        mtl.write_text("\n".join(m), encoding="utf-8")

    def write_glb(self, path):
        import trimesh
        scene = trimesh.Scene()
        for mat, (V, F) in self.parts.items():
            tris = [t for f in F for t in ([f] if len(f) == 3 else [(f[0], f[i], f[i + 1]) for i in range(1, len(f) - 1)])]
            v = np.array(V) / 100.0
            v = np.column_stack([v[:, 0], v[:, 2], -v[:, 1]])      # Y-up
            col, a = self.colors[mat]
            rgba = [int(col.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)] + [int(a * 255)]
            mesh = trimesh.Trimesh(vertices=v, faces=tris, process=False)
            mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
                name=mat, baseColorFactor=rgba, alphaMode="BLEND" if a < 1 else "OPAQUE",
                roughnessFactor=0.2 if mat == "glass" else 0.8, metallicFactor=0.0))
            scene.add_geometry(mesh, node_name=mat, geom_name=mat)
        scene.export(path)

    def faces_colored(self):
        for mat, (V, F) in self.parts.items():
            col, a = self.colors[mat]
            for f in F:
                yield [V[i] for i in f], col, a


# ---------------------------------------------------------------- البناء
def _segments(L0, L1, cuts):
    out, x = [], L0
    for a, b in sorted(cuts):
        if a > x:
            out.append((x, a))
        x = max(x, b)
    if L1 > x:
        out.append((x, L1))
    return out


def build_scene(project, rules, style, heights, cut=None, furniture=False):
    """cut: ارتفاع قطع الجدران (مقطع علوي بدون سقف). furniture: إضافة الفرش والأرضيات."""
    S = Scene()
    S.material("slab", style["slab"])
    S.material("wood", style["wood"])
    S.material("trim", style["trim"])
    S.material("frame", style["frame"])
    S.material("glass", style["glass"], style["glass_alpha"])
    S.material("roof_tiles", style["roof"])
    S.material("rafters", style["trim"])
    S.material("sheathing", style["trim"])
    S.material("wood_in", style["wood"])
    S.material("ceiling", style["wood"])
    S.material("joist", style["wood"])
    S.material("door", style["frame"])
    half = wall_thickness(rules) / 2
    x0, y0, x1, y1 = outer_bbox(project, rules)
    sh = project.slab_height
    S.box("slab", x0 - 10, y0 - 10, -sh, x1 + 10, y1 + 10, 0)

    g = roof_geometry(project, rules)
    ridge_y = project.roof.ridge_axis == "y"
    p, rise, ov = g["pitch"], g["rise"], project.roof.overhang
    tp = math.tan(p)
    tr = style["trims"]

    top = project.top_floor
    for w in project.walls:
        H = heights[w.name]
        lev = project.level(w.floor)
        if cut and cut - lev <= 5:
            continue                      # دور فوق مستوى القطع
        S.zoff = lev
        Hc = min(H, cut - lev) if cut else H
        L = w.length
        t_lo, t_hi = (-half, L + half) if w.exterior else (0, L)
        wm = "wood" if w.exterior else "wood_in"
        shown = [o for o in w.openings if not (cut and (o.sill if o.kind == "window" else 0) >= cut - lev)]
        cuts = [(o.offset, o.offset + o.width) for o in shown]
        for a, b in _segments(t_lo, t_hi, cuts):
            S.wbox(wm, w, a, b, -half, half, 0, Hc)
        for o in shown:
            a, b = o.offset, o.offset + o.width
            z0 = o.sill if o.kind == "window" else 0
            z1 = min(z0 + o.height, Hc)
            if z0 > 0:
                S.wbox(wm, w, a, b, -half, half, 0, z0)
            if z1 < Hc:
                S.wbox(wm, w, a, b, -half, half, z1, Hc)
            _opening(S, w, o, a, b, z0, z1, half, style, exterior=w.exterior)
        ux, uy = w.u
        gable_end = w.exterior and w.floor == top and ((abs(uy) < 1e-6) == ridge_y)
        if cut:
            pass
        elif gable_end and w.gable_glass:
            _glass_gable(S, w, L, H, rise, half, math.tan(p))
        elif gable_end:
            S.wprism("wood", w, [(-half, H), (L + half, H), (L / 2, H + rise)], -half, half)
        if w.exterior:   # ألواح الزوايا
            cb = tr["corner_boards"]
            for t in (-half, L + half - cb["w"]):
                S.wbox("trim", w, t, t + cb["w"], -half - cb["t"], -half, 0, Hc)
    S.zoff = 0
    # أرضيات الأدوار العلوية (جسور + تطبيق) مع فتحة الدرج
    for f in range(1, top + 1):
        lev = project.level(f)
        if cut and cut <= lev:
            continue
        holes = [st["rect"] for st in project.stairs if st.get("from", 0) == f - 1]
        pieces = [(x0, y0, x1, y1)]
        for hx0, hy0, hx1, hy1 in holes:
            nxt = []
            for a0, b0, a1, b1 in pieces:
                if hx1 <= a0 or hx0 >= a1 or hy1 <= b0 or hy0 >= b1:
                    nxt.append((a0, b0, a1, b1))
                    continue
                if hy0 > b0:
                    nxt.append((a0, b0, a1, hy0))
                if hy1 < b1:
                    nxt.append((a0, hy1, a1, b1))
                if hx0 > a0:
                    nxt.append((a0, max(b0, hy0), hx0, min(b1, hy1)))
                if hx1 < a1:
                    nxt.append((hx1, max(b0, hy0), a1, min(b1, hy1)))
            pieces = nxt
        # الأرضية العلوية مكشوفة من تحت مثل الواقع: تطبيق خشب (نفس خشب الأرضية) فوق مدادات 5×15 كل 60 سم
        # (قاعدة المصنع) تمتد بين الجدران الحاملة، وحزام (رِم) فوق كل جدار من الدور اللي تحته
        fj = rules["members"].get("floor_joist", {"w": 15, "t": 5, "spacing": 60})
        deck_t, jd, jw, sp = 2.5, fj["w"], fj["t"], fj["spacing"]
        for a0, b0, a1, b1 in pieces:
            S.box("ceiling", a0, b0, lev - deck_t, a1, b1, lev)
            yy = b0 + half + jw
            while a1 - a0 > 40 and yy + jw <= b1 - half:
                S.box("joist", max(a0, x0 + 2 * half + 1), yy, lev - deck_t - jd,
                      min(a1, x1 - 2 * half - 1), yy + jw, lev - deck_t)
                yy += sp
        S.zoff = lev - 25
        for w in project.walls_on(f - 1):
            t_lo, t_hi = (-half, w.length + half) if w.exterior else (0, w.length)
            S.wbox("wood" if w.exterior else "joist", w, t_lo, t_hi, -half, half, 0, 25 - deck_t)
        S.zoff = 0
    for st in project.stairs:
        add_stair(S, project, st, cut)
    if furniture:      # "floors" = أرضيات فقط (الفرش الحقيقي يضيفه Blender)
        add_interior(S, project, style, cut, pieces=furniture != "floors")

    if not cut:
        # السقف: مدادات + تطبيق خشب + قرميد
        H = project.roof_base
        rafter_d = rules["members"]["rafter"]["w"]
        rafter_t = rules["members"]["rafter"]["t"]
        if ridge_y:
            a_lo, a_hi, b_lo, b_hi = x0, x1, y0, y1
            to_xy = lambda a, b: (a, b)  # noqa: E731
        else:
            a_lo, a_hi, b_lo, b_hi = y0, y1, x0, x1
            to_xy = lambda a, b: (b, a)  # noqa: E731
        ac = (a_lo + a_hi) / 2
        B0, B1 = b_lo - ov - project.roof.ext_start, b_hi + ov + project.roof.ext_end
        zb = lambda a, side: H + ((a - a_lo) if side < 0 else (a_hi - a)) * tp  # noqa: E731
        kv = 1 / math.cos(p)

        def slope_hexa(mat, side, aa, ab, bb0, bb1, z_off0, z_off1):
            pts = []
            for zo in (z_off0, z_off1):
                for a, b in ((aa, bb0), (ab, bb0), (ab, bb1), (aa, bb1)):
                    pts.append((*to_xy(a, b), zb(a, side) + zo * kv))
            S.hexa(mat, pts)

        for side, eave in ((-1, a_lo - ov), (1, a_hi + ov)):
            aa, ab = (eave, ac) if side < 0 else (ac, eave)
            slope_hexa("sheathing", side, aa, ab, B0, B1, rafter_d, rafter_d + 2.5)     # تطبيق
            slope_hexa("roof_tiles", side, aa, ab, B0, B1, rafter_d + 2.5, rafter_d + 6.5)
            for pos in rafter_positions(project, rules):
                b0 = max(pos - rafter_t / 2, B0)
                b1 = min(pos + rafter_t / 2, B1)
                slope_hexa("rafters", side, aa, ab, b0, b1, 0, rafter_d)
            if not style["exposed_rafter_tails"]:     # لوح واجهة المداد
                fa, fb = sorted((eave, eave + side * tr["fascia"]["t"]))
                ztop = zb(eave, side) + (rafter_d + 6.5) * kv
                zbot = ztop - tr["fascia"]["h"] - 6.5
                c0, c1 = to_xy(fa, B0), to_xy(fb, B1)
                S.box("trim", min(c0[0], c1[0]), min(c0[1], c1[1]), zbot,
                      max(c0[0], c1[0]), max(c0[1], c1[1]), ztop)
        # ألواح حافة الجملون (barge boards)
        bb = tr["barge_board"]
        for bpos in (B0 - bb["t"], B1):
            for side, eave in ((-1, a_lo - ov), (1, a_hi + ov)):
                aa, ab = (eave, ac) if side < 0 else (ac, eave)
                slope_hexa("trim", side, aa, ab, bpos, bpos + bb["t"], rafter_d + 6.5 - bb["h"], rafter_d + 6.5)

    if not cut:
        _cross_gables(S, project, rules, half)
    for d in project.decks:
        if cut and d.level > 0 and d.level > cut:
            continue
        _deck(S, d, style, x0, y0, x1, y1, sh)
    # أعمدة الجلسة المسقوفة + جسر أمامي يحمل طرف الجملون
    pz = []
    for pt in project.posts:
        px, py = pt["at"]
        if cut:
            ztop = cut
        else:
            a = px if ridge_y else py
            ztop = zb(a, -1 if a <= ac else 1)
        ps = pt.get("size", 15)
        S.box("trim", px - ps / 2, py - ps / 2, pt.get("base", 0), px + ps / 2, py + ps / 2, ztop)
        pz.append((px, py, ztop))
    if len(pz) >= 2 and project.roof.ext_start and not cut:
        b_edge = sum((py if ridge_y else px) for px, py, _ in pz) / len(pz)
        a0, a1 = a_lo, a_hi
        c0, c1 = to_xy(a0, b_edge - 8), to_xy(a1, b_edge + 8)
        S.box("trim", min(c0[0], c1[0]), min(c0[1], c1[1]), H - 22, max(c0[0], c1[0]), max(c0[1], c1[1]), H)
    return S


def _cross_gables(S, project, rules, half):
    """المثلثات البارزة: سطحين (مدادات+تطبيق كطبقة وحدة، ثم قرميد)، حشوة المثلث، شباك، وكوابيل تحت الرفرف."""
    rd = rules["members"]["rafter"]["w"]
    for g in cross_gables(project, rules):
        kv = 1 / math.cos(math.radians(g["pitch"]))
        for tri in cross_planes(g):
            n = 3
            faces = [(0, 1, 2), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
            S.poly("sheathing", list(tri) + [(x, y, z + (rd + 2.5) * kv) for x, y, z in tri], faces)
            S.poly("roof_tiles", [(x, y, z + (rd + 2.5) * kv) for x, y, z in tri]
                   + [(x, y, z + (rd + 6.5) * kv) for x, y, z in tri], faces)
        wall, sg, c, hw, H, zr = g["wall"], g["sg"], g["c"], g["hw"], g["H"], g["zr"]
        ax_y = g["axis"] == "y"
        P = (lambda a, b, z: (a, b, z)) if ax_y else (lambda a, b, z: (b, a, z))
        tri = [P(wall, c - hw, H), P(wall, c, zr), P(wall, c + hw, H)]
        inner = [P(wall - sg * 2 * half, c - hw, H), P(wall - sg * 2 * half, c, zr), P(wall - sg * 2 * half, c + hw, H)]
        S.poly("wood", tri + inner, [(0, 1, 2), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)])
        cg = next(x for x in project.roof.cross_gables if x.get("side", "W") == g["side"])
        ww = cg.get("window_width", 110)
        wz0 = H + 15
        wz1 = min(H + cg.get("window_height", 140), zr - (ww / 2) * g["t"] - 25)
        if wz1 - wz0 > 40:
            S.box("frame", *(lambda a, b: (min(a[0], b[0]), min(a[1], b[1]), wz0 - 6, max(a[0], b[0]), max(a[1], b[1]), wz1 + 6))(
                P(wall + sg * 1.5, c - ww / 2 - 6, 0), P(wall, c + ww / 2 + 6, 0)))
            S.box("glass", *(lambda a, b: (min(a[0], b[0]), min(a[1], b[1]), wz0, max(a[0], b[0]), max(a[1], b[1]), wz1))(
                P(wall + sg * 3, c - ww / 2, 0), P(wall + sg * 1.5, c + ww / 2, 0)))
        for y in (c - hw + 35, c + hw - 35):             # كوابيل خشب تحت رفرف المثلث
            a0 = P(wall, y - 3.5, 0)
            a1 = P(wall + sg * 55, y + 3.5, 0)
            S.hexa("trim", [(a0[0], a0[1], H - 60), (a1[0], a0[1], H - 5), (a1[0], a1[1], H - 5), (a0[0], a1[1], H - 60),
                            (a0[0], a0[1], H - 50), (a1[0], a0[1], H + 5), (a1[0], a1[1], H + 5), (a0[0], a1[1], H - 50)]
                   if ax_y else
                   [(a0[0], a0[1], H - 60), (a0[0], a1[1], H - 5), (a1[0], a1[1], H - 5), (a1[0], a0[1], H - 60),
                    (a0[0], a0[1], H - 50), (a0[0], a1[1], H + 5), (a1[0], a1[1], H + 5), (a1[0], a0[1], H - 50)])


def _opening(S, w, o, a, b, z0, z1, half, style, exterior):
    out = -half
    fw = 6
    if o.kind == "window":
        S.wbox("glass", w, a, b, -1, 1, z0, z1)
        for (ta, tb, za, zb_) in ((a, a + fw, z0, z1), (b - fw, b, z0, z1), (a, b, z0, z0 + fw), (a, b, z1 - fw, z1)):
            S.wbox("frame", w, ta, tb, out - 2, half, za, zb_)
        grid = style["window_grid"]
        if grid in ("mullion", "grid") and o.width >= 90:
            m = (a + b) / 2
            S.wbox("frame", w, m - 2.5, m + 2.5, -3, 3, z0, z1)
        if grid == "grid" and o.height >= 90:
            m = (z0 + z1) / 2
            S.wbox("frame", w, a, b, -3, 3, m - 2.5, m + 2.5)
        if getattr(o, "transom", 0):
            S.wbox("frame", w, a, b, -3, 3, o.transom - 3, o.transom + 3)
        tr = style["trims"]["window_trim"]
        if exterior:
            for (ta, tb, za, zb_) in ((a - tr["w"], a, z0 - tr["w"], z1 + tr["w"]),
                                      (b, b + tr["w"], z0 - tr["w"], z1 + tr["w"]),
                                      (a, b, z0 - tr["w"], z0), (a, b, z1, z1 + tr["w"])):
                S.wbox("trim", w, ta, tb, out - tr["t"], out, za, zb_)
    else:
        if o.leaves == 0:           # فتحة بدون باب — إطار خشب جانبي فقط
            for (ta, tb) in ((a, a + 4), (b - 4, b)):
                S.wbox("trim", w, ta, tb, -half, half, 0, z1)
            return
        for (ta, tb, za, zb_) in ((a, a + fw, 0, z1), (b - fw, b, 0, z1), (a, b, z1 - fw, z1)):
            S.wbox("frame", w, ta, tb, out - 2, half, za, zb_)
        if getattr(o, "style", "") in ("sliding", "fixed"):
            S.wbox("glass", w, a + fw, b - fw, -1, 1, 0, z1 - fw)
            n = max(2, round(o.width / 100))
            for k in range(1, n):
                t = a + (b - a) * k / n
                S.wbox("frame", w, t - 3, t + 3, -3, 3, 0, z1)
            S.wbox("frame", w, a, b, -3, 3, 0, 5)
        else:
            n = o.leaves
            lw = (o.width - 2 * fw) / n
            for k in range(n):
                la, lb = a + fw + k * lw, a + fw + (k + 1) * lw
                if style["door_style"] == "french" and exterior:
                    S.wbox("glass", w, la + 8, lb - 8, -1, 1, 10, z1 - fw - 8)
                    for (ta, tb, za, zb_) in ((la, la + 8, 0, z1 - fw), (lb - 8, lb, 0, z1 - fw),
                                              (la, lb, 0, 10), (la, lb, z1 - fw - 8, z1 - fw)):
                        S.wbox("door", w, ta, tb, -2.5, 2.5, za, zb_)
                    for zz in np.linspace(10, z1 - fw - 8, 5)[1:-1]:
                        S.wbox("door", w, la + 8, lb - 8, -1.5, 1.5, zz - 1.5, zz + 1.5)
                    mm = (la + lb) / 2
                    S.wbox("door", w, mm - 1.5, mm + 1.5, -1.5, 1.5, 10, z1 - fw - 8)
                else:
                    S.wbox("door", w, la, lb, -2, 2, 0, z1 - fw)
    if getattr(o, "transom", 0):
        zt = o.transom
        S.wbox("frame", w, a, b, out - 2, half, zt - 3, zt + 3)


def gable_glass_geometry(L, H, rise, tp, border=20, post=10, spacing=110):
    """هندسة مثلث الجملون الزجاج بإطار خشب: (المثلث الداخلي للزجاج، مواقع القوائم، دالة الحافة الداخلية)."""
    bv = border * math.sqrt(1 + tp * tp)            # الإزاحة الرأسية للحافة المائلة الداخلية
    tl = (border + bv) / tp
    apex = H + rise - bv
    inner = [(tl, H + border), (L - tl, H + border), (L / 2, apex)]
    zin = lambda t: H + min(t, L - t) * tp - bv      # noqa: E731
    n = max(1, round((L - 2 * tl) / spacing))
    posts = [tl + (L - 2 * tl) * k / n for k in range(1, n)]
    return inner, posts, zin, bv, tl


FURN_H = [("سرير", 55, "linen"), ("دولاب", 220, "furn"), ("كنبة", 80, "fabric"), ("كرسي", 80, "fabric"),
          ("طاولة", 75, "furn"), ("تلفزيون", 110, "dark"), ("كاونتر", 90, "counter"),
          ("ثلاجة", 180, "white")]


def add_interior(S, project, style, cut=None, pieces=True):
    """أرضيات + فرش مبسط (للمقطع العلوي والعرض الداخلي) — كل دور على منسوبه."""
    S.material("floor", "#B89066")
    S.material("tiles", "#D5D9DC")
    S.material("furn", "#CDBBA2")
    S.material("linen", "#F1EEE8")
    S.material("fabric", "#8E8A84")
    S.material("counter", "#E2DDD5")
    S.material("white", "#F4F4F2")
    S.material("dark", "#2B2B2B")
    for r in project.rooms:
        if cut and cut <= project.level(r.floor):
            continue
        if r.kind == "stair" and r.floor > 0:      # فتحة الدرج في الدور العلوي
            continue
        S.zoff = project.level(r.floor)
        x0, y0, x1, y1 = r.rect
        S.box("tiles" if r.wet else "floor", x0, y0, 0, x1, y1, 1.2)
    for f in (project.furniture if pieces else []):
        if cut and cut <= project.level(f.floor):
            continue
        S.zoff = project.level(f.floor)
        x0, y0, x1, y1 = f.rect
        if f.shape == "shower":
            S.box("white", x0, y0, 1.2, x1, y1, 6)
            continue
        if f.shape == "wc":
            S.box("white", x0 + 4, y0 + 4, 1.2, x1 - 4, y1 - 4, 42)
            continue
        if f.shape == "basin":
            S.box("white", x0, y0, 70, x1, y1, 86)
            continue
        h, m = 50, "furn"
        for key, hh, mm in FURN_H:
            if key in f.name:
                h, m = hh, mm
                break
        if m == "linen":      # سرير: قاعدة خشب + مرتبة + لوح رأس
            S.box("furn", x0, y0, 1.2, x1, y1, 30)
            S.box("linen", x0 + 2, y0 + 2, 30, x1 - 2, y1 - 2, 52)
            continue
        if "طاولة" in f.name:
            S.box("furn", x0, y0, 71, x1, y1, 75)
            for lx, ly in ((x0 + 3, y0 + 3), (x1 - 8, y0 + 3), (x0 + 3, y1 - 8), (x1 - 8, y1 - 8)):
                S.box("furn", lx, ly, 1.2, lx + 5, ly + 5, 71)
            continue
        if m == "fabric" and "كنبة" in f.name:
            S.box("fabric", x0, y0, 1.2, x1, y1, 42)
            S.box("fabric", x0, y1 - 18, 42, x1, y1, 80)
            continue
        S.box(m, x0, y0, 1.2, x1, y1, h)
    S.zoff = 0


def stair_geometry(project, st):
    """درج U: شاحط أول ثم بسطة ثم شاحط راجع. يرجع (قائمة الدرجات [(x0,y0,x1,y1,z_top)], البسطة, رقم القائمة)."""
    x0, y0, x1, y1 = st["rect"]
    fw = st.get("flight_w", 90)
    tread = st.get("tread", 27)
    rise_total = project.level(st.get("from", 0) + 1) - project.level(st.get("from", 0))
    n = max(2, round(rise_total / st.get("riser", 17.5)))
    r = rise_total / n
    n1 = math.ceil(n / 2)          # قوائم الشاحط الأول (آخرها البسطة)
    n2 = n - n1                    # قوائم الشاحط الثاني (آخرها أرضية الدور)
    first_east = st.get("first", "east") == "east"
    fa = (x1 - fw, x1) if first_east else (x0, x0 + fw)
    fb = (x0, x0 + fw) if first_east else (x1 - fw, x1)
    steps = []
    for i in range(1, n1):         # الشاحط الأول باتجاه الشمال
        steps.append((fa[0], y0 + (i - 1) * tread, fa[1], y0 + i * tread, i * r))
    ly0 = y0 + (n1 - 1) * tread
    landing = (x0, ly0, x1, ly0 + st.get("landing", 90), n1 * r)
    for j in range(1, n2):         # الشاحط الثاني باتجاه الجنوب
        steps.append((fb[0], ly0 - j * tread, fb[1], ly0 - (j - 1) * tread, (n1 + j) * r))
    return steps, landing, r, n


def add_stair(S, project, st, cut=None):
    lev = project.level(st.get("from", 0))
    S.material("stair", S.colors.get("trim", ("#8B5A2B", 1))[0])
    steps, landing, r, n = stair_geometry(project, st)
    S.zoff = lev
    # درج خشب حقيقي: قائمة 4 سم + قفلة 2 سم على كل درجة، وجانبين (كمرات مائلة 5×30) لكل شاحط
    tread = st.get("tread", 27)
    for x0, y0, x1, y1, zt in steps:
        if cut and lev + zt > cut + 40:
            continue
        S.box("stair", x0, y0, zt - 4, x1, y1, zt)
        going_n = y1 - y0 > 0 and zt <= landing[4]
        yr = (y0, y0 + 2) if going_n else (y1 - 2, y1)            # القفلة تحت مقدمة الدرجة
        S.box("stair", x0 + 2, yr[0], max(zt - r, 0), x1 - 2, yr[1], zt - 4)
    lx0, ly0, lx1, ly1, lz = landing
    if not (cut and lev + lz > cut + 40):
        S.box("stair", lx0, ly0, lz - 20, lx1, ly1, lz)
    fw = st.get("flight_w", 90)
    sx0, sy0, sx1, sy1 = st["rect"]
    first_east = st.get("first", "east") == "east"
    fa = (sx1 - fw, sx1) if first_east else (sx0, sx0 + fw)
    fb = (sx0, sx0 + fw) if first_east else (sx1 - fw, sx1)
    top = project.level(st.get("from", 0) + 1) - lev
    k = r / tread
    flights = [(fa, sy0, r, ly0, lz), (fb, ly0, lz + r, sy0 + tread, top)]
    for (xa, xb), ya, za, yb, zb in flights:
        if cut and lev + min(za, zb) > cut + 40:
            continue
        for xs in (xa, xb - 5):
            lo_a, lo_b = max(za - 34, 0), zb - 34
            S.hexa("stair", [(xs, ya, lo_a), (xs + 5, ya, lo_a), (xs + 5, yb, lo_b), (xs, yb, lo_b),
                             (xs, ya, za + 4), (xs + 5, ya, za + 4), (xs + 5, yb, zb + 4), (xs, yb, zb + 4)])
    S.zoff = 0
    # دربزين حول فتحة الدرج في الدور العلوي
    if not cut or cut > project.level(st.get("from", 0) + 1) + 50:
        x0, y0, x1, y1 = st["rect"]
        fw = st.get("flight_w", 90)
        top = project.level(st.get("from", 0) + 1)
        import yaml
        from .style import PRESETS
        spec = yaml.safe_load(open(PRESETS, encoding="utf-8"))["railings"]["vertical_balusters"]
        first_east = st.get("first", "east") == "east"
        a, b = (x0 + fw, x1) if first_east else (x0, x1 - fw)
        railing_run(S, Wall("sr", (a, y0), (b, y0)), 0, b - a, top, "vertical_balusters", spec, height=100)
        # الجهة المفتوحة للشاحط الثاني على موزع الدور العلوي (لين أول جدار)
        xo = x0 if first_east else x1
        ywall = min([min(w.start[1], w.end[1]) for w in project.walls_on(st.get("from", 0) + 1)
                     if abs(w.start[0] - w.end[0]) < 1 and abs(w.start[0] - xo) < 10
                     and max(w.start[1], w.end[1]) > y0] + [y1])
        if ywall - y0 > 30:
            railing_run(S, Wall("sr2", (xo, y0), (xo, ywall)), 0, ywall - y0, top, "vertical_balusters", spec,
                        height=100)
    # دربزين الدرج نفسه: درابزين مائل على الجهة الداخلية للشاحطين + عرض البسطة
    if not cut:
        stair_railing(S, project, st)


def stair_railing(S, project, st, h=90, bal=12):
    lev = project.level(st.get("from", 0))
    top = project.level(st.get("from", 0) + 1) - lev
    steps, landing, r, n = stair_geometry(project, st)
    x0, y0, x1, y1 = st["rect"]
    fw = st.get("flight_w", 90)
    first_east = st.get("first", "east") == "east"
    xa = x1 - fw if first_east else x0 + fw          # الحد الداخلي للشاحط الأول
    xb = x0 + fw if first_east else x1 - fw          # الحد الداخلي للشاحط الثاني
    ly0, lz = landing[1], landing[4]

    def tread_z(x, y):
        for sx0, sy0, sx1, sy1, zt in steps + [landing]:
            if sx0 - 1 <= x <= sx1 + 1 and sy0 - 0.01 <= y <= sy1 + 0.01:
                return zt
        return 0.0 if y < ly0 and abs(x - xa) < abs(x - xb) else top

    S.zoff = lev

    def run(x, ya, za, yb, zb, inset):
        xr = x + inset
        k = (zb - za) / (yb - ya)
        rail = lambda y: za + k * (y - ya) + h
        S.hexa("stair", [(xr - 3, ya, rail(ya)), (xr + 3, ya, rail(ya)), (xr + 3, yb, rail(yb)), (xr - 3, yb, rail(yb)),
                         (xr - 3, ya, rail(ya) + 5), (xr + 3, ya, rail(ya) + 5), (xr + 3, yb, rail(yb) + 5),
                         (xr - 3, yb, rail(yb) + 5)])
        m = max(1, round(abs(yb - ya) / bal))
        for i in range(1, m):
            y = ya + (yb - ya) * i / m
            S.box("stair", xr - 1.8, y - 1.8, tread_z(x + 2 * inset, y), xr + 1.8, y + 1.8, rail(y))
        for y in (ya, yb):     # قوائم رئيسية
            S.box("stair", xr - 4.5, y - 4.5 if y > min(ya, yb) else y, tread_z(x + 2 * inset, y),
                  xr + 4.5, y + 4.5 if y == min(ya, yb) else y, rail(y) + 12)

    sgn = -1 if first_east else 1        # الدربزين فوق الدرجة من جهتها الداخلية
    run(xa, y0, r, ly0, lz, -sgn * 5)
    run(xb, ly0, lz + r, y0 + 27, top, sgn * 5)
    # حافة البسطة المطلة على الفراغ بين الشاحطين
    xl, xh = sorted((xa, xb))
    S.box("stair", xl, ly0 + 1, lz + h, xh, ly0 + 7, lz + h + 5)
    m = max(1, round((xh - xl) / bal))
    for i in range(1, m):
        xx = xl + (xh - xl) * i / m
        S.box("stair", xx - 1.8, ly0 + 2.2, lz, xx + 1.8, ly0 + 5.8, lz + h)
    S.zoff = 0


def gable_transom(H, rise, border, bv):
    """منسوب العارضة الأفقية في زجاج الجملون (45% من ارتفاع الزجاج)."""
    return H + border + (rise - bv - border) * 0.45


def _glass_gable(S, w, L, H, rise, half, tp, border=20, post=10, spacing=110):
    """مثلث جملون زجاج مركّب داخل إطار خشب: حافة سفلية ومائلة 20 سم + قوائم خشب 10 سم."""
    inner, posts, zin, bv, tl = gable_glass_geometry(L, H, rise, tp, border, post, spacing)
    S.wbox("wood", w, -half, L + half, -half, half, H, H + border)
    S.wprism("wood", w, [(-half, H), (L / 2, H + rise), (L / 2, H + rise - bv), (tl, H + border), (tl, H)],
             -half, half)
    S.wprism("wood", w, [(L + half, H), (L - tl, H), (L - tl, H + border), (L / 2, H + rise - bv),
                         (L / 2, H + rise)], -half, half)
    for t in posts:
        S.wbox("wood", w, t - post / 2, t + post / 2, -half, half, H + border, zin(t) + 1)
    S.wprism("glass", w, inner, -1, 1)
    # إطار ألمنيوم أسود حول كل لوح زجاج (مثل الأبواب والشبابيك) — عشان الزجاج يبان مركّب مو فتحة فاضية
    fw_, fd = 5, 4
    zb = H + border
    S.wbox("frame", w, tl, L - tl, -fd, fd, zb, zb + fw_)
    S.wdiag("frame", w, tl, zb, L / 2, H + rise - bv, fw_ * 2, -fd, fd)
    S.wdiag("frame", w, L / 2, H + rise - bv, L - tl, zb, fw_ * 2, -fd, fd)
    for t in posts:
        for a in (t - post / 2 - fw_, t + post / 2):
            S.wbox("frame", w, a, a + fw_, -fd, fd, zb, zin(a + fw_ / 2))
    # تقسيم أفقي للزجاج (عارضة خشب بإطار أسود) — يعطي الواجهة العلوية حركة ويصغّر الألواح للتركيب
    zh = gable_transom(H, rise, border, bv)
    ta = (zh - H + bv) / tp
    if L - 2 * ta > 60:
        S.wbox("wood", w, ta, L - ta, -half, half, zh - post / 2, zh + post / 2)
        S.wbox("frame", w, ta, L - ta, -fd, fd, zh - post / 2 - fw_, zh + post / 2 + fw_)
    # كنار خارجي حول الزجاج (خط التركيب)
    S.wbox("trim", w, tl, L - tl, -half - 2.5, -half, H + border - 5, H + border)


# ---------------------------------------------------------------- الدكة والدربزين
def _deck(S, d, style, bx0, by0, bx1, by1, sh=20):
    x0, y0, x1, y1 = d.rect
    upper = d.level > 0
    top = d.level if upper else d.height - sh
    S.box("wood", x0, y0, (top - 25) if upper else -sh, x1, y1, top)
    spec_name = d.railing_style or style["railing"]
    import yaml
    from .style import PRESETS
    lib = yaml.safe_load(open(PRESETS, encoding="utf-8"))["railings"]
    spec = lib[spec_name]
    edges = {"S": ((x0, y0), (x1, y0)), "E": ((x1, y0), (x1, y1)),
             "N": ((x1, y1), (x0, y1)), "W": ((x0, y1), (x0, y0))}
    for side in d.railing:
        p0, p1 = edges[side]
        w = Wall("rail", p0, p1)
        L = w.length
        gaps = []
        if d.stairs and d.stairs.get("side") == side:
            gaps = [(d.stairs["offset"], d.stairs["offset"] + d.stairs["width"])]
        for a, b in _segments(0, L, gaps):
            railing_run(S, w, a, b, top, spec_name, spec, height=105 if upper else None)
    if d.stairs and d.height > 25 and not upper:
        p0, p1 = edges[d.stairs["side"]]
        w = Wall("st", p0, p1)
        n = math.ceil(d.height / 18)
        rise = d.height / n
        a, b = d.stairs["offset"], d.stairs["offset"] + d.stairs["width"]
        for k in range(1, n):
            S.wbox("wood", w, a, b, -30 * (n - k), 0, -sh, -sh + rise * k)


def _clip_line(t0, z0, dt, dz, ta, tb, za, zb):
    """قص خط بارامتري على مستطيل (Liang-Barsky)."""
    lo, hi = -1e9, 1e9
    for p_, q_ in ((-dt, t0 - ta), (dt, tb - t0), (-dz, z0 - za), (dz, zb - z0)):
        if abs(p_) < 1e-12:
            if q_ < 0:
                return None
            continue
        r = q_ / p_
        if p_ < 0:
            lo = max(lo, r)
        else:
            hi = min(hi, r)
    if lo > hi:
        return None
    return (t0 + dt * lo, z0 + dz * lo, t0 + dt * hi, z0 + dz * hi)


def railing_run(S, w, a, b, z0, name, spec, height=None):
    H = height or spec["height"]
    ps = spec["post"]
    L = b - a
    nb = max(1, math.ceil(L / spec["post_spacing"]))
    posts = [a + (L - ps) * i / nb for i in range(nb + 1)]
    for t in posts:
        S.wbox("trim", w, t, t + ps, -ps / 2, ps / 2, z0, z0 + H + 5)
    bays = [(pa + ps, pb) for pa, pb in zip(posts, posts[1:])]
    if name == "three_rail":
        r = spec["rail"]
        n = spec["rails"]
        for k in range(n):
            zz = z0 + H - r["w"] - k * (H - 25) / (n - 1)
            S.wbox("wood", w, a, b, -r["h"] / 2, r["h"] / 2, zz, zz + r["w"])
        return
    if name == "horizontal_slats":
        sl = spec["slat"]
        zz = z0 + H - sl["w"]
        while zz > z0 + 5:
            S.wbox("wood", w, a, b, -ps / 2 - sl["t"], -ps / 2, zz, zz + sl["w"])
            zz -= sl["w"] + sl["gap"]
        S.wbox("wood", w, a, b, -ps / 2 - 3, ps / 2, z0 + H, z0 + H + 4)
        return
    tr_, br = spec["top_rail"], spec["bottom_rail"]
    S.wbox("wood", w, a, b, -tr_["w"] / 2, tr_["w"] / 2, z0 + H - tr_["h"], z0 + H)
    zb0 = z0 + br["gap"]
    S.wbox("wood", w, a, b, -br["w"] / 2, br["w"] / 2, zb0, zb0 + br["h"])
    za, zt = zb0 + br["h"], z0 + H - tr_["h"]
    for ia, ib in bays:
        if name == "vertical_balusters":
            bw, clr = spec["baluster"]["w"], spec["baluster"]["clear"]
            n = max(0, math.ceil((ib - ia - clr) / (bw + clr)))
            gap = (ib - ia - n * bw) / (n + 1)
            for k in range(n):
                t = ia + gap + k * (bw + gap)
                S.wbox("wood", w, t, t + bw, -bw / 2, bw / 2, za, zt)
        elif name == "wide_boards":
            bd = spec["board"]
            n = max(1, round((ib - ia + bd["gap"]) / (bd["w"] + bd["gap"])))
            wd = (ib - ia - (n - 1) * bd["gap"]) / n
            for k in range(n):
                t = ia + k * (wd + bd["gap"])
                S.wbox("wood", w, t, t + wd, -bd["t"] / 2, bd["t"] / 2, za, zt)
        elif name == "glass_panel":
            S.wbox("glass", w, ia + 2, ib - 2, -0.6, 0.6, za + 2, zt - 2)
        elif name == "x_cross":
            dg = spec["diagonal"]
            S.wdiag("wood", w, ia, za, ib, zt, dg["w"], -dg["t"] / 2, dg["t"] / 2)
            S.wdiag("wood", w, ia, zt, ib, za, dg["w"], -dg["t"] / 2 - dg["t"], -dg["t"] / 2)
        elif name == "zigzag":
            dg = spec["diagonal"]
            zm = (za + zt) / 2
            S.wbox("wood", w, ia, ib, -br["w"] / 2, br["w"] / 2, zm - 2.5, zm + 2.5)
            k = bays.index((ia, ib)) % 2
            S.wdiag("wood", w, ia, za if k else zm, ib, zm if k else za, dg["w"], -dg["t"] / 2, dg["t"] / 2)
            S.wdiag("wood", w, ia, zm if k else zt, ib, zt if k else zm, dg["w"], -dg["t"] / 2, dg["t"] / 2)
        elif name == "lattice":
            dg = spec["diagonal"]
            sp = dg["spacing"]
            span = (ib - ia) + (zt - za)
            c = -span
            while c < span * 2:
                for sgn, s0 in ((1, -dg["t"]), (-1, 0)):
                    seg = _clip_line(ia + c, za, sgn * span * 3, span * 3, ia, ib, za, zt) if sgn > 0 else \
                        _clip_line(ia + c, za, -span * 3, span * 3, ia, ib, za, zt)
                    if seg and math.hypot(seg[2] - seg[0], seg[3] - seg[1]) > 3:
                        S.wdiag("wood", w, *seg, dg["w"], s0, s0 + dg["t"])
                c += sp


# ---------------------------------------------------------------- معاينة
def _subdivide(P, maxlen, strip):
    """يقسم الوجه الرباعي لقطع صغيرة (لترتيب الرسم الصحيح) وشرائح أفقية للتلبيس."""
    if len(P) != 4:        # مضلع محدب → مثلثات كرباعيات منكمشة ثم تقسيم
        out = []
        for i in range(1, len(P) - 1):
            out += _subdivide(np.array([P[0], P[i], P[i + 1], P[i + 1]]), maxlen, strip)
        return out
    e1, e2 = P[1] - P[0], P[3] - P[0]
    vertical = abs(np.cross(e1, e2)[2]) < 1e-6 * np.linalg.norm(np.cross(e1, e2)) + 1e-9
    nu = max(1, math.ceil(np.linalg.norm(e1) / maxlen))
    step = strip if (vertical and strip) else maxlen
    nv = max(1, math.ceil(np.linalg.norm(e2) / step))
    out = []
    for i in range(nu):
        for j in range(nv):
            def at(u, v):
                return (P[0] * (1 - u) * (1 - v) + P[1] * u * (1 - v) + P[2] * u * v + P[3] * (1 - u) * v)
            u0, u1, v0, v1 = i / nu, (i + 1) / nu, j / nv, (j + 1) / nv
            out.append((np.array([at(u0, v0), at(u1, v0), at(u1, v1), at(u0, v1)]), j))
    return out


def render_preview(scene, path, views=((20, -55), (20, 125)), size=(16, 7), strip=18.67,
                   hidden=("rafters", "wood_in", "sheathing"), zoom=1.0, tight=False, dpi=130):
    """معاينة منظور بالراسم البرمجي (z-buffer)."""
    from .raster import render
    render(scene, path, views, int(size[0] * dpi), int(size[1] * dpi), hidden, strip, tight, zoom)


def railing_catalog(out_dir, style):
    """صورة لكل نوع دربزين — ترجع [(مسار الصورة, الاسم العربي)]."""
    import yaml
    from .style import PRESETS
    lib = yaml.safe_load(open(PRESETS, encoding="utf-8"))["railings"]
    res = []
    for n in ("vertical_balusters", "three_rail", "x_cross"):
        S = Scene()
        S.material("wood", style["wood"])
        S.material("trim", style["trim"])
        S.material("slab", style["slab"])
        S.box("slab", -20, -30, -8, 340, 30, 0)
        railing_run(S, Wall("r", (0, 0), (320, 0)), 0, 320, 0, n, lib[n])
        path = out_dir / f"_railing_{n}.png"
        render_preview(S, path, views=((12, -70),), size=(5, 3), hidden=(), zoom=1.05, tight=True)
        res.append((path, lib[n]["ar"]))
    return res
