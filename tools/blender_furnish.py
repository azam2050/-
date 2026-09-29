# يُنفَّذ داخل tools/render_blender.py (exec) عند وجود cfg["furnish"]:
# فرش حقيقي للقطات الداخلية — موديلات CC0 من Poly Haven + قطع إجرائية (سرير، دولاب، مطبخ، حمام)
# بحواف مشطوفة وخامات قماش/خشب/حجر. كل قطعة تُبنى محلياً ووجهها نحو ‎-Y‎ ثم تُدار لاتجاه facing.
import glob
import os

MODELS = cfg.get("models_dir", "/opt/blender/models")


def pmat(name, color, rough=0.5, metal=0.0, bump=0.0, bump_scale=300.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N["Principled BSDF"]
    b.inputs["Base Color"].default_value = hex2rgb(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    if bump:
        tc = N.new("ShaderNodeTexCoord")
        nz = N.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = bump_scale
        nz.inputs["Detail"].default_value = 8
        L.new(tc.outputs["Object"], nz.inputs["Vector"])
        bp = N.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.002
        L.new(nz.outputs["Fac"], bp.inputs["Height"])
        L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def shade_mat():
    m = pmat("F_shade", "#F3E9D8", 0.9)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (1.0, 0.72, 0.42, 1)
    b.inputs["Emission Strength"].default_value = 2.5
    b.inputs["Subsurface Weight"].default_value = 0.3
    return m


FM = {
    "sofa": pmat("F_sofa", "#9A9286", 0.95, bump=0.35),
    "linen": pmat("F_linen", "#F2EFE9", 0.9, bump=0.25, bump_scale=500),
    "duvet": pmat("F_duvet", "#E4DED3", 0.95, bump=0.3, bump_scale=400),
    "pillow": pmat("F_pillow", "#F7F5F1", 0.9, bump=0.2),
    "throw": pmat("F_throw", "#8C6A4E", 1.0, bump=0.6, bump_scale=150),
    "headboard": pmat("F_head", "#B8AD9C", 0.95, bump=0.4),
    "rug": pmat("F_rug", "#C9BFAE", 1.0, bump=0.8, bump_scale=120),
    "cabinet": pmat("F_cab", "#ECE7DF", 0.55),
    "stone": pmat("F_stone", "#DEDAD3", 0.22, bump=0.05, bump_scale=40),
    "steel": pmat("F_steel", "#C8CACC", 0.28, metal=1.0),
    "black": pmat("F_black", "#0B0B0C", 0.08, coat=1.0),
    "shade": shade_mat(),
    "screen": pmat("F_screen", "#050506", 0.35, coat=0.3),
    "ceramic": pmat("F_ceramic", "#F8F8F6", 0.06, coat=0.5),
    "tile": pmat("F_tile", "#E6E3DE", 0.18),
    "mirror": pmat("F_mirror", "#FFFFFF", 0.02, metal=1.0),
    "glass": MATS["glass"],
    "wood": tex_material("F_wood", "WoodFloor043", 1.2, None, bump=0.05),
}


def fbox(parent, mat, x0, y0, z0, x1, y1, z1, bevel=0.008, seg=3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.scale = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        md = o.modifiers.new("bv", "BEVEL")
        md.width = min(bevel, 0.45 * min(o.dimensions))
        md.segments = seg
        md.limit_method = "NONE"
    o.data.materials.append(FM[mat] if isinstance(mat, str) else mat)
    for p in o.data.polygons:
        p.use_smooth = True
    o.parent = parent
    return o


def fcyl(parent, mat, x, y, z0, z1, r, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=z1 - z0, vertices=verts, location=(x, y, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.data.materials.append(FM[mat])
    o.parent = parent
    return o


def holder(it):
    """Empty محلي: الأصل = مركز المستطيل على الأرض، ‎-Y‎ = الوجه. يرجع (empty, W, D)."""
    x0, y0, x1, y1 = it["rect"]
    fx, fy = it["facing"]
    W, D = (x1 - x0, y1 - y0) if abs(fy) >= abs(fx) else (y1 - y0, x1 - x0)
    e = bpy.data.objects.new(it["kind"], None)
    scene.collection.objects.link(e)
    e.location = ((x0 + x1) / 2, (y0 + y1) / 2, it["z"])
    e.rotation_euler = (0, 0, math.atan2(fy, fx) + math.pi / 2)
    return e, W, D


def model(mid, parent, W, D, H=None, z=0.0, rot=0.0, fit="contain"):
    """استيراد موديل Poly Haven وملاءمته لمستطيل W×D (وجهه ‎-Y‎)."""
    f = glob.glob(f"{MODELS}/{mid}/{mid}.gltf")
    if not f:
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f[0])
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(mid, None)
    scene.collection.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    root.rotation_euler = (0, 0, rot)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    dx, dy, dz = hi - lo
    s = min(W / dx, D / dy)
    if H:
        s = min(s, H / dz)
    sc = (s, s, s) if fit == "contain" else (W / dx, D / dy, (H / dz) if H else min(W / dx, D / dy))
    ctr = (lo + hi) / 2
    wrap = bpy.data.objects.new(mid + "_fit", None)
    scene.collection.objects.link(wrap)
    root.parent = wrap
    root.location = (-ctr.x, -ctr.y, -lo.z)
    wrap.scale = sc
    wrap.location = (0, 0, z)
    wrap.parent = parent
    return wrap


# ---------------------------------------------------------------- القطع
def p_bed(it):
    e, W, D = holder(it)
    y0, y1 = -D / 2, D / 2
    fbox(e, "wood", -W / 2, y0, 0.0, W / 2, y1, 0.30, 0.012)
    fbox(e, "linen", -W / 2 + 0.02, y0 + 0.02, 0.30, W / 2 - 0.02, y1 - 0.02, 0.52, 0.05, 5)
    fbox(e, "duvet", -W / 2 - 0.025, y0 - 0.025, 0.34, W / 2 + 0.015, y1 - 0.62, 0.575, 0.06, 6)
    fbox(e, "throw", -W / 2 - 0.02, y0 - 0.02, 0.44, W / 2 + 0.02, y0 + 0.42, 0.59, 0.05, 5)
    n = 2 if W >= 1.35 else 1
    pw = (W - 0.16) / n
    for i in range(n):
        a = -W / 2 + 0.08 + i * pw
        fbox(e, "pillow", a + 0.02, y1 - 0.50, 0.50, a + pw - 0.02, y1 - 0.12, 0.68, 0.08, 6)
    fbox(e, "headboard", -W / 2 - 0.04, y1 - 0.02, 0.0, W / 2 + 0.04, y1 + 0.06, 1.10, 0.03, 4)


def p_wardrobe(it, H=2.20):
    e, W, D = holder(it)
    fbox(e, "wood", -W / 2, -D / 2 + 0.02, 0, W / 2, D / 2, H, 0.006)
    n = max(1, round(W / 0.5))
    dw = W / n
    for i in range(n):
        a = -W / 2 + i * dw
        fbox(e, "cabinet", a + 0.003, -D / 2, 0.06, a + dw - 0.003, -D / 2 + 0.022, H - 0.01, 0.004)
        hx = a + dw - 0.06 if i % 2 == 0 else a + 0.06
        fbox(e, "steel", hx - 0.006, -D / 2 - 0.02, 0.95, hx + 0.006, -D / 2, 1.25, 0.003)


def p_kitchen(it):
    e, W, D = holder(it)
    y0, y1 = -D / 2, D / 2
    fbox(e, "wood", -W / 2, y0 + 0.05, 0, W / 2, y1, 0.10, 0.0)                      # قاعدة
    n = max(1, round(W / 0.6))
    dw = W / n
    for i in range(n):
        a = -W / 2 + i * dw
        fbox(e, "cabinet", a + 0.002, y0, 0.10, a + dw - 0.002, y1, 0.86, 0.004)
        fbox(e, "steel", a + 0.08, y0 - 0.02, 0.78, a + dw - 0.08, y0, 0.795, 0.003)
    fbox(e, "stone", -W / 2, y0 - 0.02, 0.86, W / 2, y1, 0.90, 0.004)
    fbox(e, "tile", -W / 2, y1 - 0.01, 0.90, W / 2, y1, 1.45, 0.0)                  # ظهر مطبخ
    for i in range(n):                                                             # دواليب علوية
        a = -W / 2 + i * dw
        fbox(e, "cabinet", a + 0.002, y1 - 0.34, 1.50, a + dw - 0.002, y1, 2.20, 0.004)
    # مغسلة + خلاط، ومسطح طبخ
    fbox(e, "steel", -W / 4 - 0.25, -0.20, 0.895, -W / 4 + 0.25, 0.20, 0.905, 0.01)
    fbox(e, "steel", -W / 4 - 0.01, 0.22, 0.90, -W / 4 + 0.01, 0.25, 1.18, 0.005)
    fbox(e, "black", W / 4 - 0.30, -0.24, 0.90, W / 4 + 0.30, 0.24, 0.906, 0.003)
    model("wooden_bowl_01", e, 0.30, 0.30, z=0.905).location.x = 0.0


def p_fridge(it):
    e, W, D = holder(it)
    fbox(e, "steel", -W / 2 + 0.01, -D / 2, 0, W / 2 - 0.01, D / 2, 1.85, 0.02, 4)
    fbox(e, "black", -W / 2 + 0.01, -D / 2 - 0.001, 1.20, W / 2 - 0.01, -D / 2 + 0.002, 1.205, 0.0)
    fbox(e, "steel", W / 2 - 0.08, -D / 2 - 0.04, 0.60, W / 2 - 0.06, -D / 2, 1.60, 0.005)


def p_tv(it):
    e, W, D = holder(it)
    fbox(e, "wood", -W / 2, -D / 2, 0.08, W / 2, D / 2, 0.48, 0.006)
    fbox(e, "black", -W / 2 + 0.02, -D / 2 + 0.02, 0.0, W / 2 - 0.02, D / 2 - 0.02, 0.08, 0.0)
    tw = min(1.45, W - 0.1)
    fbox(e, "screen", -tw / 2, D / 2 - 0.05, 0.95, tw / 2, D / 2 - 0.02, 0.95 + tw * 0.5625, 0.006)
    model("potted_plant_02", e, 0.35, 0.3, 0.5, z=0.48).location.x = W / 2 - 0.25
    model("book_encyclopedia_set_01", e, 0.4, 0.14, z=0.48).location.x = -W / 2 + 0.3


def p_sofa(it):
    """كنبة حديثة: قاعدة خشب + مقاعد ومساند قماش بحواف ناعمة + مخدات."""
    e, W, D = holder(it)
    y0, y1 = -D / 2, D / 2
    arm = 0.16
    fbox(e, "wood", -W / 2 + 0.05, y0 + 0.05, 0.0, W / 2 - 0.05, y1 - 0.05, 0.12, 0.005)
    fbox(e, "sofa", -W / 2, y0, 0.12, W / 2, y1, 0.30, 0.03, 4)
    fbox(e, "sofa", -W / 2, y1 - 0.20, 0.30, W / 2, y1, 0.78, 0.06, 5)             # ظهر
    for sx in (-1, 1):                                                              # مساند
        fbox(e, "sofa", sx * W / 2 - (arm if sx > 0 else 0), y0, 0.30,
             sx * W / 2 + (arm if sx < 0 else 0), y1, 0.60, 0.05, 5)
    n = 3 if W > 1.9 else 2
    cw = (W - 2 * arm) / n
    for i in range(n):
        a = -W / 2 + arm + i * cw
        fbox(e, "sofa", a + 0.005, y0 + 0.02, 0.30, a + cw - 0.005, y1 - 0.20, 0.44, 0.06, 6)
        fbox(e, "sofa", a + 0.01, y1 - 0.34, 0.44, a + cw - 0.01, y1 - 0.18, 0.80, 0.07, 6)
    for i, mt in ((0, "throw"), (n - 1, "pillow")):
        a = -W / 2 + arm + i * cw + cw / 2
        fbox(e, mt, a - 0.22, y1 - 0.42, 0.46, a + 0.22, y1 - 0.30, 0.86, 0.07, 6)


def p_armchair(it):
    e, W, D = holder(it)
    model("mid_century_lounge_chair", e, W + 0.1, D + 0.1)


def p_coffee(it):
    e, W, D = holder(it)
    fbox(e, "wood", -W / 2, -D / 2, 0.36, W / 2, D / 2, 0.42, 0.01)
    for lx in (-W / 2 + 0.08, W / 2 - 0.08):
        fbox(e, "wood", lx - 0.03, -D / 2 + 0.06, 0.0, lx + 0.03, D / 2 - 0.06, 0.36, 0.004)
    model("book_encyclopedia_set_01", e, 0.3, 0.12, z=0.42).location.x = -W * 0.2
    rw, rd = W + 1.0, D + 1.2
    fbox(e, "rug", -rw / 2, -rd / 2, 0.0, rw / 2, rd / 2, 0.012, 0.004)
    model("ceramic_vase_01", e, 0.14, 0.14, z=0.42).location.x = W * 0.25


def p_dining(it):
    e, W, D = holder(it)
    model("wooden_table_02", e, W, D, 0.76, fit="stretch")      # بأبعاد المخطط بالضبط
    model("wooden_bowl_01", e, 0.32, 0.32, z=0.76)
    # إضاءة معلقة فوق الطاولة
    lamp = model("modern_ceiling_lamp_01", e, 0.45, 0.45, 0.95, z=it.get("ceil", 2.80) - 0.95)
    L_ = bpy.data.lights.new("pend", "POINT")
    L_.energy = 35
    L_.color = (1.0, 0.80, 0.58)
    L_.shadow_soft_size = 0.05
    o = bpy.data.objects.new("pend", L_)
    o.parent = e
    o.location = (0, 0, it.get("ceil", 2.80) - 0.85)
    scene.collection.objects.link(o)


def p_dchair(it):
    e, W, D = holder(it)
    model("dining_chair_02", e, W + 0.05, D + 0.12)


def p_night(it):
    e, W, D = holder(it)
    model("painted_wooden_nightstand", e, W, D)
    top = 0.60 * min(W / 0.505, D / 0.509)          # ارتفاع الكومودينو بعد الملاءمة
    fcyl(e, "ceramic", 0, 0.03, top, top + 0.28, 0.055)                       # أباجورة
    sh = fcyl(e, "linen", 0, 0.03, top + 0.26, top + 0.46, 0.14)
    sh.data.materials[0] = FM["shade"]
    L_ = bpy.data.lights.new("bedside", "POINT")
    L_.energy = 6
    L_.color = (1.0, 0.75, 0.5)
    L_.shadow_soft_size = 0.08
    o = bpy.data.objects.new("bedside", L_)
    o.parent = e
    o.location = (0, 0.03, top + 0.36)
    o.visible_glossy = False
    scene.collection.objects.link(o)


def p_side(it):
    e, W, D = holder(it)
    model("side_table_01", e, W, D)


def p_shower(it):
    e, W, D = holder(it)
    fbox(e, "ceramic", -W / 2, -D / 2, 0.0, W / 2, D / 2, 0.05, 0.01)
    fbox(e, "glass", -W / 2, -D / 2, 0.05, W / 2 - 0.55, -D / 2 + 0.01, 2.0, 0.002)
    fbox(e, "steel", W / 2 - 0.25, D / 2 - 0.05, 1.95, W / 2 - 0.05, D / 2, 1.97, 0.004)


def p_wc(it):
    e, W, D = holder(it)
    fbox(e, "ceramic", -0.18, -D / 2, 0.0, 0.18, D / 2 - 0.12, 0.40, 0.10, 6)
    fbox(e, "ceramic", -0.19, D / 2 - 0.14, 0.40, 0.19, D / 2, 0.78, 0.03, 4)


def p_basin(it):
    e, W, D = holder(it)
    fbox(e, "wood", -W / 2, -D / 2, 0.20, W / 2, D / 2, 0.82, 0.006)
    fbox(e, "ceramic", -W / 2 + 0.02, -D / 2 + 0.02, 0.82, W / 2 - 0.02, D / 2 - 0.02, 0.88, 0.02, 4)
    fbox(e, "mirror", -W / 2 + 0.03, D / 2 - 0.012, 1.10, W / 2 - 0.03, D / 2, 1.80, 0.004)


BUILD = {"bed": p_bed, "wardrobe": p_wardrobe, "kitchen": p_kitchen, "fridge": p_fridge, "tv": p_tv,
         "sofa": p_sofa, "armchair": p_armchair, "coffee_table": p_coffee, "dining_table": p_dining,
         "dining_chair": p_dchair, "nightstand": p_night, "side_table": p_side,
         "shower": p_shower, "wc": p_wc, "basin": p_basin}

for it in cfg.get("furnish", []):
    fn = BUILD.get(it["kind"])
    if fn:
        fn(it)

# نبتة في ركن كل غرفة معيشة/نوم فاضٍ
for pl in cfg.get("plants", []):
    e = bpy.data.objects.new("plant", None)
    scene.collection.objects.link(e)
    e.location = pl["at"]
    model(pl.get("model", "potted_plant_01"), e, 0.55, 0.55, 1.25)

# إضاءة داخلية ناعمة (مسطحة مخفية تحت السقف) بدل النقاط الساطعة
for i, a in enumerate(cfg.get("area_lights", [])):
    L_ = bpy.data.lights.new(f"area{i}", "AREA")
    L_.shape = "RECTANGLE"
    L_.size, L_.size_y = a["size"]
    L_.energy = a.get("w", 120)
    L_.color = (1.0, 0.86, 0.70)
    o = bpy.data.objects.new(f"area{i}", L_)
    o.location = a["at"]
    o.visible_camera = False
    o.visible_glossy = False
    scene.collection.objects.link(o)


# ---------------------------------------------------------------- المحيط الخارجي (نسخ مرتبطة خفيفة)
_COLL = {}


def coll(mid):
    if mid in _COLL:
        return _COLL[mid]
    f = glob.glob(f"{MODELS}/{mid}/{mid}.gltf")
    if not f:
        _COLL[mid] = None
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f[0])
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = bpy.data.collections.new("C_" + mid)
    for o in new:
        for uc in list(o.users_collection):
            uc.objects.unlink(o)
        c.objects.link(o)
    c.instance_offset = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)
    _COLL[mid] = (c, hi - lo)
    return _COLL[mid]


def inst(mid, at, H=None, W=None, rot=0.0):
    got = coll(mid)
    if not got:
        return None
    c, d = got
    s = H / d.z if H else W / max(d.x, d.y)
    e = bpy.data.objects.new(mid, None)
    e.instance_type = "COLLECTION"
    e.instance_collection = c
    e.scale = (s, s, s)
    e.location = at
    e.rotation_euler = (0, 0, rot)
    scene.collection.objects.link(e)
    return e


for it in cfg.get("landscape", []):
    if it.get("kind") == "paver":
        x, y, z = it["at"]
        w, d = it["size"]
        fbox(None, FM["stone"], x - w / 2, y - d / 2, z, x + w / 2, y + d / 2, z + 0.04, 0.01)
        continue
    inst(it["model"], it["at"], it.get("H"), it.get("W"), math.radians(it.get("rot", 0)))
