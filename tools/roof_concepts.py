"""رندر واقعي لأشكال الأسقف الجديدة (watad/roofs_new.py) للعرض على المصنع قبل الاعتماد.
  python tools/roof_concepts.py out/roofs [N01 N02 ...] [--samples 40]
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from watad.realistic import BLENDER, DAY, MODELS, TEX  # noqa: E402
from watad.roofs_new import CLIENT, CONCEPTS, build, build_client  # noqa: E402
from watad.style import resolve_style  # noqa: E402


def landscape(lo, hi, cam, seed=3):
    rnd = random.Random(seed)
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    out = []
    for _ in range(18):
        a = math.radians(rnd.uniform(-10, 190))
        r = rnd.uniform(8, 20)
        tx, ty = cx + r * math.cos(a), cy + 2 + r * math.sin(a)
        dx, dy = cx - cam[0], cy - cam[1]
        t = max(0, min(1, ((tx - cam[0]) * dx + (ty - cam[1]) * dy) / (dx * dx + dy * dy)))
        if math.hypot(tx - cam[0] - t * dx, ty - cam[1] - t * dy) < 3.5:
            continue
        out.append({"model": "tree_small_02", "at": [tx, ty, -0.2], "H": rnd.uniform(4, 7), "rot": rnd.uniform(0, 360)})
    for _ in range(10):
        a = math.radians(rnd.uniform(-20, 200))
        r = rnd.uniform(6, 13)
        out.append({"model": "shrub_02", "at": [cx + r * math.cos(a), cy + r * math.sin(a), -0.2],
                    "H": rnd.uniform(0.8, 1.4), "rot": rnd.uniform(0, 360)})
    return out


def main():
    args = sys.argv[1:]
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    samples = 40
    if "--samples" in args:
        samples = int(args[args.index("--samples") + 1])
    res = [1400, 875]
    if "--res" in args:
        res = [int(v) for v in args[args.index("--res") + 1].split("x")]
    codes = [a for a in args[1:] if a[:1] in "NSC" and a[1:].isdigit()] or [c["code"] for c in CONCEPTS]
    style = resolve_style({"preset": "walnut_black", "wood": "natural_pine"})
    for code in codes:
        S, issues = (build_client if code.startswith("C") else build)(code, style)
        print(code, "تصريف:", issues or "سليم", flush=True)
        glb = out / f"{code}.glb"
        S.write_glb(glb)
        V = np.array([v for V_, _ in S.parts.values() for v in V_]) / 100
        lo, hi = V.min(axis=0), V.max(axis=0)
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        htop = hi[2]
        R = max(hi[0] - lo[0], htop * 1.3, 7)
        cam = (lo[0] - 0.42 * R, lo[1] - 0.82 * R, 1.6)
        dist = math.hypot(cx - cam[0], cy - cam[1])
        shift = max(0.0, min(0.25, (0.62 * htop - 1.6) / dist * 24 / 36))
        cfg = {"glb": str(glb), "out_dir": str(out), "tex_dir": TEX, "models_dir": MODELS,
               "colors": {k: style[k] for k in ("wood", "trim", "roof", "frame", "glass", "slab")},
               "views": [], "furnish_py": str(ROOT / "tools" / "blender_furnish.py"),
               "landscape": landscape(lo, hi, cam), **DAY,
               "shots": [[code, list(cam), [cx + 0.4, cy, 1.6], 24, round(shift, 3), 0.0]]
               + ([[code + "b", [hi[0] + (lo[0] - cam[0]), cam[1], 1.6], [cx - 0.4, cy, 1.6], 24, round(shift, 3), 0.0]]
                  if "--both" in args else []),
               "samples": samples, "res": res, "ground_z": -0.2, "lights": [], "lens": 35}
        p = out / f"{code}.json"
        p.write_text(json.dumps(cfg, ensure_ascii=False))
        subprocess.run([BLENDER, "-b", "-P", str(ROOT / "tools" / "render_blender.py"), "--", str(p)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        glb.unlink(missing_ok=True)
        print("ok", code, flush=True)


if __name__ == "__main__":
    main()
