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
        "ridge_level": round(project.wall_height + g["rise"], 1),
        "rafters_per_side": per_side,
        "rafter_count": per_side * 2,
        "rafter_length": round(length, 1),
        "stock_length": stock,
        "warning": None if stock else f"طول المداد {length:.0f} سم أطول من كل الأطوال المتوفرة — يحتاج قرار",
    }


def rafter_positions(project, rules):
    """مواقع المدادات على طول الجملون (من بداية السقف مع البروز)."""
    g = roof_geometry(project, rules)
    r = project.roof
    spacing = rules["roof"]["rafter_spacing"]
    lo = (g["bbox"][0] if r.ridge_axis == "x" else g["bbox"][1]) - r.overhang - r.ext_start
    n = math.floor((g["ridge_len"] + 2 * r.overhang + r.ext_start + r.ext_end) / spacing) + 1
    return [lo + i * spacing for i in range(n)]
