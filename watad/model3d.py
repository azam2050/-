"""نموذج 3D كامل للكوخ بالمواد والألوان — OBJ+MTL (3ds Max) و GLB.

المحاور: x,y المسقط، z للأعلى، z=0 وجه الصبة، الأرض الطبيعية z=-20. الوحدة سم في OBJ، متر في GLB.
"""
import math

import numpy as np

from .model import Wall, outer_bbox, wall_thickness
from .roof import rafter_positions, roof_geometry


class Scene:
    def __init__(self):
        self.parts = {}     # material -> [verts, faces]
        self.colors = {}    # material -> (hex, alpha)

    def material(self, name, color, alpha=1.0):
        self.colors[name] = (color, alpha)

    def poly(self, mat, verts, faces, center=None):
        """يضيف مجسم محدب؛ يضبط اتجاه الأوجه للخارج."""
        V, F = self.parts.setdefault(mat, [[], []])
        base = len(V)
        verts = [tuple(map(float, v)) for v in verts]
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


def build_scene(project, rules, style, heights):
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

    for w in project.walls:
        H = heights[w.name]
        L = w.length
        t_lo, t_hi = (-half, L + half) if w.exterior else (0, L)
        cuts = [(o.offset, o.offset + o.width) for o in w.openings]
        wm = "wood" if w.exterior else "wood_in"
        for a, b in _segments(t_lo, t_hi, cuts):
            S.wbox(wm, w, a, b, -half, half, 0, H)
        for o in w.openings:
            a, b = o.offset, o.offset + o.width
            z0 = o.sill if o.kind == "window" else 0
            z1 = z0 + o.height
            if z0 > 0:
                S.wbox(wm, w, a, b, -half, half, 0, z0)
            if z1 < H:
                S.wbox(wm, w, a, b, -half, half, z1, H)
            _opening(S, w, o, a, b, z0, z1, half, style, exterior=w.exterior)
        ux, uy = w.u
        gable_end = w.exterior and ((abs(uy) < 1e-6) == ridge_y)
        if gable_end and w.gable_glass:
            _glass_gable(S, w, L, H, rise, half, math.tan(p))
        elif gable_end:
            S.wprism("wood", w, [(-half, H), (L + half, H), (L / 2, H + rise)], -half, half)
        if w.exterior:   # ألواح الزوايا
            cb = tr["corner_boards"]
            for t in (-half, L + half - cb["w"]):
                S.wbox("trim", w, t, t + cb["w"], -half - cb["t"], -half, 0, H)

    # السقف: مدادات + تطبيق خشب + قرميد
    H = project.wall_height
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

    for d in project.decks:
        _deck(S, d, style, x0, y0, x1, y1, sh)
    # أعمدة الجلسة المسقوفة + جسر أمامي يحمل طرف الجملون
    pz = []
    for pt in project.posts:
        px, py = pt["at"]
        a = px if ridge_y else py
        side = -1 if a <= ac else 1
        ztop = zb(a, side)
        ps = pt.get("size", 15)
        S.box("trim", px - ps / 2, py - ps / 2, pt.get("base", 0), px + ps / 2, py + ps / 2, ztop)
        pz.append((px, py, ztop))
    if len(pz) >= 2 and project.roof.ext_start:
        b_edge = sum((py if ridge_y else px) for px, py, _ in pz) / len(pz)
        a0, a1 = a_lo, a_hi
        c0, c1 = to_xy(a0, b_edge - 8), to_xy(a1, b_edge + 8)
        S.box("trim", min(c0[0], c1[0]), min(c0[1], c1[1]), H - 22, max(c0[0], c1[0]), max(c0[1], c1[1]), H)
    return S


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
        for (ta, tb, za, zb_) in ((a, a + fw, 0, z1), (b - fw, b, 0, z1), (a, b, z1 - fw, z1)):
            S.wbox("frame", w, ta, tb, out - 2, half, za, zb_)
        if o.leaves == 0:
            return
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
    # كنار خارجي حول الزجاج (خط التركيب)
    S.wbox("trim", w, tl, L - tl, -half - 2.5, -half, H + border - 5, H + border)


# ---------------------------------------------------------------- الدكة والدربزين
def _deck(S, d, style, bx0, by0, bx1, by1, sh=20):
    x0, y0, x1, y1 = d.rect
    top = d.height - sh
    S.box("wood", x0, y0, -sh, x1, y1, top)
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
            railing_run(S, w, a, b, top, spec_name, spec)
    if d.stairs and d.height > 25:
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
