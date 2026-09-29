"""أشكال أسقف جديدة للعرض والاختيار قبل اعتمادها في المحرك.

شروط المصنع لكل شكل (تُفحص آلياً في drainage_issues):
  - كل سطح مائل للخارج بميل لا يقل عن 20° — لا سقف مسطح ولا قناة/وادي داخلي يجمع مويه الأمطار.
  - أوطى حافة لكل سطح تكون برا الجدران اللي يغطيها (المويه تنزل لبرا مو على جدار أو سقف ثاني بدون مخرج).
  - مدادات مستقيمة 5×15 كل 60 سم بجلسة على الجدار — بدون تقويس ولا قطع معقدة.
كل نموذج على كوخ قياسي (9.00 × 6.00 م تقريباً) عشان المقارنة عادلة. الوحدات سم.
"""
import math

from .catalog import Maker

W, D, H = 900, 600, 280
MIN_PITCH = 20
CONCEPTS = []


def concept(code, ar, note, roof_mat="roof_tiles"):
    def deco(fn):
        CONCEPTS.append({"code": code, "ar": ar, "note": note, "fn": fn, "roof": roof_mat})
        return fn
    return deco


# ------------------------------------------------------------ أدوات
class Ctx:
    def __init__(self, M, mat):
        self.M, self.mat, self.planes = M, mat, []

    def prism(self, mat, pts, th, down=True):
        n = len(pts)
        other = [(x, y, z - th if down else z + th) for x, y, z in pts]
        faces = [tuple(range(n)), tuple(range(n, 2 * n))] + \
                [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.M.S.poly(mat, list(pts) + other, faces)

    def roof(self, pts, cover, mat=None):
        """لوح سقف (سطح علوي pts محدب مستوٍ) فوق المستطيل cover=(x0,y0,x1,y1) اللي يغطيه."""
        self.prism("trim", pts, 12)
        self.prism(mat or self.mat, pts, 4, down=False)
        self.planes.append((pts, cover))

    def vwall(self, mat, pts, t=12, inward=(0, 0)):
        n = len(pts)
        other = [(x + inward[0] * t, y + inward[1] * t, z) for x, y, z in pts]
        faces = [tuple(range(n)), tuple(range(n, 2 * n))] + \
                [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.M.S.poly(mat, list(pts) + other, faces)

    def brace(self, x, y, z, dx, dy, L=70):
        """كابولي خشب مائل تحت الرفرف (لمسة شاليه)."""
        self.M.S.poly("trim", *_bar((x, y, z - L), (x + dx * L, y + dy * L, z), 7))


def _bar(a, b, s):
    ax, ay, az = a
    bx, by, bz = b
    h = s / 2
    if abs(bx - ax) > abs(by - ay):
        off = [(0, -h, -h), (0, h, -h), (0, h, h), (0, -h, h)]
    else:
        off = [(-h, 0, -h), (h, 0, -h), (h, 0, h), (-h, 0, h)]
    v = [(ax + o[0], ay + o[1], az + o[2]) for o in off] + [(bx + o[0], by + o[1], bz + o[2]) for o in off]
    return v, [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def hip_planes(C, x0, y0, x1, y1, z_plate, pitch, ov, mat=None, cover=None):
    """رباعي على مستطيل: 4 سطوح من الرفرف للقمة — كلها تصرف لبرا."""
    t = math.tan(math.radians(pitch))
    Wd, Dd = x1 - x0, y1 - y0
    half = min(Wd, Dd) / 2
    ze, zr = z_plate - ov * t, z_plate + half * t
    a, b = (x0 - ov, y0 - ov), (x1 + ov, y1 + ov)
    cover = cover or (x0, y0, x1, y1)
    if Wd >= Dd:
        ym = (y0 + y1) / 2
        r0, r1 = (x0 + half, ym), (x1 - half, ym)
        C.roof([(a[0], a[1], ze), (b[0], a[1], ze), (r1[0], r1[1], zr), (r0[0], r0[1], zr)], cover, mat)
        C.roof([(b[0], b[1], ze), (a[0], b[1], ze), (r0[0], r0[1], zr), (r1[0], r1[1], zr)], cover, mat)
        C.roof([(a[0], b[1], ze), (a[0], a[1], ze), (r0[0], r0[1], zr)], cover, mat)
        C.roof([(b[0], a[1], ze), (b[0], b[1], ze), (r1[0], r1[1], zr)], cover, mat)
    else:
        xm = (x0 + x1) / 2
        r0, r1 = (xm, y0 + half), (xm, y1 - half)
        C.roof([(a[0], b[1], ze), (a[0], a[1], ze), (r0[0], r0[1], zr), (r1[0], r1[1], zr)], cover, mat)
        C.roof([(b[0], a[1], ze), (b[0], b[1], ze), (r1[0], r1[1], zr), (r0[0], r0[1], zr)], cover, mat)
        C.roof([(a[0], a[1], ze), (b[0], a[1], ze), (r0[0], r0[1], zr)], cover, mat)
        C.roof([(b[0], b[1], ze), (a[0], b[1], ze), (r1[0], r1[1], zr)], cover, mat)
    return zr


def gable_x(C, x0, x1, y0, y1, z_plate, pitch, ov, ove, mat=None, walls=True, cover=None):
    """جملون قمته موازية لـ x، مع حشوة الجدارين الطرفيين."""
    t = math.tan(math.radians(pitch))
    ym = (y0 + y1) / 2
    ze, zr = z_plate - ov * t, z_plate + (ym - y0) * t
    cover = cover or (x0, y0, x1, y1)
    C.roof([(x0 - ove, y0 - ov, ze), (x1 + ove, y0 - ov, ze), (x1 + ove, ym, zr), (x0 - ove, ym, zr)], cover, mat)
    C.roof([(x1 + ove, y1 + ov, ze), (x0 - ove, y1 + ov, ze), (x0 - ove, ym, zr), (x1 + ove, ym, zr)], cover, mat)
    if walls:
        for x, s in ((x0, 1), (x1, -1)):
            C.vwall("wood", [(x, y0, z_plate), (x, ym, zr - 13), (x, y1, z_plate)], 12, (s, 0))
    return zr


def gable_y(C, y0, y1, x0, x1, z_plate, pitch, ov, ove, mat=None, walls=True, cover=None):
    t = math.tan(math.radians(pitch))
    xm = (x0 + x1) / 2
    ze, zr = z_plate - ov * t, z_plate + (xm - x0) * t
    cover = cover or (x0, y0, x1, y1)
    C.roof([(x0 - ov, y1 + ove, ze), (x0 - ov, y0 - ove, ze), (xm, y0 - ove, zr), (xm, y1 + ove, zr)], cover, mat)
    C.roof([(x1 + ov, y0 - ove, ze), (x1 + ov, y1 + ove, ze), (xm, y1 + ove, zr), (xm, y0 - ove, zr)], cover, mat)
    if walls:
        for y, s in ((y0, 1), (y1, -1)):
            C.vwall("wood", [(x0, y, z_plate), (xm, y, zr - 13), (x1, y, z_plate)], 12, (0, s))
    return zr


def front(M, x0=0, x1=W, deck=True, big=False, depth=200, sides=True, y=0):
    L = x1 - x0
    c = (x0 + x1) / 2
    if big:
        M.window(("y", y, -1), x0 + 90, x1 - 90, 0, 240)
        for k in range(1, 4):
            xx = x0 + 90 + (L - 180) * k / 4
            M.S.box("frame", xx - 3, y - 2, 0, xx + 3, y + 1.5, 240)
    else:
        M.window(("y", y, -1), c - 120, c + 120, 0, 230)
        for a in (x0 + 80, x1 - 240):
            M.window(("y", y, -1), a, a + 160, 90, 220)
    if sides:
        M.window(("x", x0, -1), 230, 370, 90, 210)
        M.window(("x", x1, 1), 230, 370, 90, 210)
    if deck:
        M.deck(x0, y - depth, x1, y, 0, rail_sides="EW", stairs=("S", L / 2 - 150, L / 2 + 150))


# ------------------------------------------------------------ النماذج
@concept("S01", "رباعي بكسرة عند الحافة", "رباعي 32° وعند الرفرف كسرة أخف 20° — شكل ياباني ناعم والمويه تنزل بعيد عن الجدار")
def s01(M, C):
    M.base(0, 0, W, D)
    M.block(0, 0, W, D, 0, H)
    t1, t2 = math.tan(math.radians(32)), math.tan(math.radians(20))
    ov = 80
    ze = H - ov * t2
    zr = H + D / 2 * t1
    o = [(-ov, -ov), (W + ov, -ov), (W + ov, D + ov), (-ov, D + ov)]
    i_ = [(0, 0), (W, 0), (W, D), (0, D)]
    for k in range(4):                        # حلقة الكسرة
        (x0, y0), (x1, y1) = o[k], o[(k + 1) % 4]
        (u1, v1), (u0, v0) = i_[(k + 1) % 4], i_[k]
        C.roof([(x0, y0, ze), (x1, y1, ze), (u1, v1, H), (u0, v0, H)], (0, 0, W, D))
    r0, r1 = (D / 2, D / 2), (W - D / 2, D / 2)
    C.roof([(0, 0, H), (W, 0, H), (r1[0], r1[1], zr), (r0[0], r0[1], zr)], (0, 0, W, D))
    C.roof([(W, D, H), (0, D, H), (r0[0], r0[1], zr), (r1[0], r1[1], zr)], (0, 0, W, D))
    C.roof([(0, D, H), (0, 0, H), (r0[0], r0[1], zr)], (0, 0, W, D))
    C.roof([(W, 0, H), (W, D, H), (r1[0], r1[1], zr)], (0, 0, W, D))
    front(M)


@concept("S02", "رباعي بطابقين (باغودا)", "رباعي فوق شريط زجاج علوي وتحته مظلة تلف الكوخ — طابع شرقي فخم وإضاءة من فوق")
def s02(M, C):
    M.base(0, 0, W, D)
    hw = H + 90
    M.block(0, 0, W, D, 0, H)
    M.S.box("glass", 2, 2, H + 8, W - 2, D - 2, hw - 6)       # شريط زجاج علوي
    for x in range(0, W + 1, 150):
        for y in (0, D - 8):
            M.S.box("frame", min(x, W - 8), y, H, min(x, W - 8) + 8, y + 8, hw)
    for y in range(0, D + 1, 150):
        for x in (0, W - 8):
            M.S.box("frame", x, min(y, D - 8), H, x + 8, min(y, D - 8) + 8, hw)
    M.S.box("trim", -2, -2, hw - 8, W + 2, D + 2, hw)
    hip_planes(C, 0, 0, W, D, hw, 30, 60)
    t = math.tan(math.radians(22))           # مظلة محيطة (بنت هاوس) تحت الشريط الزجاجي
    dv = 90
    o = [(-dv, -dv), (W + dv, -dv), (W + dv, D + dv), (-dv, D + dv)]
    i_ = [(0, 0), (W, 0), (W, D), (0, D)]
    for k in range(4):
        (x0, y0), (x1, y1) = o[k], o[(k + 1) % 4]
        (u1, v1), (u0, v0) = i_[(k + 1) % 4], i_[k]
        C.roof([(x0, y0, H - dv * t), (x1, y1, H - dv * t), (u1, v1, H), (u0, v0, H)], (0, 0, W, D))
    front(M)


@concept("S03", "A-فريم بجناحين", "A-فريم بواجهة زجاج بالوسط وجناحين بميل لبرا — مويه الـA تنزل على الجناح ثم للأرض")
def s03(M, C):
    a0, a1 = 210, 690
    hk = 300
    M.base(0, 0, W, D)
    for x0, x1 in ((0, a0), (a1, W)):
        M.block(x0, 0, x1, D, 0, 260)
    M.block(a0, 0, a1, D, 0, hk)
    tw = math.tan(math.radians(22))
    C.roof([(a0, -40, 272), (a0, D + 40, 272), (-50, D + 40, 272 - (a0 + 50) * tw), (-50, -40, 272 - (a0 + 50) * tw)],
           (0, 0, a0, D))
    C.roof([(a1, D + 40, 272), (a1, -40, 272), (W + 50, -40, 272 - (a0 + 50) * tw), (W + 50, D + 40, 272 - (a0 + 50) * tw)],
           (a1, 0, W, D))
    t = math.tan(math.radians(55))
    xm = (a0 + a1) / 2
    ov = 45
    zr = hk + (xm - a0) * t
    C.roof([(a0 - ov, D + 60, hk - ov * t), (a0 - ov, -60, hk - ov * t), (xm, -60, zr), (xm, D + 60, zr)], (a0, 0, a1, D))
    C.roof([(a1 + ov, -60, hk - ov * t), (a1 + ov, D + 60, hk - ov * t), (xm, D + 60, zr), (xm, -60, zr)], (a0, 0, a1, D))
    M.window(("y", 0, -1), a0 + 20, a1 - 20, 0, hk - 10)       # زجاج الواجهة
    C.vwall("glass", [(a0, -1, hk), (xm, -1, zr - 16), (a1, -1, hk)], 3, (0, 1))
    for x in (a0 + 120, xm, a1 - 120):
        z1 = hk + (min(x - a0, a1 - x)) * t - 16
        M.S.box("frame", x - 4, -3, 0, x + 4, 2, z1)
    M.S.box("frame", a0, -3, hk - 6, a1, 2, hk + 2)
    C.vwall("wood", [(a0, D, hk), (xm, D, zr - 13), (a1, D, hk)], 12, (0, -1))
    for x0 in (40,):
        M.window(("y", 0, -1), x0, x0 + 130, 90, 210)
        M.window(("y", 0, -1), W - x0 - 130, W - x0, 90, 210)
    M.deck(0, -200, W, 0, 0, rail_sides="EW", stairs=("S", 300, 600))


@concept("S04", "جملون بمنور مرفوع", "جملون وفوقه جملون أصغر مرفوع بشريط زجاج على طول الكوخ — ضوء وتهوية من القمة")
def s04(M, C):
    M.base(0, 0, W, D)
    M.block(0, 0, W, D, 0, H)
    t = math.tan(math.radians(28))
    mw = 130                                  # نص عرض المنور
    ym = D / 2
    ov, ove = 60, 50
    zm = H + (ym - mw) * t                    # منسوب جلسة جدران المنور
    ze = H - ov * t
    C.roof([(-ove, -ov, ze), (W + ove, -ov, ze), (W + ove, ym - mw, zm), (-ove, ym - mw, zm)], (0, 0, W, ym - mw))
    C.roof([(W + ove, D + ov, ze), (-ove, D + ov, ze), (-ove, ym + mw, zm), (W + ove, ym + mw, zm)], (0, ym + mw, W, D))
    hm = zm + 85
    for y in (ym - mw, ym + mw - 8):
        M.S.box("glass", 0, y + 2, zm + 4, W, y + 6, hm - 8)
        for x in range(0, W + 1, 150):
            M.S.box("frame", min(x, W - 8), y, zm, min(x, W - 8) + 8, y + 8, hm)
    M.S.box("trim", 0, ym - mw, hm - 8, W, ym + mw, hm)
    gable_x(C, 0, W, ym - mw, ym + mw, hm, 28, 40, ove, walls=False)
    zr = hm + mw * t
    for x, s in ((0, 1), (W, -1)):
        C.vwall("wood", [(x, 0, H), (x, ym - mw, zm), (x, ym - mw, H)], 12, (s, 0))
        C.vwall("wood", [(x, ym + mw, H), (x, ym + mw, zm), (x, D, H)], 12, (s, 0))
        C.vwall("wood", [(x, ym - mw, H), (x, ym - mw, hm), (x, ym, zr - 13), (x, ym + mw, hm), (x, ym + mw, H)], 12, (s, 0))
    front(M)


@concept("S05", "جملون مشطوف الأطراف بكوابيل", "الجملون مقصوص من فوق بميل رباعي صغير ورفرف عميق على كوابيل خشب — شاليه أنيق")
def s05(M, C):
    M.base(0, 0, W, D)
    M.block(0, 0, W, D, 0, H)
    t = math.tan(math.radians(35))
    ov, ove = 80, 70
    ym = D / 2
    ze, zr = H - ov * t, H + ym * t
    zc = H + ym * t * 0.55                    # بداية القص
    yc = -ov + (zc - ze) / t
    th = math.tan(math.radians(50))
    dx = (zr - zc) / th - ove
    C.roof([(-ove, -ov, ze), (W + ove, -ov, ze), (W + ove, yc, zc), (W - dx, ym, zr), (dx, ym, zr), (-ove, yc, zc)],
           (0, 0, W, D))
    yc2 = D - yc
    C.roof([(W + ove, D + ov, ze), (-ove, D + ov, ze), (-ove, yc2, zc), (dx, ym, zr), (W - dx, ym, zr), (W + ove, yc2, zc)],
           (0, 0, W, D))
    C.roof([(-ove, yc2, zc), (-ove, yc, zc), (dx, ym, zr)], (0, 0, W, D))
    C.roof([(W + ove, yc, zc), (W + ove, yc2, zc), (W - dx, ym, zr)], (0, 0, W, D))
    y1 = (zc - H) / t
    for x, s in ((0, 1), (W, -1)):
        C.vwall("wood", [(x, 0, H), (x, y1, zc - 13), (x, D - y1, zc - 13), (x, D, H)], 12, (s, 0))
        for y in (60, D - 60):
            C.brace(x, y, H + 20, -s, 0)
    for x in (80, W / 2, W - 80):
        C.brace(x, 0, H - 5, 0, -1)
    front(M)


@concept("S06", "مقدمة زجاج بارزة (برو)", "الواجهة الأمامية تطلع لقدام على شكل رأس سهم زجاج تحت امتداد السقف — منظر بانورامي", "roof_tiles")
def s06(M, C):
    Wx, Dy, P = 620, 800, 170                 # عرض، عمق، بروز الرأس
    M.base(0, 0, Wx, Dy)
    M.block(0, 0, Wx, Dy, 0, H)
    M.S.box("slab", 0, -P, -20, Wx, 0, 0)
    t = math.tan(math.radians(35))
    xm = Wx / 2
    ov = 60
    zr = H + xm * t
    C.roof([(-ov, Dy + 50, H - ov * t), (-ov, -P - 60, H - ov * t), (xm, -P - 60, zr), (xm, Dy + 50, zr)], (0, -P, Wx, Dy))
    C.roof([(Wx + ov, -P - 60, H - ov * t), (Wx + ov, Dy + 50, H - ov * t), (xm, Dy + 50, zr), (xm, -P - 60, zr)],
           (0, -P, Wx, Dy))
    C.vwall("wood", [(0, Dy, H), (xm, Dy, zr - 13), (Wx, Dy, H)], 12, (0, -1))
    # جدارين زجاج مائلين بالمسقط يلتقون عند رأس البروز — أعلى كل جدار يتبع ميل السقف
    for xa, sgn in ((0, 1), (Wx, -1)):
        pts = [(xa, 0, 0), (xm, -P, 0), (xm, -P, zr - 14), (xa, 0, H - 2)]
        M.S.poly("glass", pts + [(x, y + 2, z) for x, y, z in pts],
                 [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
        for f in (0.33, 0.66):
            x = xa + (xm - xa) * f
            y = -P * f
            z1 = H + (x if x <= xm else Wx - x) * t - 14 if False else H + min(x, Wx - x) * t - 14
            M.S.box("frame", x - 4, y - 4, 0, x + 4, y + 4, z1)
    M.S.box("frame", xm - 5, -P - 5, 0, xm + 5, -P + 5, zr - 14)
    M.window(("x", 0, -1), 300, 460, 90, 210)
    M.window(("x", Wx, 1), 300, 460, 90, 210)
    M.deck(-150, -P - 150, Wx + 150, -P + 30, 0, rail_sides="", stairs=None)


@concept("S07", "رباعي غير متماثل يغطي التراس", "الميل الأمامي طويل ينزل فوق التراس على أعمدة، والخلفي أقصر — ظل كبير بسقف واحد")
def s07(M, C):
    hh, dep = 300, 260
    M.base(0, -dep, W, D)
    M.block(0, 0, W, D, 0, hh)
    tb = math.tan(math.radians(40))
    yr, a = 380, 260
    zr = hh + (D - yr) * tb
    ov = 50
    zf = 245                                  # منسوب الرفرف الأمامي فوق التراس
    zb = hh - ov * tb
    yf = -dep - 30
    C.roof([(-ov, yf, zf), (W + ov, yf, zf), (W - a, yr, zr), (a, yr, zr)], (0, -dep, W, D))
    C.roof([(W + ov, D + ov, zb), (-ov, D + ov, zb), (a, yr, zr), (W - a, yr, zr)], (0, -dep, W, D))
    C.roof([(-ov, D + ov, zb), (-ov, yf, zf), (a, yr, zr)], (0, -dep, W, D))
    C.roof([(W + ov, yf, zf), (W + ov, D + ov, zb), (W - a, yr, zr)], (0, -dep, W, D))
    tf = (zr - zf) / (yr - yf)
    for x in (10, W / 3, 2 * W / 3, W - 10):
        M.post(x, -dep + 12, 0, zf + (-dep + 12 - yf) * tf - 12, 16)
    front(M, deck=False)
    M.S.box("wood", 0, -dep, -20, W, 0, 0)
    for x in range(0, W, 225):
        pass


@concept("S08", "جملونين متدرجين", "جملون عالي فوق الصالة وجملون أوطى فوق الغرف بنفس الاتجاه — كتلة متحركة وسهلة التنفيذ")
def s08(M, C):
    xs = 540
    M.base(0, 0, W, D)
    M.block(0, 0, xs, D, 0, 320)
    M.block(xs, 40, W, D - 40, 0, 260)
    gable_y(C, 0, D, 0, xs, 320, 32, 60, 50)
    t = math.tan(math.radians(32))
    ym = D / 2
    ze2, zr2 = 260 - 50 * t, 260 + (ym - 40) * t
    C.roof([(xs, -10, ze2), (W + 50, -10, ze2), (W + 50, ym, zr2), (xs, ym, zr2)], (xs, 40, W, D - 40))
    C.roof([(W + 50, D + 10, ze2), (xs, D + 10, ze2), (xs, ym, zr2), (W + 50, ym, zr2)], (xs, 40, W, D - 40))
    C.vwall("wood", [(W, 40, 260), (W, ym, zr2 - 13), (W, D - 40, 260)], 12, (-1, 0))
    M.window(("y", 0, -1), 60, xs - 60, 0, 240)
    for k in range(1, 4):
        xx = 60 + (xs - 120) * k / 4
        M.S.box("frame", xx - 3, -2, 0, xx + 3, 1.5, 240)
    C.vwall("glass", [(60, -1, 330), (xs / 2, -1, 320 + xs / 2 * t - 30), (xs - 60, -1, 330)], 3, (0, 1))
    M.window(("y", 40, -1), xs + 90, W - 90, 90, 210)
    M.window(("x", W, 1), 220, 380, 90, 210)
    M.deck(0, -200, xs, 0, 0, rail_sides="W", stairs=("S", 120, 420))


@concept("S09", "شاليه جبلي بشرفة علوية", "جملون حاد 40° ورفرف 1.2 م وشرفة خشب على الواجهة العلوية — طابع شاليهات الجبال")
def s09(M, C):
    Wx, Dy = 700, 800
    hh = 300
    M.base(0, 0, Wx, Dy)
    M.block(0, 0, Wx, Dy, 0, hh)
    zr = gable_y(C, 0, Dy, 0, Wx, hh, 40, 90, 120)
    M.window(("y", 0, -1), 200, 500, 0, 240)
    M.window(("y", 0, -1), 60, 160, 90, 210)
    M.window(("y", 0, -1), 540, 640, 90, 210)
    M.window(("y", 0, -1), 250, 450, hh + 30, hh + 240, door=True)
    M.deck(120, -120, 580, 0, hh + 10, rail_sides="SEW", upper=True)
    for x in (140, 560):
        C.brace(x, 0, hh - 10, 0, -1, 110)
    t = math.tan(math.radians(40))
    for k in range(1, 6):                       # زخرفة حافة الجملون
        pass
    M.window(("x", 0, -1), 300, 460, 90, 210)
    M.window(("x", Wx, 1), 300, 460, 90, 210)
    M.deck(0, -300, Wx, -120, 0, rail_sides="EW", stairs=("S", 200, 500))


@concept("S10", "جناح مثمن", "كوخ مثمن بسقف ثماني الأضلاع لقمة وحدة — منظر من كل الجهات وتصريف مثالي")
def s10(M, C):
    R = 400                                   # نصف القطر للزوايا
    cx, cy = R, R
    pts = [(cx + R * math.cos(math.radians(22.5 + 45 * k)), cy + R * math.sin(math.radians(22.5 + 45 * k)))
           for k in range(8)]
    M.S.box("slab", 0, 0, -20, 2 * R, 2 * R, 0)
    for k in range(8):
        (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % 8]
        L = math.hypot(x1 - x0, y1 - y0)
        nx, ny = (y1 - y0) / L, -(x1 - x0) / L
        C.vwall("wood", [(x0, y0, 0), (x1, y1, 0), (x1, y1, H), (x0, y0, H)], 12, (-nx, -ny))
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        mid = (mx, my)
        if k in (5, 6, 7, 0, 4):
            wv = 0.32 * L
            g0 = (mx - (x1 - x0) / L * wv + nx * 1, my - (y1 - y0) / L * wv + ny * 1)
            g1 = (mx + (x1 - x0) / L * wv + nx * 1, my + (y1 - y0) / L * wv + ny * 1)
            z0, z1 = (0, 235) if k == 6 else (80, 220)
            q = [(g0[0], g0[1], z0), (g1[0], g1[1], z0), (g1[0], g1[1], z1), (g0[0], g0[1], z1)]
            M.S.poly("glass", q + [(x + nx * 2, y + ny * 2, z) for x, y, z in q],
                     [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    t = math.tan(math.radians(30))
    ov = 70
    zr = H + R * math.cos(math.radians(22.5)) * t
    k_ = (R + ov / math.cos(math.radians(22.5))) / R
    ze = H - ov * t
    for k in range(8):
        (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % 8]
        C.roof([(cx + (x0 - cx) * k_, cy + (y0 - cy) * k_, ze), (cx + (x1 - cx) * k_, cy + (y1 - cy) * k_, ze), (cx, cy, zr)],
               (cx - R * 0.65, cy - R * 0.65, cx + R * 0.65, cy + R * 0.65))   # مربع داخل المثمن
    M.deck(cx - 200, -180, cx + 200, 60, 0, rail_sides="EW", stairs=("S", 100, 300))


# ------------------------------------------------------------ فحص التصريف
def drainage_issues(C):
    """يرجع قائمة مشاكل: سطح ميله أقل من 20°، أو أوطى حافة داخل الجدران اللي يغطيها (مويه تتجمع)."""
    out = []
    for pts, (x0, y0, x1, y1) in C.planes:
        p = [tuple(map(float, v)) for v in pts]
        a, b, c = p[0], p[1], p[2]
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        L = math.sqrt(sum(k * k for k in n)) or 1
        pitch = math.degrees(math.acos(abs(n[2]) / L))
        if pitch < MIN_PITCH - 0.5:
            out.append(f"ميل {pitch:.0f}° أقل من {MIN_PITCH}°")
        zmin = min(q[2] for q in p)
        low = [q for q in p if q[2] - zmin < 1]
        mx, my = sum(q[0] for q in low) / len(low), sum(q[1] for q in low) / len(low)
        if x0 + 1 < mx < x1 - 1 and y0 + 1 < my < y1 - 1:
            out.append("أوطى حافة داخل الجدران — مويه تتجمع")
    return out


def build(code, style):
    c = next(c for c in CONCEPTS if c["code"] == code)
    M = Maker(style)
    for m, col in (("metal_roof", "#33373A"), ("green_roof", "#5E7D3A")):
        M.S.material(m, col)
    C = Ctx(M, c["roof"])
    c["fn"](M, C)
    return M.S, drainage_issues(C)


# ============================================================ أفكار سقف لعميل الدورين 120 م²
# الكتلة: 7.80 × 7.70 م لكل دور (60.06 × 2 = 120.1 م²) + تراس أرضي وبلكونة علوية 7.80 × 2.40 (مجاناً خارج المساحة)
CW, CD, H1, LV2, H2 = 780, 770, 280, 305, 585
TD = 240
CLIENT = []


def client_idea(code, ar, note):
    def deco(fn):
        CLIENT.append({"code": code, "ar": ar, "note": note, "fn": fn, "roof": "roof_tiles"})
        return fn
    return deco


def _client_mass(M, C):
    M.S.box("slab", -10, -TD - 10, -20, CW + 10, CD + 10, 0)
    M.block(0, 0, CW, CD, 0, H1)
    M.S.box("trim", -3, -3, H1, CW + 3, CD + 3, LV2)          # حزام بين الدورين
    M.block(0, 0, CW, CD, LV2, H2)
    # الواجهة الأمامية (نفس مخطط العميل)
    for a, b in ((60, 200), (568, 708)):
        M.window(("y", 0, -1), a, b, 30, 240)
    M.window(("y", 0, -1), 234, 534, 0, 265)
    for x in (334, 434):
        M.S.box("frame", x - 3, -2, 0, x + 3, 1.5, 265)
    M.window(("y", 0, -1), 30, 130, LV2 + 30, LV2 + 240)
    M.window(("y", 0, -1), 150, 390, LV2, LV2 + 240)
    # الجوانب والخلف
    M.window(("x", CW, 1), 120, 240, 110, 210)
    M.window(("x", CW, 1), 60, 120, LV2 + 150, LV2 + 210)
    M.window(("x", CW, 1), 520, 620, LV2 + 100, LV2 + 210)
    for a, b, z0 in ((560, 680, 100), (120, 280, 90), (560, 680, LV2 + 100), (120, 240, LV2 + 100)):
        M.window(("x", 0, -1), a, b, z0, z0 + 115)
    # التراس الأرضي + البلكونة العلوية (درابزين 105)
    M.deck(0, -TD, CW, 0, 0, rail_sides="EW", stairs=("S", 250, 530))
    M.S.box("wood", 0, -TD, LV2 - 25, CW, 0, LV2)
    for sd in (((CW, -TD), (0, -TD)), ((0, -TD), (0, 0)), ((CW, 0), (CW, -TD))):
        M.railing(*sd, LV2, upper=True)
    for x in (9, CW - 9):
        M.post(x, -TD + 9, 0, H2, 18)


def _kick_ring(C, rect, z, dv, pitch, cover):
    x0, y0, x1, y1 = rect
    t = math.tan(math.radians(pitch))
    o = [(x0 - dv, y0 - dv), (x1 + dv, y0 - dv), (x1 + dv, y1 + dv), (x0 - dv, y1 + dv)]
    i_ = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for k in range(4):
        (a0, b0), (a1, b1) = o[k], o[(k + 1) % 4]
        (u1, v1), (u0, v0) = i_[(k + 1) % 4], i_[k]
        C.roof([(a0, b0, z - dv * t), (a1, b1, z - dv * t), (u1, v1, z), (u0, v0, z)], cover)


@client_idea("C1", "رباعي بكسرة الحافة يغطي البلكونة",
             "سقف رباعي 30° بكسرة ناعمة 20° عند الرفرف، يمتد فوق البلكونة على عمودين — المويه تنزل من الأربع جهات")
def c1(M, C):
    _client_mass(M, C)
    M.S.box("trim", -10, -TD, H2 - 22, CW + 10, -TD + 16, H2)
    rect = (0, -TD, CW, CD)
    hip_planes(C, *rect, H2, 30, 0, cover=rect)
    _kick_ring(C, rect, H2, 80, 20, rect)


@client_idea("C2", "شاليه بقمة مشطوفة وواجهة زجاج",
             "جملون 38° واجهته على التراس، قمته مقصوصة بميل صغير، زجاج بإطار أسود تحت القص ورفرف عميق على كوابيل")
def c2(M, C):
    _client_mass(M, C)
    t = math.tan(math.radians(38))
    ov, ove = 70, 60
    xm = CW / 2
    y0, y1 = -TD, CD
    ze, zr = H2 - ov * t, H2 + xm * t
    zc = H2 + xm * t * 0.62
    xc = -ov + (zc - ze) / t
    th = math.tan(math.radians(55))
    dy = (zr - zc) / th - ove
    rect = (0, -TD, CW, CD)
    C.roof([(-ov, y1 + ove, ze), (-ov, y0 - ove, ze), (xc, y0 - ove, zc), (xm, y0 + dy, zr), (xm, y1 - dy, zr), (xc, y1 + ove, zc)], rect)
    xc2 = CW - xc
    C.roof([(CW + ov, y0 - ove, ze), (CW + ov, y1 + ove, ze), (xc2, y1 + ove, zc), (xm, y1 - dy, zr), (xm, y0 + dy, zr), (xc2, y0 - ove, zc)], rect)
    C.roof([(xc, y0 - ove, zc), (xc2, y0 - ove, zc), (xm, y0 + dy, zr)], rect)
    C.roof([(xc2, y1 + ove, zc), (xc, y1 + ove, zc), (xm, y1 - dy, zr)], rect)
    x1_ = (zc - H2) / t
    # واجهة زجاج مثلثية مقصوصة فوق البلكونة (على جدار الدور الأول) + الخلف خشب
    C.vwall("glass", [(0, -1, H2), (x1_, -1, zc - 16), (CW - x1_, -1, zc - 16), (CW, -1, H2)], 3, (0, 1))
    for x in (x1_, CW / 3, 2 * CW / 3, CW - x1_):
        z1 = min(H2 + min(x, CW - x) * t, zc) - 16
        M.S.box("frame", x - 4, -3, H2, x + 4, 2, z1)
    M.S.box("frame", 0, -3, H2 - 4, CW, 2, H2 + 4)
    M.S.box("frame", x1_, -3, zc - 22, CW - x1_, 2, zc - 14)
    C.vwall("wood", [(0, CD, H2), (x1_, CD, zc - 13), (CW - x1_, CD, zc - 13), (CW, CD, H2)], 12, (0, -1))
    M.S.box("trim", -10, -TD, H2 - 22, CW + 10, -TD + 16, H2)
    for x in (0, CW):
        for y in (-TD + 60, CD - 60):
            C.brace(x, y, H2 - 5, -1 if x == 0 else 1, 0, 80)


@client_idea("C3", "باغودا: رباعي فوق ومظلة بين الدورين",
             "رباعي 30° فوق الدور الأول والبلكونة، ومظلة مائلة 22° تلف الدور الأرضي من ثلاث جهات — شكل طبقتين فخم وحماية للجدران")
def c3(M, C):
    _client_mass(M, C)
    M.S.box("trim", -10, -TD, H2 - 22, CW + 10, -TD + 16, H2)
    rect = (0, -TD, CW, CD)
    hip_planes(C, *rect, H2, 30, 70, cover=rect)
    t = math.tan(math.radians(22))
    dv, z = 90, H1 + 15
    for pts in ([(CW + dv, 0, z - dv * t), (CW + dv, CD + dv, z - dv * t), (CW, CD, z), (CW, 0, z)],
                [(CW + dv, CD + dv, z - dv * t), (-dv, CD + dv, z - dv * t), (0, CD, z), (CW, CD, z)],
                [(-dv, CD + dv, z - dv * t), (-dv, 0, z - dv * t), (0, 0, z), (0, CD, z)]):
        C.roof(pts, (0, 0, CW, CD))


def build_client(code, style):
    c = next(c for c in CLIENT if c["code"] == code)
    M = Maker(style)
    C = Ctx(M, c["roof"])
    c["fn"](M, C)
    return M.S, drainage_issues(C)
