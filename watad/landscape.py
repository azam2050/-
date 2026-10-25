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
    if project.site:
        return _site_landscape(project, rnd, gz)
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
            _deck_set(project, d, out, dx0, dy0, dx1, dy1, z)
        else:
            out.append({"model": "planter_box_01", "at": [dx1 - 0.7, dy0 + 0.45, z], "W": 0.9})
            out.append({"model": "potted_plant_02", "at": [dx0 + 0.5, dy0 + 0.5, z], "H": 0.85})
    return out


def _deck_set(project, d, out, dx0, dy0, dx1, dy1, z, ox=0.0, oy=0.0):
    """جلسة التراس الأرضي: بعيد عن الأبواب وطريق الدرج (ملاحظة المصنع)."""
    for f in project.furniture:                  # التراس مفروش بالتصميم (جلسة مصممة) — لا نضيف طاولة تلقائية
        fx, fy = (f.rect[0] + f.rect[2]) / 2, (f.rect[1] + f.rect[3]) / 2
        if d.rect[0] <= fx <= d.rect[2] and d.rect[1] <= fy <= d.rect[3]:
            return
    # ملاحظة المصنع: الجلسة ما تنحط قدام باب ولا على طريق الدرج — نحسب المناطق المحجوزة على طول التراس
    busy = []
    for w in project.walls:
        if not w.exterior or w.floor != 0:
            continue
        for o in w.openings:
            if o.kind != "door":
                continue
            (ax, ay), (bx, by) = w.point(o.offset), w.point(o.offset + o.width)
            if min(ay, by) - 30 <= d.rect[3] + 20 and max(ay, by) + 30 >= d.rect[1] - 20 and abs(ay - by) < 1:
                busy.append((min(ax, bx) / 100 + ox - 0.6, max(ax, bx) / 100 + ox + 0.6))
    st = d.stairs if isinstance(d.stairs, dict) else None
    if st:
        sx = (d.rect[0] + st.get("offset", 0)) / 100 + ox
        busy.append((sx - 0.2, sx + st.get("width", 100) / 100 + 0.2))
    spot = None
    if dy1 - dy0 >= 1.8:                         # التراس عميق كفاية لجلسة (≥ 1.80 م)
        for cx in _steps(dx0 + 0.9, dx1 - 0.9, 0.25):
            if all(cx + 0.85 < b0 or cx - 0.85 > b1 for b0, b1 in busy):
                spot = cx
                break
    if spot is not None:
        out.append({"model": "outdoor_table_chair_set_01", "at": [spot, (dy0 + dy1) / 2, z], "H": 0.86,
                    "rot": 90})
    pc = next((x for x in (dx1 - 0.5, dx0 + 0.5) if all(x + 0.3 < b0 or x - 0.3 > b1 for b0, b1 in busy)), None)
    if pc is not None:
        out.append({"model": "potted_plant_01", "at": [pc, dy1 - 0.45, z], "H": 1.3})


def _steps(a, b, step):
    n = max(1, int((b - a) / step))
    return [a + (b - a) * i / n for i in range(n + 1)]


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return ((p[0] - ax - t * dx) ** 2 + (p[1] - ay - t * dy) ** 2) ** 0.5


def _site_landscape(project, rnd, gz):
    """مشروع بموقع عام: أشجار المخطط (لكل وحدة) + أشجار خلفية خارج السور + جلسة التراس ونباتات البلكونة لكل وحدة."""
    import math
    from .site import boundary, expand, units_of
    st = expand(project.site)
    out = []
    for t in st.get("trees", []):
        x, y = t["at"][0] / 100, t["at"][1] / 100
        if t.get("kind") == "shrub":
            out.append({"model": "shrub_02", "at": [x, y, gz], "H": rnd.uniform(0.8, 1.1), "rot": rnd.uniform(0, 360)})
        else:
            out.append({"model": "tree_small_02", "at": [x, y, gz], "H": t.get("r", 120) / 100 * 2.6,
                        "rot": rnd.uniform(0, 360)})
    bp = [(x / 100, y / 100) for x, y in boundary(st)]
    cx = sum(p[0] for p in bp) / len(bp)
    cy = sum(p[1] for p in bp) / len(bp)
    for i in range(26):                                  # خلفية جبلية خضراء خارج السور (ما عدا جهة الشارع)
        ang = math.radians(rnd.uniform(10, 170))
        rad = rnd.uniform(17, 32)
        out.append({"model": "tree_small_02", "at": [cx + rad * math.cos(ang), cy + rad * math.sin(ang), gz],
                    "H": rnd.uniform(4.5, 8.0), "rot": rnd.uniform(0, 360)})
    for dx, dy in units_of(project.site):
        for d in project.decks:
            dx0, dy0, dx1, dy1 = ((d.rect[0] + dx) / 100, (d.rect[1] + dy) / 100, (d.rect[2] + dx) / 100,
                                  (d.rect[3] + dy) / 100)
            z = (d.level or 0) / 100
            if not d.level:
                _deck_set(project, d, out, dx0, dy0, dx1, dy1, z, dx / 100, dy / 100)
            else:
                out.append({"model": "planter_box_01", "at": [dx1 - 0.7, dy0 + 0.45, z], "W": 0.9})
                out.append({"model": "potted_plant_02", "at": [dx0 + 0.5, dy0 + 0.5, z], "H": 0.85})
    return out
