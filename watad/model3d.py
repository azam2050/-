"""نموذج 3D كامل للكوخ بالمواد والألوان — OBJ+MTL (3ds Max) و GLB.

المحاور: x,y المسقط، z للأعلى، z=0 وجه الصبة، الأرض الطبيعية z=-20. الوحدة سم في OBJ، متر في GLB.
"""
import math

import numpy as np

from .model import Wall, outer_bbox, wall_thickness
from .roof import cross_ext_planes, cross_gables, cross_planes, rafter_positions, roof_geometry


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
    S.material("hardware", "#1E1E1E")          # مقابض ومفصلات معدن
    S.material("door_in", style["wood"])       # ضلفة الباب الداخلي (نفس خشب الجدار — تنعبر بالجولة)
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
        if w.glass_front and not cut and w.exterior and w.floor == top:
            shown = []
            cuts = [(t_lo, t_hi)]
        else:
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
        if not w.exterior and w.floor == top and not cut and project.roof.type in ("gable",) and \
                project.roof.ridge_axis in ("x", "y"):
            # جدار داخلي بالدور الأخير يكمل لين بطن السقف المائل (الغرفة مقفلة بالكامل — ملاحظة المصنع)
            from .features import roof_z
            ts = [0.0, L]
            tc_ = None
            px0, py0 = w.point(0, 0)
            px1, py1 = w.point(L, 0)
            rc = (y0 + y1) / 2 if project.roof.ridge_axis == "x" else (x0 + x1) / 2
            c0, c1 = (py0, py1) if project.roof.ridge_axis == "x" else (px0, px1)
            if (c0 - rc) * (c1 - rc) < 0:
                tc_ = L * (rc - c0) / (c1 - c0)
                ts = [0.0, tc_, L]
            zs = [roof_z(project, rules, *w.point(t_, 0)) - lev - 4 for t_ in ts]
            if max(zs) > H + 5:
                poly = [(0, H), (L, H)] + [(t_, max(z_, H)) for t_, z_ in reversed(list(zip(ts, zs)))]
                S.wprism(wm, w, poly, -half, half)
        ux, uy = w.u
        gable_end = w.exterior and w.floor == top and ((abs(uy) < 1e-6) == ridge_y) and \
            project.roof.type not in ("peaks", "tent_hip")
        if cut:
            pass
        elif gable_end and project.roof.type == "shed":       # حشوة الجدار الجانبي تحت الميل
            from .roof import shed_z
            za, zb_ = (shed_z(project, rules, *w.point(t, 0)) - lev for t in (-half, L + half))
            poly = [(-half, H), (L + half, H)] + ([(L + half, zb_)] if zb_ > H + 1 else []) + \
                   ([(-half, za)] if za > H + 1 else [])
            if len(poly) >= 3:
                S.wprism("wood", w, poly, -half, half)
        elif gable_end and w.glass_front:
            _glass_front(S, w, L, H, rise, half)
        elif gable_end and w.gable_glass:
            _glass_gable(S, w, L, H, rise, half, math.tan(p))
        elif gable_end and w.gable_openings:
            _gable_with_openings(S, w, L, H, rise, half, style)
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
        holes = [st["rect"] for st in project.stairs if st.get("from", 0) == f - 1] + \
            [v["rect"] for v in project.voids if v.get("floor", 1) == f]
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
    for v in project.voids:          # دربزين حول فراغ الدور العلوي (ارتفاع 100)
        lev = project.level(v.get("floor", 1))
        if cut and cut <= lev:
            continue
        vx0, vy0, vx1, vy1 = v["rect"]
        sides = v.get("railing", ["S", "E", "W", "N"])
        segs = {"S": (vx0, vy0, vx1, vy0), "N": (vx0, vy1, vx1, vy1), "W": (vx0, vy0, vx0, vy1), "E": (vx1, vy0, vx1, vy1)}
        for sd in sides:
            a0, b0, a1, b1 = segs[sd]
            S.box("trim", min(a0, a1) - 3, min(b0, b1) - 3, lev + 95, max(a0, a1) + 3, max(b0, b1) + 3, lev + 100)
            n = max(2, int(max(abs(a1 - a0), abs(b1 - b0)) / 12))
            for k in range(n + 1):
                px, py = a0 + (a1 - a0) * k / n, b0 + (b1 - b0) * k / n
                S.box("trim", px - 1.5, py - 1.5, lev, px + 1.5, py + 1.5, lev + 95)
    for st in project.stairs:
        add_stair(S, project, st, cut)
    if furniture:      # "floors" = أرضيات فقط (الفرش الحقيقي يضيفه Blender)
        add_interior(S, project, style, cut, pieces=furniture != "floors")

    if not cut:
        # السقف: مدادات + تطبيق خشب + قرميد
        H = project.roof_base
        from .model import roof_bbox
        x0, y0, x1, y1 = roof_bbox(project, rules)     # السقف فوق الدور الأخير (الباقي سطح)
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
        shed = project.roof.type == "shed"
        peaks = project.roof.type in ("peaks", "tent_hip")
        gable_sides = [] if shed or peaks else [(-1, a_lo - ov), (1, a_hi + ov)]
        if project.roof.type == "peaks":
            _peaks_3d(S, project, rafter_d)
        elif peaks:
            from .tent_roof import add_3d as _tent_3d
            _tent_3d(S, project, rafter_d)
        if shed:            # سقف مائل باتجاه واحد: لوح واحد من الحافة العالية للواطية
            hi_lo = project.roof.high_side in ("S", "W")
            a_low = a_hi if hi_lo else a_lo
            zsh = lambda a: H + ((a_low - a) if hi_lo else (a - a_low)) * tp  # noqa: E731
            e_lo, e_hi = a_lo - ov, a_hi + ov

            def sh_hexa(mat, bb0, bb1, z_off0, z_off1, aa=e_lo, ab=e_hi):
                pts = []
                for zo in (z_off0, z_off1):
                    for a, b in ((aa, bb0), (ab, bb0), (ab, bb1), (aa, bb1)):
                        pts.append((*to_xy(a, b), zsh(a) + zo * kv))
                S.hexa(mat, pts)
            sh_hexa("sheathing", B0, B1, rafter_d, rafter_d + 2.5)
            sh_hexa("roof_tiles", B0, B1, rafter_d + 2.5, rafter_d + 6.5)
            for pos in rafter_positions(project, rules):
                sh_hexa("rafters", max(pos - rafter_t / 2, B0), min(pos + rafter_t / 2, B1), 0, rafter_d)
            if project.roof.soffit:                      # تلبيس أملس تحت المدادات (مثل الصورة: سقف خشب نظيف بسبوتات)
                sh_hexa("ceiling", B0, B1, -2.0, 0.0)
            for eave in (e_lo, e_hi):                    # لوح واجهة المداد على الحافتين
                fa, fb = sorted((eave, eave + (-1 if eave == e_lo else 1) * tr["fascia"]["t"]))
                ztop = zsh(eave) + (rafter_d + 6.5) * kv
                c0, c1 = to_xy(fa, B0), to_xy(fb, B1)
                S.box("trim", min(c0[0], c1[0]), min(c0[1], c1[1]), ztop - tr["fascia"]["h"] - 6.5,
                      max(c0[0], c1[0]), max(c0[1], c1[1]), ztop)
            bb = tr["barge_board"]
            for bpos in (B0 - bb["t"], B1):
                sh_hexa("trim", bpos, bpos + bb["t"], rafter_d + 6.5 - bb["h"], rafter_d + 6.5)

        def slope_hexa(mat, side, aa, ab, bb0, bb1, z_off0, z_off1):
            pts = []
            for zo in (z_off0, z_off1):
                for a, b in ((aa, bb0), (ab, bb0), (ab, bb1), (aa, bb1)):
                    pts.append((*to_xy(a, b), zb(a, side) + zo * kv))
            S.hexa(mat, pts)

        from .roof import cross_gables as _cgs
        for side, eave in gable_sides:
            aa, ab = (eave, ac) if side < 0 else (ac, eave)
            # الرفرف الرئيسي ينقطع خلف المثلث البارز (واجهة المثلث تنزل بدون شريط رفرف قدامها — مثل الشاليه)
            wall_a = a_lo if side < 0 else a_hi
            cuts = sorted((g["c"] - g["hw"], g["c"] + g["hw"]) for g in _cgs(project, rules)
                          if abs(g["wall"] - wall_a) < 1)
            spans, b_at = [], B0
            for c0, c1 in cuts:
                if c0 > b_at:
                    spans.append((b_at, c0, aa, ab))
                spans.append((c0, c1) + ((wall_a, ab) if side < 0 else (aa, wall_a)))
                b_at = c1
            spans.append((b_at, B1, aa, ab))
            for s0, s1, sa, sb in spans:
                slope_hexa("sheathing", side, sa, sb, s0, s1, rafter_d, rafter_d + 2.5)     # تطبيق
                slope_hexa("roof_tiles", side, sa, sb, s0, s1, rafter_d + 2.5, rafter_d + 6.5)
            for pos in rafter_positions(project, rules):
                b0 = max(pos - rafter_t / 2, B0)
                b1 = min(pos + rafter_t / 2, B1)
                sa, sb = next(((sa, sb) for s0, s1, sa, sb in spans if s0 <= pos <= s1), (aa, ab))
                slope_hexa("rafters", side, sa, sb, b0, b1, 0, rafter_d)
            if not style["exposed_rafter_tails"]:     # لوح واجهة المداد
                fa, fb = sorted((eave, eave + side * tr["fascia"]["t"]))
                ztop = zb(eave, side) + (rafter_d + 6.5) * kv
                zbot = ztop - tr["fascia"]["h"] - 6.5
                c0, c1 = to_xy(fa, B0), to_xy(fb, B1)
                S.box("trim", min(c0[0], c1[0]), min(c0[1], c1[1]), zbot,
                      max(c0[0], c1[0]), max(c0[1], c1[1]), ztop)
        # جسور حاملة طولية (شاليه) تحت المدادات — أطرافها بارزة تحت الرفرف مثل الصورة
        from .roof import purlin_positions
        pw, ph = project.roof.purlin["w"], project.roof.purlin["h"]
        for a in purlin_positions(project, rules):
            ztop = zsh(a) if shed else zb(a, -1 if a <= ac else 1)
            c0, c1 = to_xy(a - pw / 2, B0 - 10), to_xy(a + pw / 2, B1 + 10)
            S.box("trim", min(c0[0], c1[0]), min(c0[1], c1[1]), ztop - ph,
                  max(c0[0], c1[0]), max(c0[1], c1[1]), ztop)
        # ألواح حافة الجملون (barge boards)
        bb = tr["barge_board"]
        for bpos in (B0 - bb["t"], B1):
            for side, eave in gable_sides:
                aa, ab = (eave, ac) if side < 0 else (ac, eave)
                slope_hexa("trim", side, aa, ab, bpos, bpos + bb["t"], rafter_d + 6.5 - bb["h"], rafter_d + 6.5)

    x0, y0, x1, y1 = outer_bbox(project, rules)        # رجوع لحدود المبنى كامل (بعد السقف)
    if not cut:
        _cross_gables(S, project, rules, half)
    for d in project.decks:
        if cut and d.level > 0 and d.level > cut:
            continue
        _deck(S, d, style, x0, y0, x1, y1, sh)
    from .features import add_3d          # شباك بارز / مظلة مدخل / برجولات
    add_3d(S, project, rules, style, cut)
    from .features import add_mezz_3d    # ميزانين + درج مستقيم
    add_mezz_3d(S, project, rules, style, cut)
    from .features import add_bumps_3d
    add_bumps_3d(S, project, rules, style, cut)
    from .site import add_site_3d       # السور والمسبح والجلسات
    add_site_3d(S, project, rules, style, cut)
    # أعمدة الجلسة المسقوفة + جسر أمامي يحمل طرف الجملون
    pz = []
    for pt in project.posts:
        px, py = pt["at"]
        if pt.get("kind") == "block":    # كتلة مصمتة (كبت/درج تحت عمود المكتبة)
            w, d, h, z0 = pt.get("w", 50), pt.get("d", 30), pt.get("h", 45), pt.get("z", 0)
            if pt.get("axis", "y") == "y":
                S.box("trim", px - d / 2, py - w / 2, z0, px + d / 2, py + w / 2, z0 + h)
            else:
                S.box("trim", px - w / 2, py - d / 2, z0, px + w / 2, py + d / 2, z0 + h)
            continue
        if pt.get("kind") == "box":      # صندوق مربع مفتوح بين أعمدة البارتشن (للفازات) — قاعدة وغطاء وجنبين
            w, d, h, z0, t = pt.get("w", 60), pt.get("d", 24), pt.get("h", 40), pt.get("z", 100), pt.get("t", 3)
            ax_y = pt.get("axis", "y") == "y"          # الصندوق ممتد على اتجاه البارتشن
            hw, hd = w / 2, d / 2
            if cut and z0 > cut:
                continue

            def bx(a0, a1, b0, b1, z_0, z_1):
                if ax_y:
                    S.box("trim", px - hd + b0, py + a0, z_0, px - hd + b1, py + a1, z_1)
                else:
                    S.box("trim", px + a0, py - hd + b0, z_0, px + a1, py - hd + b1, z_1)
            bx(-hw, hw, 0, d, z0, z0 + t)                    # القاعدة
            bx(-hw, hw, 0, d, z0 + h - t, z0 + h)            # الغطاء
            bx(-hw, -hw + t, 0, d, z0 + t, z0 + h - t)       # جنب (بين القاعدة والغطاء — بدون تداخل)
            bx(hw - t, hw, 0, d, z0 + t, z0 + h - t)         # جنب
            continue
        if cut:
            ztop = cut
        else:
            a = px if ridge_y else py
            ztop = zsh(a) if project.roof.type == "shed" else zb(a, -1 if a <= ac else 1)
        if "top" in pt:              # عمود يحمل برندة/بلكونة (ينتهي تحت أرضيتها)
            ztop = pt["top"] if not cut else min(cut, pt["top"])
        ps = pt.get("size", 15)
        S.box("trim", px - ps / 2, py - ps / 2, pt.get("base", 0), px + ps / 2, py + ps / 2, ztop)
        if not pt.get("inner"):          # أعمدة داخلية (بارتشن أعمدة) ما تدخل بحساب جسر الواجهة
            pz.append((px, py, ztop))
    if len(pz) >= 2 and project.roof.ext_start and not cut:
        b_edge = sum((py if ridge_y else px) for px, py, _ in pz) / len(pz)
        a0, a1 = a_lo, a_hi
        c0, c1 = to_xy(a0, b_edge - 8), to_xy(a1, b_edge + 8)
        S.box("trim", min(c0[0], c1[0]), min(c0[1], c1[1]), H - 22, max(c0[0], c1[0]), max(c0[1], c1[1]), H)
    return S


def _beam(S, mat, p, q, w):
    """جسر خشب مربع المقطع بين نقطتين (للأضلاع المائلة)."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    pts = []
    for dz in (-w / 2, w / 2):
        for (a, sgn) in ((p, -1), (q, -1), (q, 1), (p, 1)):
            pts.append((a[0] + sgn * nx, a[1] + sgn * ny, a[2] + dz))
    S.hexa(mat, pts)


def _peaks_3d(S, project, rd):
    """سقف بيت الشعر الخشبي: قمم هرمية متجاورة (وديان بينها) + أضلاع خشب ظاهرة + مشراق زجاج فوق القمة."""
    from .roof import peak_geometry
    tri_faces = [(0, 1, 2), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
    quad_faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    for pk in project.roof.peaks:
        G = peak_geometry(project, pk)
        E, A, T = G["E"], G["A"], G.get("T")
        for i in range(4):
            e0, e1 = E[i], E[(i + 1) % 4]
            for mat, z0, z1 in (("sheathing", 0, rd + 2.5), ("roof_tiles", rd + 2.5, rd + 6.5)):
                if T:
                    t0, t1 = T[i], T[(i + 1) % 4]
                    base = [e0, e1, t1, t0]
                    S.poly(mat, [(x, y, z + z0) for x, y, z in base] + [(x, y, z + z1) for x, y, z in base], quad_faces)
                else:
                    base = [e0, e1, A]
                    S.poly(mat, [(x, y, z + z0) for x, y, z in base] + [(x, y, z + z1) for x, y, z in base], tri_faces)
            top = T[i] if T else A
            lift = rd + 10                              # ضلع ركني خشب فوق السطح ظاهر (مثل حبال/أعمدة الخيمة)
            _beam(S, "trim", (e0[0], e0[1], e0[2] + lift), (top[0], top[1], top[2] + lift), 16)
            fa = (e0[0], e0[1], e0[2] + rd / 2)
            fb = (e1[0], e1[1], e1[2] + rd / 2)
            _beam(S, "trim", fa, fb, 14)                # لوح الرفرف
        if T:                                            # المشراق: صندوق زجاج + غطاء هرمي صغير
            zt = G["zt"]
            xs, ys = [t[0] for t in T], [t[1] for t in T]
            lx0, lx1, ly0, ly1 = min(xs), max(xs), min(ys), max(ys)
            S.box("glass", lx0 + 4, ly0 + 4, zt + rd, lx1 - 4, ly1 - 4, zt + rd + 60)
            for cx_, cy_ in ((lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1)):
                S.box("trim", cx_ - 5, cy_ - 5, zt + rd, cx_ + 5, cy_ + 5, zt + rd + 60)
            zc = zt + rd + 60
            cap = [(lx0 - 20, ly0 - 20, zc), (lx1 + 20, ly0 - 20, zc), (lx1 + 20, ly1 + 20, zc), (lx0 - 20, ly1 + 20, zc)]
            apex = ((lx0 + lx1) / 2, (ly0 + ly1) / 2, zc + 45)
            for i in range(4):
                base = [cap[i], cap[(i + 1) % 4], apex]
                S.poly("roof_tiles", base + [(x, y, z + 6) for x, y, z in base], tri_faces)


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
        qf = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        for q in cross_ext_planes(g):       # امتداد المثلث للأمام فوق البلكونة (مثل الشاليه)
            S.poly("sheathing", list(q) + [(x, y, z + (rd + 2.5) * kv) for x, y, z in q], qf)
            S.poly("roof_tiles", [(x, y, z + (rd + 2.5) * kv) for x, y, z in q]
                   + [(x, y, z + (rd + 6.5) * kv) for x, y, z in q], qf)
        wall, sg, c, hw, H, zr = g["wall"], g["sg"], g["c"], g["hw"], g["H"], g["zr"]
        ax_y = g["axis"] == "y"
        if g.get("ext"):                    # جملون أمامي مفتوح: جسر أفقي + عمود قمة + لوحين حافة
            P0 = (lambda a, b, z: (a, b, z)) if ax_y else (lambda a, b, z: (b, a, z))
            yf = wall + sg * (g["ov"] + g["ext"] - 12)
            a0, a1 = P0(yf - 9, c - hw - 10, 0), P0(yf + 9, c + hw + 10, 0)
            S.box("trim", min(a0[0], a1[0]), min(a0[1], a1[1]), H - 22, max(a0[0], a1[0]), max(a0[1], a1[1]), H)
            a0, a1 = P0(yf - 8, c - 8, 0), P0(yf + 8, c + 8, 0)
            S.box("trim", min(a0[0], a1[0]), min(a0[1], a1[1]), H, max(a0[0], a1[0]), max(a0[1], a1[1]), zr - 8)
            yr = wall + sg * (g["ov"] + g["ext"] - 4)
            for s_ in (-1, 1):
                _beam(S, "trim", P0(yr, c + s_ * (hw + g["ov"]), g["ze"] - 6), P0(yr, c, zr - 6), 14)
                _beam(S, "trim", P0(yf, c, H + 40), P0(yf, c + s_ * hw * 0.55, zr - hw * 0.55 * g["t"] - 14), 12)
        P = (lambda a, b, z: (a, b, z)) if ax_y else (lambda a, b, z: (b, a, z))
        tri = [P(wall, c - hw, H), P(wall, c, zr), P(wall, c + hw, H)]
        inner = [P(wall - sg * 2 * half, c - hw, H), P(wall - sg * 2 * half, c, zr), P(wall - sg * 2 * half, c + hw, H)]
        cg = project.roof.cross_gables[g["i"]]
        tface = [(0, 1, 2), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
        if cg.get("glass"):         # مثلث زجاج كامل بقواطع خشب (شاليه)
            gl = [P(wall - sg * 1, c - hw, H), P(wall - sg * 1, c, zr), P(wall - sg * 1, c + hw, H)]
            gi = [P(wall - sg * 3, c - hw, H), P(wall - sg * 3, c, zr), P(wall - sg * 3, c + hw, H)]
            S.poly("glass", gl + gi, tface)
            n_m = max(2, round(2 * hw / 110))
            for k in range(1, n_m):
                d_ = -hw + 2 * hw * k / n_m
                zt_ = zr - abs(d_) * g["t"]
                a0, a1 = P(wall + sg * 4, c + d_ - 3, 0), P(wall - sg * 6, c + d_ + 3, 0)
                S.box("frame", min(a0[0], a1[0]), min(a0[1], a1[1]), H, max(a0[0], a1[0]), max(a0[1], a1[1]), zt_)
            zt_ = H + (zr - H) * 0.45
            dxt = (zr - zt_) / g["t"]
            a0, a1 = P(wall + sg * 4, c - dxt, 0), P(wall - sg * 6, c + dxt, 0)
            S.box("frame", min(a0[0], a1[0]), min(a0[1], a1[1]), zt_ - 3, max(a0[0], a1[0]), max(a0[1], a1[1]), zt_ + 3)
        else:
            S.poly("wood", tri + inner, tface)
        nb = cg.get("beams", 0)     # جسور حاملة بارزة (شاليه): جسر القمة + nb بكل جهة، أطرافها برا الرفرف بكوابيل
        for k in range(-nb, nb + 1) if nb else ():
            d_ = k * hw / (nb + 1)
            ztop = zr - abs(d_) * g["t"]
            a0, a1 = P(wall - sg * g["reach"] * 0.5, c + d_ - 10, 0), P(wall + sg * (g["ov"] + 20), c + d_ + 10, 0)
            S.box("trim", min(a0[0], a1[0]), min(a0[1], a1[1]), ztop - 30, max(a0[0], a1[0]), max(a0[1], a1[1]), ztop)
            b0, b1 = P(wall, c + d_ - 8, 0), P(wall + sg * 90, c + d_ + 8, 0)      # كابول تحت طرف الجسر
            zb0 = ztop - 30
            S.hexa("trim", [(b0[0], b0[1], zb0 - 70), (b1[0], b0[1], zb0), (b1[0], b1[1], zb0), (b0[0], b1[1], zb0 - 70),
                            (b0[0], b0[1], zb0 - 55), (b1[0], b0[1], zb0 + 1), (b1[0], b1[1], zb0 + 1), (b0[0], b1[1], zb0 - 55)]
                   if ax_y else
                   [(b0[0], b0[1], zb0 - 70), (b0[0], b1[1], zb0), (b1[0], b1[1], zb0), (b1[0], b0[1], zb0 - 70),
                    (b0[0], b0[1], zb0 - 55), (b0[0], b1[1], zb0 + 1), (b1[0], b1[1], zb0 + 1), (b1[0], b0[1], zb0 - 55)])
        ww = 0 if cg.get("glass") else cg.get("window_width", 110)
        wz0 = H + 15
        wz1 = min(H + cg.get("window_height", 140), zr - (ww / 2) * g["t"] - 25)
        if wz1 - wz0 > 40 and ww > 0:
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


def _casing(S, w, a, b, z0, z1, s0, s1, cw=7, sill=True):
    """حلق/برواز خشب حول الفتحة على وجه الجدار (s0..s1 = سماكته برا الوجه)."""
    S.wbox("trim", w, a - cw, a, s0, s1, z0 - (cw if sill else 0), z1 + cw)
    S.wbox("trim", w, b, b + cw, s0, s1, z0 - (cw if sill else 0), z1 + cw)
    S.wbox("trim", w, a, b, s0, s1, z1, z1 + cw)              # الأفقي بين القائمين (بدون تداخل = بدون بقع سوداء)
    if sill:
        S.wbox("trim", w, a, b, s0, s1, z0 - cw, z0)


def _handle(S, w, t, z, s_face, sg, lever=True):
    """مقبض باب: صفيحة + ذراع (lever) بارز عن وجه الضلفة. sg = اتجاه الوجه (+1 للداخل، -1 للخارج)."""
    s0, s1 = sorted((s_face, s_face + sg * 1.0))
    S.wbox("hardware", w, t - 2.2, t + 2.2, s0, s1, z - 9, z + 9)               # الصفيحة
    s2, s3 = sorted((s_face + sg * 1.0, s_face + sg * 5.0))
    S.wbox("hardware", w, t - 0.9, t + 0.9, s2, s3, z - 0.9, z + 0.9)          # الرقبة
    if lever:
        e0, e1 = sorted((s_face + sg * 5.0, s_face + sg * 6.6))
        S.wbox("hardware", w, t - 12 if t > 0 else t, t + 0.9, e0, e1, z - 1.0, z + 1.0)   # الذراع


def _opening(S, w, o, a, b, z0, z1, half, style, exterior):
    """فتحات واقعية (ملاحظة المصنع): حلق بعمق الجدار + ضلف (sash) لكل لوح + زجاج رقيق + عتبة خارجية بارزة
    + برواز خشب داخلي، والأبواب بحشوات بارزة ومقابض ومفصلات وبرواز من الجهتين."""
    out = -half
    fw = 6
    if o.kind == "window":
        for (ta, tb, za, zb_) in ((a, a + 4, z0, z1), (b - 4, b, z0, z1), (a + 4, b - 4, z0, z0 + 4), (a + 4, b - 4, z1 - 4, z1)):
            S.wbox("frame", w, ta, tb, out, half, za, zb_)                   # الحلق بعمق الجدار
        grid = style["window_grid"]
        if o.grid:
            cols, rows = o.grid
        else:
            cols = 2 if grid in ("mullion", "grid") and o.width >= 90 else 1
            rows = 2 if grid == "grid" and o.height >= 90 else 1
        fixed = getattr(o, "style", "") == "fixed"
        nsash = 1 if fixed or o.width < 70 else (2 if o.width < 200 else 3)
        sw_ = (b - a - 8) / nsash
        for k in range(nsash):                                                # الضلف: إطار 5 سم + زجاج + تقسيم
            sa, sb = a + 4 + k * sw_, a + 4 + (k + 1) * sw_
            za, zb_ = z0 + 4, z1 - 4
            sf = 5
            for (ta, tb, zz0, zz1) in ((sa, sa + sf, za, zb_), (sb - sf, sb, za, zb_), (sa + sf, sb - sf, za, za + sf),
                                       (sa + sf, sb - sf, zb_ - sf, zb_)):
                S.wbox("frame", w, ta, tb, -2.5, 2.5, zz0, zz1)
            S.wbox("glass", w, sa + sf, sb - sf, -0.6, 0.6, za + sf, zb_ - sf)
            sc = max(1, round(cols / nsash))
            for kk in range(1, sc):                                           # قواطع رفيعة 3 سم بارزة من الجهتين
                t = sa + sf + (sb - sa - 2 * sf) * kk / sc
                S.wbox("frame", w, t - 1.5, t + 1.5, -1.8, 1.8, za + sf, zb_ - sf)
            for kk in range(1, rows):
                z = za + sf + (zb_ - za - 2 * sf) * kk / rows
                S.wbox("frame", w, sa + sf, sb - sf, -1.6, 1.6, z - 1.5, z + 1.5)
            if not fixed and o.width >= 50:                                   # مقبض الضلفة (داخلي)
                hz = (za + zb_) / 2 if zb_ - za < 160 else za + 110
                ht = sb - sf - 2 if k % 2 == 0 else sa + sf + 2
                S.wbox("hardware", w, ht - 1.2, ht + 1.2, 2.5, 4.0, hz - 6, hz + 6)
                S.wbox("hardware", w, ht - 1.0, ht + 1.0, 4.0, 5.2, hz - 1, hz + 9)
        if getattr(o, "transom", 0):
            S.wbox("frame", w, a, b, -3, 3, o.transom - 3, o.transom + 3)
        tr = style["trims"]["window_trim"]
        if exterior:
            for (ta, tb, za, zb_) in ((a - tr["w"], a, z0, z1 + tr["w"]),
                                      (b, b + tr["w"], z0, z1 + tr["w"]),
                                      (a, b, z1, z1 + tr["w"])):
                S.wbox("trim", w, ta, tb, out - tr["t"], out, za, zb_)
            S.wbox("trim", w, a - tr["w"] - 4, b + tr["w"] + 4, out - 6, out, z0 - 6, z0)      # عتبة خارجية بارزة
            _casing(S, w, a, b, z0, z1, half, half + 1.6, 6, sill=False)
            S.wbox("trim", w, a - 8, b + 8, half, half + 4, z0 - 3, z0)                         # جلسة داخلية
        else:
            _casing(S, w, a, b, z0, z1, half, half + 1.6, 6)
            _casing(S, w, a, b, z0, z1, out - 1.6, out, 6)
    else:
        if o.leaves == 0:           # فتحة بدون باب — حلق خشب بعمق الجدار + برواز من الجهتين
            for (ta, tb) in ((a, a + 3), (b - 3, b)):
                S.wbox("trim", w, ta, tb, -half, half, 0, z1)
            S.wbox("trim", w, a + 3, b - 3, -half, half, z1 - 3, z1)
            _casing(S, w, a, b, 0, z1, half, half + 1.6, 7, sill=False)
            _casing(S, w, a, b, 0, z1, out - 1.6, out, 7, sill=False)
            return
        for (ta, tb, za, zb_) in ((a, a + 4, 0, z1), (b - 4, b, 0, z1), (a + 4, b - 4, z1 - 4, z1)):
            S.wbox("frame" if exterior else "trim", w, ta, tb, out, half, za, zb_)
        S.wbox("trim", w, a + 4, b - 4, out, half, 0, 1.2)                      # عتبة
        _casing(S, w, a, b, 0, z1, half, half + 1.6, 7, sill=False)
        if not exterior:
            _casing(S, w, a, b, 0, z1, out - 1.6, out, 7, sill=False)
        if getattr(o, "style", "") in ("sliding", "fixed"):
            n = max(2, round(o.width / 100))
            pw = (b - a - 8) / n
            for k in range(n):                                                  # ضلف سحاب متداخلة (مسارين)
                la, lb = a + 4 + k * pw - (2 if k else 0), a + 4 + (k + 1) * pw + (2 if k < n - 1 else 0)
                s0 = -3.5 if k % 2 == 0 else 0.5
                for (ta, tb, za, zb_) in ((la, la + 6, 1, z1 - 4), (lb - 6, lb, 1, z1 - 4), (la + 6, lb - 6, 1, 9), (la + 6, lb - 6, z1 - 10, z1 - 4)):
                    S.wbox("frame", w, ta, tb, s0, s0 + 3, za, zb_)
                S.wbox("glass", w, la + 6, lb - 6, s0 + 1.2, s0 + 1.8, 9, z1 - 10)
                ht = lb - 9 if k % 2 == 0 else la + 9                           # مقبض سحاب رأسي
                S.wbox("hardware", w, ht - 1, ht + 1, s0 + 3, s0 + 5.5, 85, 125)
            S.wbox("hardware", w, a, b, -4, 4, 0, 1.5)                        # مسار السحاب
        else:
            n = o.leaves
            lw = (o.width - 8) / n
            hinge_left = getattr(o, "swing", "left") == "left"
            for k in range(n):
                la, lb = a + 4 + k * lw, a + 4 + (k + 1) * lw
                if (style["door_style"] == "french" or o.grid) and exterior:
                    S.wbox("glass", w, la + 10, lb - 10, -0.6, 0.6, 22, z1 - 4 - 10)
                    if o.grid:
                        cols, rows = o.grid
                        cols = max(1, round(cols / n))
                        for kk in range(1, cols):
                            t = la + 10 + (lb - la - 20) * kk / cols
                            S.wbox("door", w, t - 1.5, t + 1.5, -2, 2, 22, z1 - 14)
                        for kk in range(1, rows):
                            z = 22 + (z1 - 36) * kk / rows
                            S.wbox("door", w, la + 10, lb - 10, -1.8, 1.8, z - 1.5, z + 1.5)
                    for (ta, tb, za, zb_) in ((la, la + 10, 1, z1 - 4), (lb - 10, lb, 1, z1 - 4),
                                              (la + 10, lb - 10, 1, 12), (la + 10, lb - 10, z1 - 14, z1 - 4)):
                        S.wbox("door", w, ta, tb, -2.5, 2.5, za, zb_)
                    S.wbox("door", w, la + 10, lb - 10, -2.2, 2.2, 12, 22)          # وزرة سفلية مصمتة
                elif not exterior:                                                  # باب داخلي ألواح خشب (مثل منتج المصنع)
                    S.wbox("door_in", w, la, lb, -2, 2, 1, z1 - 4)
                else:                                                               # باب خشب بحشوات بارزة
                    S.wbox("door", w, la, lb, -2, 2, 1, z1 - 4)
                    st, rl = 11, 12
                    zt = z1 - 4
                    for sgn in (-1, 1):                                             # إطار الحشوات بالوجهين
                        f0, f1 = sorted((sgn * 2, sgn * 2.9))
                        for (ta, tb, za, zb_) in ((la, la + st, 1, zt), (lb - st, lb, 1, zt), (la + st, lb - st, zt - rl, zt),
                                                  (la + st, lb - st, 1, 1 + rl * 1.6), (la + st, lb - st, 95, 95 + rl)):
                            S.wbox("door", w, ta, tb, f0, f1, za, zb_)
                        if lb - la > 60:
                            m = (la + lb) / 2
                            for (za, zb_) in ((1 + rl * 1.6, 95), (95 + rl, zt - rl)):
                                S.wbox("door", w, m - st / 2, m + st / 2, f0, f1, za, zb_)
                        g0, g1 = sorted((sgn * 2, sgn * 2.5))                       # بروز الحشوة نفسها
                        for (za, zb_) in ((1 + rl * 1.6 + 4, 95 - 4), (95 + rl + 4, zt - rl - 4)):
                            cols = [(la + st + 4, lb - st - 4)] if lb - la <= 60 else \
                                [(la + st + 4, (la + lb) / 2 - st / 2 - 4), ((la + lb) / 2 + st / 2 + 4, lb - st - 4)]
                            for c0, c1 in cols:
                                S.wbox("door", w, c0, c1, g0, g1, za, zb_)
                hinge = (k == 0 and hinge_left) or (n == 1 and not hinge_left and False)
                ht = lb - 8 if (n == 1 and hinge_left) or (n > 1 and k == 0) else la + 8
                for sg in (-1, 1):                                                 # مقبض من الجهتين
                    _handle(S, w, ht, 100, sg * 3.0, sg)
                del hinge
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


FURN_H = [("جلسة عربية", 45, "fabric"), ("سرير", 55, "linen"), ("دولاب", 220, "furn"), ("كنبة", 80, "fabric"), ("كرسي", 80, "fabric"),
          ("طاولة", 75, "furn"), ("تلفزيون", 110, "dark"), ("كاونتر", 90, "counter"),
          ("ثلاجة", 180, "white")]


def _bath_fixture(S, project, f):
    """قطع الحمام بشكلها الحقيقي: دش بقاعدة وزجاج، كرسي حمام بخزان، مغسلة على خزانة ومرآة."""
    x0, y0, x1, y1 = f.rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    room = next((r.rect for r in project.rooms if r.floor == f.floor
                 and r.rect[0] - 1 <= cx <= r.rect[2] + 1 and r.rect[1] - 1 <= cy <= r.rect[3] + 1), None)
    rx0, ry0, rx1, ry1 = room or (x0, y0, x1, y1)
    touch = {"W": abs(x0 - rx0) < 8, "E": abs(x1 - rx1) < 8, "S": abs(y0 - ry0) < 8, "N": abs(y1 - ry1) < 8}
    d = {"W": x0 - rx0, "E": rx1 - x1, "S": y0 - ry0, "N": ry1 - y1}
    back = min(d, key=d.get)                       # الجدار اللي وراء القطعة
    if f.shape == "shower":
        S.box("white", x0, y0, 1.2, x1, y1, 9)
        for side, open_ in touch.items():          # زجاج على الجهات المفتوحة على الحمام
            if open_:
                continue
            if side in ("W", "E"):
                xx = x0 if side == "W" else x1 - 1
                S.box("glass", xx, y0, 9, xx + 1, y1, 200)
                S.box("frame", xx - 0.5, y0, 198, xx + 1.5, y1, 201)
            else:
                yy = y0 if side == "S" else y1 - 1
                S.box("glass", x0, yy, 9, x1, yy + 1, 200)
                S.box("frame", x0, yy - 0.5, 198, x1, yy + 1.5, 201)
        bx, by = {"W": (x0 + 2, cy), "E": (x1 - 6, cy), "S": (cx, y0 + 2), "N": (cx, y1 - 6)}[back]
        S.box("frame", bx - 6 if back in "SN" else bx, by - 6 if back in "WE" else by, 185,
              bx + 6 if back in "SN" else bx + 4, by + 6 if back in "WE" else by + 4, 200)
        return
    if f.shape == "wc":
        tk = 17
        bowl = {"W": (x0 + tk, y0 + 6, x1, y1 - 6), "E": (x0, y0 + 6, x1 - tk, y1 - 6),
                "S": (x0 + 6, y0 + tk, x1 - 6, y1), "N": (x0 + 6, y0, x1 - 6, y1 - tk)}[back]
        tank = {"W": (x0, y0, x0 + tk, y1), "E": (x1 - tk, y0, x1, y1),
                "S": (x0, y0, x1, y0 + tk), "N": (x0, y1 - tk, x1, y1)}[back]
        S.box("white", bowl[0], bowl[1], 1.2, bowl[2], bowl[3], 40)
        S.box("dark", bowl[0] + 2, bowl[1] + 2, 40, bowl[2] - 2, bowl[3] - 2, 42)
        S.box("white", tank[0], tank[1], 1.2, tank[2], tank[3], 80)
        return
    # مغسلة: خزانة خشب + سطح أبيض + مرآة على الجدار
    S.box("furn", x0 + 2, y0 + 2, 1.2, x1 - 2, y1 - 2, 80)
    S.box("white", x0, y0, 80, x1, y1, 88)
    m = {"W": (x0 - 1, y0, x0, y1), "E": (x1, y0, x1 + 1, y1), "S": (x0, y0 - 1, x1, y0),
         "N": (x0, y1, x1, y1 + 1)}[back]
    S.box("glass", m[0], m[1], 105, m[2], m[3], 175)


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
        if cut and cut <= f.level_in(project):
            continue
        S.zoff = f.level_in(project)
        x0, y0, x1, y1 = f.rect
        if f.shape in ("shower", "wc", "basin"):
            _bath_fixture(S, project, f)
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


def _gable_with_openings(S, w, L, H, rise, half, style):
    """مثلث جملون خشب فيه فتحات (باب/شباك فوق منسوب الجدار) — يتقسم لقطع محدبة حول كل فتحة."""
    from .model import Opening
    k = rise / (L / 2 + half)
    zr = lambda t: H + (min(t, L - t) + half) * k        # noqa: E731  حافة السقف على الجملون
    ops = sorted(w.gable_openings, key=lambda o: o["offset"])
    cuts = [-half]
    for o in ops:
        cuts += [o["offset"], o["offset"] + o["width"]]
    cuts.append(L + half)
    for i in range(0, len(cuts), 2):                      # الشرائح بين الفتحات (من H للسقف)
        a, b = cuts[i], cuts[i + 1]
        if b - a < 0.5:
            continue
        pts = [(a, H), (b, H), (b, zr(b))]
        if a < L / 2 < b:
            pts.append((L / 2, H + rise))
        pts.append((a, zr(a)))
        clean = []
        for pt in pts:                                    # بدون نقاط مكررة (المثلث عند الركن)
            if not clean or math.dist(pt, clean[-1]) > 0.1:
                clean.append(pt)
        if len(clean) > 2 and math.dist(clean[0], clean[-1]) < 0.1:
            clean.pop()
        if len(clean) >= 3:
            S.wprism("wood", w, clean, -half, half)
    for o in ops:                                          # فوق وتحت كل فتحة
        a, b = o["offset"], o["offset"] + o["width"]
        z0, z1 = o.get("sill", 0), o.get("sill", 0) + o["height"]
        if z0 > H + 0.5:
            S.wbox("wood", w, a, b, -half, half, H, z0)
        top = [(a, z1), (b, z1), (b, zr(b))] + ([(L / 2, H + rise)] if a < L / 2 < b else []) + [(a, zr(a))]
        S.wprism("wood", w, top, -half, half)
        op = Opening(kind="window", offset=a, width=o["width"], height=o["height"], sill=z0, code=o.get("code", ""),
                     grid=o.get("grid"))
        _opening(S, w, op, a, b, z0, z1, half, style, exterior=True)


def glass_front_geometry(Lo, H, rise, door, border=15, side=12, sill=10, mull=8, split=False):
    """واجهة A-frame زجاج كاملة (إحداثيات الواجهة الخارجية 0..Lo): إطار خشب + قوائم + عوارض + باب بالوسط.
    door = (بداية، نهاية، ارتفاع) بإحداثيات الواجهة. يرجع dict للرسم (2D) والمجسم (3D)."""
    k = rise / (Lo / 2)
    bv = border * math.sqrt(1 + k * k)
    zin = lambda t: H + min(t, Lo - t) * k - bv      # noqa: E731
    tl, tr = side, Lo - side
    apex = H + rise - bv
    inner = [(tl, sill), (tr, sill), (tr, zin(tr)), (Lo / 2, apex), (tl, zin(tl))]
    da, db, dh = door
    # تبسيط التركيب (طلب المصنع): عارضة وحدة فوق الباب — فوقها مثلث زجاج كامل لوح واحد،
    # وتحتها لوحين زجاج (يمين ويسار) والباب بينهم. القوائم تقف عند العارضة.
    zt1 = dh + mull / 2
    mulls = [da - mull / 2, db + mull / 2]
    ta = max(tl, (zt1 - H + bv) / k)
    trans = [(ta, Lo - ta, zt1)]
    posts = []
    if split:      # تقسيم أصغر للتركيب (طلب المصنع): عارضة ثانية بالمثلث + قائمين لطرفيها + قائم بنص كل لوح سفلي
        apex_ = H + rise - bv
        zt2 = zt1 + (apex_ - zt1) * 0.5
        ta2 = max(tl, (zt2 - H + bv) / k)
        if Lo - 2 * ta2 > 40:
            trans.append((ta2, Lo - ta2, zt2))
            for t in (ta2, Lo - ta2):
                posts.append((t, zt1 + mull / 2, zt2 - mull / 2))
        for a_, b_ in ((tl, da - mull), (db + mull, Lo - tl)):
            if b_ - a_ > 110:
                mulls.append((a_ + b_) / 2)
    return {"outer": [(0, 0), (Lo, 0), (Lo, H), (Lo / 2, H + rise), (0, H)], "inner": inner, "zin": zin,
            "mulls": [(t, min(zin(t), zt1 - mull / 2)) for t in mulls], "trans": trans, "posts": posts, "door": door, "mull": mull, "apex": apex,
            "border": border, "bv": bv, "sill": sill, "tl": tl}


def _glass_front(S, w, L, H, rise, half):
    """واجهة زجاج كاملة من الأرض لقمة الجملون (مثل الـ A-frame): إطار خشب + شبكة قوائم + باب زجاج بالوسط."""
    Lo = L + 2 * half
    d = next((o for o in w.openings if o.kind == "door"), None)
    door = (d.offset + half, d.offset + d.width + half, d.height) if d else (Lo / 2 - 45, Lo / 2 + 45, 210)
    G = glass_front_geometry(Lo, H, rise, door, split=getattr(w, "glass_split", False))
    m, fw_, fd = G["mull"], 4, 4
    for t, z0_, z1_ in G["posts"]:
        S.wbox("wood", w, t - half - m / 2, t - half + m / 2, -half, half, z0_, z1_)
    sh = lambda t: t - half                          # noqa: E731  (إحداثي الواجهة → إحداثي الجدار)
    zin, tl, bv = G["zin"], G["tl"], G["bv"]
    # الإطار: عتبة سفلية + قائمين جانبيين + الحافة المائلة
    S.wbox("wood", w, sh(0), sh(Lo), -half, half, 0, G["sill"])
    for a, b in ((0, tl), (Lo - tl, Lo)):
        S.wbox("wood", w, sh(a), sh(b), -half, half, G["sill"], H)
    S.wprism("wood", w, [(sh(0), H), (sh(Lo / 2), H + rise), (sh(Lo / 2), G["apex"]), (sh(tl), zin(tl)),
                         (sh(tl), H)], -half, half)
    S.wprism("wood", w, [(sh(Lo), H), (sh(Lo - tl), H), (sh(Lo - tl), zin(Lo - tl)), (sh(Lo / 2), G["apex"]),
                         (sh(Lo / 2), H + rise)], -half, half)
    S.wprism("glass", w, [(sh(t), z) for t, z in G["inner"]], -1, 1)
    zb = G["sill"]
    for t, ztop in G["mulls"]:
        S.wbox("wood", w, sh(t - m / 2), sh(t + m / 2), -half, half, zb, ztop + 1)
        for a in (t - m / 2 - fw_, t + m / 2):
            S.wbox("frame", w, sh(a), sh(a + fw_), -fd, fd, zb, ztop)
    for ta, tb, z in G["trans"]:
        S.wbox("wood", w, sh(ta), sh(tb), -half, half, z - m / 2, z + m / 2)
        S.wbox("frame", w, sh(ta), sh(tb), -fd, fd, z - m / 2 - fw_, z + m / 2 + fw_)
    # إطار أسود حول الزجاج (خط التركيب)
    S.wbox("frame", w, sh(tl), sh(Lo - tl), -fd, fd, zb, zb + fw_)
    for a in (tl, Lo - tl - fw_):
        S.wbox("frame", w, sh(a), sh(a + fw_), -fd, fd, zb, zin(a + fw_ / 2))
    S.wdiag("frame", w, sh(tl), zin(tl), sh(Lo / 2), G["apex"], fw_ * 2, -fd, fd)
    S.wdiag("frame", w, sh(Lo / 2), G["apex"], sh(Lo - tl), zin(Lo - tl), fw_ * 2, -fd, fd)
    # ضلفة الباب: إطار خشب داخل فتحته + مقبض
    da, db, dh = door
    st = 7
    S.wbox("wood", w, sh(da), sh(da + st), -3, 3, zb, dh - m / 2)
    S.wbox("wood", w, sh(db - st), sh(db), -3, 3, zb, dh - m / 2)
    S.wbox("wood", w, sh(da), sh(db), -3, 3, zb, zb + 14)
    S.wbox("frame", w, sh(db - st - 4), sh(db - st - 2), -half - 3, -half, 95, 125)


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
                   hidden=("rafters", "wood_in", "sheathing"), zoom=1.0, tight=False, dpi=130, labels=None):
    """معاينة منظور بالراسم البرمجي (z-buffer). labels: [(x, y, z, نص)] تنكتب بالأبيض على الصورة."""
    from .raster import render
    render(scene, path, views, int(size[0] * dpi), int(size[1] * dpi), hidden, strip, tight, zoom, labels)


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
