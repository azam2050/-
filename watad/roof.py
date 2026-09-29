"""(8) سقف جملون: مدادات 5×15 كل 60، مخلّعة على العلوي ومثبتة ببراغي."""
import math


def building_bbox(walls):
    xs = [p[0] for w in walls for p in (w.start, w.end)]
    ys = [p[1] for w in walls for p in (w.start, w.end)]
    return min(xs), min(ys), max(xs), max(ys)


def gable_rafters(project, rules):
    x0, y0, x1, y1 = building_bbox(project.walls)
    r = project.roof
    if r.ridge_axis == "x":
        ridge_len, span = x1 - x0, y1 - y0
    else:
        ridge_len, span = y1 - y0, x1 - x0
    spacing = rules["roof"]["rafter_spacing"]
    per_side = math.floor(ridge_len / spacing) + 1
    pitch = math.radians(r.pitch_deg)
    length = (span / 2 + r.overhang) / math.cos(pitch)
    rise = (span / 2) * math.tan(pitch)
    stock = next((s for s in sorted(rules["roof"]["rafter_lengths"]) if s >= length), None)
    return {
        "ridge_length": ridge_len,
        "span": span,
        "pitch_deg": r.pitch_deg,
        "rise": round(rise, 1),
        "rafters_per_side": per_side,
        "rafter_count": per_side * 2,
        "rafter_length": round(length, 1),
        "stock_length": stock,
        "warning": None if stock else f"طول المداد {length:.0f} سم أطول من كل الأطوال المتوفرة — يحتاج قرار",
    }
