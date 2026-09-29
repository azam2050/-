"""نموذج المشروع: جدران، فتحات، سقف. كل الأطوال بالسنتيمتر."""
import math
from dataclasses import dataclass, field

import yaml


@dataclass
class Opening:
    kind: str            # window | door
    offset: float        # من بداية الجدار إلى الحافة اليسرى للفتحة الصافية
    width: float
    height: float
    sill: float = 0      # ارتفاع جلسة الشباك من أعلى القاعدة (للأبواب = 0)
    name: str = ""


@dataclass
class Wall:
    name: str
    start: tuple
    end: tuple
    exterior: bool = True
    wet_inner: bool = False   # داخلها دورة مياه → أسمنت بورد من الداخل
    openings: list = field(default_factory=list)
    height: float = None

    @property
    def length(self):
        return math.dist(self.start, self.end)


@dataclass
class Roof:
    ridge_axis: str = "x"     # اتجاه خط الجملون (x أو y)
    pitch_deg: float = 25
    overhang: float = 0       # TO_CONFIRM: بروز المداد خارج الجدار


@dataclass
class Project:
    name: str
    client: str
    walls: list
    wall_height: float
    roof: Roof
    insulation: bool = False
    cladding_board_length: float = 300
    pallet_length: float = 320
    notes: list = field(default_factory=list)


def load_project(path, rules):
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    walls = []
    for w in d["walls"]:
        ops = [Opening(**o) for o in w.pop("openings", [])]
        walls.append(Wall(start=tuple(w.pop("start")), end=tuple(w.pop("end")), openings=ops, **w))
    return Project(
        name=d["name"],
        client=d.get("client", ""),
        walls=walls,
        wall_height=d.get("wall_height", rules["wall"]["default_height"]),
        roof=Roof(**d.get("roof", {})),
        insulation=d.get("insulation", rules["insulation"]["default"]),
        cladding_board_length=d.get("cladding_board_length", rules["cladding"]["lengths"][0]),
        pallet_length=d.get("pallet_length", rules["pallet"]["lengths"][0]),
        notes=d.get("notes", []),
    )
