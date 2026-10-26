"""جلسة شتوية لبلكونة قائمة 2.80 × 1.50 م — مشهد Blender مستقل (واقعي):
الموجود فعلاً: بلاط رمادي كبير، جدار حجر خشن (جهة البيت) + جدار لياسة بيج بالطرف، باب سحاب ألمنيوم أسود، ودروة لياسة.
الإضافة: جلسة أرضية L بمساند ومخدات، سجادة كليم، طاولة خشب دائرية عليها مبخرة نار نحاس ودلة، رفوف خشب بنباتات وشموع،
سدو معلّق، فوانيس، وإنارة حبال تحت سقف خشب.
تشغيل: blender -b -P balcony_scene.py -- <out_dir> <tex_dir> <models_dir> <samples> <gpu 0/1>
"""
import bpy, math, random, sys, os, glob
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, TEX, MODELS = argv[0], argv[1], argv[2]
SAMPLES, GPU = int(argv[3]), argv[4] == "1"
PCT = int(argv[5]) if len(argv) > 5 else 100
HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(7)
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def hexc(h, a=1.0):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*c, a)


MATS = {}


def mat(name, color="#888888", rough=0.6, metal=0.0, emit=None, strength=0.0, alpha=1.0, trans=0.0, sheen=0.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hexc(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    if trans:
        b.inputs["Transmission Weight"].default_value = trans
        b.inputs["IOR"].default_value = 1.45
    if emit:
        b.inputs["Emission Color"].default_value = hexc(emit)
        b.inputs["Emission Strength"].default_value = strength
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    MATS[name] = m
    return m


def texmat(name, asset, tile, tint=None, rough=None, bump=0.4, img=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    if img:
        L.new(tc.outputs["UV"], mp.inputs["Vector"])
    else:
        mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1 / tile)
        L.new(tc.outputs["Object"], mp.inputs["Vector"])

    def load(path, nc=False):
        n = N.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(path)
        if not img:
            n.projection = "BOX"
            n.projection_blend = 0.25
        if nc:
            n.image.colorspace_settings.name = "Non-Color"
        L.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n
    if img:
        c = load(img)
        L.new(c.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = rough or 0.9
        b.inputs["Sheen Weight"].default_value = 0.5
        return m
    f = glob.glob(f"{TEX}/{asset}/{asset}_2K-JPG_Color.jpg")[0]
    c = load(f)
    if tint:
        mix = N.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        L.new(c.outputs["Color"], mix.inputs[6])
        mix.inputs[7].default_value = hexc(tint)
        L.new(mix.outputs[2], b.inputs["Base Color"])
    else:
        L.new(c.outputs["Color"], b.inputs["Base Color"])
    r = glob.glob(f"{TEX}/{asset}/{asset}_2K-JPG_Roughness.jpg")
    if r and rough is None:
        L.new(load(r[0], True).outputs["Color"], b.inputs["Roughness"])
    else:
        b.inputs["Roughness"].default_value = rough or 0.7
    n = glob.glob(f"{TEX}/{asset}/{asset}_2K-JPG_NormalGL.jpg")
    if n:
        nm = N.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = bump
        L.new(load(n[0], True).outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m


def box(m, x0, y0, z0, x1, y1, z1, bevel=0.0, name="b"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.name = name
    o.scale = (x1 - x0, y1 - y0, z1 - z0)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new("bv", "BEVEL")
        bv.width, bv.segments = bevel, 4
        bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    return o


def cyl(m, x, y, z0, z1, r, verts=40, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=z1 - z0, vertices=verts, location=(x, y, (z0 + z1) / 2))
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=z1 - z0, vertices=verts, location=(x, y, (z0 + z1) / 2))
    o = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    return o


def plight(loc, w, color="#FFB46B", r=0.03):
    d = bpy.data.lights.new("L", "POINT")
    color = "#FFC890" if color in ("#FFB566", "#FFA54D") else color
    d.energy, d.shadow_soft_size = w, r
    d.color = hexc(color)[:3]
    o = bpy.data.objects.new("L", d)
    o.location = loc
    scene.collection.objects.link(o)
    return o


_COLL = {}


def model(mid, at, H=None, W=None, rot=0.0):
    if mid not in _COLL:
        f = glob.glob(f"{MODELS}/{mid}/{mid}.gltf")
        if not f:
            _COLL[mid] = None
        else:
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
    got = _COLL[mid]
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


# ---------------------------------------------------------------- المواد
M_TILE = texmat("tile", "Tiles107", 3.2, tint="#BDB8B0", rough=0.45, bump=0.12)
M_STONE = texmat("stone", "Bricks111A", 1.1, tint="#E2D6C2", bump=1.2)
M_STUCCO = texmat("stucco", "Plaster001", 0.8, tint="#CDBFAE", bump=0.6)
M_WOOD = texmat("wood", "Planks037A", 1.5, tint="#B98654", bump=0.4)
M_WOODD = texmat("woodd", "Planks037A", 1.2, tint="#7A5232", bump=0.5)
M_ALU = mat("alu", "#2A2622", 0.35, 0.8)
M_GLASS = mat("glass", "#DDE6EA", 0.02, trans=1.0)
M_CREAM = mat("cream", "#EFE6D6", 0.95, sheen=0.8)
M_SHERPA = mat("sherpa", "#F4EEE3", 1.0, sheen=1.0)
M_RUST = mat("rust", "#7E3520", 0.9, sheen=0.5)
M_TERRA = mat("terra", "#A65A30", 0.9, sheen=0.5)
M_BEIGE = mat("beige", "#B9A07E", 0.95, sheen=0.6)
M_KNIT = mat("knit", "#6E5442", 1.0, sheen=0.8)
M_KILIM = texmat("kilim", None, 1, img=os.path.join(HERE, "kilim.png"))
M_SADU = texmat("sadu", None, 1, img=os.path.join(HERE, "sadu.png"))
M_COPPER = mat("copper", "#C7764A", 0.25, 1.0)
M_BRASS = mat("brass", "#C9A04E", 0.22, 1.0)
M_CUP = mat("cup", "#F7F4EE", 0.2)
M_BLACK = mat("black", "#151312", 0.4, 0.6)
M_FLAME = mat("flame", "#FFFFFF", 1, emit="#FF8A2A", strength=40)
M_EMBER = mat("ember", "#200A04", 0.9, emit="#FF4A10", strength=4)
M_CANDLE = mat("candle", "#F3E9D8", 0.6, emit="#FFB566", strength=0.4)
M_BULB = mat("bulb", "#FFFFFF", 0.1, emit="#FFD9A0", strength=45)
M_WIRE = mat("wire", "#1A1A1A", 0.6)
M_LEAF = mat("leaf", "#3F5A2E", 0.6)
M_CURTAIN = mat("curtain", "#F2EEE8", 0.9, emit="#FFD9A8", strength=1.2)
M_SOIL = mat("soil", "#3A2A1E", 1.0)

X1, Y1, H = 2.80, 1.50, 3.00          # البلكونة: x على الطول، y من جدار البيت (0) للدروة (1.50)

# ---------------------------------------------------------------- الموجود: الأرضية والجدران والباب والدروة
box(M_TILE, -0.1, -0.1, -0.05, X1 + 0.1, Y1 + 0.25, 0.0)
box(M_STONE, -0.1, -0.12, 0.0, 2.0, 0.0, H)                       # جدار البيت حجر خشن
box(M_STONE, 2.78, -0.12, 0.0, X1 + 0.1, 0.0, H)
box(M_STONE, 2.0, -0.12, 2.42, 2.78, 0.0, H)                      # فوق الباب
box(M_STUCCO, -0.25, -0.12, 0.0, 0.0, Y1 + 0.25, H)                # الطرف (لياسة)
box(M_STUCCO, X1, -0.12, 0.0, X1 + 0.25, Y1 + 0.25, H)
box(M_STUCCO, -0.25, Y1, 0.0, X1 + 0.25, Y1 + 0.22, 1.05)          # الدروة
box(M_STUCCO, -0.25, Y1 - 0.03, 1.05, X1 + 0.25, Y1 + 0.25, 1.10, bevel=0.01)
# باب سحاب ألمنيوم أسود + ستارة بيضاء مضاءة من الداخل
for x0, x1 in ((2.0, 2.04), (2.74, 2.78), (2.37, 2.41)):
    box(M_ALU, x0, -0.10, 0.0, x1, -0.02, 2.42)
box(M_ALU, 2.0, -0.10, 2.38, 2.78, -0.02, 2.42)
box(M_ALU, 2.0, -0.10, 0.0, 2.78, -0.02, 0.05)
box(M_GLASS, 2.04, -0.07, 0.05, 2.74, -0.06, 2.38)
box(M_ALU, 2.33, -0.02, 1.0, 2.35, 0.01, 1.25)                    # مقبض
for i in range(14):                                               # ستارة كسرات
    x = 2.02 + i * 0.054
    cyl(M_CURTAIN, x, -0.22 + (0.03 if i % 2 else 0), 0.02, 2.4, 0.03, 12)
plight((2.4, -1.0, 2.0), 120, "#FFD7A6", 0.5)

# ---------------------------------------------------------------- سقف خشب (تحسين) + إنارة حبال
box(M_WOOD, -0.25, -0.12, H, X1 + 0.25, Y1 + 0.25, H + 0.03)
for k in range(7):
    box(M_WOODD, -0.25, 0.1 + k * 0.23, H - 0.05, X1 + 0.25, 0.16 + k * 0.23, H)


def string_lights(p0, p1, sag, n):
    pts = []
    for i in range(n + 1):
        t = i / n
        p = Vector(p0).lerp(Vector(p1), t)
        p.z -= sag * 4 * t * (1 - t)
        pts.append(p)
    for a, b in zip(pts, pts[1:]):
        mid, v = (a + b) / 2, b - a
        bpy.ops.mesh.primitive_cylinder_add(radius=0.003, depth=v.length, location=mid)
        o = bpy.context.active_object
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(v.normalized())
        o.data.materials.append(M_WIRE)
    for k, p in enumerate(pts[1:-1]):
        cyl(M_BLACK, p.x, p.y, p.z - 0.03, p.z, 0.012, 12)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.028, location=(p.x, p.y, p.z - 0.06))
        bpy.ops.object.shade_smooth()
        bpy.context.active_object.data.materials.append(M_BULB)
        if k % 3 == 1:
            plight((p.x, p.y, p.z - 0.12), 6, "#FFB566", 0.05)


string_lights((0.05, 1.42, 2.92), (2.75, 1.42, 2.92), 0.28, 15)
string_lights((0.05, 0.12, 2.92), (1.95, 0.12, 2.92), 0.18, 10)
string_lights((0.08, 0.15, 2.9), (0.08, 1.4, 2.9), 0.15, 7)

# ---------------------------------------------------------------- الجلسة الأرضية L
D = 0.66
box(M_WOODD, 0.0, 0.0, 0.0, 1.88, D, 0.12, bevel=0.01)            # قاعدة خشب
box(M_WOODD, 0.0, D, 0.0, D, 1.44, 0.12, bevel=0.01)
box(M_SHERPA, 0.02, 0.02, 0.12, 1.86, D - 0.02, 0.27, bevel=0.05)  # فرشة
box(M_CREAM, 0.02, D - 0.02, 0.12, D - 0.02, 1.42, 0.27, bevel=0.05)
# مساند الظهر على الجدارين
cols = [M_RUST, M_BEIGE, M_TERRA, M_CREAM, M_RUST]
for i, x in enumerate((0.25, 0.62, 0.99, 1.36, 1.70)):
    o = box(cols[i % 5], x - 0.18, 0.02, 0.27, x + 0.18, 0.20, 0.72, bevel=0.07)
    o.rotation_euler = (math.radians(-9), 0, 0)
for i, y in enumerate((0.9, 1.25)):
    o = box(cols[(i + 2) % 5], 0.02, y - 0.17, 0.27, 0.20, y + 0.17, 0.70, bevel=0.07)
    o.rotation_euler = (0, math.radians(9), 0)
# مخدات صغيرة
for (x, y, r, m) in ((0.45, 0.30, 15, M_TERRA), (1.12, 0.28, -10, M_BEIGE), (0.32, 1.05, 70, M_RUST), (1.55, 0.30, 8, M_CREAM)):
    o = box(m, x - 0.2, y - 0.07, 0.27, x + 0.2, y + 0.07, 0.62, bevel=0.06)
    o.rotation_euler = (math.radians(-14), 0, math.radians(r))
# بطانية صوف مسدولة على الركن

# ---------------------------------------------------------------- سجادة كليم + طاولة + مبخرة + دلة
rug = box(M_KILIM, 0.62, 0.62, 0.0, 2.05, 1.42, 0.012)
bpy.ops.object.select_all(action="DESELECT")
rug.select_set(True)
bpy.context.view_layer.objects.active = rug
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.uv.cube_project(cube_size=1.0)
bpy.ops.object.mode_set(mode="OBJECT")
for f in rug.data.polygons:                                       # UV للوجه العلوي على كامل الصورة
    pass
me = rug.data
uvl = me.uv_layers.active
for poly in me.polygons:
    for li in poly.loop_indices:
        v = me.vertices[me.loops[li].vertex_index].co
        uvl.data[li].uv = ((v.x + 0.5), (v.y + 0.5))
TX, TY, TR = 1.22, 1.02, 0.30
cyl(M_WOODD, TX, TY, 0.34, 0.38, TR, 48)
for a in range(4):
    ang = math.pi / 4 + a * math.pi / 2
    cyl(M_WOODD, TX + 0.18 * math.cos(ang), TY + 0.18 * math.sin(ang), 0.012, 0.34, 0.025, 12)
cyl(M_WOODD, TX, TY, 0.10, 0.13, 0.2, 32)
# مبخرة/موقد نحاس بنار
cyl(M_COPPER, TX - 0.06, TY + 0.02, 0.38, 0.40, 0.07, 32)
cyl(M_COPPER, TX - 0.06, TY + 0.02, 0.40, 0.48, 0.07, 32, r2=0.11)
cyl(M_EMBER, TX - 0.06, TY + 0.02, 0.465, 0.475, 0.095, 32)
for k in range(5):
    a = k * 1.256
    cyl(M_FLAME, TX - 0.06 + 0.03 * math.cos(a), TY + 0.02 + 0.03 * math.sin(a), 0.47, 0.58 + 0.03 * (k % 2), 0.022, 12, r2=0.0)
plight((TX - 0.06, TY + 0.02, 0.62), 35, "#FF8A3A", 0.04)
# دلة نحاس
dx, dy = TX + 0.13, TY - 0.06
cyl(M_BRASS, dx, dy, 0.38, 0.40, 0.065, 32)
cyl(M_BRASS, dx, dy, 0.40, 0.52, 0.07, 32, r2=0.045)
cyl(M_BRASS, dx, dy, 0.52, 0.58, 0.035, 32, r2=0.05)
cyl(M_BRASS, dx, dy, 0.58, 0.63, 0.02, 16, r2=0.0)
bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.16, location=(dx - 0.08, dy, 0.55))
o = bpy.context.active_object
o.rotation_euler = (0, math.radians(-55), 0)
o.data.materials.append(M_BRASS)
# فناجين + صحن تمر
for (x, y) in ((TX + 0.02, TY - 0.2), (TX + 0.2, TY + 0.12)):
    cyl(M_CUP, x, y, 0.38, 0.385, 0.05, 24)
    cyl(M_CUP, x, y, 0.385, 0.43, 0.028, 24, r2=0.034)
model("wooden_bowl_01", (TX - 0.05, TY + 0.2, 0.38), W=0.18)

# ---------------------------------------------------------------- رفوف خشب على جدار الطرف + نباتات وشموع
for z in (1.30, 1.72):
    box(M_WOOD, 0.0, 0.72, z - 0.03, 0.24, 1.42, z, bevel=0.004)
    for y in (0.78, 1.36):
        box(M_BLACK, 0.0, y - 0.01, z - 0.12, 0.2, y + 0.01, z - 0.03)


def candle(x, y, z, h=0.12, r=0.035):
    cyl(M_CANDLE, x, y, z, z + h, r, 20)
    cyl(M_FLAME, x, y, z + h, z + h + 0.035, 0.008, 8, r2=0.0)
    plight((x, y, z + h + 0.05), 1.2, "#FFA54D", 0.01)


def lantern(x, y, z, s=1.0):
    w = 0.11 * s
    h = 0.30 * s
    box(M_BLACK, x - w, y - w, z, x + w, y + w, z + 0.02)
    box(M_BLACK, x - w, y - w, z + h, x + w, y + w, z + h + 0.025)
    for dx_, dy_ in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        box(M_BLACK, x + dx_ * w - 0.008, y + dy_ * w - 0.008, z, x + dx_ * w + 0.008, y + dy_ * w + 0.008, z + h)
    box(M_GLASS, x - w + 0.01, y - w + 0.01, z + 0.02, x + w - 0.01, y + w - 0.01, z + h)
    cyl(M_BLACK, x, y, z + h + 0.025, z + h + 0.08, w * 0.7, 16, r2=0.01)
    candle(x, y, z + 0.02, 0.12 * s, 0.03 * s)


model("potted_plant_02", (0.12, 0.85, 1.30), H=0.3)
candle(0.12, 1.05, 1.30, 0.1)
candle(0.12, 1.13, 1.30, 0.16, 0.03)
model("potted_plant_04", (0.12, 1.32, 1.30), H=0.28)
model("potted_plant_01", (0.12, 0.95, 1.72), H=0.3)
lantern(0.12, 1.25, 1.72, 0.8)
# سدو معلّق على الجدار الحجر فوق الجلسة + أباليك فوانيس
box(M_SADU, 0.85, 0.005, 0.95, 1.45, 0.02, 1.95)
uvl = None
sad = bpy.context.active_object
me = sad.data
me.uv_layers.new()
uvl = me.uv_layers.active
for poly in me.polygons:
    for li in poly.loop_indices:
        v = me.vertices[me.loops[li].vertex_index].co
        uvl.data[li].uv = ((v.x + 0.5), (v.z + 0.5))
cyl(M_WOODD, 1.15, 0.03, 1.96, 1.96 + 0.001, 0.01)
bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=0.7, location=(1.15, 0.03, 1.97))
o = bpy.context.active_object
o.rotation_euler = (0, math.radians(90), 0)
o.data.materials.append(M_WOODD)
for x in (0.45, 1.80):
    box(M_BLACK, x - 0.01, 0.0, 1.95, x + 0.01, 0.16, 1.97)
    lantern(x, 0.14, 1.62, 0.85)
# فانوس أرضي بالركن (قبل الباب) + نباتات حجر عند الدروة
lantern(2.15, 1.30, 0.0, 1.0)
for (x, y, mdl) in ((2.52, 1.22, "potted_plant_01"),):
    box(texmat("planter", "Concrete034", 0.6, tint="#D8CDBD", bump=0.8), x - 0.2, y - 0.17, 0.0, x + 0.2, y + 0.17, 0.42, bevel=0.01)
    box(M_SOIL, x - 0.18, y - 0.15, 0.39, x + 0.18, y + 0.15, 0.41)
    model(mdl, (x, y, 0.40), H=0.85)

# ---------------------------------------------------------------- الخلفية: سماء ليل + أضواء مدينة بعيدة
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = hexc("#0B1530")
bg.inputs["Strength"].default_value = 0.6
M_CITY = mat("city", "#FFFFFF", 1, emit="#FFC98A", strength=8)
for _ in range(260):
    x = random.uniform(-30, 33)
    y = random.uniform(25, 70)
    z = random.uniform(-14, -4) + (y - 25) * 0.08
    s = random.uniform(0.04, 0.12)
    box(M_CITY, x, y, z, x + s, y + 0.01, z + s)
box(mat("ground", "#06080D", 1.0), -60, 12, -16, 60, 90, -15)
moon = bpy.data.lights.new("moon", "SUN")
moon.energy, moon.color = 0.08, hexc("#9FB4E0")[:3]
mo = bpy.data.objects.new("moon", moon)
mo.rotation_euler = (math.radians(55), 0, math.radians(200))
scene.collection.objects.link(mo)

# ---------------------------------------------------------------- الريندر
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
if GPU:
    cp = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            cp.compute_device_type = kind
            cp.get_devices()
            devs = [d for d in cp.devices if d.type == kind]
            if devs:
                for d in cp.devices:
                    d.use = d.type == kind
                scene.cycles.device = "GPU"
                break
        except Exception as e:  # noqa: BLE001
            print("gpu", kind, e)
cy = scene.cycles
cy.samples = SAMPLES
cy.use_denoising = True
cy.denoiser = "OPENIMAGEDENOISE"
cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces, cy.transmission_bounces = 10, 5, 5, 10
cy.blur_glossy = 0.5
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -0.15
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 95

SHOTS = [
    ("b1", (2.66, 0.55, 1.58), (0.25, 0.95, 0.55), 15, (1200, 1700)),     # من الباب (مثل المرجع)
    ("b2", (2.55, 1.30, 1.55), (0.3, 0.25, 0.65), 16, (1700, 1100)),      # من ركن الدروة على الجلسة والسدو
    ("b3", (1.20, 1.38, 1.05), (0.1, 0.4, 0.7), 14, (1700, 1100)),        # قريب على الطاولة والرفوف
]
for name, cam, tgt, lens, res in SHOTS:
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    co = bpy.data.objects.new(name, cd)
    co.location = cam
    d = Vector(tgt) - Vector(cam)
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(co)
    scene.camera = co
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = PCT
    scene.render.filepath = os.path.join(OUT, name + ".jpg")
    bpy.ops.render.render(write_still=True)
print("DONE")
