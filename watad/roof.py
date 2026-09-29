"""(8) سقف جملون: مدادات 5×15 كل 60، مخلّعة على العلوي ومثبتة ببراغي."""
import math

from .model import outer_bbox


def roof_geometry(project, rules):
    x0, y0, x1, y1 = outer_bbox(project, rules)
    r = project.roof
    if r.ridge_axis == "x":
        ridge_len, span = x1 - x0, y1 - y0
    else:
        ridge_len, span = y1 - y0, x1 - x0
    pitch = math.radians(r.pitch_deg)
    rise = (span / 2) * math.tan(pitch)
    return {"bbox": (x0, y0, x1, y1), "ridge_len": ridge_len, "span": span, "rise": rise,
            "pitch": pitch}


def gable_rafters(project, rules):
    g = roof_geometry(project, rules)
    r = project.roof
    spacing = rules["roof"]["rafter_spacing"]
    roof_len = g["ridge_len"] + 2 * r.overhang + r.ext_start + r.ext_end
    per_side = math.floor(roof_len / spacing) + 1
    length = (g["span"] / 2 + r.overhang) / math.cos(g["pitch"])
    stock = next((s for s in sorted(rules["roof"]["rafter_lengths"]) if s >= length), None)
    return {
        "ridge_length": round(g["ridge_len"], 1),
        "roof_length": round(roof_len, 1),
        "span": round(g["span"], 1),
        "pitch_deg": r.pitch_deg,
        "overhang": r.overhang,
        "rise": round(g["rise"], 1),
        "ridge_level": round(project.roof_base + g["rise"], 1),
        "rafters_per_side": per_side,
        "rafter_count": per_side * 2,
        "rafter_length": round(length, 1),
        "stock_length": stock,
        "warning": None if stock else f"طول المداد {length:.0f} سم أطول من كل الأطوال المتوفرة — يحتاج قرار",
    }


def cross_rafters(project, rules):
    """مدادات المثلثات البارزة: مدادات عادية (تقصر عند الوادي) + مداد وادي لكل جهة."""
    out = []
    lens = sorted(rules["roof"]["rafter_lengths"])
    for g in cross_gables(project, rules):
        stock = next((s for s in lens if s >= g["rafter_length"]), None)
        vstock = next((s for s in lens if s >= g["valley_length"]), None)
        out.append({"side": g["side"], "pitch": g["pitch"], "rafters": g["rafters"], "rafter_length": g["rafter_length"],
                    "stock": stock, "valleys": 2, "valley_length": g["valley_length"], "valley_stock": vstock,
                    "warning": None if vstock else
                    f"مداد الوادي {g['valley_length']:.0f} سم أطول من الطبلية — يُوصل بوصلة مثبتة فوق جدار/دعامة"})
    return out


def rafter_positions(project, rules):
    """مواقع المدادات على طول الجملون (من بداية السقف مع البروز)."""
    g = roof_geometry(project, rules)
    r = project.roof
    spacing = rules["roof"]["rafter_spacing"]
    lo = (g["bbox"][0] if r.ridge_axis == "x" else g["bbox"][1]) - r.overhang - r.ext_start
    n = math.floor((g["ridge_len"] + 2 * r.overhang + r.ext_start + r.ext_end) / spacing) + 1
    return [lo + i * spacing for i in range(n)]


def cross_gables(project, rules):
    """المثلثات البارزة (جملون متقاطع) على جدران الرفرف — كل واحد جملون صغير قمته عمودية على قمة السقف الرئيسي.

    الإدخال في roof.cross_gables: {side: W|E (أو S|N إذا القمة على x), center: موقع الوسط على الجدار (سم، محور)،
    width: عرض المثلث على الجدار، pitch: ميله، overhang: رفرفه}.
    الوادي بينه وبين السقف الرئيسي مائل وينزل للرفرف — ما يتجمع فيه مويه.
    يرجع قائمة بالهندسة (إحداثيات الوجه الخارجي، منسوب الجدار العلوي H=roof_base).
    """
    x0, y0, x1, y1 = outer_bbox(project, rules)
    r = project.roof
    H = project.roof_base
    tm = math.tan(math.radians(r.pitch_deg))
    out = []
    for cg in r.cross_gables:
        side = cg.get("side", "W")
        pitch = cg.get("pitch", 45)
        t = math.tan(math.radians(pitch))
        hw = cg.get("width", 400) / 2
        ov = cg.get("overhang", r.overhang)
        rise = hw * t
        zr, ze = H + rise, H - ov * t
        reach = rise / tm                    # المسافة من الجدار لين يلاقي سطح السقف الرئيسي
        if r.ridge_axis == "y":
            wall = x0 if side == "W" else x1
            sg = -1 if side == "W" else 1     # للخارج
            c = cg.get("center", (y0 + y1) / 2)
        else:
            wall = y0 if side == "S" else y1
            sg = -1 if side == "S" else 1
            c = cg.get("center", (x0 + x1) / 2)
        rafter_len = (hw + ov) / math.cos(math.radians(pitch))
        n_side = math.floor((reach + ov) / rules["roof"]["rafter_spacing"]) + 1
        valley = math.sqrt((reach + ov) ** 2 + (hw + ov) ** 2 + (rise + ov * t) ** 2)
        out.append({"side": side, "axis": r.ridge_axis, "wall": wall, "sg": sg, "c": c, "hw": hw, "ov": ov,
                    "pitch": pitch, "t": t, "rise": rise, "zr": zr, "ze": ze, "reach": reach, "H": H,
                    "rafter_length": round(rafter_len, 1), "rafters": 2 * n_side, "valley_length": round(valley, 1)})
    return out


def cross_planes(g):
    """سطحا المثلث البارز كمضلعات ثلاثية (x, y, z) — الوادي من ركن الرفرف لطرف القمة."""
    wall, sg, c, hw, ov = g["wall"], g["sg"], g["c"], g["hw"], g["ov"]
    xo, xi = wall + sg * ov, wall - sg * g["reach"]
    P = lambda a, b, z: (a, b, z) if g["axis"] == "y" else (b, a, z)  # noqa: E731
    return [[P(xo, c + hw + ov, g["ze"]), P(xi, c, g["zr"]), P(xo, c, g["zr"])],
            [P(xo, c - hw - ov, g["ze"]), P(xo, c, g["zr"]), P(xi, c, g["zr"])]]
