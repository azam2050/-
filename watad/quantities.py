"""حساب الكميات: خطة تقطيع الطبليات (2)، التلبيس (5)، الأسمنت بورد، العزل (6)."""
import math
from collections import Counter

from .framing import frame_wall
from .roof import gable_rafters


def split_long(lengths, stock):
    """القطع الأطول من الخام تُقسَّم (TO_CONFIRM: مكان الوصلة في القاعدة/العلوي)."""
    out = []
    for L in lengths:
        n = math.ceil(L / stock)
        out += [L / n] * n
    return out


def pack(lengths, stock, kerf, bins=None):
    """First-Fit-Decreasing: يرجع قائمة شرائح، كل شريحة = قائمة قطع."""
    bins = bins if bins is not None else []
    for L in sorted(lengths, reverse=True):
        for b in bins:
            if sum(b) + kerf * len(b) + L <= stock + 1e-6:
                b.append(L)
                break
        else:
            bins.append([L])
    return bins


def pallet_plan(project, rules, walls_members):
    """(2) نبدأ بالمدادات: كل مداد = طبلية بالطريقة الأولى (مداد + عمود 7×5).
    باقي الأعمدة من الطبليات بالطريقة الثانية (3 أعمدة لكل طبلية)."""
    kerf = rules["pallet"]["saw_kerf"]
    roof = gable_rafters(project, rules)
    rafter_stock = roof["stock_length"] or max(rules["pallet"]["lengths"])
    n_m1 = roof["rafter_count"]

    stud_pieces = [m.length for ms in walls_members.values() for m in ms]
    stud_stock = project.pallet_length

    # شرائح 7×5 الناتجة من طبليات الطريقة الأولى (بطول طبلية المداد)
    free_bins = [[] for _ in range(n_m1)]
    pieces = split_long(stud_pieces, max(rafter_stock, stud_stock))
    long_pieces = [p for p in pieces if p > stud_stock]
    short_pieces = [p for p in pieces if p <= stud_stock]
    # القطع الطويلة لازم تروح للشرائح الطويلة أولاً
    pack(long_pieces, rafter_stock, kerf, free_bins)
    overflow = []
    if len(free_bins) > n_m1:
        overflow = free_bins[n_m1:]
        free_bins = free_bins[:n_m1]
    # نملأ الفراغ في الشرائح المجانية بالقطع القصيرة
    remaining = []
    for p in sorted(short_pieces, reverse=True):
        for b in free_bins:
            if sum(b) + kerf * len(b) + p <= rafter_stock + 1e-6:
                b.append(p)
                break
        else:
            remaining.append(p)
    extra_bins = pack(remaining, stud_stock, kerf)
    long_extra = pack([p for b in overflow for p in b], rafter_stock, kerf)

    m2 = math.ceil(len(extra_bins) / 3)
    m2_long = math.ceil(len(long_extra) / 3)
    return {
        "method1_pallets": {"count": n_m1, "length": rafter_stock,
                            "yield": f"{n_m1} مداد 5×15 + {n_m1} عمود 7×5"},
        "method2_pallets": {"count": m2, "length": stud_stock,
                            "yield": f"{m2 * 3} عمود 7×5 (3 لكل طبلية)"},
        "method2_long_pallets": {"count": m2_long, "length": rafter_stock},
        "total_pallets": n_m1 + m2 + m2_long,
        "stud_pieces_total": len(stud_pieces),
        "stud_cut_list": sorted(Counter(round(p) for p in stud_pieces).items(), reverse=True),
        "roof": roof,
    }


def row_segments(wall, y0, y1, yb):
    """المقاطع الأفقية المتصلة في صف تلبيس (مع خصم الفتحات)."""
    cuts = []
    for o in wall.openings:
        bot = yb + o.sill if o.kind == "window" else 0
        top = yb + (o.sill + o.height if o.kind == "window" else o.height)
        if y0 < top and y1 > bot:
            cuts.append((o.offset, o.offset + o.width))
    segs, x = [], 0
    for a, b in sorted(cuts):
        if a > x:
            segs.append(a - x)
        x = max(x, b)
    if wall.length > x:
        segs.append(wall.length - x)
    return segs


def cladding(project, rules, heights):
    c = rules["cladding"]
    cover, stock = c["effective_cover"], project.cladding_board_length
    t = rules["members"]["stud"]["t"]
    cb = rules["wet_room"]["cement_board"]
    pieces, sheets, sides = [], 0, 0
    for w in project.walls:
        H = heights[w.name]
        rows = math.ceil(round((H + c["cladding_start_offset"]) / cover, 6))
        faces = ["out", "in"]
        if w.wet_inner:
            faces = ["out"]
            sheets += math.ceil(w.length / cb["w"]) * math.ceil(H / cb["h"])
        if not w.exterior and w.wet_inner:
            faces = ["in"]   # جدار داخلي: الوجه الآخر غير المبلل
        for _ in faces:
            sides += 1
            for r in range(rows):
                y0 = r * cover - c["cladding_start_offset"]
                pieces += row_segments(w, y0, y0 + cover, t)
    bins = pack(split_long(pieces, stock), stock, 0)
    return {"boards": len(bins), "board_length": stock, "faces": sides,
            "total_run_m": round(sum(pieces) / 100, 1), "cement_board_sheets": sheets}


def insulation(project, rules, heights):
    if not project.insulation:
        return None
    p = rules["insulation"]["panel"]
    area = sum(w.length * heights[w.name] - sum(o.width * o.height for o in w.openings)
               for w in project.walls)
    return {"panels": math.ceil(area / (p["w"] * p["h"])), "area_m2": round(area / 1e4, 1)}


def build_quantities(project, rules, heights):
    members = {}
    for i, w in enumerate(project.walls):
        members[w.name] = frame_wall(w, heights[w.name], rules)
    return members, {
        "pallets": pallet_plan(project, rules, members),
        "cladding": cladding(project, rules, heights),
        "insulation": insulation(project, rules, heights),
    }
