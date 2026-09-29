"""كتالوج النماذج: أشكال الأسقف (دور/دور ونص/دورين) وأنواع الدربزين — للاختيار بالرمز.

نماذج كتلية مبسطة (بدون تقسيمات داخلية) لعرض الشكل الخارجي فقط.
"""
import math
from pathlib import Path

import yaml

from .model import Wall
from .model3d import Scene, railing_run, render_preview
from .style import PRESETS, resolve_style

WALL = 12
FLOOR = 280          # ارتفاع الدور
SLAB2 = 25           # سماكة أرضية الدور الثاني


class Maker:
    def __init__(self, style):
        self.S = Scene()
        st = style
        for m, c in (("slab", st["slab"]), ("wood", st["wood"]), ("trim", st["trim"]),
                     ("frame", st["frame"]), ("roof_tiles", st["roof"]), ("door", st["frame"])):
            self.S.material(m, c)
        self.S.material("glass", st["glass"], st["glass_alpha"])
        self.rails = yaml.safe_load(open(PRESETS, encoding="utf-8"))["railings"]
        self.rail = st["railing"]

    # ------------------------------------------------ عناصر أساسية
    def base(self, x0, y0, x1, y1):
        self.S.box("slab", x0 - 10, y0 - 10, -20, x1 + 10, y1 + 10, 0)

    def block(self, x0, y0, x1, y1, z0, z1):
        self.S.box("wood", x0, y0, z0, x1, y1, z1)
        cb = 10
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            sx, sy = (-1 if x == x0 else 1), (-1 if y == y0 else 1)
            self.S.box("trim", min(x, x + sx * 2.5), min(y - sy * cb, y + sy * 2.5), z0,
                       max(x, x + sx * 2.5), max(y - sy * cb, y + sy * 2.5), z1)

    def window(self, face, a, b, z0, z1, door=False):
        """face = (axis, value, sign): axis 'y' → جدار موازي لمحور x عند y=value، sign للخارج."""
        ax, v, sg = face
        lo = lambda d: (v + sg * d)  # noqa: E731
        mat = "door" if door else "glass"

        def bx(m, a_, b_, za, zb, d0, d1):
            p0, p1 = sorted((lo(d0), lo(d1)))
            if ax == "y":
                self.S.box(m, a_, p0, za, b_, p1, zb)
            else:
                self.S.box(m, p0, a_, za, p1, b_, zb)
        bx("frame", a - 6, b + 6, z0 - 6, z1 + (0 if door else 6), 0, 1.5)
        bx(mat, a, b, z0, z1, 1.5, 3)
        if not door and b - a >= 90:
            m = (a + b) / 2
            bx("frame", m - 2.5, m + 2.5, z0, z1, 2.5, 3.5)

    def post(self, x, y, z0, z1, s=12):
        self.S.box("trim", x - s / 2, y - s / 2, z0, x + s / 2, y + s / 2, z1)

    def railing(self, p0, p1, z0, gaps=(), upper=False, name=None):
        name = name or self.rail
        w = Wall("r", p0, p1)
        h = 105 if upper else None
        cuts = sorted(gaps)
        x = 0
        for a, b in cuts + [(w.length, w.length)]:
            if a - x > 20:
                railing_run(self.S, w, x, a, z0, name, self.rails[name], height=h)
            x = b

    def deck(self, x0, y0, x1, y1, top=0, rail_sides="SEW", stairs=None, upper=False, th=None):
        th = th or (top + 20 if not upper else SLAB2)
        self.S.box("wood", x0, y0, top - th, x1, y1, top)
        e = {"S": ((x0, y0), (x1, y0)), "E": ((x1, y0), (x1, y1)), "N": ((x1, y1), (x0, y1)),
             "W": ((x0, y1), (x0, y0))}
        for sd in rail_sides:
            gaps = [stairs[1:]] if stairs and stairs[0] == sd else []
            self.railing(*e[sd], top, gaps, upper)
        if stairs and not upper and top > 10:
            sd, a, b = stairs
            n = math.ceil((top + 20) / 18)
            r = (top + 20) / n
            (px0, py0), (px1, py1) = e[sd]
            for k in range(1, n):
                d = 28 * (n - k)
                if sd == "S":
                    self.S.box("wood", x0 + a, y0 - d, -20, x0 + b, y0, -20 + r * k)

    # ------------------------------------------------ الأسقف
    def profile_roof(self, axis, u0, u1, prof, ovu=40, gable_walls=True, th=14, z_wall_top=None):
        """سقف ممتد على طول u بمقطع prof = [(v, z)] (خط أسفل المداد) من طرف الرفرف للطرف الآخر."""
        T = (lambda u, v, z: (u, v, z)) if axis == "x" else (lambda u, v, z: (v, u, z))
        S = self.S
        for (va, za), (vb, zb) in zip(prof, prof[1:]):
            pts = [T(u0 - ovu, va, za), T(u1 + ovu, va, za), T(u1 + ovu, vb, zb), T(u0 - ovu, vb, zb)]
            S.hexa("roof_tiles", pts + [(x, y, z + th) for x, y, z in pts])
            for uu in (u0 - ovu - 3, u1 + ovu):          # ألواح حافة الجملون
                pts = [T(uu, va, za - 12), T(uu + 3, va, za - 12), T(uu + 3, vb, zb - 12), T(uu, vb, zb - 12)]
                S.hexa("trim", pts + [(x, y, z + th + 11) for x, y, z in pts])
        for (ve, ze), (vn, _) in ((prof[0], prof[1]), (prof[-1], prof[-2])):   # لوح واجهة المداد
            sg = -1 if ve < vn else 1
            pts = [T(u0 - ovu, ve, ze - 14), T(u1 + ovu, ve, ze - 14), T(u1 + ovu, ve + sg * 3, ze - 14),
                   T(u0 - ovu, ve + sg * 3, ze - 14)]
            S.hexa("trim", pts + [(x, y, z + th + 13) for x, y, z in pts])
        if gable_walls:
            zt = z_wall_top if z_wall_top is not None else min(z for _, z in prof[1:-1])
            inner = [(v, z) for v, z in prof[1:-1]]
            poly = [(inner[0][0], zt)] + inner + [(inner[-1][0], zt)]
            poly = [p for i, p in enumerate(poly) if i == 0 or p != poly[i - 1]]
            for ua, ub in ((u0, u0 + WALL), (u1 - WALL, u1)):
                front = [T(ua, v, z) for v, z in poly]
                back = [T(ub, v, z) for v, z in poly]
                n = len(poly)
                faces = [tuple(range(n)), tuple(range(n, 2 * n))] + \
                        [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
                S.poly("wood", front + back, faces)

    @staticmethod
    def gable_prof(v0, v1, ze, pitch, ov=40, frac=0.5, pitch2=None):
        vr = v0 + (v1 - v0) * frac
        t1 = math.tan(math.radians(pitch))
        rise = (vr - v0) * t1
        t2 = rise / (v1 - vr) if pitch2 is None else math.tan(math.radians(pitch2))
        return [(v0 - ov, ze - ov * t1), (v0, ze), (vr, ze + rise), (v1, ze), (v1 + ov, ze - ov * t2)]

    @staticmethod
    def gambrel_prof(v0, v1, ze, ov=40, low=60, up=25, knee=0.22):
        span = v1 - v0
        vk1, vk2 = v0 + span * knee, v1 - span * knee
        zk = ze + (vk1 - v0) * math.tan(math.radians(low))
        zt = zk + (span / 2 - (vk1 - v0)) * math.tan(math.radians(up))
        tl = math.tan(math.radians(low))
        return [(v0 - ov * 0.5, ze - ov * 0.5 * tl), (v0, ze), (vk1, zk), ((v0 + v1) / 2, zt), (vk2, zk),
                (v1, ze), (v1 + ov * 0.5, ze - ov * 0.5 * tl)]

    def gable_block(self, axis, u0, u1, v0, v1, ze, pitch, ov=40, ovu=40, frac=0.5, z0=0):
        x0, y0, x1, y1 = (u0, v0, u1, v1) if axis == "x" else (v0, u0, v1, u1)
        self.block(x0, y0, x1, y1, z0, ze)
        self.profile_roof(axis, u0, u1, self.gable_prof(v0, v1, ze, pitch, ov, frac), ovu)

    def pent(self, x0, y0, x1, y1, z, depth=70, pitch=25):
        """شريط سقف مائل حول المبنى (بين الدورين)."""
        t = math.tan(math.radians(pitch))
        for (ax, v, sg, a, b) in (("y", y0, -1, x0, x1), ("y", y1, 1, x0, x1), ("x", x0, -1, y0, y1),
                                  ("x", x1, 1, y0, y1)):
            a, b = a - depth, b + depth
            for m, d0, d1 in (("trim", 0, 9), ("roof_tiles", 9, 14)):
                if ax == "y":
                    pts = [(a, v, z + d0), (b, v, z + d0), (b, v + sg * depth, z - depth * t + d0),
                           (a, v + sg * depth, z - depth * t + d0)]
                else:
                    pts = [(v, a, z + d0), (v, b, z + d0), (v + sg * depth, b, z - depth * t + d0),
                           (v + sg * depth, a, z - depth * t + d0)]
                self.S.hexa(m, pts + [(x, y, zz + d1 - d0) for x, y, zz in pts])


# ======================================================== النماذج
def _std_windows(M, x0, y0, x1, y1, z0=90, h=120, door_side="S", door_at=None, row=0, n=2):
    zz = z0 + row * (FLOOR + SLAB2)
    L = x1 - x0
    for k in range(n):
        c = x0 + L * (k + 1) / (n + 1)
        if row == 0 and door_side == "S" and door_at is not None and abs(c - door_at) < 110:
            continue
        M.window(("y", y0, -1), c - 60, c + 60, zz, zz + h)
    if row == 0 and door_at is not None:
        M.window(("y", y0, -1), door_at - 55, door_at + 55, 0, 210, door=True)


ROOFS = []


def roof(code, ar, floors, note, stars, view=(18, -58)):
    def deco(fn):
        ROOFS.append({"code": code, "ar": ar, "floors": floors, "note": note, "stars": stars, "fn": fn,
                      "view": view})
        return fn
    return deco


@roof("R01", "جملون بسيط", "دور", "الأساس الحالي للمصنع — أسرع تنفيذ وأقل هدر", 1)
def r01(M):
    M.base(0, 0, 900, 550)
    M.gable_block("x", 0, 900, 0, 550, 280, 28)
    _std_windows(M, 0, 0, 900, 550, door_at=450, n=3)
    M.window(("x", 900, 1), 200, 320, 90, 210)


@roof("R02", "جملون + جلسة أمامية تحت السقف", "دور", "السقف يمتد فوق جلسة على طرف الجملون (مثل صورة 5)", 2)
def r02(M):
    M.base(0, 0, 900, 550)
    M.block(0, 0, 680, 550, 0, 280)
    M.profile_roof("x", 0, 900, M.gable_prof(0, 550, 280, 28), 40)
    for y in (6, 544):
        M.post(894, y, 0, 280)
    M.S.box("wood", 680, 0, -20, 900, 550, 0)
    M.railing((900, 550), (900, 0), 0, gaps=[(215, 335)])
    M.window(("x", 680, 1), 215, 335, 0, 210, door=True)
    M.window(("x", 680, 1), 60, 180, 90, 210)
    M.window(("x", 680, 1), 370, 490, 90, 210)
    _std_windows(M, 0, 0, 680, 550, n=2)


@roof("R03", "جملون + مظلة مدخل بجملون صغير", "دور", "مدخل بارز بجملون صغير فوق الباب (مثل صورة 1)", 2)
def r03(M):
    M.base(0, -140, 900, 550)
    M.gable_block("x", 0, 900, 0, 550, 280, 30)
    M.S.box("wood", 380, -140, -20, 520, 0, 0)
    for x in (386, 514):
        M.post(x, -134, 0, 260)
    M.profile_roof("y", -150, 0, M.gable_prof(380, 520, 260, 38, 15), 0, gable_walls=False)
    _std_windows(M, 0, 0, 900, 550, door_at=450, n=4)


@roof("R04", "شكل L — جملونين متقاطعين", "دور", "مساحة أكبر وواجهتين جملون (مثل صورة 2)", 3,
      view=(22, 30))
def r04(M):
    M.base(0, 0, 1000, 900)
    M.gable_block("x", 0, 1000, 0, 500, 280, 28)
    M.gable_block("y", 450, 900, 0, 450, 280, 28)
    _std_windows(M, 0, 0, 1000, 500, door_at=700, n=3)
    M.window(("x", 450, 1), 580, 700, 90, 210)


@roof("R05", "شكل T", "دور", "جناح أمامي في الوسط — واجهة رئيسية فخمة", 3)
def r05(M):
    M.base(0, -300, 1100, 500)
    M.gable_block("x", 0, 1100, 0, 500, 280, 28)
    M.gable_block("y", -300, 250, 350, 750, 280, 28)
    M.window(("y", -300, -1), 490, 610, 90, 210)
    M.window(("y", 0, -1), 100, 220, 90, 210)
    M.window(("y", 0, -1), 880, 1000, 90, 210)


@roof("R06", "جملون أمامي بارز", "دور", "بروز صغير بجملون مستقل على الواجهة الطويلة", 2)
def r06(M):
    M.base(0, -150, 950, 550)
    M.gable_block("x", 0, 950, 0, 550, 280, 28)
    M.gable_block("y", -150, 100, 300, 650, 280, 34, ovu=0)
    M.window(("y", -150, -1), 415, 535, 0, 210, door=True)
    _std_windows(M, 0, 0, 950, 550, n=4, door_at=475)


@roof("R07", "جملون غير متماثل (سولت بوكس)", "دور", "ميول مختلفة للجهتين — شكل عصري ويسمح بشباك علوي", 2)
def r07(M):
    M.base(0, 0, 900, 600)
    M.block(0, 0, 900, 600, 0, 280)
    M.profile_roof("x", 0, 900, M.gable_prof(0, 600, 280, 35, 40, frac=0.35), 40)
    _std_windows(M, 0, 0, 900, 600, door_at=450, n=3)


@roof("R08", "جملون بذيل ممتد فوق جلسة (كات سلايد)", "دور", "الميل الأمامي يكمل تحت ليغطي جلسة بطول الواجهة", 2)
def r08(M):
    M.base(0, -220, 900, 550)
    M.block(0, 0, 900, 550, 0, 280)
    t = math.tan(math.radians(28))
    prof = [(-260, 280 - 260 * t * 0.55), (0, 280), (275, 280 + 275 * t), (550, 280), (590, 280 - 40 * t)]
    M.profile_roof("x", 0, 900, prof, 30, gable_walls=True, z_wall_top=280)
    for x in (6, 300, 600, 894):
        M.post(x, -214, 0, 280 - 214 * t * 0.55)
    M.deck(0, -220, 900, 0, 0, rail_sides="SEW", stairs=("S", 390, 510))
    _std_windows(M, 0, 0, 900, 550, door_at=450, n=3)


@roof("R09", "جملون مكسور (مخزن / بارن)", "دور ونص", "ميلين لكل جهة — مساحة علوية للتخزين أو غرفة", 3)
def r09(M):
    M.base(0, 0, 900, 600)
    M.block(0, 0, 900, 600, 0, 260)
    M.profile_roof("x", 0, 900, M.gambrel_prof(0, 600, 260), 40, z_wall_top=260)
    _std_windows(M, 0, 0, 900, 600, door_at=450, n=3)
    M.window(("x", 900, 1), 240, 360, 380, 480)


@roof("R10", "جملون مع شبابيك سقف بارزة (دورمر)", "دور ونص", "شبابيك بجملونات صغيرة على الميل — إضاءة للعلية", 3)
def r10(M):
    M.base(0, 0, 900, 600)
    M.gable_block("x", 0, 900, 0, 600, 260, 40)
    t = math.tan(math.radians(40))
    for c in (250, 650):
        y0 = 90
        M.block(c - 80, y0 - 10, c + 80, y0 + 150, 260, 260 + 90 * t + 30)
        M.window(("y", y0 - 10, -1), c - 45, c + 45, 300, 370)
        M.profile_roof("y", y0 - 10, y0 + 150, M.gable_prof(c - 80, c + 80, 260 + 90 * t + 30, 35, 15),
                       0, gable_walls=True)
    _std_windows(M, 0, 0, 900, 600, door_at=450, n=3)


@roof("R11", "A-فريم (جملون حاد للأرض)", "دور ونص", "السقف يشكل الجدران — واجهة زجاج كبيرة ودور علوي مفتوح", 3)
def r11(M):
    M.base(0, 0, 700, 900)
    M.block(0, 0, 700, 900, 0, 60)
    M.profile_roof("y", 0, 900, M.gable_prof(0, 700, 60, 60, 30), 30, z_wall_top=60)
    for a, b, z0, z1 in ((180, 520, 0, 240), (215, 485, 260, 420), (275, 425, 440, 540)):
        M.window(("y", 0, -1), a, b, z0, z1)


@roof("T01", "دورين — جملون بسيط", "دورين", "أبسط دورين — حمامات فوق بعض (قاعدة المصنع)", 2)
def t01(M):
    M.base(0, 0, 800, 550)
    top = 2 * FLOOR + SLAB2
    M.gable_block("x", 0, 800, 0, 550, top, 28)
    for r in (0, 1):
        _std_windows(M, 0, 0, 800, 550, door_at=400 if r == 0 else None, row=r, n=3)
    M.window(("x", 800, 1), 215, 335, FLOOR + SLAB2 + 90, FLOOR + SLAB2 + 210)


@roof("T02", "دورين + بلكونة على واجهة الجملون", "دورين", "بلكونة بدربزين علوي 105 سم وباب من الدور الثاني", 3)
def t02(M):
    M.base(0, -170, 800, 550)
    top = 2 * FLOOR + SLAB2
    M.gable_block("y", 0, 550, 0, 800, top, 32)
    z2 = FLOOR + SLAB2
    M.deck(150, -170, 650, 0, z2, rail_sides="SEW", upper=True)
    for x in (158, 642):
        M.post(x, -162, 0, z2 - SLAB2)
    M.window(("y", 0, -1), 340, 460, z2, z2 + 210, door=True)
    M.window(("y", 0, -1), 340, 460, 0, 210, door=True)
    M.window(("y", 0, -1), 80, 200, 90, 210)
    M.window(("y", 0, -1), 600, 720, 90, 210)
    M.window(("y", 0, -1), 360, 440, z2 + 250, z2 + 320)


@roof("T03", "دورين + جلسة أرضية وبلكونة فوقها", "دورين", "الجلسة الأرضية سقفها أرضية البلكونة", 3)
def t03(M):
    M.base(0, -220, 900, 550)
    top = 2 * FLOOR + SLAB2
    M.gable_block("x", 0, 900, 0, 550, top, 28)
    z2 = FLOOR + SLAB2
    M.deck(0, -220, 900, 0, 0, rail_sides="SEW", stairs=("S", 390, 510))
    M.deck(0, -220, 900, 0, z2, rail_sides="SEW", upper=True)
    for x in (6, 300, 600, 894):
        M.post(x, -214, 0, z2 - SLAB2)
    for r in (0, 1):
        _std_windows(M, 0, 0, 900, 550, door_at=450 if r == 0 else None, row=r, n=3)
    M.window(("y", 0, -1), 395, 505, z2, z2 + 210, door=True)


@roof("T04", "دورين + شريط سقف بين الدورين", "دورين", "شريط مائل يحمي الدور الأرضي ويكسر الارتفاع (مثل صورة 3)", 2)
def t04(M):
    M.base(0, 0, 700, 550)
    top = 2 * FLOOR + SLAB2
    M.gable_block("y", 0, 550, 0, 700, top, 34)
    M.pent(0, 0, 700, 550, FLOOR + 10)
    for r in (0, 1):
        z = 90 + r * (FLOOR + SLAB2)
        M.window(("y", 0, -1), 90, 210, z, z + 130)
        M.window(("y", 0, -1), 490, 610, z, z + 130)
    M.window(("y", 0, -1), 295, 405, 0, 210, door=True)
    M.window(("y", 0, -1), 300, 400, FLOOR + SLAB2 + 60, FLOOR + SLAB2 + 220)


@roof("T05", "دورين + جملون مرتفع فوق الجملون", "دورين", "جزء وسطي مرفوع بشبابيك عالية — إضاءة وارتفاع (مثل صورة 3)", 3)
def t05(M):
    M.base(0, 0, 900, 700)
    top = 2 * FLOOR + SLAB2
    M.gable_block("y", 0, 900, 0, 700, top, 30)
    rise = 350 * math.tan(math.radians(30))
    M.gable_block("y", -20, 880, 230, 470, top + rise * 0.55 + 90, 40, ov=25, ovu=40, z0=top)
    M.window(("y", -20, -1), 280, 420, top + 40, top + rise * 0.55 + 70)
    for r in (0, 1):
        z = 90 + r * (FLOOR + SLAB2)
        M.window(("y", 0, -1), 60, 200, z, z + 150)
        M.window(("y", 0, -1), 500, 640, z, z + 150)
    M.window(("y", 0, -1), 295, 405, 0, 210, door=True)


@roof("T06", "دورين شكل L", "دورين", "جناحين بجملونين — مناسب للمساحات الكبيرة", 3,
      view=(22, 30))
def t06(M):
    M.base(0, 0, 1000, 900)
    top = 2 * FLOOR + SLAB2
    M.gable_block("x", 0, 1000, 0, 500, top, 30)
    M.gable_block("y", 450, 900, 0, 450, FLOOR + SLAB2 + 150, 30)
    for r in (0, 1):
        _std_windows(M, 0, 0, 1000, 500, door_at=700 if r == 0 else None, row=r, n=3)


@roof("T07", "دور ونص — جملون حاد بعلية", "دور ونص", "جدران قصيرة + سقف حاد، الدور العلوي تحت الميل", 2)
def t07(M):
    M.base(0, 0, 800, 600)
    M.gable_block("y", 0, 600, 0, 800, 380, 50)
    _std_windows(M, 0, 0, 800, 600, door_at=400, n=2)
    M.window(("y", 0, -1), 330, 470, 430, 600)


# ======================================================== الإخراج
def _page(fig_title, items, draw):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig = plt.figure(figsize=(16.54, 11.69))
    fig.patches.append(Rectangle((0.02, 0.025), 0.96, 0.955, transform=fig.transFigure, fill=False, lw=1.2))
    fig.text(0.5, 0.945, fig_title, ha="center", fontsize=18)
    for i, it in enumerate(items):
        r, c = divmod(i, 3)
        x = 0.68 - c * 0.31
        y = 0.52 - r * 0.44
        draw(fig, it, x, y)
    return fig


def build_catalog(out_pdf, style_name="honey_burgundy"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    style = resolve_style(style_name)
    out_pdf = Path(out_pdf)
    tmp = out_pdf.parent / "_cat"
    tmp.mkdir(parents=True, exist_ok=True)
    for it in ROOFS:
        M = Maker(style)
        it["fn"](M)
        it["png"] = tmp / f"{it['code']}.png"
        render_preview(M.S, it["png"], views=(it["view"],), size=(7, 5), hidden=(), zoom=1.15, tight=True)

    lib = yaml.safe_load(open(PRESETS, encoding="utf-8"))["railings"]
    rails = []
    for i, (name, spec) in enumerate(lib.items()):
        M = Maker(style)
        M.S.box("slab", -20, -30, -8, 340, 30, 0)
        railing_run(M.S, Wall("r", (0, 0), (320, 0)), 0, 320, 0, name, spec)
        png = tmp / f"B{i + 1:02d}.png"
        render_preview(M.S, png, views=((10, -70),), size=(6, 3.2), hidden=(), zoom=1.05, tight=True)
        rails.append({"code": f"B{i + 1:02d}", "ar": spec["ar"], "png": png, "name": name,
                      "h": spec["height"]})

    def draw_roof(fig, it, x, y):
        ax = fig.add_axes([x, y + 0.07, 0.29, 0.33])
        ax.imshow(plt.imread(it["png"]))
        ax.axis("off")
        fig.text(x + 0.285, y + 0.05, f"{it['code']}  —  {it['ar']}", ha="right", fontsize=13, weight="bold")
        fig.text(x + 0.285, y + 0.025, f"{it['floors']}  |  التعقيد: {'★' * it['stars']}{'☆' * (3 - it['stars'])}",
                 ha="right", fontsize=9.5, color="#6b4f3a")
        fig.text(x + 0.285, y + 0.002, it["note"], ha="right", fontsize=9, color="#444")

    def draw_rail(fig, it, x, y):
        ax = fig.add_axes([x, y + 0.1, 0.29, 0.3])
        ax.imshow(plt.imread(it["png"]))
        ax.axis("off")
        fig.text(x + 0.285, y + 0.07, f"{it['code']}  —  {it['ar']}", ha="right", fontsize=10.5, weight="bold")
        fig.text(x + 0.285, y + 0.045, f"أرضي/دكة: {it['h']} سم  |  دور علوي/بلكونة: 105 سم", ha="right",
                 fontsize=9.5, color="#6b4f3a")

    groups = [("دور واحد", [r for r in ROOFS if r["floors"] == "دور"]),
              ("دور ونص (علية)", [r for r in ROOFS if r["floors"] == "دور ونص"]),
              ("دورين", [r for r in ROOFS if r["floors"] == "دورين"])]
    pages = []
    cover = plt.figure(figsize=(16.54, 11.69))
    cover.text(0.5, 0.78, "مصنع وتد الأخشاب", ha="center", fontsize=34, weight="bold", color="#5a3a22")
    cover.text(0.5, 0.7, "كتالوج أشكال الأسقف والدربزين", ha="center", fontsize=26)
    lines = [f"{len(ROOFS)} شكل سقف  +  {len(rails)} نوع دربزين",
             "اختر بالرمز: مثال  R04 + B03   أو   T03 + B01",
             "كل الأشكال جملون (حسب طريقة المصنع) بمدادات 5×15 كل 60 سم",
             "الألوان هنا موحدة (عسلي + قرميد عنابي) للمقارنة — اللون يُختار لاحقاً من الأنماط الأربعة",
             "النماذج كتلية للشكل الخارجي فقط — التفاصيل والمقاسات تطلع من المحرك بعد الاختيار"]
    for i, t in enumerate(lines):
        cover.text(0.5, 0.58 - i * 0.055, t, ha="center", fontsize=15 if i < 2 else 12,
                   color="#222" if i < 2 else "#555")
    pages.append(cover)
    for g, items in groups:
        for k in range(0, len(items), 6):
            pages.append(_page(f"أشكال الأسقف — {g}", items[k:k + 6], draw_roof))
    for k in range(0, len(rails), 6):
        pages.append(_page("أنواع الدربزين — للدكة والدرج والبلكونات", rails[k:k + 6], draw_rail))
    n = len(pages)
    with PdfPages(out_pdf) as pdf:
        for i, f in enumerate(pages, 1):
            f.text(0.5, 0.04, f"مصنع وتد الأخشاب  |  كتالوج النماذج  |  صفحة {i} / {n}", ha="center", fontsize=10)
            pdf.savefig(f)
            plt.close(f)
    for p in tmp.glob("*.png"):
        p.unlink()
    tmp.rmdir()
    return [(r["code"], r["ar"]) for r in ROOFS] + [(b["code"], b["ar"]) for b in rails]


if __name__ == "__main__":
    import sys
    print(build_catalog(sys.argv[1] if len(sys.argv) > 1 else "catalog.pdf"))
