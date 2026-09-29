"""نموذج المشروع: جدران، فتحات، غرف، فرش، سقف. كل الأطوال بالسنتيمتر.

الإحداثيات: محور الجدار (centerline). +y = الشمال.
الجدران الخارجية تُكتب بعكس عقارب الساعة (جنوب ← شرق ← شمال ← غرب)
فيكون يسار الجدار = الداخل، وبداية الجدار = يسار الواجهة عند النظر من الخارج.
"""
import math
from dataclasses import dataclass, field

import yaml


@dataclass
class Opening:
    kind: str            # window | door
    offset: float        # من بداية الجدار (المحور) إلى الحافة الأقرب للفتحة الصافية
    width: float
    height: float
    sill: float = 0      # ارتفاع الجلسة من وجه الصبة (للأبواب = 0)
    code: str = ""       # ش1، ب2 ...
    name: str = ""
    swing: str = "left"  # جهة فتح الباب بالنسبة لاتجاه الجدار: left | right
    leaves: int = 1      # عدد الضلف (0 = فتحة بدون باب)
    style: str = ""      # sliding | fixed (للأبواب الزجاج)
    transom: float = 0   # ارتفاع قاطع أفقي (شباك علوي فوق الباب/الزجاج)

    def __post_init__(self):
        self.name = self.name or self.code


@dataclass
class Wall:
    name: str
    start: tuple
    end: tuple
    exterior: bool = True
    openings: list = field(default_factory=list)
    height: float = None
    title: str = ""      # اسم الواجهة (للخارجي)
    gable_glass: bool = False   # مثلث الجملون فوق هذا الجدار زجاج بدل خشب

    @property
    def length(self):
        return math.dist(self.start, self.end)

    @property
    def u(self):
        (x0, y0), (x1, y1) = self.start, self.end
        L = self.length
        return (x1 - x0) / L, (y1 - y0) / L

    @property
    def n(self):
        """العمودي على يسار اتجاه الجدار (= الداخل للجدران الخارجية)."""
        ux, uy = self.u
        return -uy, ux

    def point(self, t, s=0.0):
        """نقطة على بُعد t على طول الجدار و s على العمودي الأيسر."""
        ux, uy = self.u
        nx, ny = self.n
        return self.start[0] + ux * t + nx * s, self.start[1] + uy * t + ny * s


@dataclass
class Room:
    name: str
    rect: list           # [x0, y0, x1, y1] الأبعاد الداخلية الصافية
    wet: bool = False
    kind: str = ""
    cut: list = field(default_factory=list)   # مستطيلات مخصومة (غرفة على شكل L)
    label: list = None                         # موضع اسم الغرفة في المسقط (اختياري)

    @property
    def w(self):
        return self.rect[2] - self.rect[0]

    @property
    def h(self):
        return self.rect[3] - self.rect[1]

    @property
    def area_m2(self):
        a = self.w * self.h
        for c in self.cut:
            ix = min(self.rect[2], c[2]) - max(self.rect[0], c[0])
            iy = min(self.rect[3], c[3]) - max(self.rect[1], c[1])
            if ix > 0 and iy > 0:
                a -= ix * iy
        return a / 1e4


@dataclass
class Furniture:
    name: str
    rect: list
    shape: str = "rect"  # rect | circle | wc | basin | shower


@dataclass
class Deck:
    """دكة/جلسة خارجية مع دربزين (اختياري)."""
    name: str
    rect: list                 # [x0, y0, x1, y1]
    height: float = 20         # منسوب سطح الدكة من الأرض الطبيعية
    railing: list = field(default_factory=lambda: ["S", "E", "W"])   # الجهات اللي عليها دربزين
    stairs: dict = None        # {side: S, offset: 100, width: 120} فتحة الدرج في الدربزين
    railing_style: str = None  # يغلب نمط المشروع


@dataclass
class Roof:
    ridge_axis: str = "x"     # اتجاه خط الجملون (x أو y)
    pitch_deg: float = 25
    overhang: float = 0       # بروز المداد خارج الجدار (أفقي)
    ext_start: float = 0      # امتداد إضافي للسقف عند بداية محور الجملون (جلسة/تراس مسقوف)
    ext_end: float = 0        # امتداد إضافي عند نهاية محور الجملون


@dataclass
class Project:
    name: str
    client: str
    walls: list
    wall_height: float
    roof: Roof
    title: str = ""
    rooms: list = field(default_factory=list)
    furniture: list = field(default_factory=list)
    insulation: bool = False
    cladding_board_length: float = 300
    pallet_length: float = 320
    price_per_m2: float = None
    style: object = None
    slab_height: float = 20
    posts: list = field(default_factory=list)
    decks: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    @property
    def exterior_walls(self):
        return [w for w in self.walls if w.exterior]


def load_project(path, rules):
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    walls = []
    for w in d["walls"]:
        w = dict(w)
        ops = [Opening(**o) for o in w.pop("openings", [])]
        walls.append(Wall(start=tuple(w.pop("start")), end=tuple(w.pop("end")), openings=ops, **w))
    return Project(
        name=d["name"],
        title=d.get("title", d["name"]),
        client=d.get("client", ""),
        walls=walls,
        rooms=[Room(**r) for r in d.get("rooms", [])],
        furniture=[Furniture(**f) for f in d.get("furniture", [])],
        wall_height=d.get("wall_height", rules["wall"]["default_height"]),
        roof=Roof(**d.get("roof", {})),
        insulation=d.get("insulation", rules["insulation"]["default"]),
        cladding_board_length=d.get("cladding_board_length", rules["cladding"]["lengths"][0]),
        pallet_length=d.get("pallet_length", rules["pallet"]["lengths"][0]),
        price_per_m2=d.get("price_per_m2"),
        style=d.get("style"),
        slab_height=d.get("slab_height", rules["slab"]["height"]),
        posts=d.get("posts", []),
        decks=[Deck(**k) for k in d.get("decks", [])],
        meta=d.get("meta", {}),
        notes=d.get("notes", []),
    )


def wall_thickness(rules):
    return rules["members"]["stud"]["w"] + 2 * rules["cladding"]["thickness"]


def outer_bbox(project, rules):
    """حدود المبنى الخارجية (وجه التلبيس الخارجي)."""
    t = wall_thickness(rules) / 2
    xs = [p[0] for w in project.exterior_walls for p in (w.start, w.end)]
    ys = [p[1] for w in project.exterior_walls for p in (w.start, w.end)]
    return min(xs) - t, min(ys) - t, max(xs) + t, max(ys) + t
