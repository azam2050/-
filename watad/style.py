"""أنماط الألوان والمواد (config/style_presets.yaml)."""
from pathlib import Path

import yaml

PRESETS = Path(__file__).resolve().parent.parent / "config" / "style_presets.yaml"
DEFAULT = "honey_burgundy"


def _darker(hex_, k=0.7):
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#{:02X}{:02X}{:02X}".format(int(r * k), int(g * k), int(b * k))


def resolve_style(spec=None, path=None):
    """spec: اسم نمط، أو dict فيه preset + تعديلات."""
    with open(path or PRESETS, encoding="utf-8") as f:
        lib = yaml.safe_load(f)
    if spec is None:
        spec = DEFAULT
    if isinstance(spec, str):
        spec = {"preset": spec}
    base = dict(lib["presets"][spec.get("preset", DEFAULT)])
    base.update({k: v for k, v in spec.items() if k != "preset"})
    codes = list(lib["railings"])
    rl = str(base.get("railing", "three_rail"))
    if rl.upper().startswith("B") and rl[1:].isdigit():       # رمز الكتالوج B01..B08
        base["railing"] = codes[int(rl[1:]) - 1]
    m = lib["materials"]
    wood = m["wood"][base["wood"]]
    frame_color = (m["frame"][base["frame"]].get("color") or _darker(wood["color"], 0.6))
    glass = m["glass"][base["glass"]]
    return {
        "name": spec.get("preset", DEFAULT),
        "ar": base.get("ar", ""),
        "wood": wood["color"], "wood_line": wood["line"], "wood_ar": wood["ar"],
        "trim": _darker(wood["color"], 0.8),
        "roof": m["roof"][base["roof"]]["color"], "roof_ar": m["roof"][base["roof"]]["ar"],
        "glass": glass["color"], "glass_alpha": glass.get("alpha", 0.8), "glass_ar": glass["ar"],
        "frame": frame_color, "frame_ar": m["frame"][base["frame"]]["ar"],
        "slab": m["other"]["slab"]["color"],
        "window_grid": base.get("window_grid", "mullion"),
        "door_style": base.get("door_style", "panel"),
        "railing": base.get("railing", "three_rail"),
        "railing_spec": lib["railings"][base.get("railing", "three_rail")],
        "railing_ar": lib["railings"][base.get("railing", "three_rail")]["ar"],
        "exposed_rafter_tails": base.get("exposed_rafter_tails", False),
        "trims": lib["trims"],
    }
