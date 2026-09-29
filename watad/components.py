"""مكتبة أشكال الشبابيك والأبواب — كل عنصر له رمز (W.. / D..) ويُرسم على قطعة جدار."""
import math

from .model import Wall
from .model3d import Scene

T = 12            # سماكة الجدار
FACE = -T / 2     # وجه الجدار الخارجي (s)


def _scene(style):
    S = Scene()
    for m, c in (("wood", style["wood"]), ("trim", style["trim"]), ("frame", style["frame"]),
                 ("door", style["frame"]), ("slab", style["slab"])):
        S.material(m, c)
    S.material("glass", style["glass"])
    S.material("frosted", "#C9D3D8")
    S.material("metal", "#2A2A2A")
    return S


def _circle(cx, cz, r, n=32, a0=0, a1=2 * math.pi):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cz + r * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(n + (0 if a1 - a0 >= 2 * math.pi - 1e-9 else 1))]


def _grow(pts, d):
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    out = []
    for x, z in pts:
        L = math.hypot(x - cx, z - cz) or 1
        out.append((x + (x - cx) / L * d, z + (z - cz) / L * d))
    return out


class Patch:
    """قطعة جدار مع أدوات رسم العناصر البارزة عن وجه التلبيس."""

    def __init__(self, style, width=260, height=280, gable=False):
        self.S = _scene(style)
        self.w = Wall("p", (0, 0), (width, 0))
        self.W, self.H = width, height
        self.S.box("slab", -15, -20, -20, width + 15, 20, 0)
        self.S.wbox("wood", self.w, 0, width, -T / 2, T / 2, 0, height)
        if gable:
            self.S.wprism("wood", self.w, [(0, height), (width, height), (width / 2, height + width * 0.45)],
                          -T / 2, T / 2)

    def rect(self, mat, a, b, z0, z1, d0, d1):
        self.S.wbox(mat, self.w, a, b, FACE - d1, FACE - d0, z0, z1)

    def poly(self, mat, pts, d0, d1):
        self.S.wprism(mat, self.w, pts, FACE - d1, FACE - d0)

    def framed(self, a, b, z0, z1, fw=6, glass="glass", trim=True):
        if trim:
            self.rect("trim", a - fw - 7, b + fw + 7, z0 - fw - 7, z1 + fw + 7, 0, 1.5)
        self.rect("frame", a - fw, b + fw, z0 - fw, z1 + fw, 0, 3)
        self.rect(glass, a, b, z0, z1, 3, 3.6)

    def bars(self, a, b, z0, z1, nv=0, nh=0, bw=4, mat="frame"):
        for i in range(1, nv + 1):
            x = a + (b - a) * i / (nv + 1)
            self.rect(mat, x - bw / 2, x + bw / 2, z0, z1, 3.4, 5)
        for j in range(1, nh + 1):
            z = z0 + (z1 - z0) * j / (nh + 1)
            self.rect(mat, a, b, z - bw / 2, z + bw / 2, 3.4, 5)

    def framed_poly(self, pts, fw=6, glass="glass"):
        self.poly("trim", _grow(pts, fw + 7), 0, 1.5)
        self.poly("frame", _grow(pts, fw), 0, 3)
        self.poly(glass, pts, 3, 3.6)


WINDOWS, DOORS = [], []


def item(lst, code, ar, note=""):
    def deco(fn):
        lst.append({"code": code, "ar": ar, "note": note, "fn": fn})
        return fn
    return deco


# ------------------------------------------------------------------ الشبابيك
@item(WINDOWS, "W01", "ثابت بانورامي", "زجاج واحد بدون فتح — للإطلالات")
def w01(p):
    p.framed(50, 210, 80, 220)


@item(WINDOWS, "W02", "ضلفتين مفصلي", "الأكثر استخداماً في مشاريع المصنع")
def w02(p):
    p.framed(70, 190, 90, 210)
    p.bars(70, 190, 90, 210, nv=1, bw=6)


@item(WINDOWS, "W03", "منزلق (سحاب)", "ضلفتين تنزلق — ما تاخذ مساحة")
def w03(p):
    p.framed(60, 200, 90, 210, glass="glass")
    p.rect("frame", 128, 134, 90, 210, 3, 6)
    p.rect("frame", 60, 134, 90, 96, 3, 6)
    p.rect("frame", 128, 200, 204, 210, 3, 6)


@item(WINDOWS, "W04", "بتقسيمات (كولونيال)", "شبكة 2×3 — طابع ريفي كلاسيكي (مثل صورة 5)")
def w04(p):
    p.framed(75, 185, 80, 215)
    p.bars(75, 185, 80, 215, nv=1, nh=2)


@item(WINDOWS, "W05", "حمام صغير مصنفر", "60×60 زجاج مصنفر للخصوصية")
def w05(p):
    p.framed(100, 160, 160, 220, glass="frosted")


@item(WINDOWS, "W06", "طولي ضيق", "شرائح رأسية — تناسب الدرج والممرات")
def w06(p):
    for a in (70, 150):
        p.framed(a, a + 40, 50, 230)


@item(WINDOWS, "W07", "عريض ثلاث ضلف", "للصالات — واجهة كبيرة")
def w07(p):
    p.framed(25, 235, 90, 210)
    p.bars(25, 235, 90, 210, nv=2, bw=6)


@item(WINDOWS, "W08", "مثلث في الجملون", "يتبع شكل الجملون فوق الجدار")
def w08(p):
    H = p.H
    p.framed_poly([(70, H + 12), (190, H + 12), (130, H + 12 + 60 * 0.9)])
    p.framed(80, 180, 100, 200)


@item(WINDOWS, "W09", "مائل مع الميل (شبه منحرف)", "يتبع ميل السقف (مثل صورة 3)")
def w09(p):
    p.framed_poly([(60, 60), (200, 60), (200, 170), (60, 240)])
    p.rect("frame", 127, 133, 60, 205, 3.4, 5)


@item(WINDOWS, "W10", "دائري", "شباك زخرفي للجملون أو الحمام")
def w10(p):
    p.framed_poly(_circle(130, 170, 45))
    p.rect("frame", 128, 132, 125, 215, 3.4, 5)
    p.rect("frame", 85, 175, 168, 172, 3.4, 5)


@item(WINDOWS, "W11", "قوس علوي", "مستطيل بقوس نصف دائري")
def w11(p):
    pts = [(180, 80), (180, 170)] + _circle(130, 170, 50, 24, 0, math.pi)[1:-1] + [(80, 170), (80, 80)]
    p.framed_poly(pts)
    p.rect("frame", 127, 133, 80, 218, 3.4, 5)


@item(WINDOWS, "W12", "شريطي علوي", "شباك عالي عريض — إضاءة مع خصوصية")
def w12(p):
    p.framed(30, 230, 190, 235)
    p.bars(30, 230, 190, 235, nv=3, bw=5)


@item(WINDOWS, "W13", "مع شيش خشب", "ضلفتين شيش جانبية زخرفية")
def w13(p):
    p.framed(85, 175, 90, 210)
    p.bars(85, 175, 90, 210, nv=1, nh=1)
    for a, b in ((33, 76), (184, 227)):
        p.rect("trim", a, b, 84, 216, 0, 3)
        for z in range(92, 210, 10):
            p.rect("frame", a + 4, b - 4, z, z + 4, 3, 4.5)


@item(WINDOWS, "W14", "زاوية (L)", "شباكين متلاقيين عند الزاوية — منظر أوسع", )
def w14(p):
    p.framed(120, 250, 90, 210, trim=False)
    p.bars(120, 250, 90, 210, nv=1, bw=6)


# ------------------------------------------------------------------ الأبواب
def _door_frame(p, a, b, h=210, fw=7):
    p.rect("trim", a - fw - 7, b + fw + 7, 0, h + fw + 7, 0, 1.5)
    p.rect("frame", a - fw, b + fw, 0, h + fw, 0, 3)


@item(DOORS, "D01", "خشب بحشوات", "باب داخلي/خارجي كلاسيكي")
def d01(p):
    _door_frame(p, 85, 175)
    p.rect("door", 85, 175, 0, 210, 3, 5)
    for z0, z1 in ((20, 95), (115, 195)):
        for a, b in ((93, 126), (134, 167)):
            p.rect("trim", a, b, z0, z1, 5, 6.5)
    p.rect("metal", 163, 168, 100, 110, 5, 8)


@item(DOORS, "D02", "ألواح رأسية ريفي", "ألواح خشب مع مربوع Z")
def d02(p):
    _door_frame(p, 85, 175)
    for i in range(6):
        p.rect("door", 85 + i * 15, 85 + i * 15 + 14, 0, 210, 3, 5)
    p.rect("trim", 88, 172, 30, 40, 5, 7)
    p.rect("trim", 88, 172, 170, 180, 5, 7)
    p.S.wdiag("trim", p.w, 92, 40, 168, 170, 10, FACE - 7, FACE - 5)
    p.rect("metal", 163, 168, 100, 110, 7, 10)


@item(DOORS, "D03", "نص زجاج", "زجاج فوق وحشوة تحت")
def d03(p):
    _door_frame(p, 85, 175)
    p.rect("door", 85, 175, 0, 210, 3, 5)
    p.rect("glass", 97, 163, 110, 195, 5, 5.5)
    p.rect("trim", 97, 163, 20, 90, 5, 6.5)
    p.rect("metal", 163, 168, 100, 110, 5, 8)


@item(DOORS, "D04", "فرنسي مفرد", "زجاج بتقسيمات كامل")
def d04(p):
    _door_frame(p, 85, 175)
    p.rect("door", 85, 175, 0, 210, 3, 4)
    p.rect("glass", 95, 165, 12, 198, 4, 4.5)
    p.bars(95, 165, 12, 198, nv=1, nh=3, mat="door")


@item(DOORS, "D05", "فرنسي مزدوج", "ضلفتين زجاج بتقسيمات (مثل صورة 2)")
def d05(p):
    _door_frame(p, 60, 200)
    p.rect("door", 60, 200, 0, 210, 3, 4)
    for a in (70, 135):
        p.rect("glass", a, a + 55, 12, 198, 4, 4.5)
        p.bars(a, a + 55, 12, 198, nv=1, nh=3, mat="door")


@item(DOORS, "D06", "مزدوج خشب مصمت", "مدخل رئيسي فخم")
def d06(p):
    _door_frame(p, 60, 200)
    for a, b in ((60, 129), (131, 200)):
        p.rect("door", a, b, 0, 210, 3, 5)
        for z0, z1 in ((20, 95), (115, 195)):
            p.rect("trim", a + 10, b - 10, z0, z1, 5, 6.5)
    p.rect("metal", 122, 127, 95, 125, 5, 8)
    p.rect("metal", 133, 138, 95, 125, 5, 8)


@item(DOORS, "D07", "منزلق زجاج", "سحاب كبير على الجلسة")
def d07(p):
    _door_frame(p, 30, 230, 215)
    p.rect("glass", 30, 230, 0, 215, 3, 3.6)
    p.rect("frame", 126, 134, 0, 215, 3, 7)
    p.rect("frame", 30, 230, 0, 8, 3, 7)


@item(DOORS, "D08", "مخزن منزلق (بارن)", "باب على سكة ظاهرة مع X")
def d08(p):
    p.rect("metal", 20, 240, 222, 228, 0, 3)
    a, b = 90, 200
    for i in range(7):
        p.rect("door", a + i * 15.7, a + i * 15.7 + 15, 0, 218, 3, 5)
    p.rect("trim", a, b, 0, 12, 5, 7)
    p.rect("trim", a, b, 206, 218, 5, 7)
    p.rect("trim", a, a + 12, 0, 218, 5, 7)
    p.rect("trim", b - 12, b, 0, 218, 5, 7)
    p.S.wdiag("trim", p.w, a + 8, 10, b - 8, 208, 10, FACE - 7, FACE - 5)
    p.S.wdiag("trim", p.w, a + 8, 208, b - 8, 10, 10, FACE - 8.5, FACE - 7)


@item(DOORS, "D09", "مع شباك جانبي", "باب + زجاج ثابت على الجانب")
def d09(p):
    _door_frame(p, 60, 200)
    p.rect("door", 60, 150, 0, 210, 3, 5)
    p.rect("glass", 72, 138, 120, 195, 5, 5.5)
    p.rect("frame", 150, 156, 0, 210, 3, 5)
    p.rect("glass", 156, 200, 0, 210, 3, 3.6)
    p.rect("metal", 138, 143, 100, 110, 5, 8)


@item(DOORS, "D10", "مع شباك علوي", "باب + زجاج ثابت فوقه (ضوء إضافي)")
def d10(p):
    _door_frame(p, 85, 175, 255)
    p.rect("door", 85, 175, 0, 210, 3, 5)
    p.rect("frame", 85, 175, 210, 216, 3, 5)
    p.rect("glass", 85, 175, 216, 255, 3, 3.6)
    p.rect("trim", 97, 163, 20, 195, 5, 6.5)
    p.rect("metal", 163, 168, 100, 110, 5, 8)


@item(DOORS, "D11", "حمام بفتحات تهوية", "شرائح تهوية أسفل الباب")
def d11(p):
    _door_frame(p, 90, 170)
    p.rect("door", 90, 170, 0, 210, 3, 5)
    for z in range(15, 60, 8):
        p.rect("frame", 98, 162, z, z + 4, 5, 6.5)
    p.rect("trim", 98, 162, 80, 195, 5, 6.5)
    p.rect("metal", 158, 163, 100, 110, 5, 8)


@item(DOORS, "D12", "قوس علوي", "باب خشب بقوس — طابع تراثي")
def d12(p):
    pts = [(175, 0), (175, 175)] + _circle(130, 175, 45, 24, 0, math.pi)[1:-1] + [(85, 175), (85, 0)]
    p.poly("trim", [(x + (8 if x > 130 else -8 if x < 130 else 0), z + (8 if z > 175 else 0)) for x, z in pts], 0, 1.5)
    p.poly("door", pts, 0, 5)
    for i in range(1, 6):
        x = 85 + i * 15
        p.rect("trim", x - 0.8, x + 0.8, 0, 175 + (45 ** 2 - (x - 130) ** 2) ** 0.5 - 4, 5, 5.6)
    p.rect("metal", 163, 168, 100, 110, 5, 8)


def build(item_, style):
    gable = item_["code"] == "W08"
    p = Patch(style, height=200 if gable else 280, gable=gable)
    if item_["code"] == "W14":      # زاوية: جدار ثاني عمودي
        w2 = Wall("p2", (260, 0), (260, 200))
        p.S.wbox("wood", w2, 0, 200, -T / 2, T / 2, 0, 280)
        p.S.wbox("frame", w2, 0, 110, -T / 2 - 3, -T / 2, 84, 216)
        p.S.wbox("glass", w2, 0, 104, -T / 2 - 3.6, -T / 2 - 3, 90, 210)
    item_["fn"](p)
    return p.S
