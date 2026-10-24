# يُنفَّذ داخل tools/render_blender.py (exec) بعد blender_furnish.py عند وجود cfg["decor"]:
# ديكورات داخلية بالخشب وإنارتها (بالمتر): شرائح خشب على الجدار بإضاءة مخفية، جسور خشب ظاهرة بإنارة علوية
# تغسل السقف، إنارة مخفية على رأس الجدار، ثريات خشب معلقة، لوحات، سجاد، مشب معلّق ومشب نار خارجي.
# المحور: x/y بالمخطط، z من وجه الصبة (كلها بالمتر بعد التحويل من سم). w = واط. انظر watad/realistic.py:decor_items.

LED = (1.0, 0.74, 0.45)


def emit_mat(name, color=(1.0, 0.78, 0.5), strength=12.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    em = N.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    L.new(em.outputs[0], N["Material Output"].inputs["Surface"])
    return m


def sadu_mat(name="D_sadu", band="Z", scale=9.0):
    """نقشة السدو: أشرطة أحمر/أسود/أبيض مع مثلثات (موجة مسننة) — قماش الجلسة العربية."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.95
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs["Vector"])
    # الأشرطة على z + مثلثات مسننة
    saw = N.new("ShaderNodeTexWave")
    saw.wave_type = "BANDS"
    saw.bands_direction = band
    saw.wave_profile = "SAW"
    saw.inputs["Scale"].default_value = scale
    L.new(tc.outputs["Object"], saw.inputs["Vector"])
    tri = N.new("ShaderNodeTexWave")
    tri.wave_type = "BANDS"
    tri.bands_direction = "X" if band != "X" else "Y"
    tri.wave_profile = "TRI"
    tri.inputs["Scale"].default_value = scale * 1.6
    L.new(tc.outputs["Object"], tri.inputs["Vector"])
    add = N.new("ShaderNodeMath")
    add.operation = "ADD"
    L.new(saw.outputs["Fac"], add.inputs[0])
    tm = N.new("ShaderNodeMath")
    tm.operation = "MULTIPLY"
    tm.inputs[1].default_value = 0.35
    L.new(tri.outputs["Fac"], tm.inputs[0])
    L.new(tm.outputs[0], add.inputs[1])
    ramp = N.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    cols = [(0.0, "#7A1A16"), (0.32, "#1A1412"), (0.45, "#EDE3CF"), (0.55, "#7A1A16"), (0.78, "#C9A45C"),
            (0.88, "#1A1412")]
    while len(cr.elements) < len(cols):
        cr.elements.new(0.5)
    for el, (p, c) in zip(cr.elements, cols):
        el.position = p
        el.color = hex2rgb(c)
    mod = N.new("ShaderNodeMath")
    mod.operation = "FRACT"
    L.new(add.outputs[0], mod.inputs[0])
    L.new(mod.outputs[0], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


DM = {
    "slat": tex_material("D_slat", "WoodFloor043", 0.6, "#B07A45", 0.35, bump=0.05),
    "slat_dark": tex_material("D_slat_dk", "WoodFloor043", 0.6, "#5A3A22", 0.75, bump=0.05),
    "beam": tex_material("D_beam", "WoodFloor043", 0.9, "#8A5A32", 0.55, bump=0.08),
    "led": emit_mat("D_led", LED, 18.0),
    "flame": emit_mat("D_flame", (1.0, 0.45, 0.12), 45.0),
    "ember": emit_mat("D_ember", (1.0, 0.3, 0.05), 8.0),
    "shade": emit_mat("D_shade", (1.0, 0.7, 0.42), 6.0),
    "black": pmat("D_black", "#121212", 0.35, metal=0.6),
    "stone": pmat("D_stone", "#8F877C", 0.9, bump=0.6, bump_scale=30),
}
if cfg.get("sadu"):                     # قماش الجلسة والسجادة بنقشة السدو (يستبدل خامة الفرش بعد بنائه)
    _sw = {"F_majlis": sadu_mat("D_sadu", "Z", 9.0), "F_majlis_rug": sadu_mat("D_sadu_rug", "Y", 2.2)}
    FM["majlis_rug"] = _sw["F_majlis_rug"]
    for _ob in scene.objects:
        if _ob.type == "MESH":
            for _k, _m in enumerate(_ob.data.materials):
                if _m and _m.name.split(".")[0] in _sw:
                    _ob.data.materials[_k] = _sw[_m.name.split(".")[0]]


def dbox(mat, x0, y0, z0, x1, y1, z1, bevel=0.003):
    o = fbox(None, DM[mat] if isinstance(mat, str) else mat, min(x0, x1), min(y0, y1), min(z0, z1),
             max(x0, x1), max(y0, y1), max(z0, z1), bevel, 2)
    if not bevel:                      # صندوق بدون شطف: تظليل مسطح (الناعم يقلب الإضاءة على الألواح الرقيقة)
        for p_ in o.data.polygons:
            p_.use_smooth = False
    return o


DIM = 1.0 if cfg.get("night") else cfg.get("decor_day", 0.35)   # بالنهار الإنارة أخف (النور الطبيعي هو الأساس)


def area(name, at, size, w, up=True, color=LED):
    w *= DIM
    L_ = bpy.data.lights.new(name, "AREA")
    L_.shape = "RECTANGLE"
    L_.size, L_.size_y = size
    L_.energy = w
    L_.color = color
    o = bpy.data.objects.new(name, L_)
    o.location = at
    if up:
        o.rotation_euler = (math.pi, 0, 0)
    o.visible_camera = False
    o.visible_glossy = False
    scene.collection.objects.link(o)
    return o


def point(name, at, w, r=0.05, color=LED):
    w *= DIM if "fire" not in name and "pit" not in name else 1.0
    L_ = bpy.data.lights.new(name, "POINT")
    L_.energy = w
    L_.shadow_soft_size = r
    L_.color = color
    o = bpy.data.objects.new(name, L_)
    o.location = at
    o.visible_camera = False
    scene.collection.objects.link(o)


def d_slats(i, d):
    """شرائح خشب رأسية على الجدار + رف علوي بإضاءة مخفية تغسل الشرائح وتطلع للسقف."""
    x0, y0, x1, y1 = d["rect"]
    z0, z1 = d["z"]
    alongx = (x1 - x0) >= (y1 - y0)
    nx, ny = d["n"]                         # اتجاه الغرفة (من الجدار للداخل)
    pitch, sw, sd = d.get("pitch", 0.09), d.get("sw", 0.045), d.get("sd", 0.04)
    wall = (y0 if ny > 0 else y1) if alongx else (x0 if nx > 0 else x1)
    a0, a1 = (x0, x1) if alongx else (y0, y1)
    # لوح خلفي غامق ثم الشرائح
    if alongx:
        dbox("slat_dark", a0, wall, z0, a1, wall + ny * 0.015, z1, 0)
    else:
        dbox("slat_dark", wall, a0, z0, wall + nx * 0.015, a1, z1, 0)
    n = int((a1 - a0) / pitch)
    off = (a1 - a0 - n * pitch) / 2
    for k in range(n + 1):
        a = a0 + off + k * pitch
        if alongx:
            dbox("slat", a - sw / 2, wall + ny * 0.015, z0, a + sw / 2, wall + ny * (0.015 + sd), z1)
        else:
            dbox("slat", wall + nx * 0.015, a - sw / 2, z0, wall + nx * (0.015 + sd), a + sw / 2, z1)
    depth = sd + 0.12
    if d.get("shelf", True):                # رف/كورنيش علوي وتحته شريط LED
        if alongx:
            dbox("beam", a0 - 0.05, wall, z1, a1 + 0.05, wall + ny * depth, z1 + 0.06)
            dbox("led", a0, wall + ny * (sd + 0.03), z1 - 0.012, a1, wall + ny * (sd + 0.05), z1)
            dbox("led", a0, wall + ny * (sd + 0.03), z1 + 0.06, a1, wall + ny * (sd + 0.05), z1 + 0.072)
            area(f"sl{i}a", ((a0 + a1) / 2, wall + ny * (sd + 0.06), z1 - 0.02), (a1 - a0, 0.04), 18 * (a1 - a0), up=False)
            area(f"sl{i}b", ((a0 + a1) / 2, wall + ny * (sd + 0.06), z1 + 0.08), (a1 - a0, 0.04), 30 * (a1 - a0))
        else:
            dbox("beam", wall, a0 - 0.05, z1, wall + nx * depth, a1 + 0.05, z1 + 0.06)
            dbox("led", wall + nx * (sd + 0.03), a0, z1 - 0.012, wall + nx * (sd + 0.05), a1, z1)
            dbox("led", wall + nx * (sd + 0.03), a0, z1 + 0.06, wall + nx * (sd + 0.05), a1, z1 + 0.072)
            area(f"sl{i}a", (wall + nx * (sd + 0.06), (a0 + a1) / 2, z1 - 0.02), (0.04, a1 - a0), 18 * (a1 - a0), up=False)
            area(f"sl{i}b", (wall + nx * (sd + 0.06), (a0 + a1) / 2, z1 + 0.08), (0.04, a1 - a0), 30 * (a1 - a0))
    if d.get("base_led", True):             # إضاءة مخفية تحت الجلسة/أسفل الجدار
        if alongx:
            area(f"sl{i}c", ((a0 + a1) / 2, wall + ny * (sd + 0.1), z0 + 0.05), (a1 - a0, 0.04), 6 * (a1 - a0))
        else:
            area(f"sl{i}c", (wall + nx * (sd + 0.1), (a0 + a1) / 2, z0 + 0.05), (0.04, a1 - a0), 6 * (a1 - a0))


def d_beam(i, d):
    """جسر خشب ظاهر (رابط) وفوقه شريط LED يغسل السقف المائل بنور دافئ."""
    (ax, ay, az), (bx, by, bz) = d["from"], d["to"]
    w, h = d.get("bw", 0.16), d.get("bh", 0.28)
    if abs(bx - ax) >= abs(by - ay):
        dbox("beam", ax, ay - w / 2, az - h, bx, ay + w / 2, az)
        if d.get("uplight", True):
            dbox("led", ax + 0.1, ay - 0.02, az, bx - 0.1, ay + 0.02, az + 0.01, 0)
            area(f"bm{i}", ((ax + bx) / 2, ay, az + 0.03), (abs(bx - ax) - 0.2, 0.05), 55 * abs(bx - ax))
    else:
        dbox("beam", ax - w / 2, ay, az - h, ax + w / 2, by, az)
        if d.get("uplight", True):
            dbox("led", ax - 0.02, ay + 0.1, az, ax + 0.02, by - 0.1, az + 0.01, 0)
            area(f"bm{i}", (ax, (ay + by) / 2, az + 0.03), (0.05, abs(by - ay) - 0.2), 55 * abs(by - ay))


def d_cove(i, d):
    """إضاءة مخفية على رأس الجدار (كورنيش خشب) تطلع للسقف المائل."""
    x0, y0, x1, y1 = d["line"]
    z = d["z"]
    nx, ny = d["n"]
    L = math.hypot(x1 - x0, y1 - y0)
    if abs(x1 - x0) >= abs(y1 - y0):
        dbox("beam", x0, y0, z - 0.18, x1, y0 + ny * 0.12, z - 0.02)
        area(f"cv{i}", ((x0 + x1) / 2, y0 + ny * 0.06, z), (L, 0.05), 35 * L)
    else:
        dbox("beam", x0, y0, z - 0.18, x0 + nx * 0.12, y1, z - 0.02)
        area(f"cv{i}", (x0 + nx * 0.06, (y0 + y1) / 2, z), (0.05, L), 35 * L)


def d_pendant(i, d):
    """ثريا خشب: أسطوانة شرائح خشب بداخلها نور، معلقة بسلك من السقف."""
    x, y = d["at"]
    z = d["z"]
    r, h = d.get("dia", 0.5) / 2, d.get("hgt", 0.35)
    top = d.get("ceil", z + 1.0)
    fcyl(None, "black", x, y, z + h, top, 0.004, 8)
    n = 20
    for k in range(n):
        a = 2 * math.pi * k / n
        cx, cy = x + r * math.cos(a), y + r * math.sin(a)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, z + h / 2))
        o = bpy.context.active_object
        o.scale = (0.03, 0.012, h)
        o.rotation_euler = (0, 0, a + math.pi / 2)
        o.data.materials.append(DM["slat"])
    bpy.ops.mesh.primitive_cylinder_add(radius=r * 0.8, depth=h * 0.7, location=(x, y, z + h / 2))
    bpy.context.active_object.data.materials.append(DM["shade"])
    point(f"pd{i}", (x, y, z + h / 2), d.get("w", 90), r * 0.6)


def d_rug(i, d):
    x0, y0, x1, y1 = d["rect"]
    fbox(None, FM["majlis_rug"] if d.get("sadu") else FM["rug"], x0, y0, 0.012, x1, y1, 0.026, 0.006, 2)


def d_art(i, d):
    """لوحة نسيج سدو بإطار خشب غامق + سبوت صغير فوقها."""
    x, y = d["at"]
    z = d["z"]
    nx, ny = d["n"]
    w, h = d.get("aw", 1.0), d.get("ah", 0.7)
    if not hasattr(d_art, "mat"):
        d_art.mat = sadu_mat("D_sadu_art", "Z", 7.0)
    if abs(nx) > abs(ny):
        dbox("slat_dark", x, y - w / 2, z - h / 2, x + nx * 0.04, y + w / 2, z + h / 2)
        dbox(d_art.mat, x + nx * 0.04, y - w / 2 + 0.05, z - h / 2 + 0.05, x + nx * 0.05, y + w / 2 - 0.05, z + h / 2 - 0.05, 0)
    else:
        dbox("slat_dark", x - w / 2, y, z - h / 2, x + w / 2, y + ny * 0.04, z + h / 2)
        dbox(d_art.mat, x - w / 2 + 0.05, y + ny * 0.04, z - h / 2 + 0.05, x + w / 2 - 0.05, y + ny * 0.05, z + h / 2 - 0.05, 0)
    point(f"art{i}", (x + nx * 0.45, y + ny * 0.45, z + h / 2 + 0.2), 20, 0.03)


def d_hanging_fire(i, d):
    """مشب معلّق أسود مفتوح: صحن جمر تحت + لهب ظاهر بالفتحة + قمع ومدخنة لين المشراق، على 3 قضبان."""
    x, y = d["at"]
    z0, top = d.get("z", 0.85), d["top"]
    r = d.get("r", 0.45)
    bpy.ops.mesh.primitive_cone_add(radius1=r * 0.55, radius2=r, depth=0.22, vertices=48, location=(x, y, z0 + 0.11))
    bpy.context.active_object.data.materials.append(DM["black"])            # الصحن
    bpy.ops.mesh.primitive_cylinder_add(radius=r * 0.9, depth=0.02, vertices=48, location=(x, y, z0 + 0.22))
    bpy.context.active_object.data.materials.append(DM["ember"])            # الجمر
    for k in range(7):                                                      # ألسنة لهب
        a = 2 * math.pi * k / 7
        rr = 0.06 + 0.1 * (k % 3) / 2
        bpy.ops.mesh.primitive_cone_add(radius1=0.06, radius2=0.0, depth=0.24 + 0.08 * (k % 3), vertices=12,
                                        location=(x + rr * math.cos(a), y + rr * math.sin(a), z0 + 0.34 + 0.03 * (k % 3)))
        bpy.context.active_object.data.materials.append(DM["flame"])
    zc = z0 + 0.62                                                          # القمع فوق الفتحة
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=0.12, depth=0.75, vertices=48, location=(x, y, zc + 0.375))
    bpy.context.active_object.data.materials.append(DM["black"])
    for k in range(3):                                                      # قضبان تربط الصحن بالقمع
        a = 2 * math.pi * k / 3 + 0.3
        fcyl(None, "black", x + r * 0.93 * math.cos(a), y + r * 0.93 * math.sin(a), z0 + 0.2, zc + 0.02, 0.012, 8)
    fcyl(None, "black", x, y, zc + 0.74, top, 0.11, 32)
    point(f"fire{i}", (x, y, z0 + 0.42), d.get("w", 260), 0.12, (1.0, 0.5, 0.18))


def d_fire_pit(i, d):
    """مشب نار خارجي: حلقة حجر + جمر + لهب ونور."""
    x, y = d["at"]
    z = d.get("z", 0.0)
    r = d.get("r", 0.45)
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.1, location=(x, y, z + 0.1))
    bpy.context.active_object.data.materials.append(DM["stone"])
    fcyl(None, "black", x, y, z, z + 0.12, r - 0.05, 32)
    bpy.ops.mesh.primitive_cylinder_add(radius=r - 0.12, depth=0.04, location=(x, y, z + 0.14))
    bpy.context.active_object.data.materials.append(DM["ember"])
    for k in range(6):
        a = 2 * math.pi * k / 6
        bpy.ops.mesh.primitive_cone_add(radius1=0.08, radius2=0.0, depth=0.35 + 0.1 * (k % 2), vertices=12,
                                        location=(x + 0.12 * math.cos(a), y + 0.12 * math.sin(a), z + 0.33))
        bpy.context.active_object.data.materials.append(DM["flame"])
    point(f"pit{i}", (x, y, z + 0.5), d.get("w", 300), 0.2, (1.0, 0.5, 0.18))


def d_lantern(i, d):
    """فانوس معلّق (تحت المظلة/على العمود)."""
    x, y, z = d["at"]
    dbox("black", x - 0.12, y - 0.12, z - 0.02, x + 0.12, y + 0.12, z)
    dbox("shade", x - 0.1, y - 0.1, z - 0.32, x + 0.1, y + 0.1, z - 0.02, 0)
    dbox("black", x - 0.12, y - 0.12, z - 0.34, x + 0.12, y + 0.12, z - 0.32)
    point(f"ln{i}", (x, y, z - 0.17), d.get("w", 60), 0.08)


# ------------------------------------------------ باقة التصميم الداخلي (مرجع فيديو المصنع)
def _tmat(key, asset, tile, tint, mix=0.85, rough=None, bump=0.2):
    if key not in DM:
        DM[key] = tex_material(f"D_{key}", asset, tile, tint, mix, rough=rough, bump=bump)
    return DM[key]


def _art_mat(k):
    key = f"art{k}"
    if key not in DM:
        m = bpy.data.materials.new(f"D_{key}")
        m.use_nodes = True
        N, L = m.node_tree.nodes, m.node_tree.links
        b = N["Principled BSDF"]
        b.inputs["Roughness"].default_value = 0.55
        t = N.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(f"{TEX}/art/art{k}.jpg", check_existing=True)
        uv = N.new("ShaderNodeTexCoord")
        L.new(uv.outputs["UV"], t.inputs["Vector"])
        L.new(t.outputs["Color"], b.inputs["Base Color"])
        DM[key] = m
        DM[key + "_ar"] = t.image.size[0] / max(1, t.image.size[1])
    return DM[key]


def _plane(mat, p0, u, v):
    """مستطيل رقيق (صورة اللوحة) بإحداثيات UV كاملة: p0 + s*u + t*v."""
    me = bpy.data.meshes.new("pl")
    P = [p0, tuple(p0[i] + u[i] for i in range(3)), tuple(p0[i] + u[i] + v[i] for i in range(3)), tuple(p0[i] + v[i] for i in range(3))]
    me.from_pydata(P, [], [(0, 1, 2, 3)])
    uvl = me.uv_layers.new()
    for li, (a_, b_) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uvl.data[li].uv = (a_, b_)
    o = bpy.data.objects.new("pl", me)
    scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def _wallbox(mat, d, a0, a1, z0, z1, s0, s1, bevel=0.002):
    """صندوق على جدار: a على طول الجدار، s بعيد عن وجه الجدار للداخل (اتجاه n)."""
    (x0, y0, x1, y1), (nx, ny) = d["line"], d["n"]
    alongx = abs(x1 - x0) >= abs(y1 - y0)
    if alongx:
        return dbox(mat, a0, y0 + ny * s0, z0, a1, y0 + ny * s1, z1, bevel)
    return dbox(mat, x0 + nx * s0, a0, z0, x0 + nx * s1, a1, z1, bevel)


def _sconce(name, at, n, w=40, updown=True):
    """أبليك جداري أسطوانة سوداء بنور فوق وتحت (مثل الفيديو)."""
    x, y, z = at
    nx, ny = n
    cx, cy = x + nx * 0.07, y + ny * 0.07
    dbox("black", x + nx * 0.0 - (0.04 if abs(ny) > 0 else 0), y - (0.04 if abs(nx) > 0 else 0), z - 0.05,
         x + nx * 0.03 + (0.04 if abs(ny) > 0 else 0), y + ny * 0.03 + (0.04 if abs(nx) > 0 else 0), z + 0.05)
    fcyl(None, "black", cx, cy, z - 0.11, z + 0.11, 0.035, 20)
    dbox("led", cx - 0.03, cy - 0.03, z + 0.108, cx + 0.03, cy + 0.03, z + 0.112, 0)
    dbox("led", cx - 0.03, cy - 0.03, z - 0.112, cx + 0.03, cy + 0.03, z - 0.108, 0)
    for k, dz in enumerate((1, -1) if updown else (-1,)):
        L_ = bpy.data.lights.new(f"{name}{k}", "SPOT")
        L_.energy = w * DIM
        L_.color = LED
        L_.spot_size = math.radians(55)
        L_.spot_blend = 0.6
        L_.shadow_soft_size = 0.02
        o = bpy.data.objects.new(f"{name}{k}", L_)
        o.location = (cx, cy, z + dz * 0.12)
        o.rotation_euler = (0 if dz > 0 else math.pi, 0, 0)
        o.visible_camera = False
        scene.collection.objects.link(o)


def d_feature_wall(i, d):
    """جدار مميز: دهان رمادي فحمي مطفي + شرائح خشب رأسية على الطرفين + لوحات ببراويز موزعة + أباليك."""
    (x0, y0, x1, y1) = d["line"]
    nx, ny = d["n"]
    alongx = abs(x1 - x0) >= abs(y1 - y0)
    a0, a1 = (min(x0, x1), max(x0, x1)) if alongx else (min(y0, y1), max(y0, y1))
    z0, z1 = d.get("z", [0.0, 2.7])
    sw = d.get("slat_w", 0.36)
    paint = _tmat("paint_" + d.get("color", "#3A3D40").lstrip("#"), "Plaster001", 1.2, d.get("color", "#3A3D40"), 0.92,
                  rough=0.92, bump=0.08)
    _wallbox(paint, d, a0 + sw, a1 - sw, z0, z1, 0.0, 0.012, 0)
    for b0, b1 in ((a0, a0 + sw), (a1 - sw, a1)):                   # شرائح خشب رأسية (فلوتنق) على الطرفين
        _wallbox("slat_dark", d, b0, b1, z0, z1, 0.0, 0.01, 0)
        n = max(3, int((b1 - b0) / 0.06))
        for k in range(n):
            c = b0 + (k + 0.5) * (b1 - b0) / n
            _wallbox("slat", d, c - 0.017, c + 0.017, z0, z1, 0.01, 0.045)
    # لوحات: صف أو صفين حسب الارتفاع المتاح فوق الكنب
    arts = d.get("arts", [1, 2, 3, 4])
    rows = d.get("rows", 1 if len(arts) <= 3 else 2)
    per = math.ceil(len(arts) / rows)
    span = (a1 - a0) - 2 * sw - 0.5
    fh = d.get("fh", 0.55 if rows == 2 else 0.8)
    zc0 = d.get("art_z", 1.55 if rows == 2 else 1.75)
    k = 0
    for r in range(rows):
        cnt = min(per, len(arts) - k)
        fw = min(d.get("fw", 0.75), (span - (cnt - 1) * 0.25) / max(cnt, 1))
        gap = (span - cnt * fw) / (cnt + 1)
        zc = zc0 + (rows - 1 - r) * (fh + 0.22) - (rows - 1) * (fh + 0.22) / 2
        for j in range(cnt):
            art = arts[k]
            k += 1
            m = _art_mat(art)
            ar = DM[f"art{art}_ar"]
            w_, h_ = (fw, min(fh, fw / ar)) if fw / ar <= fh else (fh * ar, fh)
            c = a0 + sw + 0.25 + gap * (j + 1) + fw * j + fw / 2
            fr = 0.035
            _wallbox("black", d, c - w_ / 2 - fr, c + w_ / 2 + fr, zc - h_ / 2 - fr, zc + h_ / 2 + fr, 0.012, 0.045)
            _wallbox(_tmat("mat_white", "Plaster001", 1.0, "#EFEAE0", 0.9, rough=0.9, bump=0.0), d,
                     c - w_ / 2 - 0.004, c + w_ / 2 + 0.004, zc - h_ / 2 - 0.004, zc + h_ / 2 + 0.004, 0.045, 0.047, 0)
            s_ = 0.049
            if alongx:
                y_ = y0 + ny * s_
                sgn = 1 if ny < 0 else -1          # الصورة مواجهة للغرفة
                p0 = (c - sgn * w_ / 2, y_, zc - h_ / 2)
                _plane(m, p0, (sgn * w_, 0, 0), (0, 0, h_))
            else:
                x_ = x0 + nx * s_
                sgn = 1 if nx > 0 else -1
                p0 = (x_, c - sgn * w_ / 2, zc - h_ / 2)
                _plane(m, p0, (0, sgn * w_, 0), (0, 0, h_))
    if d.get("sconces", True):                  # أبليكين على الشرائح
        for c in (a0 + sw / 2, a1 - sw / 2):
            at = (c, y0 + ny * 0.045, d.get("sconce_z", 1.9)) if alongx else (x0 + nx * 0.045, c, d.get("sconce_z", 1.9))
            _sconce(f"fw{i}_{c:.2f}", at, (nx, ny), 35)


def d_downlights(i, d):
    """سبوت لايت غاطس بالسقف موزع منتظم (حلقة سوداء + قرص منير + سبوت للأسفل)."""
    x0, y0, x1, y1 = d["rect"]
    z = d["z"]
    sp = d.get("spacing", 1.2)
    nx_, ny_ = max(1, round((x1 - x0) / sp)), max(1, round((y1 - y0) / sp))
    for a in range(nx_):
        for b in range(ny_):
            x = x0 + (a + 0.5) * (x1 - x0) / nx_
            y = y0 + (b + 0.5) * (y1 - y0) / ny_
            fcyl(None, "black", x, y, z - 0.012, z - 0.002, 0.05, 24)
            bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.004, vertices=24, location=(x, y, z - 0.014))
            bpy.context.active_object.data.materials.append(DM["led"])
            L_ = bpy.data.lights.new(f"dl{i}_{a}_{b}", "SPOT")
            L_.energy = d.get("w", 22) * DIM
            L_.color = (1.0, 0.82, 0.62)
            L_.spot_size = math.radians(80)
            L_.spot_blend = 0.8
            L_.shadow_soft_size = 0.03
            o = bpy.data.objects.new(f"dl{i}_{a}_{b}", L_)
            o.location = (x, y, z - 0.03)
            o.rotation_euler = (math.pi, 0, 0)
            o.visible_camera = False
            scene.collection.objects.link(o)


def d_tile_floor(i, d):
    """بلاط رمادي كبير فوق أرضية الفراغ (الصالة/الطعام/المطبخ)."""
    x0, y0, x1, y1 = d["rect"]
    z = d.get("z", 0.026)               # فوق تشطيب أرضية الخشب (وجهها ≈ +2 سم)
    m = _tmat("tile_" + d.get("color", "#45443F").lstrip("#"), "Tiles107", d.get("tile", 1.2), d.get("color", "#45443F"),
              0.95, rough=0.3, bump=0.1)
    dbox(m, x0, y0, z, x1, y1, z + 0.01, 0)


def d_slat_column(i, d):
    """عمود/فاصل مكسو شرائح خشب رأسية من الأرض للسقف."""
    x0, y0, x1, y1 = d["rect"]
    z0, z1 = d.get("z", [0.0, 2.7])
    dbox("slat_dark", x0 + 0.02, y0 + 0.02, z0, x1 - 0.02, y1 - 0.02, z1, 0)
    for alongx, (a0, a1, s0, s1) in ((True, (x0, x1, y0, y0 + 0.03)), (True, (x0, x1, y1 - 0.03, y1)),
                                     (False, (y0, y1, x0, x0 + 0.03)), (False, (y0, y1, x1 - 0.03, x1))):
        n = max(3, int((a1 - a0) / 0.06))
        for k in range(n):
            c = a0 + (k + 0.5) * (a1 - a0) / n
            if alongx:
                dbox("slat", c - 0.017, s0, z0, c + 0.017, s1, z1)
            else:
                dbox("slat", s0, c - 0.017, z0, s1, c + 0.017, z1)


def d_stone(i, d):
    """تكسية حجر فاتح على الوجه الخارجي (حول الشبابيك/الدور الأرضي). line = الوجه الخارجي، n = للخارج."""
    m = _tmat("stone_clad", "Bricks111A", d.get("tile", 1.4), d.get("color", "#D9CBB0"), 0.55, rough=0.85, bump=0.6)
    (x0, y0, x1, y1), (nx, ny) = d["line"], d["n"]
    z0, z1 = d.get("z", [0.0, 1.0])
    t = d.get("thick", 0.035)
    alongx = abs(x1 - x0) >= abs(y1 - y0)
    if alongx:
        dbox(m, min(x0, x1), y0, z0, max(x0, x1), y0 + ny * t, z1, 0.004)
    else:
        dbox(m, x0, min(y0, y1), z0, x0 + nx * t, max(y0, y1), z1, 0.004)


def d_sconce(i, d):
    """أبليك أب/داون (داخلي أو على الواجهة)."""
    _sconce(f"sc{i}", d["at"], d["n"], d.get("w", 45), d.get("updown", True))


DECOR = {"slats": d_slats, "beam": d_beam, "cove": d_cove, "pendant": d_pendant, "rug": d_rug, "art": d_art,
         "hanging_fire": d_hanging_fire, "fire_pit": d_fire_pit, "lantern": d_lantern,
         "feature_wall": d_feature_wall, "downlights": d_downlights, "tile_floor": d_tile_floor,
         "slat_column": d_slat_column, "stone": d_stone, "sconce": d_sconce}
for _i, _d in enumerate(cfg.get("decor", [])):
    if _d.get("night_only") and not cfg.get("night"):
        continue
    DECOR[_d["kind"]](_i, _d)
