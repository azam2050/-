"""تخطيط الفرش الواقعي للقطات الداخلية: يحوّل عناصر furniture في المشروع إلى قطع
(نوع + مستطيل بالمتر + منسوب + اتجاه الوجه) يضعها tools/blender_furnish.py بموديلات حقيقية.

الاتجاه (facing) = المتجه من ظهر القطعة إلى وجهها: الظهر هو الضلع الأقرب لجدار الغرفة،
والكراسي حول الطاولة تواجه مركزها.
"""
import math


KINDS = [("كنبة", "sofa"), ("كرسي", "armchair"), ("طاولة 6", "dining_table"), ("طاولة", "coffee_table"),
         ("تلفزيون", "tv"), ("كاونتر", "kitchen"), ("ثلاجة", "fridge"), ("سرير", "bed"), ("دولاب", "wardrobe")]


def _room_of(project, f):
    cx, cy = (f.rect[0] + f.rect[2]) / 2, (f.rect[1] + f.rect[3]) / 2
    best = None
    for r in project.rooms:
        if r.floor != f.floor:
            continue
        x0, y0, x1, y1 = r.rect
        if x0 - 1 <= cx <= x1 + 1 and y0 - 1 <= cy <= y1 + 1:
            a = (x1 - x0) * (y1 - y0)
            if best is None or a < best[0]:
                best = (a, r)
    return best[1] if best else None


def _back_to_wall(rect, room):
    """الاتجاه من الضلع الأقرب لجدار الغرفة نحو داخلها."""
    x0, y0, x1, y1 = rect
    rx0, ry0, rx1, ry1 = room.rect
    d = [(x0 - rx0, (1, 0)), (rx1 - x1, (-1, 0)), (y0 - ry0, (0, 1)), (ry1 - y1, (0, -1))]
    return min(d)[1]


def plan_furniture(project):
    tables = [f for f in project.furniture if "طاولة" in f.name]
    beds = [f for f in project.furniture if "سرير" in f.name]
    items = []
    for f in project.furniture:
        x0, y0, x1, y1 = f.rect
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        room = _room_of(project, f)
        kind = next((k for key, k in KINDS if key in f.name), None)
        if f.shape in ("shower", "wc", "basin"):
            kind = f.shape
        facing = _back_to_wall(f.rect, room) if room else (0, -1)
        if kind is None:          # قطعة بدون اسم: كرسي طاولة أو كومودينو سرير
            near_t = [t for t in tables if t.floor == f.floor and _gap(f.rect, t.rect) < 25]
            near_b = [b for b in beds if b.floor == f.floor and _gap(f.rect, b.rect) < 20]
            if near_t:
                kind = "dining_chair"
                tx, ty = (near_t[0].rect[0] + near_t[0].rect[2]) / 2, (near_t[0].rect[1] + near_t[0].rect[3]) / 2
                dx, dy = tx - cx, ty - cy
                facing = (1 if dx > 0 else -1, 0) if abs(dx) > abs(dy) else (0, 1 if dy > 0 else -1)
            elif near_b:
                kind = "nightstand"
            else:
                kind = "side_table"
        if kind == "kitchen" or kind == "fridge" or kind == "wardrobe" or kind == "tv":
            facing = _back_to_wall(f.rect, room) if room else facing
        items.append({"kind": kind, "name": f.name, "rect": [x0 / 100, y0 / 100, x1 / 100, y1 / 100],
                      "z": project.level(f.floor) / 100 + 0.012, "facing": list(facing),
                      "room": [v / 100 for v in room.rect] if room else None})
    return items


def plan_decor(project):
    """نباتات وإضاءة سقف ولوحات — لمسة سكنية لكل غرفة غير رطبة."""
    out = []
    for r in project.rooms:
        if r.kind in ("stair", "corridor") or r.wet:
            continue
        x0, y0, x1, y1 = (v / 100 for v in r.rect)
        z = project.level(r.floor) / 100
        out.append({"kind": "ceiling_lamp", "at": [(x0 + x1) / 2, (y0 + y1) / 2, z], "room": [x0, y0, x1, y1]})
    return out


def _gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0)
    dy = max(b[1] - a[3], a[1] - b[3], 0)
    return math.hypot(dx, dy)
