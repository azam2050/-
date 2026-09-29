"""يولّد صور استبيان الاختيار (أسقف، دربزين، شبابيك، أبواب) + data.json."""
import json
import sys
from pathlib import Path

import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from watad import components  # noqa: E402
from watad.catalog import ROOFS, Maker  # noqa: E402
from watad.model import Wall  # noqa: E402
from watad.model3d import railing_run, render_preview  # noqa: E402
from watad.style import PRESETS, resolve_style  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "survey"
IMG = OUT / "img"
IMG.mkdir(parents=True, exist_ok=True)
style = resolve_style("honey_burgundy")


def save(scene, code, view, size):
    png = IMG / f"{code}.png"
    render_preview(scene, png, views=(view,), size=size, hidden=(), tight=True, dpi=110)
    im = Image.open(png).convert("RGB")
    im.thumbnail((720, 560))
    im.save(IMG / f"{code}.jpg", quality=84, optimize=True)
    png.unlink()
    return f"img/{code}.jpg"


data = {"roofs": [], "railings": [], "windows": [], "doors": []}
for it in ROOFS:
    M = Maker(style)
    it["fn"](M)
    data["roofs"].append({"code": it["code"], "ar": it["ar"], "floors": it["floors"], "note": it["note"],
                          "stars": it["stars"], "img": save(M.S, it["code"], it["view"], (6, 4.4))})
lib = yaml.safe_load(open(PRESETS, encoding="utf-8"))["railings"]
for i, (name, spec) in enumerate(lib.items()):
    M = Maker(style)
    M.S.box("slab", -20, -30, -8, 340, 30, 0)
    railing_run(M.S, Wall("r", (0, 0), (320, 0)), 0, 320, 0, name, spec)
    code = f"B{i + 1:02d}"
    data["railings"].append({"code": code, "ar": spec["ar"], "key": name,
                             "note": f"ارتفاع {spec['height']} سم أرضي — 105 سم للدور العلوي",
                             "img": save(M.S, code, (10, -70), (6, 3.2))})
for kind, lst in (("windows", components.WINDOWS), ("doors", components.DOORS)):
    for it in lst:
        S = components.build(it, style)
        data[kind].append({"code": it["code"], "ar": it["ar"], "note": it["note"],
                           "img": save(S, it["code"], (6, -62), (4.5, 4.5))})
(OUT / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print({k: len(v) for k, v in data.items()})
