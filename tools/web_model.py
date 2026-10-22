"""مجسم الويب الواقعي للجولة الافتراضية: Blender يضيف الفرش وديكورات الخشب ويصدّر web.glb خفيف.

python tools/web_model.py projects/X.yaml <مجلد>
"""
import sys, json, subprocess
sys.path.insert(0, "/home/user/-")
from pathlib import Path
from watad.rules import load_rules
from watad.model import load_project
from watad.height import suggest_height
from watad.style import resolve_style
from watad import realistic
from watad.model3d import build_scene
from watad.interior import plan_furniture
rules = load_rules(None)
P = load_project(sys.argv[1], rules)
P.wall_height = suggest_height(P.wall_height, rules)["suggested"]
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
style = resolve_style(P.style)
heights = {w.name: P.wall_height for w in P.walls}
S = build_scene(P, rules, style, heights, furniture="floors")
S.write_glb(out / "scene.glb")
items = plan_furniture(P)
for it in items:
    it["ceil"] = (P.floor_list[0]["height"] if P.floors else P.wall_height) / 100
cfg = {"glb": str(out / "scene.glb"), "out": str(out / "web.glb"), "tex_dir": realistic.TEX, "models_dir": realistic.MODELS,
       "furnish": items, "furnish_py": str(realistic.ROOT / "tools" / "blender_furnish.py"), "landscape": [],
       "decor": realistic.decor_items(P), "sadu": bool(P.render.get("sadu")), "max_tex": 512}
(out / "cfg.json").write_text(json.dumps(cfg, ensure_ascii=False))
r = subprocess.run([realistic.BLENDER, "-b", "-P", str(realistic.ROOT / "tools" / "export_web.py"), "--", str(out / "cfg.json")],
                   capture_output=True, text=True)
print(r.stdout[-1500:], r.stderr[-1500:])
