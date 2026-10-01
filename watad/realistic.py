"""رندر واقعي (Blender Cycles) — خطوة اختيارية: python -m watad مشروع.yaml --real

المعيار المعتمد من المصنع لكل تصميم:
  - لقطات خارجية على مستوى النظر (4 نهار + 2 وقت الغروب والإنارة شغالة) مع أشجار وشجيرات وممر وجلسة التراس.
  - لقطات داخلية لكل غرفة معيشة/نوم بأثاث حقيقي في مكانه حسب المسقط، جدران بخشب الأرضية، مدادات مكشوفة.
يحتاج Blender و خامات ambientCG + سماء HDRI في BLENDER_TEX، وموديلات الأثاث في BLENDER_MODELS
(tools/fetch_models.py ينزلها من Poly Haven).
"""
import json
import math
import os
import subprocess
from pathlib import Path

from .interior import plan_furniture
from .landscape import plan_landscape
from .model3d import build_scene

ROOT = Path(__file__).resolve().parent.parent
BLENDER = os.environ.get("BLENDER", "/opt/blender/blender-4.2.3-linux-x64/blender")
TEX = os.environ.get("BLENDER_TEX", "/opt/blender/tex")
MODELS = os.environ.get("BLENDER_MODELS", "/opt/blender/models")

EYE_OUT, EYE_IN = 1.6, 1.35
DAY = {"exterior_pine": True, "sky": 0.9, "sun": 4.0, "sun_elev": 35, "sun_azim": -40, "wood_mix": 0.3, "grass_tile": 1.2,
       "grass_tint": "#6E8B3D"}
DUSK = {**DAY, "sky": 0.12, "sun": 0.6, "sun_elev": 4, "sun_azim": -60}


def available():
    return Path(BLENDER).exists() and Path(TEX, "sky.hdr").exists()


def _bbox(project):
    xs = [p[0] / 100 for w in project.walls for p in (w.start, w.end)]
    ys = [p[1] / 100 for w in project.walls for p in (w.start, w.end)]
    yf = min([min(ys)] + [d.rect[1] / 100 for d in project.decks])
    return min(xs), min(ys), max(xs), max(ys), yf


def exterior_shots(project):
    """أربع زوايا على مستوى النظر: أمامي يسار/يمين، أمامي مباشر، خلفي. الإزاحة الرأسية تحسب من ارتفاع الكوخ."""
    x0, y0, x1, y1, yf = _bbox(project)
    W = x1 - x0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    from .roof import roof_geometry
    from .rules import load_rules
    htop = (project.roof_base + roof_geometry(project, load_rules(None))["rise"]) / 100
    R = max(W, htop * 1.1, 6.0)
    out = []
    for key, name, cam, lens in [
        ("x1", "أمامي من اليسار", (x0 - 0.65 * R, yf - 1.2 * R), 24),
        ("x2", "أمامي من اليمين", (x1 + 0.65 * R, yf - 1.15 * R), 24),
        ("x3", "الواجهة الأمامية", (cx, yf - 1.45 * R), 26),
        ("x4", "خلفي من اليسار", (x0 - 0.85 * R, y1 + 1.05 * R), 24),
    ]:
        dist = math.hypot(cx - cam[0], cy - cam[1])
        shift = max(0.0, min(0.25, (0.7 * htop - EYE_OUT) / dist * lens / 36))
        out.append([key, name, [cam[0], cam[1], EYE_OUT], [cx + (0.3 if key == "x1" else -0.3 if key == "x2" else 0),
                                                           cy, EYE_OUT], lens, round(shift, 3)])
    return out


def interior_shots(project, max_shots=6):
    """لكل غرفة معيشة/نوم: كاميرا في الركن اللي يطلع أكثر فرش وشبابيك وأقل عوائق، باتجاه الركن المقابل."""
    furn = [(f.floor, [v / 100 for v in f.rect]) for f in project.furniture]
    rooms = [r for r in project.rooms if not r.wet and r.kind not in ("corridor", "stair") and r.area_m2 >= 7]
    rooms.sort(key=lambda r: -r.area_m2)
    out = []
    for r in rooms:
        x0, y0, x1, y1 = (v / 100 for v in r.rect)
        z = project.level(r.floor) / 100
        ins = 0.35
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        cands = []                     # نقاط على محيط الغرفة كل 50 سم، والهدف هو النقطة المقابلة عبر المركز
        for a, b, n_ in (((x0 + ins, y0 + ins), (x1 - ins, y0 + ins), 0), ((x1 - ins, y0 + ins), (x1 - ins, y1 - ins), 0),
                         ((x1 - ins, y1 - ins), (x0 + ins, y1 - ins), 0), ((x0 + ins, y1 - ins), (x0 + ins, y0 + ins), 0)):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            for i in range(max(1, int(L / 0.5))):
                f_ = i * 0.5 / L
                cands.append((a[0] + (b[0] - a[0]) * f_, a[1] + (b[1] - a[1]) * f_))
        scored = []
        for c in cands:
            t = (2 * mx - c[0], 2 * my - c[1])
            d = (t[0] - c[0], t[1] - c[1])
            n = math.hypot(*d)
            if n < 2.0:
                continue
            score = 0.4 * n                           # زاوية أطول = إحساس أوسع
            for fl, (a0, b0, a1, b1) in furn:
                if fl != r.floor:
                    continue
                if a0 - 0.25 < c[0] < a1 + 0.25 and b0 - 0.25 < c[1] < b1 + 0.25:
                    score -= 100                      # الكاميرا داخل/لاصقة بقطعة فرش
                fx, fy = (a0 + a1) / 2, (b0 + b1) / 2
                v = (fx - c[0], fy - c[1])
                dv = math.hypot(*v)
                if dv > 1.0 and (v[0] * d[0] + v[1] * d[1]) / (dv * n) > math.cos(math.radians(50)):
                    score += 1
            for w in project.walls_on(r.floor):
                for o in w.openings:
                    ox, oy = w.point(o.offset + o.width / 2, 0)
                    ox, oy = ox / 100, oy / 100
                    if abs(ox - c[0]) < 0.6 and abs(oy - c[1]) < 0.6:
                        score -= 100                  # قدام باب/شباك
                    if not w.exterior:
                        continue
                    v = (ox - c[0], oy - c[1])
                    dv = math.hypot(*v)
                    if dv > 0.5 and (v[0] * d[0] + v[1] * d[1]) / (dv * n) > math.cos(math.radians(45)):
                        score += 1.5 if o.width >= 200 else 0.7
            scored.append((score, c, t))
        scored.sort(key=lambda s_: -s_[0])
        picks = scored[:1]
        if r.area_m2 >= 20:
            far = [s_ for s_ in scored if math.hypot(s_[1][0] - picks[0][1][0], s_[1][1] - picks[0][1][1]) > 3
                   and s_[0] > -50]
            picks += far[:1]
        for j, (_s, c, t) in enumerate(picks):
            name = r.name + (" — منظر 2" if j else "")
            out.append([f"i{len(out) + 1}", name, [c[0], c[1], z + EYE_IN], [t[0], t[1], z + EYE_IN], 17, -0.06])
            if len(out) >= max_shots:
                return out
    return out


def _areas(project, per_m2):
    out = []
    for r in project.rooms:
        x0, y0, x1, y1 = (v / 100 for v in r.rect)
        z = project.level(r.floor) / 100
        out.append({"at": [(x0 + x1) / 2, (y0 + y1) / 2, z + 2.55], "size": [(x1 - x0) * 0.5, (y1 - y0) * 0.5],
                    "w": per_m2 * (x1 - x0) * (y1 - y0)})
    return out


def _run(cfg, out):
    p = out / f"cfg-{cfg['tag']}.json"
    p.write_text(json.dumps(cfg, ensure_ascii=False))
    subprocess.run([BLENDER, "-b", "-P", str(ROOT / "tools" / "render_blender.py"), "--", str(p)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render_real(project, rules, style, heights, out_dir, samples=64, res=(1600, 1000)):
    """يرجع {"exterior": [(مسار، اسم)], "dusk": [...], "interior": [...]} ويحفظ shots.json للإعادة."""
    out = Path(out_dir) / "realistic"
    out.mkdir(parents=True, exist_ok=True)
    # WATAD_REAL_PARTS=exterior,dusk → يعيد الخارج فقط ويحتفظ بصور الداخل السابقة (تعديل سقف/واجهة)
    parts = set(os.environ.get("WATAD_REAL_PARTS", "exterior,dusk,interior").split(","))
    for old in out.glob("*.jpg"):
        if (old.name[0] == "i" and "interior" not in parts) or (old.name[0] == "d" and "dusk" not in parts):
            continue
        old.unlink()
    scene = build_scene(project, rules, style, heights, furniture="floors")
    glb = out / "scene.glb"
    scene.write_glb(glb)
    ext = exterior_shots(project)
    inn = interior_shots(project)
    items = plan_furniture(project)
    for it in items:
        it["ceil"] = (project.floor_list[0]["height"] if project.floors else project.wall_height) / 100
    base = {"glb": str(glb), "out_dir": str(out), "tex_dir": TEX, "models_dir": MODELS,
            "colors": {k: style[k] for k in ("wood", "trim", "roof", "frame", "glass", "slab")},
            "views": [], "furnish": items, "furnish_py": str(ROOT / "tools" / "blender_furnish.py"),
            "landscape": plan_landscape(project, keep_clear=[tuple(s[2][:2]) for s in ext]),
            "samples": samples, "res": list(res), "ground_z": -project.slab_height / 100, "lights": [], "lens": 35}
    day = ([[s[0], s[2], s[3], s[4], s[5], 0.0] for s in ext] if "exterior" in parts else []) + \
        ([[s[0], s[2], s[3], s[4], s[5], 0.6] for s in inn] if "interior" in parts else [])
    if day:
        _run({**base, **DAY, "tag": "day", "shots": day, "area_lights": _areas(project, 15)}, out)
    dusk = [["d" + s[0][1:], s[2], s[3], s[4], s[5], 1.2] for s in ext[:2]]
    if "dusk" in parts:
        _run({**base, **DUSK, "tag": "dusk", "shots": dusk, "area_lights": _areas(project, 40)}, out)
    glb.unlink(missing_ok=True)
    meta = {"exterior": [[f"{s[0]}.jpg", s[1]] for s in ext],
            "dusk": [[f"d{s[0][1:]}.jpg", s[1] + " — وقت الغروب"] for s in ext[:2]],
            "interior": [[f"{s[0]}.jpg", s[1]] for s in inn]}
    (out / "shots.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return load_shots(out_dir)


def load_shots(out_dir):
    """الصور الواقعية الموجودة (لإعادة استخدامها بدون رندر جديد، مثل تعديل السعر)."""
    out = Path(out_dir) / "realistic"
    meta = out / "shots.json"
    if not meta.exists():
        return {}
    m = json.loads(meta.read_text(encoding="utf-8"))
    return {k: [(out / f, n) for f, n in v if (out / f).exists()] for k, v in m.items()}
