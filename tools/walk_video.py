"""فيديو جولة واقعية لمشروع (render.video بالمشروع): Blender بإضاءة النهار + مسار كاميرا، ثم ffmpeg يجمع الفيديو.

python tools/walk_video.py projects/X.yaml <مجلد الإخراج>
"""
import json, sys, subprocess
from pathlib import Path
sys.path.insert(0, "/home/user/-")
from watad.rules import load_rules
from watad.model import load_project
from watad.height import suggest_height
from watad.style import resolve_style
from watad import realistic

rules = load_rules(None)
P = load_project(sys.argv[1], rules)
P.wall_height = suggest_height(P.wall_height, rules)["suggested"]
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
v = P.render["video"]
cm = lambda L: [[c / 100 for c in p] for p in L]
# نعيد استخدام بناء الإعداد من render_real بدون رندر: نستدعي _run بنسخة معدلة
from watad.model3d import build_scene
from watad.interior import plan_furniture
from watad.landscape import plan_landscape
style = resolve_style(P.style)
heights = {w.name: P.wall_height for w in P.walls}
scene = build_scene(P, rules, style, heights, furniture="floors")
glb = out / "scene.glb"
scene.write_glb(glb)
items = plan_furniture(P)
for it in items:
    it["ceil"] = (P.floor_list[0]["height"] if P.floors else P.wall_height) / 100
cfg = {"glb": str(glb), "out_dir": str(out), "tex_dir": realistic.TEX, "models_dir": realistic.MODELS,
       "colors": {k: style[k] for k in ("wood", "trim", "roof", "frame", "glass", "slab")},
       "views": [], "furnish": items, "furnish_py": str(realistic.ROOT / "tools" / "blender_furnish.py"),
       "landscape": plan_landscape(P), "wood_frames": style.get("frame_ar", "").startswith("إطار خشب"),
       "samples": v.get("samples", 12), "res": v.get("res", [960, 540]), "ground_z": -P.slab_height / 100,
       "lights": [], "lens": 18, "decor": realistic.decor_items(P), "sadu": bool(P.render.get("sadu")),
       "ground_holes": realistic.ground_holes(P), "shots": [], "panos": [], "tag": "video",
       "area_lights": realistic._areas(P, 5), **realistic.DAY,
       "video": {**v, "path": cm(v["path"]), "look": cm(v["look"])}}
realistic._run(cfg, out)
exe = __import__("imageio_ffmpeg").get_ffmpeg_exe()
subprocess.run([exe, "-y", "-v", "error", "-framerate", str(v.get("fps", 12)), "-i", str(out / "walk" / "f_%04d.jpg"),
                "-vf", "minterpolate=fps=24:mi_mode=blend,format=yuv420p", "-c:v", "libx264", "-crf", "20",
                "-movflags", "+faststart", str(out / "walk.mp4")], check=True)
print("video:", out / "walk.mp4")
