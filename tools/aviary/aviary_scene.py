"""محمية طيور 30 × 15 م — مشهد Blender واقعي (هيكل حديد مجلفن + شبك + سقف خشب + شلال وبحيرة + ممر حجري
+ أشجار مثمرة ومجاثم وطيور + إنارة LED).
تشغيل: blender -b -P aviary_scene.py -- <out_dir> <tex_dir> <models_dir> <samples> <gpu 0/1> [pct]
"""
import bpy, math, random, sys, os, glob
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, TEX, MODELS = argv[0], argv[1], argv[2]
SAMPLES, GPU = int(argv[3]), argv[4] == "1"
PCT = int(argv[5]) if len(argv) > 5 else 100
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as Y  # noqa: E402

random.seed(11)
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def hexc(h, a=1.0):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return (*[x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c], a)


def mat(name, color="#888888", rough=0.6, metal=0.0, emit=None, strength=0.0, trans=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hexc(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if trans:
        b.inputs["Transmission Weight"].default_value = trans
    if emit:
        b.inputs["Emission Color"].default_value = hexc(emit)
        b.inputs["Emission Strength"].default_value = strength
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def texmat(name, asset, tile, tint=None, bump=0.5, rough=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tile,) * 3
    L.new(tc.outputs["Object"], mp.inputs["Vector"])

    def load(kind, nc=False):
        f = glob.glob(f"{TEX}/{asset}/{asset}_2K-JPG_{kind}.jpg")
        if not f:
            return None
        n = N.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(f[0])
        n.projection = "BOX"
        n.projection_blend = 0.3
        if nc:
            n.image.colorspace_settings.name = "Non-Color"
        L.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n
    c = load("Color")
    if tint:
        mx = N.new("ShaderNodeMix")
        mx.data_type, mx.blend_type = "RGBA", "MULTIPLY"
        mx.inputs["Factor"].default_value = 1.0
        L.new(c.outputs["Color"], mx.inputs[6])
        mx.inputs[7].default_value = hexc(tint)
        L.new(mx.outputs[2], b.inputs["Base Color"])
    else:
        L.new(c.outputs["Color"], b.inputs["Base Color"])
    r = load("Roughness", True)
    if r and rough is None:
        L.new(r.outputs["Color"], b.inputs["Roughness"])
    else:
        b.inputs["Roughness"].default_value = rough or 0.8
    n = load("NormalGL", True)
    if n:
        nm = N.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = bump
        L.new(n.outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m


def mesh_mat(axes=("X", "Z"), name="mesh"):
    """شبك حديد مجلفن: خطوط شبكة إجرائية بالشفافية (محورين حسب اتجاه الجدار)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    out = N["Material Output"]
    b = N["Principled BSDF"]
    b.inputs["Base Color"].default_value = hexc("#9AA1A8")
    b.inputs["Metallic"].default_value = 0.8
    b.inputs["Roughness"].default_value = 0.45
    tr = N.new("ShaderNodeBsdfTransparent")
    mix = N.new("ShaderNodeMixShader")
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs["Vector"])
    vals = []
    for comp in axes:
        mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 1 / 0.05
        L.new(sep.outputs[comp], mul.inputs[0])
        fr = N.new("ShaderNodeMath"); fr.operation = "FRACT"
        L.new(mul.outputs[0], fr.inputs[0])
        lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.07
        L.new(fr.outputs[0], lt.inputs[0])
        vals.append(lt)
    mx1 = N.new("ShaderNodeMath"); mx1.operation = "MAXIMUM"
    L.new(vals[0].outputs[0], mx1.inputs[0]); L.new(vals[1].outputs[0], mx1.inputs[1])
    L.new(mx1.outputs[0], mix.inputs["Fac"])
    L.new(tr.outputs[0], mix.inputs[1])
    L.new(b.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    m.blend_method = "HASHED"
    return m


def box(m, x0, y0, z0, x1, y1, z1, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.scale = (x1 - x0, y1 - y0, z1 - z0)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new("bv", "BEVEL")
        bv.width, bv.segments = bevel, 3
    o.data.materials.append(m)
    return o


def cyl(m, x, y, z0, z1, r, verts=24, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=z1 - z0, vertices=verts, location=(x, y, (z0 + z1) / 2))
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=z1 - z0, vertices=verts, location=(x, y, (z0 + z1) / 2))
    o = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    return o


def rod(m, a, b, r):
    a, b = Vector(a), Vector(b)
    v = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=v.length, vertices=10, location=(a + b) / 2)
    o = bpy.context.active_object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(v.normalized())
    o.data.materials.append(m)
    return o


def beam(m, a, b, w, h):
    """جسر خشب مستطيل بين نقطتين (عرض w وارتفاع h، معلّق تحت الخط)."""
    a, b = Vector(a), Vector(b)
    v = b - a
    bpy.ops.mesh.primitive_cube_add(size=1, location=(a + b) / 2 - Vector((0, 0, h / 2)))
    o = bpy.context.active_object
    o.scale = (v.length, w, h)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((1, 0, 0)).rotation_difference(v.normalized())
    bv = o.modifiers.new("bv", "BEVEL")
    bv.width, bv.segments = 0.006, 2
    o.data.materials.append(m)
    return o


def plight(loc, w, color="#FFC47A", r=0.05):
    d = bpy.data.lights.new("L", "POINT")
    d.energy, d.shadow_soft_size, d.color = w, r, hexc(color)[:3]
    o = bpy.data.objects.new("L", d)
    o.location = loc
    scene.collection.objects.link(o)
    return o


def smooth(pts, n=8):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in [j / n for j in range(n)]:
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in (0, 1)))
    out.append(pts[-1])
    return out


def strip(m, pts, w, z, name="strip"):
    """شريط (ممر/مجرى) مسطح حول خط المنتصف."""
    verts, faces = [], []
    for k, (x, y) in enumerate(pts):
        a = pts[max(k - 1, 0)]
        b = pts[min(k + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        nx, ny = -dy / n * w / 2, dx / n * w / 2
        verts += [(x + nx, y + ny, z), (x - nx, y - ny, z)]
        if k:
            i = 2 * k
            faces.append((i - 2, i - 1, i + 1, i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    o.data.materials.append(m)
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
    e.instance_type, e.instance_collection = "COLLECTION", c
    e.scale, e.location, e.rotation_euler = (s, s, s), at, (0, 0, rot)
    scene.collection.objects.link(e)
    return e


# ---------------------------------------------------------------- المواد
M_STEEL = mat("steel", "#8E959C", 0.35, 0.9)
M_MESH = mesh_mat(("X", "Z"), "mesh_x")
M_MESHY = mesh_mat(("Y", "Z"), "mesh_y")
M_POLY = texmat("roofwood", "japanese_cedar_planks", 1.6, tint="#F2D3A6", bump=0.8)   # سقف خشب سيدر (لسان ومجرى)
M_GLU = texmat("glulam", "hinoki_planks", 1.2, tint="#B07A45", bump=0.6)          # جسور خشب مصفّح
M_SHINGLE = texmat("shingle", "WoodSiding008", 1.0, tint="#B07A48", bump=1.0)    # الوجه الخارجي: ألواح خشب معالج
M_STONEW = texmat("stonewall", "Bricks111A", 1.2, tint="#E6D9C3", bump=1.0)
M_PATH = texmat("path", "Bricks111A", 0.8, tint="#CDBEA5", bump=0.9)
M_SOIL = texmat("soil", "Grass004", 2.0, tint="#B8A27E", bump=0.6)
M_GRASS = texmat("grass", "Grass004", 1.2, tint="#9DBB76", bump=0.5)
M_WATER = mat("water", "#3E7F95", 0.02, trans=0.85)
M_ROCK = texmat("rock", "Concrete034", 1.0, tint="#A89782", bump=1.6)
M_WOOD = texmat("wood", "Planks037A", 1.2, tint="#A5713F", bump=0.4)
M_BARK = mat("bark", "#5B4330", 0.9)
M_WALL = texmat("wall", "Plaster001", 1.0, tint="#E4DACB", bump=0.4)
M_LED = mat("led", "#FFFFFF", 0.3, emit="#FFC98A", strength=18)
M_ORANGE = mat("orange", "#E8861E", 0.5)
M_MANGO = mat("mango", "#E0A53A", 0.5)
M_FOAM = mat("foam", "#F4F8FA", 0.3, emit="#FFFFFF", strength=0.2)
BIRD = [mat("b1", "#D7261E", 0.5), mat("b2", "#1F8A3B", 0.5), mat("b3", "#2A5FC7", 0.5), mat("b4", "#F2C21B", 0.5)]

# ---------------------------------------------------------------- الأرض
box(M_GRASS, -40, -40, -0.06, 70, 55, -0.01)
box(texmat("bed", "Grass004", 1.0, tint="#A8C27E", bump=0.6), 0.0, 0.0, -0.01, Y.L, Y.W, 0.0)
sp = smooth(Y.PATH)
strip(M_PATH, sp, Y.PATH_W, 0.02, "path")
for s_ in Y.SPURS:
    strip(M_PATH, smooth(s_), Y.PATH_W * 0.85, 0.021, "spur")
strip(M_PATH, [(14.9, -2.2), (15.0, 0.0)], 1.6, 0.02, "entry")
strip(M_PATH, [(15.0, -9.0), (14.9, -2.2)], 2.0, 0.0, "walk")
# حدود الممر (حجر صغير)
for side in (-1, 1):
    pts = []
    for k, (x, y) in enumerate(sp):
        a = sp[max(k - 1, 0)]; b = sp[min(k + 1, len(sp) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; n = math.hypot(dx, dy) or 1
        pts.append((x - dy / n * Y.PATH_W / 2 * side, y + dx / n * Y.PATH_W / 2 * side))
    strip(M_ROCK, pts, 0.12, 0.05, "edge")

# البحيرة: حفرة + ماء + حواف صخر
cx, cy, rx, ry = Y.POND
bpy.ops.mesh.primitive_circle_add(vertices=64, radius=1, fill_type="NGON", location=(cx, cy, 0.03))
w = bpy.context.active_object
w.scale = (rx, ry, 1)
w.data.materials.append(M_WATER)
box(mat("pondbed", "#2E4A3E", 0.9), cx - rx, cy - ry, -0.35, cx + rx, cy + ry, -0.3)
for k in range(46):
    a = 2 * math.pi * k / 46
    x, y = cx + (rx + 0.1) * math.cos(a), cy + (ry + 0.1) * math.sin(a)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=random.uniform(0.18, 0.32), location=(x, y, 0.05))
    o = bpy.context.active_object
    o.scale = (1.2, 1.0, 0.55)
    o.rotation_euler = (0, 0, random.uniform(0, 3))
    o.data.materials.append(M_ROCK)
# المجرى
strip(M_WATER, smooth(Y.STREAM), 0.55, 0.035, "stream")
for (x, y) in smooth(Y.STREAM)[::3]:
    for s in (-1, 1):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=random.uniform(0.12, 0.22), location=(x + s * 0.32, y - s * 0.12, 0.05))
        bpy.context.active_object.data.materials.append(M_ROCK)
# الشلال: كومة صخر + شريحة ماء نازلة + رغوة
fx, fy, fr, fh = Y.FALL
for k in range(26):
    a = random.uniform(0, 2 * math.pi)
    rr = random.uniform(0, fr)
    z = (1 - rr / fr) * fh * random.uniform(0.6, 1.0)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=random.uniform(0.35, 0.7),
                                          location=(fx + rr * math.cos(a), fy + rr * math.sin(a), z))
    o = bpy.context.active_object
    o.scale = (1.3, 1.0, 0.8)
    o.data.materials.append(M_ROCK)
box(mat("fallw", "#CFE6EE", 0.05, trans=0.6, emit="#E8F6FF", strength=0.4), fx - 0.75, fy - 0.95, 0.05, fx - 0.25, fy - 0.85, fh * 0.85)
for k in range(8):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.12, 0.2), location=(fx - 0.5 + random.uniform(-0.3, 0.3), fy - 1.05, 0.06))
    bpy.context.active_object.data.materials.append(M_FOAM)
plight((fx - 0.5, fy - 1.8, 0.4), 60, "#CFE9FF", 0.3)

# منصة المشاهدة + جلسة
d = Y.DECK
box(M_WOOD, d[0], d[1], 0.0, d[2], d[3], 0.25)
box(M_WOOD, d[0] + 0.3, d[3] - 0.6, 0.25, d[2] - 0.3, d[3] - 0.15, 0.7)
box(M_WOOD, d[0] + 0.3, d[3] - 0.25, 0.7, d[2] - 0.3, d[3] - 0.15, 1.15)
for x in (d[0] + 0.05, d[2] - 0.05):
    box(M_WOOD, x - 0.05, d[1], 0.25, x + 0.05, d[3], 1.0)

# ---------------------------------------------------------------- الهيكل
for x in Y.COL_X:
    for y in (0.0, Y.W):
        box(M_STEEL, x - 0.05, y - 0.05, 0.0, x + 0.05, y + 0.05, Y.H_EAVE)
for y in Y.COL_Y[1:-1]:
    for x in (0.0, Y.L):
        h = Y.H_EAVE + (Y.H_RIDGE - Y.H_EAVE) * (1 - abs(y - Y.W / 2) / (Y.W / 2))
        box(M_STEEL, x - 0.05, y - 0.05, 0.0, x + 0.05, y + 0.05, h)
# جسور الطول + الجملون (عوارض عرضية كل 3 م)
for y in (0.0, Y.W):
    box(M_STEEL, 0, y - 0.05, Y.H_EAVE - 0.1, Y.L, y + 0.05, Y.H_EAVE)
for x in Y.COL_X:
    beam(M_GLU, (x, 0, Y.H_EAVE), (x, Y.W / 2, Y.H_RIDGE), 0.12, 0.28)
    beam(M_GLU, (x, Y.W, Y.H_EAVE), (x, Y.W / 2, Y.H_RIDGE), 0.12, 0.28)
for k in range(1, 4):
    for y0 in (Y.W / 2 * k / 4, Y.W - Y.W / 2 * k / 4):
        z = Y.H_EAVE + (Y.H_RIDGE - Y.H_EAVE) * (k / 4)
        beam(M_GLU, (0, y0, z), (Y.L, y0, z), 0.08, 0.12)
beam(M_GLU, (0, Y.W / 2, Y.H_RIDGE), (Y.L, Y.W / 2, Y.H_RIDGE), 0.16, 0.32)
# السقف خشب: ألواح خشب معالج على جسور ومدادات خشب (سطحين)
for (ya, yb) in ((0.0, Y.W / 2), (Y.W, Y.W / 2)):
    me = bpy.data.meshes.new("roof")
    me.from_pydata([(-0.2, ya, Y.H_EAVE + 0.02), (Y.L + 0.2, ya, Y.H_EAVE + 0.02), (Y.L + 0.2, yb, Y.H_RIDGE + 0.02),
                    (-0.2, yb, Y.H_RIDGE + 0.02)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("roof", me)
    scene.collection.objects.link(o)
    o.data.materials.append(M_POLY)
    o2 = o.copy(); o2.data = o.data.copy(); scene.collection.objects.link(o2)
    o2.location.z += 0.05
    o2.data.materials[0] = M_SHINGLE
    sol = o.modifiers.new("s", "SOLIDIFY")
    sol.thickness = 0.03
# الشبك: الجدران الأربعة (فوق قاعدة الحجر) + مثلثات الجملون
box(M_STONEW, -0.1, -0.12, 0.0, Y.L + 0.1, 0.12, Y.PLINTH)
box(M_STONEW, -0.1, Y.W - 0.12, 0.0, Y.L + 0.1, Y.W + 0.12, Y.PLINTH)
box(M_STONEW, -0.12, 0, 0.0, 0.12, Y.W, Y.PLINTH)
box(M_STONEW, Y.L - 0.12, 0, 0.0, Y.L + 0.12, Y.W, Y.PLINTH)
for (x0, y0, x1, y1) in ((0, 0, Y.L, 0), (0, Y.W, Y.L, Y.W)):
    me = bpy.data.meshes.new("mesh")
    me.from_pydata([(x0, y0, Y.PLINTH), (x1, y1, Y.PLINTH), (x1, y1, Y.H_EAVE), (x0, y0, Y.H_EAVE)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("mesh", me)
    scene.collection.objects.link(o)
    o.data.materials.append(M_MESH)
for x in (0.0, Y.L):
    me = bpy.data.meshes.new("mesh")
    me.from_pydata([(x, 0, Y.PLINTH), (x, Y.W, Y.PLINTH), (x, Y.W, Y.H_EAVE), (x, Y.W / 2, Y.H_RIDGE), (x, 0, Y.H_EAVE)], [],
                   [(0, 1, 2, 3, 4)])
    o = bpy.data.objects.new("mesh", me)
    scene.collection.objects.link(o)
    o.data.materials.append(M_MESHY)
# شريط LED دافي تحت الجسور الطولية
for y in (0.12, Y.W - 0.12):
    box(M_LED, 0.3, y - 0.015, Y.H_EAVE - 0.14, Y.L - 0.3, y + 0.015, Y.H_EAVE - 0.12)
# غرفة الأمان (بابين) قدام المدخل
a = Y.AIRLOCK
for (x, y) in ((a[0], a[1]), (a[2], a[1]), (a[0], a[3]), (a[2], a[3])):
    box(M_STEEL, x - 0.05, y - 0.05, 0, x + 0.05, y + 0.05, 2.5)
box(M_STEEL, a[0], a[1], 2.45, a[2], a[3], 2.5)
box(M_POLY, a[0] - 0.1, a[1] - 0.1, 2.5, a[2] + 0.1, a[3], 2.52)
for (x0, y0, x1, y1) in ((a[0], a[1], a[0], a[3]), (a[2], a[1], a[2], a[3])):
    me = bpy.data.meshes.new("am")
    me.from_pydata([(x0, y0, 0), (x1, y1, 0), (x1, y1, 2.45), (x0, y0, 2.45)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("am", me); scene.collection.objects.link(o); o.data.materials.append(M_MESHY)
for (d0, d1) in (Y.DOOR_OUT,):
    for x in (d0, d1):
        box(M_STEEL, x - 0.03, a[1] - 0.03, 0, x + 0.03, a[1] + 0.03, 2.1)
    box(M_STEEL, d0, a[1] - 0.03, 2.07, d1, a[1] + 0.03, 2.13)
    me = bpy.data.meshes.new("dm")
    me.from_pydata([(d0, a[1], 0.05), (d1, a[1], 0.05), (d1, a[1], 2.07), (d0, a[1], 2.07)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("dm", me); scene.collection.objects.link(o); o.data.materials.append(M_MESH)
for x in (a[0], d0, d1, a[2]):
    pass
for (x0, x1) in ((a[0], Y.DOOR_OUT[0]), (Y.DOOR_OUT[1], a[2])):
    me = bpy.data.meshes.new("af")
    me.from_pydata([(x0, a[1], 0), (x1, a[1], 0), (x1, a[1], 2.45), (x0, a[1], 2.45)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("af", me); scene.collection.objects.link(o); o.data.materials.append(M_MESH)
box(M_STEEL, 15.4, a[1] - 0.06, 1.0, 15.43, a[1] - 0.02, 1.15)
# غرفة الخدمة (جدران مصمتة)
s = Y.SERVICE
for (x0, y0, x1, y1) in ((s[0], s[1], s[2], s[1] + 0.12), (s[2] - 0.12, s[1], s[2], s[3])):
    box(M_WALL, x0, y0, 0, x1, y1, 2.8)
box(M_WALL, s[0], s[1], 2.8, s[2], s[3], 2.9)
box(mat("sdoor", "#6E7378", 0.4, 0.6), s[2] - 0.13, s[1] + 0.6, 0.0, s[2] + 0.01, s[1] + 1.5, 2.1)

# ---------------------------------------------------------------- الزراعة
for x, y, k in Y.TREES:
    if k == "palm":
        cyl(M_BARK, x, y, 0, 2.2, 0.12, 12, r2=0.09)
        for j in range(9):
            ang = j * 2 * math.pi / 9
            rod(mat("frond%d" % j, "#4E7A32", 0.6), (x, y, 2.2), (x + 1.1 * math.cos(ang), y + 1.1 * math.sin(ang), 1.75), 0.05)
        continue
    model("tree_small_02", (x, y, 0), H=random.uniform(2.6, 2.85), rot=random.uniform(0, 6))
    fm = M_ORANGE if k == "citrus" else M_MANGO
    for j in range(16):
        ang = random.uniform(0, 2 * math.pi)
        rr = random.uniform(0.4, 0.95)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05 if k == "citrus" else 0.06, segments=10, ring_count=6,
                                             location=(x + rr * math.cos(ang), y + rr * math.sin(ang), random.uniform(1.2, 2.1)))
        bpy.context.active_object.data.materials.append(fm)
def _free(x, y, r=1.0):
    """نقطة زراعة بعيدة عن الممر والبحيرة والمنصة وغرفة الخدمة والشلال."""
    if any(math.hypot(x - px, y - py) < Y.PATH_W / 2 + r * 0.7 for px, py in sp):
        return False
    for s_ in Y.SPURS:
        if any(math.hypot(x - px, y - py) < Y.PATH_W / 2 + r * 0.7 for px, py in smooth(s_)):
            return False
    if ((x - cx) / (rx + 1.0)) ** 2 + ((y - cy) / (ry + 1.0)) ** 2 < 1:
        return False
    if d[0] - 0.4 < x < d[2] + 0.4 and d[1] - 0.4 < y < d[3] + 0.4:
        return False
    if x < Y.SERVICE[2] + 0.4 and y > Y.SERVICE[1] - 0.4:
        return False
    if math.hypot(x - fx, y - fy) < fr + 0.5 or not (0.5 < x < Y.L - 0.5 and 0.5 < y < Y.W - 0.5):
        return False
    return True


extra, tries = [], 0
while len(extra) < 70 and tries < 4000:
    tries += 1
    x, y = random.uniform(0.6, Y.L - 0.6), random.uniform(0.6, Y.W - 0.6)
    if _free(x, y, 0.6) and all(math.hypot(x - a_, y - b_) > 0.9 for a_, b_ in extra):
        extra.append((x, y))
for i, (x, y) in enumerate(extra):
    model(("shrub_01", "shrub_02", "shrub_04")[i % 3], (x, y, 0), H=random.uniform(0.6, 1.4), rot=random.uniform(0, 6))
for i, (x, y) in enumerate(Y.SHRUBS):
    if not _free(x, y, 0.5):
        continue
    model(("shrub_01", "shrub_02", "shrub_04")[i % 3], (x, y, 0), H=random.uniform(0.7, 1.1), rot=random.uniform(0, 6))
# مجاثم جذوع + طيور
birds = []
for i, (x, y) in enumerate(Y.PERCHES):
    rod(M_BARK, (x - 0.1, y, 0), (x, y, 1.9), 0.07)
    rod(M_BARK, (x, y, 1.6), (x + 0.8, y + 0.2, 2.1), 0.04)
    rod(M_BARK, (x, y, 1.3), (x - 0.7, y - 0.2, 1.7), 0.04)
    birds += [(x + 0.55, y + 0.14, 1.99), (x - 0.5, y - 0.14, 1.62)]
for x, y in Y.FEEDERS:
    cyl(M_WOOD, x, y, 0, 1.0, 0.05)
    box(M_WOOD, x - 0.4, y - 0.4, 1.0, x + 0.4, y + 0.4, 1.05)
    box(M_WOOD, x - 0.5, y - 0.5, 1.45, x + 0.5, y + 0.5, 1.5)
    for (px, py) in ((-0.35, -0.35), (0.35, 0.35), (-0.35, 0.35), (0.35, -0.35)):
        cyl(M_WOOD, x + px, y + py, 1.05, 1.45, 0.02)
    cyl(mat("seed", "#C9A35A", 0.9), x - 0.15, y, 1.05, 1.1, 0.12)
    cyl(M_WATER, x + 0.18, y, 1.05, 1.09, 0.1)
    birds.append((x + 0.2, y - 0.3, 1.12))
for x, y in Y.NESTS:
    box(M_WOOD, x - 0.2, y - 0.3, 2.0, x + 0.2, y - 0.02, 2.4)
    cyl(mat("hole", "#1A120C", 0.9), x, y - 0.31, 2.22, 2.22 + 0.001, 0.05)
for i, (x, y, z) in enumerate(birds):
    m = BIRD[i % 4]
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=(x, y, z + 0.09))
    o = bpy.context.active_object; o.scale = (1.0, 0.8, 1.35); o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.055, location=(x + 0.03, y, z + 0.24))
    bpy.context.active_object.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    cyl(mat("beak%d" % i, "#2B2B2B", 0.4), x + 0.08, y, z + 0.22, z + 0.25, 0.018, 8, r2=0.0)
    rod(m, (x - 0.04, y, z + 0.05), (x - 0.12, y, z - 0.22), 0.025)
# مراوح سقف
for x, y in Y.FANS:
    rod(M_STEEL, (x, y, Y.H_RIDGE - 0.02), (x, y, 2.7), 0.015)
    cyl(mat("fanb", "#2A2A2A", 0.4, 0.5), x, y, 2.6, 2.7, 0.12)
    for j in range(3):
        ang = j * 2 * math.pi / 3
        o = box(mat("blade%d" % j, "#3A2A1E", 0.5), -0.06, 0.12, -0.005, 0.06, 0.75, 0.005)
        o.location = (x, y, 2.63)
        o.rotation_euler = (0, 0, ang)
# إنارة أرضية LED على الممر
acc, last = 0.0, sp[0]
for k, p in enumerate(sp[1:]):
    acc += math.hypot(p[0] - last[0], p[1] - last[1])
    if acc >= Y.BOLLARDS_EVERY:
        acc = 0
        a_ = sp[max(k, 0)]; b_ = sp[min(k + 2, len(sp) - 1)]
        dx, dy = b_[0] - a_[0], b_[1] - a_[1]; n = math.hypot(dx, dy) or 1
        bx, by = p[0] - dy / n * 0.9, p[1] + dx / n * 0.9
        cyl(mat("bol", "#2B2B2B", 0.4, 0.6), bx, by, 0, 0.55, 0.06, 12)
        cyl(M_LED, bx, by, 0.48, 0.53, 0.062, 12)
        plight((bx, by, 0.5), 8, "#FFC47A", 0.03)
    last = p

# إضاءة داخلية ناعمة تحت السقف الخشب (السقف مصمت): ألواح ضوء مخفية عن الكاميرا
AREAS = []
for x in (5.0, 15.0, 25.0):
    for y in (4.0, 11.0):
        L_ = bpy.data.lights.new("fill", "AREA")
        L_.shape, L_.size, L_.size_y = "RECTANGLE", 8.0, 5.5
        L_.color = hexc("#FFF1DC")[:3]
        o = bpy.data.objects.new("fill", L_)
        o.location = (x, y, 2.85)
        o.visible_camera = o.visible_glossy = o.visible_transmission = False
        scene.collection.objects.link(o)
        AREAS.append(L_)

# ---------------------------------------------------------------- الإضاءة والكاميرات
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
WN = world.node_tree.nodes
env = WN.new("ShaderNodeTexEnvironment")
hdr = glob.glob(f"{TEX}/sky_day.hdr") or glob.glob(f"{TEX}/sky.hdr")
env.image = bpy.data.images.load(hdr[0])
world.node_tree.links.new(env.outputs["Color"], WN["Background"].inputs["Color"])
sun_d = bpy.data.lights.new("sun", "SUN")
sun_d.energy, sun_d.angle = 3.2, math.radians(1.5)
sun = bpy.data.objects.new("sun", sun_d)
sun.rotation_euler = (math.radians(42), 0, math.radians(35))
scene.collection.objects.link(sun)

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
if GPU:
    cp = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            cp.compute_device_type = kind
            cp.get_devices()
            if [d for d in cp.devices if d.type == kind]:
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
cy.max_bounces, cy.transparent_max_bounces = 10, 24
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 95
scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
scene.render.resolution_percentage = PCT

SHOTS = [  # (اسم, كاميرا, هدف, عدسة, ليل؟)
    ("a1", (-9.0, -13.0, 11.0), (15.0, 7.0, 0.5), 24, False),       # جوي: المحمية كاملة
    ("a2", (15.0, -9.0, 1.7), (15.0, 2.0, 1.6), 24, False),          # من قدام: المدخل وغرفة الأمان
    ("a3", (15.0, 3.0, 1.65), (27.0, 12.5, 1.0), 18, False),         # من الداخل: الممر والبحيرة والشلال
    ("a4", (15.3, 6.3, 1.6), (24.0, 9.5, 0.9), 18, False),          # من منصة المشاهدة
    ("a5", (3.0, 4.0, 1.7), (27.0, 11.0, 1.0), 18, True),            # ليل: إنارة الممر وتحت الجسور
    ("a6", (34.0, -7.0, 2.2), (15.0, 7.5, 1.6), 22, True),           # ليل من الخارج
]
for name, cam, tgt, lens, night in SHOTS:
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    co = bpy.data.objects.new(name, cd)
    co.location = cam
    co.rotation_euler = (Vector(tgt) - Vector(cam)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(co)
    scene.camera = co
    WN["Background"].inputs["Strength"].default_value = 0.08 if night else 1.0
    sun_d.energy = 0.0 if night else 3.2
    for L_ in AREAS:
        L_.energy = 60 if night else 900
    scene.view_settings.exposure = 1.0 if night else 0.0
    scene.render.filepath = os.path.join(OUT, name + ".jpg")
    bpy.ops.render.render(write_still=True)
print("DONE")
