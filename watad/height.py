"""(7) ارتفاع الجدار: يُرفَّع لأقرب ارتفاع ينتهي بلوح تلبيس كامل."""
import math


def suggest_height(requested, rules):
    c = rules["cladding"]
    cover, off = c["effective_cover"], c["cladding_start_offset"]
    rows = math.ceil(round((requested + off) / cover, 6))
    h = max(requested, round(rows * cover - off))
    return {
        "requested": requested,
        "suggested": h,
        "rows": rows,
        "changed": h != requested,
        "reason": (
            f"بتغطية صافية {cover} سم للوح، الارتفاع {h} سم = {rows} صف كامل "
            "بدون تقطيع آخر لوح (يوفر وقت العامل ويعطي شكل أنظف)."
        ),
    }
