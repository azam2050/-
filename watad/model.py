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
    grid: list = None    # تقسيم خشب للزجاج [أعمدة، صفوف] (شبابيك/أبواب بشبكة مثل الكوخ الكلاسيكي)

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
    glass_front: bool = False   # الواجهة كاملة (الجدار + المثلث) زجاج بشبكة قوائم خشب وباب بالوسط (A-frame)
    glass_split: bool = False   # تقسيم زجاج الواجهة لألواح أصغر (عارضة ثانية بالمثلث + قوائم)
    gable_openings: list = field(default_factory=list)   # فتحات داخل مثلث الجملون (باب بلكونة الميزانين…)
    floor: int = 0              # رقم الدور (0 أرضي، 1 أول)

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
    floor: int = 0

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
    floor: int = 0
    z: float = None      # منسوب القطعة (للميزانين: floor: -1 + z = منسوب أرضية الميزانين)

    def level_in(self, project):
        return self.z if self.z is not None else project.level(self.floor)


@dataclass
class Deck:
    """دكة/جلسة خارجية مع دربزين (اختياري)."""
    name: str
    rect: list                 # [x0, y0, x1, y1]
    height: float = 20         # منسوب سطح الدكة من الأرض الطبيعية
    railing: list = field(default_factory=lambda: ["S", "E", "W"])   # الجهات اللي عليها دربزين
    stairs: dict = None        # {side: S, offset: 100, width: 120} فتحة الدرج في الدربزين
    railing_style: str = None  # يغلب نمط المشروع
    level: float = 0           # منسوب سطح الدكة (0 = أرضي). للبلكونة = منسوب أرضية الدور الأول


@dataclass
class Roof:
    ridge_axis: str = "x"     # اتجاه خط الجملون (x أو y) — للمائل: اتجاه الحافة العالية
    type: str = "gable"       # gable جملون | shed مائل باتجاه واحد | peaks قمم هرمية | tent_hip خيمة منسابة بدون وديان
    units: list = field(default_factory=list)   # للـ tent_hip: وحدات سقف الخيمة المنساب (انظر watad/tent_roof.py)
    peaks: list = field(default_factory=list)   # للـ peaks: [{rect: [x0,y0,x1,y1] وجه خارجي، h: ارتفاع القمة فوق الجدار،
                                                #   apex: [x,y] (اختياري)، overhang، lantern: ضلع المشراق الزجاج (سم)}]
    high_side: str = "S"      # للمائل: الجهة العالية (S/N إذا الحافة على x، W/E إذا على y)
    low_pitch_approved: bool = False   # ميل أقل من الحد الأدنى بموافقة المصنع (صاج معدني + عزل مائي)
    pitch_deg: float = 25
    overhang: float = 0       # بروز المداد خارج الجدار (أفقي)
    ext_start: float = 0      # امتداد إضافي للسقف عند بداية محور الجملون (جلسة/تراس مسقوف)
    ext_end: float = 0        # امتداد إضافي عند نهاية محور الجملون
    cross_gables: list = field(default_factory=list)   # مثلثات بارزة (جملون متقاطع) على جدران الرفرف
    splice: float = None      # للمائل الطويل: محور جدار داخلي حامل توصل فوقه المدادات (قطعتين بتراكب 60 سم)
    purlins: int = 0          # جملون عريض (شاليه): عدد المدادات الحاملة الطولية (purlins) بكل جهة بين الجدار والقمة
                              # + جسر القمة — المداد ينقسم قطع ≤ طبلية فوقها، وأطراف الجسور بارزة تحت الرفرف
    soffit: bool = False      # تلبيس خشب أملس تحت المدادات (سقف داخلي مستوي + تحت الرفرف بدون مدادات ظاهرة)
    purlin: dict = field(default_factory=lambda: {"w": 20, "h": 30})   # مقطع الجسر الحامل (سم)


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
    floors: list = field(default_factory=list)   # [{name, level, height}] — فارغ = دور واحد
    stairs: list = field(default_factory=list)   # درج داخلي
    slab_height: float = 20
    posts: list = field(default_factory=list)
    decks: list = field(default_factory=list)
    bays: list = field(default_factory=list)      # شبابيك بارزة مضلعة (bay window) — watad/features.py
    porches: list = field(default_factory=list)   # مظلة مدخل بجملون صغير على عمودين
    decor: list = field(default_factory=list)     # ديكورات خشب داخلية وإنارتها للرندر الواقعي (tools/blender_decor.py)
    render: dict = field(default_factory=dict)    # إعدادات الرندر الواقعي: sadu، لقطات داخلية محددة
    pergolas: list = field(default_factory=list)  # برجولات خشب فوق الأبواب/الشبابيك
    skirts: list = field(default_factory=list)    # سقف قصير مائل (رفرف) بين الدورين على جزء من الواجهة — watad/features.py
    mezzanines: list = field(default_factory=list)  # نص دور (ميزانين) داخل المبنى — watad/features.py
    straight_stairs: list = field(default_factory=list)  # درج مستقيم (للميزانين)
    spiral_stairs: list = field(default_factory=list)    # درج حلزوني (للميزانين) — watad/features.py
    voids: list = field(default_factory=list)   # فراغ مزدوج الارتفاع بأرضية دور علوي: [{floor: 1, rect, railing: [S,E,W,N]}]
    site: dict = None                            # الموقع العام (الأرض، السور، المسبح، الجلسات، الحديقة) — watad/site.py
    bumps: list = field(default_factory=list)   # بروز مقفل خارج الجدار (دورة مياه الميزانين + غرفة تفتيش تحت)
    meta: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    height_exact: bool = False      # ارتفاع الجدار بطلب العميل بالضبط (بدون تقريب لصف تلبيس كامل)

    @property
    def exterior_walls(self):
        return [w for w in self.walls if w.exterior]

    @property
    def floor_list(self):
        if self.floors:
            return self.floors
        return [{"name": "الدور الأرضي", "level": 0, "height": self.wall_height}]

    def level(self, floor):
        return self.floor_list[floor]["level"]

    @property
    def top_floor(self):
        return len(self.floor_list) - 1

    @property
    def roof_base(self):
        """منسوب أعلى جدار الدور الأخير (قاعدة السقف)."""
        f = self.floor_list[-1]
        return f["level"] + f["height"]

    def walls_on(self, floor):
        return [w for w in self.walls if w.floor == floor]


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
        floors=d.get("floors", []),
        stairs=d.get("stairs", []),
        slab_height=d.get("slab_height", rules["slab"]["height"]),
        posts=d.get("posts", []),
        decks=[Deck(**k) for k in d.get("decks", [])],
        bays=d.get("bays", []),
        porches=d.get("porches", []),
        skirts=d.get("skirts", []),
        pergolas=d.get("pergolas", []),
        mezzanines=d.get("mezzanines", []),
        straight_stairs=d.get("straight_stairs", []),
        spiral_stairs=d.get("spiral_stairs", []),
        voids=d.get("voids", []),
        decor=d.get("interior_decor", []),
        render=d.get("render", {}),
        bumps=d.get("bumps", []),
        site=d.get("site"),
        meta=d.get("meta", {}),
        notes=d.get("notes", []),
        height_exact=d.get("height_exact", False),
    )


def wall_thickness(rules):
    return rules["members"]["stud"]["w"] + 2 * rules["cladding"]["thickness"]


def floor_bbox(project, rules, floor):
    """حدود الدور (وجه التلبيس الخارجي) من جدرانه الخارجية — للأدوار المختلفة المقاس."""
    walls = [w for w in project.exterior_walls if w.floor == floor]
    if not walls:
        return outer_bbox(project, rules)
    t = wall_thickness(rules) / 2
    xs = [p[0] for w in walls for p in (w.start, w.end)]
    ys = [p[1] for w in walls for p in (w.start, w.end)]
    return min(xs) - t, min(ys) - t, max(xs) + t, max(ys) + t


def roof_bbox(project, rules):
    """حدود السقف: جدران الدور الأخير الخارجية — إذا الدور العلوي أصغر من الأرضي، الباقي سطح (تراس علوي)."""
    top = len(project.floor_list) - 1
    walls = [w for w in project.exterior_walls if w.floor == top] if top > 0 else []
    if not walls:
        return outer_bbox(project, rules)
    t = wall_thickness(rules) / 2
    xs = [p[0] for w in walls for p in (w.start, w.end)]
    ys = [p[1] for w in walls for p in (w.start, w.end)]
    return min(xs) - t, min(ys) - t, max(xs) + t, max(ys) + t


def outer_bbox(project, rules):
    """حدود المبنى الخارجية (وجه التلبيس الخارجي)."""
    t = wall_thickness(rules) / 2
    xs = [p[0] for w in project.exterior_walls for p in (w.start, w.end)]
    ys = [p[1] for w in project.exterior_walls for p in (w.start, w.end)]
    return min(xs) - t, min(ys) - t, max(xs) + t, max(ys) + t


def mezz_area(P):
    """مسطح الميزانين/الدور داخل المثلث (م²) — مستطيلات الأرضية ناقص فتحات الدرج. يدخل بالمساحة المبنية."""
    a = 0.0
    for m in P.mezzanines:
        x0, y0, x1, y1 = m["rect"]
        a += (x1 - x0) * (y1 - y0)
        for h in m.get("holes", []):
            hx0, hy0, hx1, hy1 = h["rect"]
            a -= (hx1 - hx0) * (hy1 - hy0)
    return a / 1e4
