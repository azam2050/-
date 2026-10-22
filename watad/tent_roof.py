"""سقف الخيمة المنساب (tent_hip): جملون هرمي بأربع جهات يصرّف للخارج من كل الجهات — بدون وديان —
بكسرة عند خط الجدار (bellcast): ميل علوي (pitch_deg) ثم رفرف منساب بميل أخف (flare_pitch) مثل قماش الخيمة
لين أوتاده، ومشراق زجاج طولي على القمة (monitor) يدخل الضوء بدون ما يحجز مويه.

roof:
  type: tent_hip
  pitch_deg: 35            # الميل العلوي
  units:                   # كل وحدة سقف مستقلة (المبنى + مظلات على أعمدة)
    - rect: [x0, y0, x1, y1]        # خط الجدار/الأعمدة (وجه خارجي)
      flare: {front: 240, back: 90, sides: 90}   # الرفرف المنساب (أفقي) — front = جهة y الصغرى
      flare_pitch: 20
      monitor: {x0: .., x1: .., w: 120, h: 60}   # مشراق زجاج على القمة (اختياري)
      pitch_deg: 30                  # (اختياري) ميل خاص بالوحدة
      base: 260                      # (اختياري) منسوب رأس الأعمدة للمظلات
"""
import math


def _hip(x0, y0, x1, y1, H, t1):
    """أسطح جملون هرمي على مستطيل: القمة على الضلع الأطول."""
    W, L = y1 - y0, x1 - x0
    out = []
    if L >= W:
        h = W / 2 * t1
        cy, xa, xb = (y0 + y1) / 2, x0 + W / 2, x1 - W / 2
        out += [[(x0, y0, H), (x1, y0, H), (xb, cy, H + h), (xa, cy, H + h)],
                [(x1, y1, H), (x0, y1, H), (xa, cy, H + h), (xb, cy, H + h)],
                [(x0, y1, H), (x0, y0, H), (xa, cy, H + h)],
                [(x1, y0, H), (x1, y1, H), (xb, cy, H + h)]]
        ridge = ((xa, cy, H + h), (xb, cy, H + h))
    else:
        h = L / 2 * t1
        cx, ya, yb = (x0 + x1) / 2, y0 + L / 2, y1 - L / 2
        out += [[(x0, y1, H), (x0, y0, H), (cx, ya, H + h), (cx, yb, H + h)],
                [(x1, y0, H), (x1, y1, H), (cx, yb, H + h), (cx, ya, H + h)],
                [(x0, y0, H), (x1, y0, H), (cx, ya, H + h)],
                [(x1, y1, H), (x0, y1, H), (cx, yb, H + h)]]
        ridge = ((cx, ya, H + h), (cx, yb, H + h))
    return out, h, ridge


def unit_geometry(project, u):
    H = u.get("base", project.roof_base)     # منسوب الكسرة (رأس الجدار أو الأعمدة)
    x0, y0, x1, y1 = u["rect"]
    t1 = math.tan(math.radians(u.get("pitch_deg", project.roof.pitch_deg)))
    t2 = math.tan(math.radians(u.get("flare_pitch", 20)))
    fl = u.get("flare", {})
    os_ = fl.get("sides", 80)
    of, ob = max(fl.get("front", os_), os_), max(fl.get("back", os_), os_)
    upper, h, ridge = _hip(x0, y0, x1, y1, H, t1)
    z = lambda d: H - t2 * d  # noqa: E731
    flare = [
        [(x0, y0, H), (x1, y0, H), (x1 + os_, y0 - os_, z(os_)), (x1 + os_, y0 - of, z(of)),
         (x0 - os_, y0 - of, z(of)), (x0 - os_, y0 - os_, z(os_))],
        [(x1, y1, H), (x0, y1, H), (x0 - os_, y1 + os_, z(os_)), (x0 - os_, y1 + ob, z(ob)),
         (x1 + os_, y1 + ob, z(ob)), (x1 + os_, y1 + os_, z(os_))],
        [(x0, y1, H), (x0, y0, H), (x0 - os_, y0 - os_, z(os_)), (x0 - os_, y1 + os_, z(os_))],
        [(x1, y0, H), (x1, y1, H), (x1 + os_, y1 + os_, z(os_)), (x1 + os_, y0 - os_, z(os_))]]
    g = {"upper": upper, "flare": flare, "h": h, "ridge": ridge, "H": H, "t1": t1, "t2": t2,
         "eave": (x0 - os_, y0 - of, x1 + os_, y1 + ob), "rect": (x0, y0, x1, y1), "glass": [], "cap": [],
         "of": of, "ob": ob, "os": os_}
    m = u.get("monitor")
    if m:                     # مشراق زجاج على القمة: جدران زجاج + غطاء هرمي صغير
        rz = H + h
        hw = m.get("w", 120) / 2
        mh = m.get("h", 60)
        alongx = ridge[0][1] == ridge[1][1]
        if alongx:
            cy = ridge[0][1]
            a0, a1, b0, b1 = m["x0"], m["x1"], cy - hw, cy + hw
        else:
            cx = ridge[0][0]
            a0, a1, b0, b1 = cx - hw, cx + hw, m["y0"], m["y1"]
        zb = rz - hw * t1
        zt = rz + mh
        for p, q in (((a0, b0), (a1, b0)), ((a1, b0), (a1, b1)), ((a1, b1), (a0, b1)), ((a0, b1), (a0, b0))):
            g["glass"].append([(p[0], p[1], zb), (q[0], q[1], zb), (q[0], q[1], zt), (p[0], p[1], zt)])
        cap, hc, _ = _hip(a0 - 25, b0 - 25, a1 + 25, b1 + 25, zt, t1)
        g["cap"] = cap
        g["monitor_rect"] = (a0, b0, a1, b1)
        g["top"] = zt + hc
    else:
        g["top"] = H + h
    return g


def units(project):
    return [unit_geometry(project, u) for u in project.roof.units]


def rise(project):
    return max(g["top"] for g in units(project)) - project.roof_base


def elev_draw(ax, P, w, half, depth, C_ROOF, C_WIN, Polygon):
    """واجهة: إسقاط أسطح السقف على مستوى الجدار (الأبعد أول) — يرجع أعلى منسوب."""
    ux, uy = w.u
    nx, ny = w.n
    tt = lambda x, y: (x - w.start[0]) * ux + (y - w.start[1]) * uy + half  # noqa: E731
    dn = lambda x, y: (x - w.start[0]) * nx + (y - w.start[1]) * ny        # noqa: E731
    faces = []
    for kind, f in all_faces(P):
        faces.append((sum(dn(p[0], p[1]) for p in f) / len(f), kind, f))
    top = 0
    for _d, kind, f in sorted(faces, key=lambda t: t[0]):
        pts = [(tt(p[0], p[1]), p[2] + (0 if kind == "glass" else depth)) for p in f]
        if kind == "glass":
            pts = [(tt(p[0], p[1]), p[2] + depth) for p in f]
            ax.add_patch(Polygon(pts, closed=True, fc="#e3f0fb", ec=C_WIN, lw=0.9, zorder=2))
        else:
            ax.add_patch(Polygon(pts, closed=True, fc="#fff3e0" if kind != "flare" else "#f6e6cf", ec=C_ROOF,
                                 lw=0.9, zorder=2))
        top = max(top, max(z for _, z in pts))
    return top, tt


def rafters(project, rules):
    """المداد العلوي (من الجدار للقمة) + قطعة الرفرف المنساب + المداد الركني."""
    lens = sorted(rules["roof"]["rafter_lengths"])
    sp = rules["roof"]["rafter_spacing"]
    up = fl = hip = 0.0
    count = 0
    for g in units(project):
        x0, y0, x1, y1 = g["rect"]
        half = min(x1 - x0, y1 - y0) / 2
        up = max(up, half * math.sqrt(1 + g["t1"] ** 2))
        fl = max(fl, (max(g["of"], g["ob"], g["os"]) + 30) * math.sqrt(1 + g["t2"] ** 2))
        hip = max(hip, math.sqrt(2 * half ** 2 + (g["h"]) ** 2))
        count += int(2 * ((x1 - x0) + (y1 - y0)) / sp) * 2
    stock = next((s for s in lens if s >= max(up, fl)), None)
    return {"rafter_length": round(max(up, fl), 1), "upper": round(up, 1), "flare": round(fl, 1),
            "hip_length": round(hip, 1), "rafter_count": count, "stock_length": stock,
            "warning": None if stock else f"المداد {max(up, fl):.0f} سم أطول من الطبلية"}


def all_faces(project):
    """[(نوع، نقاط)] لكل أسطح السقف — للرسم ثنائي الأبعاد."""
    out = []
    for g in units(project):
        out += [("flare", f) for f in g["flare"]] + [("upper", f) for f in g["upper"]]
        out += [("glass", f) for f in g["glass"]] + [("cap", f) for f in g["cap"]]
    return out


def surface_z(project, x, y):
    """منسوب سطح السقف (أعلى قيمة بين الوحدات) — للقطاع."""
    best = None
    for g in units(project):
        x0, y0, x1, y1 = g["rect"]
        ex0, ey0, ex1, ey1 = g["eave"]
        if not (ex0 <= x <= ex1 and ey0 <= y <= ey1):
            continue
        if x0 <= x <= x1 and y0 <= y <= y1:
            d = min(x - x0, x1 - x, y - y0, y1 - y)
            z = g["H"] + min(d * g["t1"], g["h"])
        else:
            d = max(x0 - x, x - x1, y0 - y, y - y1, 0)
            z = g["H"] - g["t2"] * d
        best = z if best is None else max(best, z)
    return best


def add_3d(S, project, rd):
    """أسطح السقف (تطبيق + قرميد) + ألواح الرفرف + جسر الكسرة + المشراق الزجاج وغطاه."""
    def prism(mat, pts, z0, z1):
        n = len(pts)
        verts = [(x, y, z + z0) for x, y, z in pts] + [(x, y, z + z1) for x, y, z in pts]
        faces = [tuple(range(n)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        S.poly(mat, verts, faces)
    from .model3d import _beam
    for g in units(project):
        for f in g["upper"] + g["flare"]:
            prism("sheathing", f, 0, rd + 2.5)
            prism("roof_tiles", f, rd + 2.5, rd + 6.5)
        for f in g["flare"]:                        # لوح الرفرف على الحافة الخارجية
            pts = f[2:] if len(f) == 6 else f[2:4]
            for p, q in zip(pts, pts[1:]):
                _beam(S, "trim", (p[0], p[1], p[2] + rd / 2), (q[0], q[1], q[2] + rd / 2), 14)
        x0, y0, x1, y1 = g["rect"]
        H = g["H"]
        for p, q in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            _beam(S, "trim", (p[0], p[1], H - 10), (q[0], q[1], H - 10), 18)      # جسر الكسرة (حامل الرفرف)
        (ax_, ay_, az_), (bx_, by_, bz_) = g["ridge"]
        _beam(S, "trim", (ax_, ay_, az_ + rd + 8), (bx_, by_, bz_ + rd + 8), 16)    # جسر القمة الظاهر
        for f in g["glass"]:
            p0, p1, p2, _p3 = f
            S.box("glass", min(p0[0], p1[0]) - 1.5, min(p0[1], p1[1]) - 1.5, p0[2] + rd,
                  max(p0[0], p1[0]) + 1.5, max(p0[1], p1[1]) + 1.5, p2[2])
            S.box("trim", p0[0] - 5, p0[1] - 5, p0[2] + rd, p0[0] + 5, p0[1] + 5, p2[2])
        for f in g["cap"]:
            prism("roof_tiles", f, 0, 6)
