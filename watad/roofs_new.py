"""أشكال أسقف جديدة (غير الجملون) — مفاهيم للعرض والاختيار قبل اعتمادها في المحرك.

كل نموذج على نفس الكوخ القياسي 9.00 × 6.00 م (الواجهة الأمامية y=0 جنوب) عشان المقارنة عادلة.
الوحدات سم. تُرندر واقعياً بـ tools/roof_concepts.py.
"""
import math

from .catalog import Maker

W, D, H, O = 900, 600, 280, 50
CONCEPTS = []


def concept(code, ar, note, roof_mat="metal_roof"):
    def deco(fn):
        CONCEPTS.append({"code": code, "ar": ar, "note": note, "fn": fn, "roof": roof_mat})
        return fn
    return deco


# ------------------------------------------------------------ أدوات
def prism(M, mat, pts, th, down=True):
    """مجسم من مضلع مستوٍ محدب (سطح علوي) بسماكة th للأسفل (down) أو للأعلى."""
    n = len(pts)
    other = [(x, y, z - th if down else z + th) for x, y, z in pts]
    faces = [tuple(range(n)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    M.S.poly(mat, list(pts) + other, faces)


def roof(M, pts, mat):
    """لوح سقف: تطبيق خشب 12 سم من تحت + طبقة التغطية 4 سم فوق."""
    prism(M, "trim", pts, 12)
    prism(M, mat, pts, 4, down=False)


def vwall(M, mat, pts, t=12, axis="x"):
    """حشوة جدار رأسية (مضلع محدب في مستوى x=ثابت أو y=ثابت) بسماكة t للداخل."""
    n = len(pts)
    if axis == "x":
        x = pts[0][0]
        sg = 1 if x < W / 2 else -1
        other = [(px + sg * t, py, pz) for px, py, pz in pts]
    else:
        y = pts[0][1]
        sg = 1 if y < D / 2 else -1
        other = [(px, py + sg * t, pz) for px, py, pz in pts]
    faces = [tuple(range(n)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    M.S.poly(mat, list(pts) + other, faces)


def front_std(M, deck=True, h=H, big=False):
    """واجهة أمامية قياسية: باب زجاج سحاب + شبابيك، وتراس خشب بدرج."""
    if big:
        M.window(("y", 0, -1), 120, 780, 0, 240)
        for x in (340, 560):
            M.S.box("frame", x - 3, -2, 0, x + 3, 1.5, 240)
    else:
        M.window(("y", 0, -1), 330, 570, 0, 230, door=False)
        for a in (90, 650):
            M.window(("y", 0, -1), a, a + 160, 90, 220)
    M.window(("x", 0, -1), 220, 380, 90, 210)
    M.window(("x", W, 1), 220, 380, 90, 210)
    if deck:
        M.deck(0, -200, W, 0, 0, rail_sides="EW", stairs=("S", 300, 600))


def std_block(M, h=H):
    M.base(0, 0, W, D)
    M.block(0, 0, W, D, 0, h)


# ------------------------------------------------------------ النماذج
@concept("N01", "رباعي (هيب)", "أربع ميول تنزل على كل الجهات — شكل هادئ ومقاوم للرياح، رفرف على الأربع", "roof_tiles")
def n01(M):
    std_block(M)
    t = math.tan(math.radians(25))
    ze, zr = H - O * t, H + D / 2 * t
    a, b = (-O, -O), (W + O, D + O)
    roof(M, [(a[0], a[1], ze), (b[0], a[1], ze), (W - D / 2, D / 2, zr), (D / 2, D / 2, zr)], "roof_tiles")
    roof(M, [(b[0], b[1], ze), (a[0], b[1], ze), (D / 2, D / 2, zr), (W - D / 2, D / 2, zr)], "roof_tiles")
    roof(M, [(a[0], b[1], ze), (a[0], a[1], ze), (D / 2, D / 2, zr)], "roof_tiles")
    roof(M, [(b[0], a[1], ze), (b[0], b[1], ze), (W - D / 2, D / 2, zr)], "roof_tiles")
    front_std(M)


@concept("N02", "هرمي بفانوس زجاج", "هرم على مسقط مربع وفي قمته فانوس زجاج يدخل ضوء طبيعي لوسط الصالة", "roof_tiles")
def n02(M):
    S = 700
    M.base(0, 0, S, S)
    M.block(0, 0, S, S, 0, H)
    t = math.tan(math.radians(30))
    ze = H - O * t
    k = 75                                    # نص عرض الفانوس
    c = S / 2
    zt = H + (c - k) * t
    corners = [(-O, -O), (S + O, -O), (S + O, S + O), (-O, S + O)]
    top = [(c - k, c - k), (c + k, c - k), (c + k, c + k), (c - k, c + k)]
    for i in range(4):
        (x0, y0), (x1, y1) = corners[i], corners[(i + 1) % 4]
        (u1, v1), (u0, v0) = top[(i + 1) % 4], top[i]
        roof(M, [(x0, y0, ze), (x1, y1, ze), (u1, v1, zt), (u0, v0, zt)], "roof_tiles")
    M.S.box("glass", c - k + 4, c - k + 4, zt, c + k - 4, c + k - 4, zt + 70)
    for x in (c - k, c + k - 6):
        for y in (c - k, c + k - 6):
            M.S.box("frame", x, y, zt, x + 6, y + 6, zt + 70)
    tt = math.tan(math.radians(30))
    ze2, zt2 = zt + 70, zt + 70 + (k + 15) * tt
    cs = [(c - k - 15, c - k - 15), (c + k + 15, c - k - 15), (c + k + 15, c + k + 15), (c - k - 15, c + k + 15)]
    for i in range(4):
        (x0, y0), (x1, y1) = cs[i], cs[(i + 1) % 4]
        roof(M, [(x0, y0, ze2), (x1, y1, ze2), (c, c, zt2)], "roof_tiles")
    M.window(("y", 0, -1), 230, 470, 0, 230)
    M.window(("x", 0, -1), 270, 430, 90, 210)
    M.window(("x", S, 1), 270, 430, 90, 210)
    M.deck(0, -200, S, 0, 0, rail_sides="EW", stairs=("S", 200, 500))


@concept("N03", "مائل واحد عصري (سكيليون)", "ميل واحد يرتفع للواجهة — واجهة زجاج عالية وسقف داخلي مائل مرتفع")
def n03(M):
    M.base(0, 0, W, D)
    hf, hb = 400, H
    t = (hf - hb) / D
    M.block(0, 0, W, D, 0, hb)
    M.S.box("wood", 0, 0, hb, 12, D, hb + 1)
    for x in (0, W - 12):
        vwall(M, "wood", [(x, 0, hb), (x, 0, hf), (x, D, hb)], 12)
    M.S.box("wood", 0, 0, hb, W, 12, hf)
    roof(M, [(-O, -O, hf + O * t), (W + O, -O, hf + O * t), (W + O, D + O, hb - O * t), (-O, D + O, hb - O * t)],
         "metal_roof")
    front_std(M, big=True)
    for a in (60, 330, 600):                  # شبابيك علوية تحت الميل
        M.window(("y", 0, -1), a, a + 240, 270, 370)


@concept("N04", "فراشة (بترفلاي)", "ميلين للداخل يلتقون بقناة بالوسط — شكل لافت ويجمع مياه المطر من نقطة وحدة")
def n04(M):
    std_block(M)
    hi, lo = H + 110, H + 25
    t = (hi - lo) / (D / 2)
    M.S.box("wood", 0, 0, H, W, 12, hi)
    M.S.box("wood", 0, D - 12, H, W, D, hi)
    for x in (0, W - 12):
        vwall(M, "glass", [(x, 12, H), (x, 12, hi), (x, D / 2, lo), (x, D / 2, H)], 4)
        vwall(M, "glass", [(x, D / 2, H), (x, D / 2, lo), (x, D - 12, hi), (x, D - 12, H)], 4)
        M.S.box("frame", x, D / 2 - 4, H, x + 12, D / 2 + 4, lo)
        M.S.box("frame", x, 0, H - 4, x + 12, D, H + 2)
    roof(M, [(-O, -O, hi + O * t), (W + O, -O, hi + O * t), (W + O, D / 2, lo), (-O, D / 2, lo)], "metal_roof")
    roof(M, [(W + O, D + O, hi + O * t), (-O, D + O, hi + O * t), (-O, D / 2, lo), (W + O, D / 2, lo)], "metal_roof")
    front_std(M)
    for a in (60, 480):
        M.window(("y", 0, -1), a, a + 360, H + 10, hi - 12)


@concept("N05", "مائلين متقابلين بشريط زجاج (كليريستوري)", "سقفين على منسوبين وبينهم شريط زجاج علوي — إضاءة طبيعية عميقة للداخل")
def n05(M):
    std_block(M)
    t = math.tan(math.radians(15))
    m = D * 0.45
    hf = H + m * t
    hb = hf + 110
    tb = (hb - H) / (D - m)
    roof(M, [(-O, -O, H - O * t), (W + O, -O, H - O * t), (W + O, m + 15, hf + 15 * t), (-O, m + 15, hf + 15 * t)],
         "metal_roof")
    roof(M, [(-O, m - 20, hb + 20 * tb), (W + O, m - 20, hb + 20 * tb), (W + O, D + O, H - O * tb),
             (-O, D + O, H - O * tb)], "metal_roof")
    M.S.box("glass", 0, m - 2, hf - 12, W, m + 2, hb - 12)
    for x in range(0, W + 1, 150):
        M.S.box("frame", min(x, W - 6), m - 4, hf - 12, min(x, W - 6) + 6, m + 4, hb - 12)
    for x in (0, W - 12):
        vwall(M, "wood", [(x, 0, H), (x, m, hf), (x, m, H)], 12)
        vwall(M, "wood", [(x, m, H), (x, m, hb), (x, D, H)], 12)
    front_std(M)


@concept("N06", "مسطح ببرجولا خشب", "سقف مسطح بحافة (ستارة) وبرجولا خشب فوق التراس — طابع مودرن نظيف")
def n06(M):
    M.base(0, 0, W, D)
    M.block(0, 0, W, D, 0, 300)
    M.S.box("metal_roof", -30, -30, 300, W + 30, D + 30, 312)
    M.S.box("trim", -30, -30, 312, W + 30, D + 30, 340)
    M.S.box("metal_roof", -18, -18, 330, W + 18, D + 18, 342)
    M.deck(0, -300, W, 0, 0, rail_sides="", stairs=("S", 300, 600))
    for x in (0, W - 14):
        M.post(x + 7, -290, 0, 300, 14)
    M.S.box("trim", -20, -300, 290, W + 20, -284, 310)
    for x in range(0, W + 1, 45):
        M.S.box("trim", x - 3, -310, 300, x + 3, 0, 314)
    front_std(M, deck=False, big=True)


@concept("N07", "مقوس (برميلي)", "سقف منحني ناعم ونهايته الأمامية زجاج نص دائرة — شكل مميز ويتصنع من مدادات مقوسة")
def n07(M):
    std_block(M)
    R = 90                                     # ارتفاع القوس
    xs = [-O + (W + 2 * O) * i / 12 for i in range(13)]
    zc = lambda x: H + R * (1 - ((x - W / 2) / (W / 2 + O)) ** 2) - (O * 0.4 if False else 0)  # noqa: E731
    for xa, xb in zip(xs, xs[1:]):
        roof(M, [(xa, -O - 60, zc(xa)), (xb, -O - 60, zc(xb)), (xb, D + O, zc(xb)), (xa, D + O, zc(xa))],
             "metal_roof")
    arc = [(x, zc(x)) for x in xs if 0 <= x <= W]
    arc = [(0, H)] + [(x, z) for x, z in arc if 0 < x < W] + [(W, H)]
    for y, mat in ((0, "glass"), (D - 12, "wood")):
        pts = [(x, y, z - 13) for x, z in arc]
        vwall(M, mat, pts, 4 if mat == "glass" else 12, axis="y")
    for x in range(150, W, 150):
        M.S.box("frame", x - 3, -3, H, x + 3, 3, zc(x) - 13)
    M.S.box("frame", 0, -3, H - 3, W, 3, H + 3)
    front_std(M)


@concept("N08", "هولندي (جملون فوق رباعي)", "رباعي من تحت وجملون صغير فوق — يجمع فخامة الرباعي مع فتحة تهوية/شباك بالقمة", "roof_tiles")
def n08(M):
    std_block(M)
    t = math.tan(math.radians(28))
    ze, zr = H - O * t, H + (D / 2) * t
    xg = D / 4
    d = xg + O
    zg, yA, yB = ze + d * t, -O + d, D + O - d
    roof(M, [(-O, -O, ze), (W + O, -O, ze), (W - xg, yA, zg), (W - xg, D / 2, zr), (xg, D / 2, zr), (xg, yA, zg)],
         "roof_tiles")
    roof(M, [(W + O, D + O, ze), (-O, D + O, ze), (xg, yB, zg), (xg, D / 2, zr), (W - xg, D / 2, zr), (W - xg, yB, zg)],
         "roof_tiles")
    roof(M, [(-O, D + O, ze), (-O, -O, ze), (xg, yA, zg), (xg, yB, zg)], "roof_tiles")
    roof(M, [(W + O, -O, ze), (W + O, D + O, ze), (W - xg, yB, zg), (W - xg, yA, zg)], "roof_tiles")
    for x in (xg, W - xg - 8):
        vwall(M, "wood", [(x, yA, zg), (x, D / 2, zr - 4), (x, yB, zg)], 8)
    front_std(M)


@concept("N09", "منشاري (سو تووث)", "ثلاث سنون مائلة بزجاج رأسي — إضاءة شمالية ثابتة وشكل صناعي أنيق")
def n09(M):
    std_block(M)
    n, rise = 3, 130
    wt = W / n
    for k in range(n):
        x0, x1 = k * wt, (k + 1) * wt
        roof(M, [(x0, -O, H + rise), (x1 + (O if k == n - 1 else 0), -O, H - (O * rise / wt if k == n - 1 else 0)),
                 (x1 + (O if k == n - 1 else 0), D + O, H - (O * rise / wt if k == n - 1 else 0)), (x0, D + O, H + rise)],
             "metal_roof")
        M.S.box("glass", x0 - 2, 0, H, x0 + 2, D, H + rise - 12)
        for y in range(0, D + 1, 150):
            M.S.box("frame", x0 - 4, min(y, D - 6), H, x0 + 4, min(y, D - 6) + 6, H + rise - 12)
        for y in (0, D - 12):
            vwall(M, "wood", [(x0, y, H), (x0, y, H + rise - 12), (x1, y, H)], 12, axis="y")
    front_std(M)


@concept("N10", "مانسارد", "ميول حادة من كل الجهات وسطح مسطح فوقها — مساحة علوية كاملة تحت السقف", "roof_tiles")
def n10(M):
    std_block(M, 260)
    h0 = 260
    t = math.tan(math.radians(68))
    ins = 60
    zt = h0 + ins * t
    o = 25
    ze = h0 - o * t
    outer = [(-o, -o), (W + o, -o), (W + o, D + o), (-o, D + o)]
    inner = [(ins, ins), (W - ins, ins), (W - ins, D - ins), (ins, D - ins)]
    for i in range(4):
        (x0, y0), (x1, y1) = outer[i], outer[(i + 1) % 4]
        (u1, v1), (u0, v0) = inner[(i + 1) % 4], inner[i]
        roof(M, [(x0, y0, ze), (x1, y1, ze), (u1, v1, zt), (u0, v0, zt)], "roof_tiles")
    M.S.box("metal_roof", ins - 10, ins - 10, zt, W - ins + 10, D - ins + 10, zt + 8)
    M.S.box("trim", ins - 14, ins - 14, zt - 6, W - ins + 14, D - ins + 14, zt + 2)
    for c in (230, 670):                           # شبابيك بارزة (دورمر) على الميل الأمامي
        M.S.box("wood", c - 70, 5, h0, c + 70, 60, h0 + 150)
        M.S.box("roof_tiles", c - 80, -5, h0 + 150, c + 80, 62, h0 + 160)
        M.window(("y", 5, -1), c - 50, c + 50, h0 + 20, h0 + 130)
    front_std(M, h=260)


@concept("N11", "رباعي بمظلة محيطة (فرندة)", "رباعي فوق الكوخ ومظلة سقف تلف حوله على أعمدة — ظل من كل الجهات وجلسات خارجية", "roof_tiles")
def n11(M):
    M.base(-220, -220, W + 220, D + 220)
    M.block(0, 0, W, D, 0, 320)
    hh = 320
    t = math.tan(math.radians(27))
    zr = hh + D / 2 * t
    roof(M, [(-30, -30, hh - 30 * t), (W + 30, -30, hh - 30 * t), (W - D / 2, D / 2, zr), (D / 2, D / 2, zr)], "roof_tiles")
    roof(M, [(W + 30, D + 30, hh - 30 * t), (-30, D + 30, hh - 30 * t), (D / 2, D / 2, zr), (W - D / 2, D / 2, zr)], "roof_tiles")
    roof(M, [(-30, D + 30, hh - 30 * t), (-30, -30, hh - 30 * t), (D / 2, D / 2, zr)], "roof_tiles")
    roof(M, [(W + 30, -30, hh - 30 * t), (W + 30, D + 30, hh - 30 * t), (W - D / 2, D / 2, zr)], "roof_tiles")
    zv, dv = 270, 240
    tv = math.tan(math.radians(14))
    zo = zv - dv * tv
    o = [(-dv, -dv), (W + dv, -dv), (W + dv, D + dv), (-dv, D + dv)]
    i_ = [(0, 0), (W, 0), (W, D), (0, D)]
    for k in range(4):
        (x0, y0), (x1, y1) = o[k], o[(k + 1) % 4]
        (u1, v1), (u0, v0) = i_[(k + 1) % 4], i_[k]
        roof(M, [(x0, y0, zo), (x1, y1, zo), (u1, v1, zv), (u0, v0, zv)], "roof_tiles")
    for x in (-dv + 20, W / 2, W + dv - 20):
        for y in (-dv + 20, D + dv - 20):
            M.post(x, y, 0, zo - 12, 16)
    for y in (D / 2,):
        for x in (-dv + 20, W + dv - 20):
            M.post(x, y, 0, zo - 12, 16)
    M.S.box("wood", -dv, -dv, -20, W + dv, D + dv, 0)
    front_std(M, deck=False)


@concept("N12", "مطوي (أوريغامي)", "سقف متعرج بطيّات متتالية ونهاياته زجاج — تصميم فني جريء يلفت من بعيد")
def n12(M):
    std_block(M)
    n = 4
    wt = W / n
    zlo, zhi = H + 20, H + 150

    def z(x):
        k = (x / wt) % 2 if x >= 0 else 0
        return zlo + (zhi - zlo) * (k if k <= 1 else 2 - k)
    xs = [-O] + [k * wt for k in range(1, n)] + [W + O]
    xs = [k * wt for k in range(n + 1)]
    for a, b in zip(xs, xs[1:]):
        aa, bb = (a - O if a == 0 else a), (b + O if b == W else b)
        za = z(a) - (O * (zhi - zlo) / wt if a == 0 and z(a) == zlo else 0)
        roof(M, [(aa, -O - 40, z(a)), (bb, -O - 40, z(b)), (bb, D + O, z(b)), (aa, D + O, z(a))], "metal_roof")
        vwall(M, "glass", [(a, 0, H), (a, 0, z(a) - 13), (b, 0, z(b) - 13), (b, 0, H)], 4, axis="y")
        vwall(M, "wood", [(a, D - 12, H), (a, D - 12, z(a) - 13), (b, D - 12, z(b) - 13), (b, D - 12, H)], 12, axis="y")
        M.S.box("frame", a - 3, -3, H, a + 3, 3, z(a) - 13)
    for x in (0, W - 12):
        vwall(M, "wood", [(x, 0, H), (x, 0, z(x if x == 0 else W) - 13), (x, D, z(x if x == 0 else W) - 13), (x, D, H)], 12)
    M.S.box("frame", 0, -3, H - 3, W, 3, H + 3)
    front_std(M)


@concept("N13", "سقف أخضر مائل خفيف", "ميل خفيف مغطى بعشب/نباتات — عزل حراري ممتاز ومنظر طبيعي يندمج مع المزرعة", "green_roof")
def n13(M):
    M.base(0, 0, W, D)
    hf, hb = 330, H
    t = (hf - hb) / D
    M.block(0, 0, W, D, 0, hb)
    for x in (0, W - 12):
        vwall(M, "wood", [(x, 0, hb), (x, 0, hf), (x, D, hb)], 12)
    M.S.box("wood", 0, 0, hb, W, 12, hf)
    O2 = 80
    pts = [(-O2, -O2, hf + O2 * t), (W + O2, -O2, hf + O2 * t), (W + O2, D + O2, hb - O2 * t), (-O2, D + O2, hb - O2 * t)]
    prism(M, "trim", pts, 30)
    prism(M, "green_roof", [(x, y, z) for x, y, z in pts], 10, down=False)
    front_std(M, big=True)


@concept("N14", "مائل ممتد فوق التراس (كانتيليفر)", "ميل واحد يطلع فوق التراس بمسافة كبيرة بدون أعمدة بالوسط — ظل واسع وواجهة زجاج")
def n14(M):
    M.base(0, 0, W, D)
    hf, hb = 390, 300
    ext = 260
    t = (hf - hb) / D
    M.block(0, 0, W, D, 0, hb)
    for x in (0, W - 12):
        vwall(M, "wood", [(x, 0, hb), (x, 0, hf), (x, D, hb)], 12)
    M.S.box("wood", 0, 0, hb, W, 12, hf)
    pts = [(-40, -ext, hf + ext * t), (W + 40, -ext, hf + ext * t), (W + 40, D + 40, hb - 40 * t), (-40, D + 40, hb - 40 * t)]
    prism(M, "trim", pts, 22)
    prism(M, "metal_roof", pts, 4, down=False)
    for x in (10, W - 10):
        M.post(x, -ext + 20, 0, hf + (ext - 20) * t - 22, 14)
    M.deck(0, -ext, W, 0, 0, rail_sides="", stairs=("S", 250, 650))
    front_std(M, deck=False, big=True)
    for a in (60, 330, 600):
        M.window(("y", 0, -1), a, a + 240, 270, 370)


def build(code, style):
    c = next(c for c in CONCEPTS if c["code"] == code)
    M = Maker(style)
    for m, col in (("metal_roof", "#33373A"), ("green_roof", "#5E7D3A")):
        M.S.material(m, col)
    c["fn"](M)
    return M.S
