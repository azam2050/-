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


def ext_lights(project, rules, spacing=0.9):
    """سبوت تحت رفرف السقف والمثلثات البارزة + مظلة المدخل + فوانيس جنب الأبواب الخارجية (بالمتر)."""
    import math as _m
    from .model import outer_bbox, wall_thickness
    from .roof import cross_gables, roof_geometry
    x0, y0, x1, y1 = (v / 100 for v in outer_bbox(project, rules))
    r = project.roof
    H = project.roof_base / 100
    ov = r.overhang / 100
    tp = _m.tan(_m.radians(r.pitch_deg))
    rise = roof_geometry(project, rules)["rise"] / 100
    pts = []
    if r.type == "tent_hip":
        pts = tent_lights(project)
    elif r.type != "shed":
        zs = H - 0.12
        if r.ridge_axis == "x":
            for yy in (y0 - ov * 0.55, y1 + ov * 0.55):
                n = max(2, int((x1 - x0) / spacing))
                pts += [[x0 + (x1 - x0) * (k + 0.5) / n, yy, zs, 6, "spot"] for k in range(n)]
            for xx, sg in ((x0, -1), (x1, 1)):            # رفرف الجملون على الجنبين
                for k in range(1, 9):
                    f = k / 9
                    yy = y0 + (y1 - y0) / 2 * f
                    pts.append([xx + sg * ov * 0.55, yy, H + rise * f - 0.18, 6, "spot"])
                    pts.append([xx + sg * ov * 0.55, y1 - (y1 - y0) / 2 * f, H + rise * f - 0.18, 6, "spot"])
        else:
            for xx in (x0 - ov * 0.55, x1 + ov * 0.55):
                n = max(2, int((y1 - y0) / spacing))
                pts += [[xx, y0 + (y1 - y0) * (k + 0.5) / n, zs, 6, "spot"] for k in range(n)]
    for g in cross_gables(project, rules):                # تحت رفرف المثلثات البارزة (على المائل)
        c, hw, wall, sg = g["c"] / 100, g["hw"] / 100, g["wall"] / 100, g["sg"]
        zr, Hg = g["zr"] / 100, g["H"] / 100
        for k in range(1, 7):
            f = k / 7
            for side in (-1, 1):
                a = c + side * hw * (1 - f)
                z = Hg + (zr - Hg) * f - 0.2
                o = wall + sg * g["ov"] / 100 * 0.55
                pts.append([a, o, z, 6, "spot"] if g["axis"] == "x" else [o, a, z, 6, "spot"])
    half = wall_thickness(rules) / 2
    for pc in project.porches:
        w = next(w_ for w_ in project.walls if w_.name == pc["wall"])
        x, y = w.point(pc["offset"] + pc["width"] / 2, -half - pc.get("depth", 120) / 2)
        pts.append([x / 100, y / 100, (project.level(w.floor) + pc.get("eave", 240) - 8) / 100, 25, "spot"])
    for w in project.walls:                              # فوانيس جنب الأبواب الخارجية
        if not w.exterior:
            continue
        for o in w.openings:
            if o.kind != "door" or o.leaves == 0:
                continue
            for t in (o.offset - 22, o.offset + o.width + 22):
                x, y = w.point(t, -half - 0.12 * 100)
                pts.append([x / 100, y / 100, (project.level(w.floor) + 205) / 100, 18, "lamp"])
    return pts


CM_KEYS = ("rect", "line", "at", "from", "to", "z", "top", "ceil", "r", "dia", "hgt", "pitch", "sw", "sd", "bw", "bh",
           "aw", "ah", "slat_w", "fw", "fh", "gap", "spacing", "thick", "tile", "drop", "art_z", "sconce_z")


def ground_holes(project):
    """فتحات في أرضية العشب للمسابح والجلسات المدفونة (بالمتر)."""
    if not project.site:
        return []
    from .site import expand
    return [[v / 100 for v in z["rect"]] for z in expand(project.site).get("zones", [])
            if z["kind"] in ("pool", "sunken")]


def decor_items(project):
    """interior_decor بالمشروع (سم) → بالمتر لـ tools/blender_decor.py."""
    def cm(v):
        return [cm(x) for x in v] if isinstance(v, (list, tuple)) else v / 100
    return [{k: (cm(v) if k in CM_KEYS else v) for k, v in d.items()} for d in project.decor]


def tent_lights(project):
    """سقف الخيمة المنساب: سبوتات تحت الرفرف المنساب (كل ~1.2 م) بمستوى سطحه."""
    from .tent_roof import units
    pts = []
    for g in units(project):
        x0, y0, x1, y1 = g["rect"]
        ex0, ey0, ex1, ey1 = g["eave"]
        H, t2 = g["H"], g["t2"]
        for (a, b, fixed, d_out, alongx) in ((x0, x1, y0 - g["of"] * 0.45, g["of"] * 0.45, True),
                                             (x0, x1, y1 + g["ob"] * 0.5, g["ob"] * 0.5, True),
                                             (y0, y1, x0 - g["os"] * 0.5, g["os"] * 0.5, False),
                                             (y0, y1, x1 + g["os"] * 0.5, g["os"] * 0.5, False)):
            n = max(2, int((b - a) / 120))
            z = (H - t2 * d_out - 14) / 100
            for k in range(n):
                v = a + (b - a) * (k + 0.5) / n
                pts.append([v / 100, fixed / 100, z, 8, "spot"] if alongx else [fixed / 100, v / 100, z, 8, "spot"])
    return pts


def _areas(project, per_m2):
    out = []
    for r in project.rooms:
        x0, y0, x1, y1 = (v / 100 for v in r.rect)
        z = project.level(r.floor) / 100
        out.append({"at": [(x0 + x1) / 2, (y0 + y1) / 2, z + 2.55], "size": [(x1 - x0) * 0.5, (y1 - y0) * 0.5],
                    "w": per_m2 * (x1 - x0) * (y1 - y0)})
    return out


def _run(cfg, out):
    if os.environ.get("WATAD_GPU"):      # الرندر على كرت شاشة سحابي
        from . import gpu
        return gpu.run(cfg, Path(out))
    p = out / f"cfg-{cfg['tag']}.json"
    p.write_text(json.dumps(cfg, ensure_ascii=False))
    subprocess.run([BLENDER, "-b", "-P", str(ROOT / "tools" / "render_blender.py"), "--", str(p)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render_real(project, rules, style, heights, out_dir, samples=64, res=(1600, 1000)):
    """يرجع {"exterior": [(مسار، اسم)], "dusk": [...], "interior": [...]} ويحفظ shots.json للإعادة."""
    out = Path(out_dir) / "realistic"
    out.mkdir(parents=True, exist_ok=True)
    # WATAD_REAL_PARTS=exterior,dusk → يعيد الخارج فقط ويحتفظ بصور الداخل السابقة (تعديل سقف/واجهة)
    parts = set(os.environ.get("WATAD_REAL_PARTS", "exterior,dusk,interior,pano").split(","))
    for old in out.glob("*.jpg"):
        if (old.name[0] == "x" and "exterior" not in parts) or (old.name[0] == "i" and "interior" not in parts) or (old.name[0] in "dn" and "dusk" not in parts) or \
                (old.name.startswith("pano") and "pano" not in parts):
            continue
        old.unlink()
    scene = build_scene(project, rules, style, heights, furniture="floors")
    glb = out / "scene.glb"
    scene.write_glb(glb)
    ext = exterior_shots(project)
    inn = interior_shots(project)
    rs = project.render or {}
    if rs.get("exterior"):           # لقطات خارجية محددة بالمشروع (سم) — للمواقع العامة (سور ووحدات)
        ext = [[f"x{k + 1}", s_["name"], [v / 100 for v in s_["cam"]], [v / 100 for v in s_["target"]],
                s_.get("lens", 24), s_.get("shift", 0.0)] for k, s_ in enumerate(rs["exterior"])]
    if rs.get("interior"):           # لقطات داخلية محددة بالمشروع (سم)
        inn = [[f"i{k + 1}", s_["name"], [v / 100 for v in s_["cam"]], [v / 100 for v in s_["target"]],
                s_.get("lens", 17), s_.get("shift", -0.06)] for k, s_ in enumerate(rs["interior"])]
    items = plan_furniture(project)
    for it in items:
        it["ceil"] = (project.floor_list[0]["height"] if project.floors else project.wall_height) / 100
    base = {"glb": str(glb), "out_dir": str(out), "tex_dir": TEX, "models_dir": MODELS,
            "colors": {k: style[k] for k in ("wood", "trim", "roof", "frame", "glass", "slab")},
            "views": [], "furnish": items, "furnish_py": str(ROOT / "tools" / "blender_furnish.py"),
            "landscape": plan_landscape(project, keep_clear=[tuple(s[2][:2]) for s in ext]),
            "wood_frames": style.get("frame_ar", "").startswith("إطار خشب"),
            "samples": samples, "res": list(res), "ground_z": -project.slab_height / 100, "lights": [], "lens": 35,
            "decor": decor_items(project), "sadu": bool(rs.get("sadu")), "pano_res": rs.get("pano_res", [2400, 1200]), "ground_holes": ground_holes(project),
            "site_wall": ((project.site or {}).get("wall") or {}).get("finish", "plaster"),
            "palette": rs.get("palette", {}),
            "hq": rs.get("quality", "high") != "draft"}
    pano = lambda key: [[p_["name"], [v / 100 for v in p_["at"]], p_.get("yaw", 0)]  # noqa: E731
                        for p_ in rs.get("panos", []) if p_.get(key, key == "day")]
    lk = rs.get("ext_lens_k", 1.0)       # تقريب اللقطات الخارجية
    ext = [s[:4] + [round(s[4] * lk), round(min(0.3, s[5] * lk), 3)] for s in ext]
    day = ([[s[0], s[2], s[3], s[4], s[5], 0.0] for s in ext] if "exterior" in parts else []) + \
        ([[s[0], s[2], s[3], s[4], s[5], rs.get("day_exposure", 0.9 if rs.get("quality", "high") != "draft" else 0.6)] for s in inn] if "interior" in parts else [])
    if day:
        _run({**base, **DAY, **({"sky_hdr": "sky_day.hdr", "sky": 1.0} if base["hq"] and Path(TEX, "sky_day.hdr").exists() else {}), "tag": "day", "shots": day, "panos": pano("day") if "pano" in parts else [], "area_lights": _areas(project, 5 if project.decor else 15)}, out)
    dusk = [["d" + s[0][1:], s[2], s[3], s[4], s[5], 1.2] for s in ext[:2]]
    night_in = [["n" + s[0][1:], s[2], s[3], s[4], s[5], rs.get("night_exposure", 0.4)] for s in inn[:rs.get("night_interior", 0)]]
    dusk += night_in
    if "dusk" in parts or "nightpano" in parts:
        _run({**base, **DUSK, "tag": "dusk", "night": True, "shots": dusk if "dusk" in parts else [],
              "panos": pano("night") if "pano" in parts or "nightpano" in parts else [], "pano_exposure": 1.3,
              "area_lights": _areas(project, 10 if project.decor else 40),
              "ext_lights": ext_lights(project, rules)}, out)
    glb.unlink(missing_ok=True)
    meta = {"exterior": [[f"{s[0]}.jpg", s[1]] for s in ext],
            "dusk": [[f"d{s[0][1:]}.jpg", s[1] + " — وقت الغروب"] for s in ext[:2]] +
                    [[f"n{s[0][1:]}.jpg", s[1] + " — بالليل والإنارة شغالة"] for s in inn[:len(night_in)]],
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


def bake_web(project, rules, style, heights, out_dir, samples=128, res=2048):
    """مجسم الويب بإضاءة مخبوزة (نهار + ليل) — نفس مشهد الرندر: web.glb + lm_*.jpg + lm.json في out_dir."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scene = build_scene(project, rules, style, heights, furniture="floors")
    glb = out / "scene.glb"
    scene.write_glb(glb)
    items = plan_furniture(project)
    for it in items:
        it["ceil"] = (project.floor_list[0]["height"] if project.floors else project.wall_height) / 100
    rs = project.render or {}
    hq = rs.get("quality", "high") != "draft"
    day = {**DAY, "lamps": 0.25}
    if hq and Path(TEX, "sky_day.hdr").exists():
        day.update({"sky_hdr": "sky_day.hdr", "sky": 1.0})
    cfg = {"glb": str(glb), "out_dir": str(out), "tex_dir": TEX, "models_dir": MODELS,
           "colors": {k: style[k] for k in ("wood", "trim", "roof", "frame", "glass", "slab")},
           "views": [], "furnish": items, "furnish_py": str(ROOT / "tools" / "blender_furnish.py"),
           "landscape": [], "wood_frames": style.get("frame_ar", "").startswith("إطار خشب"),
           "samples": samples, "res": [800, 600], "ground_z": -project.slab_height / 100, "lights": [], "lens": 35,
           "decor": decor_items(project), "sadu": bool(rs.get("sadu")), "ground_holes": ground_holes(project),
           "hq": hq, **DUSK, "tag": "bake", "night": True, "shots": [], "panos": [],
           "area_lights": _areas(project, 10 if project.decor else 40), "ext_lights": ext_lights(project, rules),
           "bake": {"script": str(ROOT / "tools" / "bake_web.py"), "out_dir": str(out), "res": res,
                    "samples": samples, "day": day, "max_tex": 1024}}
    if os.environ.get("WATAD_GPU"):
        from . import gpu
        gpu.run(cfg, out)
        glb.unlink(missing_ok=True)
        return out / "web.glb"
    p = out / "cfg-bake.json"
    p.write_text(json.dumps(cfg, ensure_ascii=False))
    r = subprocess.run([BLENDER, "-b", "-P", str(ROOT / "tools" / "render_blender.py"), "--", str(p)],
                       capture_output=True, text=True)
    (out / "bake.log").write_text(r.stdout[-20000:] + r.stderr[-5000:])
    glb.unlink(missing_ok=True)
    return out / "web.glb"
