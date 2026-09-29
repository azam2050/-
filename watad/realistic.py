"""رندر واقعي (Blender Cycles) — خطوة اختيارية: python -m watad مشروع.yaml --real

يحتاج Blender و خامات ambientCG + سماء HDRI في BLENDER_TEX (الافتراضي /opt/blender/tex).
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

from .model3d import build_scene

ROOT = Path(__file__).resolve().parent.parent
BLENDER = os.environ.get("BLENDER", "/opt/blender/blender-4.2.3-linux-x64/blender")
TEX = os.environ.get("BLENDER_TEX", "/opt/blender/tex")

VIEWS = [
    ("واقعي-أمامي", 4, -90, 0.95),
    ("واقعي-أمامي-يسار", 7, -58, 0.95),
    ("واقعي-أمامي-يمين", 7, -122, 0.95),
    ("واقعي-خلفي", 10, 55, 1.0),
]


def available():
    return Path(BLENDER).exists() and Path(TEX, "sky.hdr").exists()


def render_real(project, rules, style, heights, out_dir, samples=64, res=(1600, 1000), views=VIEWS):
    out = Path(out_dir) / "realistic"
    out.mkdir(parents=True, exist_ok=True)
    scene = build_scene(project, rules, style, heights, furniture=True)
    glb = out / "scene.glb"
    scene.write_glb(glb)
    lights = [((r.rect[0] + r.rect[2]) / 200, (r.rect[1] + r.rect[3]) / 200, 2.4)
              for r in project.rooms if r.area_m2 > 8]
    cfg = {"glb": str(glb), "out_dir": str(out), "tex_dir": TEX,
           "colors": {k: style[k] for k in ("wood", "trim", "roof", "frame", "glass", "slab")},
           "views": [[f"v{i}", e, a, k] for i, (_n, e, a, k) in enumerate(views, 1)],
           "samples": samples, "res": list(res), "ground_z": -project.slab_height / 100,
           "lights": lights, "lens": 35}
    (out / "cfg.json").write_text(json.dumps(cfg, ensure_ascii=False))
    subprocess.run([BLENDER, "-b", "-P", str(ROOT / "tools" / "render_blender.py"), "--", str(out / "cfg.json")],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shots = []
    for i, (name, *_r) in enumerate(views, 1):
        p = out / f"v{i}.jpg"
        if p.exists():
            shots.append((p, name.replace("واقعي-", "").replace("-", " ")))
    glb.unlink(missing_ok=True)
    return shots
