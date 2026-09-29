"""محيط الكوخ في اللقطات الخارجية الواقعية: أشجار خلفية، شجيرات حول القاعدة، ممر حجر من درج التراس،
جلسة خارجية على التراس ونباتات على البلكونة. كل الإحداثيات بالمتر (نفس نظام المشروع: +y خلف، التراس جنوب).
"""
import random


def plan_landscape(project, seed=7, keep_clear=()):
    """keep_clear: نقاط كاميرات (x,y) — لا شجر بينها وبين الكوخ."""
    rnd = random.Random(seed)
    xs = [p[0] for w in project.walls for p in (w.start, w.end)]
    ys = [p[1] for w in project.walls for p in (w.start, w.end)]
    x0, x1, y0, y1 = min(xs) / 100, max(xs) / 100, min(ys) / 100, max(ys) / 100
    for d in project.decks:
        y0 = min(y0, d.rect[1] / 100)
    gz = -project.slab_height / 100
    out = []
    # حزام أشجار خلف الكوخ وعلى الجانبين (الواجهة الأمامية مفتوحة للكاميرا)
    import math
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for i in range(22):
        ang = math.radians(rnd.uniform(-20, 200))          # من الشرق إلى الغرب مروراً بالخلف
        rad = rnd.uniform(8.0, 22.0)
        tx, ty = cx + rad * math.cos(ang), cy + 2 + rad * math.sin(ang)
        if any(_seg_dist((tx, ty), c, (cx, cy)) < 3.5 for c in keep_clear):
            continue
        out.append({"model": "tree_small_02", "at": [tx, ty, gz], "H": rnd.uniform(4.0, 7.5), "rot": rnd.uniform(0, 360)})
    for i in range(14):                                     # شجيرات متفرقة بين الأشجار
        ang = math.radians(rnd.uniform(-30, 210))
        rad = rnd.uniform(6.0, 16.0)
        out.append({"model": "shrub_02", "at": [cx + rad * math.cos(ang), cy + rad * math.sin(ang), gz],
                    "H": rnd.uniform(0.9, 1.6), "rot": rnd.uniform(0, 360)})
    # شجيرات على طول الجدارين الجانبيين والخلفي
    for y in _steps(0.6, y1 - 0.8, 2.2):
        for x, r in ((x0 - 0.9, 90), (x1 + 0.9, -90)):
            out.append({"model": "shrub_02", "at": [x, y, gz], "H": rnd.uniform(0.7, 1.0), "rot": r + rnd.uniform(-20, 20)})
    for x in _steps(x0 + 0.6, x1 - 0.6, 2.4):
        out.append({"model": "shrub_02", "at": [x, y1 + 0.9, gz], "H": rnd.uniform(0.7, 1.0), "rot": rnd.uniform(-20, 20)})
    # ممر حجر من درج التراس
    for d in project.decks:
        st = d.stairs if isinstance(d.stairs, dict) else None
        if not st or d.level:
            continue
        cx = (d.rect[0] + st.get("offset", 0) + st.get("width", 100) / 2) / 100
        yy = d.rect[1] / 100 - 0.9
        for i in range(8):
            out.append({"kind": "paver", "at": [cx + rnd.uniform(-0.05, 0.05), yy - i * 0.75, gz - 0.02],
                        "size": [min(1.4, st.get("width", 100) / 100 * 0.5), 0.45]})
        # شجيرات على جانبي الدرج
        for sx in (d.rect[0] / 100 + 0.6, d.rect[2] / 100 - 0.6):
            if abs(sx - cx) > st.get("width", 100) / 200 + 0.5:
                out.append({"model": "shrub_02", "at": [sx, d.rect[1] / 100 - 0.8, gz], "H": 0.8, "rot": 0})
    # جلسة خارجية + نباتات على التراس الأرضي، وأحواض زرع على البلكونة
    for d in project.decks:
        dx0, dy0, dx1, dy1 = (v / 100 for v in d.rect)
        z = (d.level or 0) / 100
        if not d.level:
            out.append({"model": "outdoor_table_chair_set_01", "at": [dx0 + 1.3, (dy0 + dy1) / 2, z], "H": 0.86,
                        "rot": 90})
            out.append({"model": "potted_plant_01", "at": [dx1 - 0.5, dy1 - 0.45, z], "H": 1.3})
        else:
            out.append({"model": "planter_box_01", "at": [dx1 - 0.7, dy0 + 0.45, z], "W": 0.9})
            out.append({"model": "potted_plant_02", "at": [dx0 + 0.5, dy0 + 0.5, z], "H": 0.85})
    return out


def _steps(a, b, step):
    n = max(1, int((b - a) / step))
    return [a + (b - a) * i / n for i in range(n + 1)]


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return ((p[0] - ax - t * dx) ** 2 + (p[1] - ay - t * dy) ** 2) ** 0.5
