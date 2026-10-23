"""رندر واقعي بـ Blender Cycles لنموذج المحرك (GLB): خامات حقيقية + سماء HDRI + شمس + عشب.

التشغيل (يستدعيه watad/realistic.py):
  blender -b -P tools/render_blender.py -- config.json
config.json: {glb, out_dir, tex_dir, colors:{wood,trim,roof,frame,glass,slab}, views:[[name,elev,azim,dist_k]],
              samples, res:[w,h], ground_z}
"""
import json
import math
import sys

import bpy
from mathutils import Vector

cfg = json.load(open(sys.argv[sys.argv.index("--") + 1]))
TEX = cfg["tex_dir"]
HQ = bool(cfg.get("hq"))      # render.quality: high في المشروع


def hex2rgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x ** 2.2 for x in c] + [1.0]   # sRGB → linear


# ---------------------------------------------------------------- المشهد
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=cfg["glb"])
scene = bpy.context.scene


def tex_material(name, asset, tile_m, tint=None, tint_mix=0.85, rough=None, bump=0.25, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tile_m, 1 / tile_m, 1 / tile_m)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])

    def img(kind, non_color=False):
        import glob
        f = glob.glob(f"{TEX}/{asset}/{asset}_2K-JPG_{kind}.jpg")
        if not f:
            return None
        n = N.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(f[0])
        n.projection = "BOX"
        n.projection_blend = 0.2
        if non_color:
            n.image.colorspace_settings.name = "Non-Color"
        L.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n
    col = img("Color")
    if tint:
        bw = N.new("ShaderNodeRGBToBW")
        L.new(col.outputs["Color"], bw.inputs["Color"])
        mul = N.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        # الحبيبات (رمادي × 2) مضروبة في لون الصبغة
        gain = N.new("ShaderNodeMath")
        gain.operation = "MULTIPLY"
        gain.inputs[1].default_value = cfg.get("tint_gain", 2.6)
        L.new(bw.outputs["Val"], gain.inputs[0])
        L.new(gain.outputs["Value"], mul.inputs[6])
        mul.inputs[7].default_value = hex2rgb(tint)
        mix = N.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["Factor"].default_value = tint_mix
        L.new(col.outputs["Color"], mix.inputs[6])
        L.new(mul.outputs[2], mix.inputs[7])
        L.new(mix.outputs[2], bsdf.inputs["Base Color"])
    elif HQ:
        # جودة عالية: تهدئة البرتقالي (تشبّع أقل وإضاءة أعلى) عشان يبان صنوبر طبيعي مثل الصور الحقيقية
        hs = N.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = cfg.get("hq_sat", 0.78)
        hs.inputs["Value"].default_value = cfg.get("hq_val", 1.12)
        L.new(col.outputs["Color"], hs.inputs["Color"])
        L.new(hs.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        L.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    r = img("Roughness", True)
    if r and rough is None:
        L.new(r.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = rough if rough is not None else 0.6
    d = img("Displacement", True)
    nm = img("NormalGL", True) if HQ else None
    if nm:
        # جودة عالية: خريطة Normal حقيقية (عروق وشقوق الخشب واضحة) + حواف مشطوفة تلمع مثل الخشب المصنّع
        nmap = N.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = min(1.0, 0.4 + bump * 2)
        L.new(nm.outputs["Color"], nmap.inputs["Color"])
        bev = N.new("ShaderNodeBevel")
        bev.samples = 6
        bev.inputs["Radius"].default_value = 0.004
        L.new(nmap.outputs["Normal"], bev.inputs["Normal"])
        L.new(bev.outputs["Normal"], bsdf.inputs["Normal"])
    elif d and bump:
        b = N.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        b.inputs["Distance"].default_value = 0.01
        L.new(d.outputs["Color"], b.inputs["Height"])
        L.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Metallic"].default_value = metal
    return m


def flat_material(name, color, rough=0.5, metal=0.0, transmission=0.0, ior=1.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hex2rgb(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = ior
    return m


C = cfg["colors"]
MATS = {
    "wood": tex_material("W_wood", "WoodSiding008", 2.4, C["wood"], cfg.get("wood_mix", 0.7)),
    "wood_in": tex_material("W_wood_in", "WoodSiding008", 2.4, C["wood"], cfg.get("wood_in_mix", 0.7)),
    "trim": tex_material("W_trim", "WoodFloor043", 1.6, C["trim"], 0.9, bump=0.1),
    "rafters": tex_material("W_raft", "WoodFloor043", 1.6, C["trim"], 0.9, bump=0.1),
    "sheathing": tex_material("W_sheath", "WoodFloor043", 1.6, C["trim"], 0.9, bump=0.1),
    "door": tex_material("W_door", "WoodFloor043", 1.2, C["frame"], 0.6, bump=0.05),
    "stair": tex_material("W_stair", "WoodFloor043", 1.2, C["trim"], 0.8, bump=0.05),
    "roof_tiles": tex_material("W_roof", "RoofingTiles006", 1.0, C["roof"], 1.0, rough=0.85, bump=1.0, metal=0.0),
    "slab": flat_material("W_slab", "#6F6B64", rough=0.95),
    "ceiling": tex_material("W_ceil", "WoodSiding008", 2.4, C["wood"], cfg.get("wood_in_mix", 0.7)),
    "floor": tex_material("W_floor", "WoodFloor043", 1.5, None, bump=0.05),
    "tiles": flat_material("W_tiles", "#D5D9DC", rough=0.3),
    "furn": flat_material("W_furn", "#CDBBA2", rough=0.6),
    "linen": flat_material("W_linen", "#F1EEE8", rough=0.8),
    "fabric": flat_material("W_fabric", "#8E8A84", rough=0.9),
    "counter": flat_material("W_counter", "#E2DDD5", rough=0.3),
    "white": flat_material("W_white", "#F4F4F2", rough=0.2),
    "dark": flat_material("W_dark", "#2B2B2B", rough=0.3),
    "frame": flat_material("W_frame", C["frame"], rough=0.35, metal=0.7),
    "glass": flat_material("W_glass", "#A7B6BE", rough=0.02, transmission=0.93, ior=1.52),
}
MATS["joist"] = MATS["ceiling"]
# الموقع العام: بلاط، سور، مسبح، مساند الجلسات
MATS["paver"] = tex_material("W_paver", "Concrete034", 1.2, "#9C8F7A", 0.85, rough=0.85, bump=0.3)
MATS["site_wall"] = tex_material("W_site_wall", "Concrete034", 2.0, "#DCD4C6", 0.55, rough=0.9, bump=0.2)
MATS["pool_edge"] = flat_material("W_pool_edge", "#E8E4DC", rough=0.45)
MATS["water"] = flat_material("W_water", "#1E7FA6", rough=0.03, transmission=0.55, ior=1.33)
MATS["cushion"] = flat_material("W_cushion", "#7B5B44", rough=0.95)
MATS["lawn_bed"] = tex_material("W_lawn_bed", "Grass004", 0.9, None, rough=1.0, bump=0.6)
MATS["metal_roof"] = flat_material("W_metal_roof", "#2E3235", rough=0.38, metal=0.7)
MATS["green_roof"] = tex_material("W_green_roof", "Grass004", 0.9, None, rough=1.0, bump=0.9)
# زجاج معماري: انعكاس سماء خفيف (طبقة لامعة) عشان يبان زجاج مركّب مو فتحة فاضية
MATS["glass"].node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 0.7
if HQ:
    # زجاج رقيق يمرّر الشمس والسماء للداخل (بقع شمس على الأرضية) مع انعكاس حسب زاوية النظر
    g_ = bpy.data.materials.new("W_glass_hq")
    g_.use_nodes = True
    gn = g_.node_tree
    gn.nodes.remove(gn.nodes["Principled BSDF"])
    tr_ = gn.nodes.new("ShaderNodeBsdfTransparent")
    gl_ = gn.nodes.new("ShaderNodeBsdfGlossy")
    gl_.inputs["Roughness"].default_value = 0.02
    lw = gn.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.12
    mx = gn.nodes.new("ShaderNodeMixShader")
    gn.links.new(lw.outputs["Fresnel"], mx.inputs["Fac"])
    gn.links.new(tr_.outputs[0], mx.inputs[1])
    gn.links.new(gl_.outputs[0], mx.inputs[2])
    gn.links.new(mx.outputs[0], gn.nodes["Material Output"].inputs["Surface"])
    MATS["glass"] = g_
if cfg.get("furnish") or cfg.get("landscape"):
    # الداخل مثل كبائن المصنع: الجدران وتطبيق السقف والمدادات بنفس خشب الأرضية (صنوبر طبيعي)
    pine = tex_material("W_pine", "WoodFloor043", 0.8, None, bump=0.08)
    beam = tex_material("W_beam", "WoodFloor043", 0.9, "#E2B27C", 0.2, bump=0.05)
    MATS.update({"wood_in": pine, "ceiling": pine, "sheathing": pine, "joist": beam, "rafters": beam})
    if cfg.get("exterior_pine"):
        # الخارج خشب طبيعي فاتح مثل كبائن المصنع الحقيقية (بدل الصبغة الغامقة)
        ext = tex_material("W_ext", "WoodFloor043", 0.8, "#D8A868", 0.18, bump=0.12)
        MATS.update({"wood": ext, "trim": beam, "stair": beam, "door": beam})
MATS["frame_wood"] = MATS["trim"]      # تقسيم خشب الزجاج (الشبابيك البارزة/الأبواب الفرنسية)
if cfg.get("wood_frames"):              # إطارات خشب (مثل الكوخ الكلاسيكي) بدل الألمنيوم
    MATS["frame"] = MATS["trim"]
for ob in list(scene.objects):
    if ob.type != "MESH":
        continue
    key = ob.name.split(".")[0]
    for m in ob.data.materials:
        key = (m.name if m else key).split(".")[0]
    if key in MATS:
        ob.data.materials.clear()
        ob.data.materials.append(MATS[key])
    bpy.context.view_layer.objects.active = ob
    for poly in ob.data.polygons:
        poly.use_smooth = False

# حدود المبنى
pts = [ob.matrix_world @ Vector(c) for ob in scene.objects if ob.type == "MESH" for c in ob.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (lo + hi) / 2
size = (hi - lo).length

# الأرض: عشب
if cfg.get("ground_holes"):      # أرضية صلبة رقيقة (Boolean يحتاج مجسم مقفل) بفتحات للمسابح والجلسات المدفونة
    bpy.ops.mesh.primitive_cube_add(size=1, location=(center.x, center.y, cfg["ground_z"] - 0.005 - 0.05))
    ground = bpy.context.active_object
    ground.scale = (120, 120, 0.1)
    bpy.ops.object.transform_apply(scale=True)
else:
    bpy.ops.mesh.primitive_plane_add(size=120, location=(center.x, center.y, cfg["ground_z"] - 0.005))
    ground = bpy.context.active_object
for i, (hx0, hy0, hx1, hy1) in enumerate(cfg.get("ground_holes", [])):    # فتحات المسابح والجلسات المدفونة
    bpy.ops.mesh.primitive_cube_add(size=1, location=((hx0 + hx1) / 2, (hy0 + hy1) / 2, cfg["ground_z"]))
    cut = bpy.context.active_object
    cut.scale = (hx1 - hx0 + 0.3, hy1 - hy0 + 0.3, 0.6)
    md = ground.modifiers.new(f"hole{i}", "BOOLEAN")
    md.operation = "DIFFERENCE"
    md.object = cut
    md.solver = "EXACT"
    cut.hide_render = True
    cut.hide_viewport = True
ground.data.materials.append(tex_material("W_grass", "Grass004", cfg.get("grass_tile", 2.5), cfg.get("grass_tint"), 0.35, rough=1.0, bump=0.6))

# السماء + الشمس
world = bpy.data.worlds.new("sky")
scene.world = world
world.use_nodes = True
wn = world.node_tree
env = wn.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(f"{TEX}/{cfg.get('sky_hdr', 'sky.hdr')}")
wn.links.new(env.outputs["Color"], wn.nodes["Background"].inputs["Color"])
wn.nodes["Background"].inputs["Strength"].default_value = cfg.get("sky", 1.0)
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = cfg.get("sun", 4.5)
sun.color = (1.0, 0.95, 0.88)
sun.angle = math.radians(1.5)
sun_ob = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(sun_ob)
sun_ob.rotation_euler = (math.radians(90 - cfg.get("sun_elev", 40)), 0, math.radians(cfg.get("sun_azim", 35)))

# إضاءة داخلية دافئة (مثل صور المساء)
for i, (x, y, z) in enumerate(cfg.get("lights", [])):
    L_ = bpy.data.lights.new(f"in{i}", "POINT")
    L_.energy = cfg.get("light_w", 120)
    L_.color = (1.0, 0.78, 0.55)
    L_.shadow_soft_size = 0.02      # مصدر صغير لا يظهر ككرة في الصورة
    o = bpy.data.objects.new(f"in{i}", L_)
    o.location = (x, y, z)
    o.visible_camera = False
    scene.collection.objects.link(o)

# إنارة خارجية (سبوت تحت الرفرف + فوانيس جدارية) — للقطات الليل مثل كبائن المصنع
_spot_mat = bpy.data.materials.new("W_spot")
_spot_mat.use_nodes = True
_em = _spot_mat.node_tree.nodes.new("ShaderNodeEmission")
_em.inputs["Color"].default_value = (1.0, 0.86, 0.62, 1)
_em.inputs["Strength"].default_value = 60
_spot_mat.node_tree.links.new(_em.outputs[0], _spot_mat.node_tree.nodes["Material Output"].inputs["Surface"])
for i, (x, y, z, w, kind) in enumerate(cfg.get("ext_lights", [])):
    if kind == "spot":                     # سبوت سقف موجّه للأسفل
        L_ = bpy.data.lights.new(f"ex{i}", "SPOT")
        L_.spot_size = math.radians(110)
        L_.spot_blend = 0.8
        L_.shadow_soft_size = 0.03
    else:                                  # فانوس جداري
        L_ = bpy.data.lights.new(f"ex{i}", "POINT")
        L_.shadow_soft_size = 0.06
    L_.energy = w
    L_.color = (1.0, 0.8, 0.55)
    o = bpy.data.objects.new(f"ex{i}", L_)
    o.location = (x, y, z - (0.03 if kind == "spot" else 0))
    o.visible_camera = False
    scene.collection.objects.link(o)
    r = 0.035 if kind == "spot" else 0.07
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=0.02 if kind == "spot" else 0.16, location=(x, y, z))
    bpy.context.active_object.data.materials.append(_spot_mat)

# فرش حقيقي للقطات الداخلية
if cfg.get("furnish") or cfg.get("landscape"):
    import os as _os
    exec(open(cfg["furnish_py"], encoding="utf-8").read())
    if cfg.get("decor"):          # ديكورات خشب داخلية وإنارتها (المشروع: interior_decor)
        exec(open(cfg["furnish_py"].replace("blender_furnish", "blender_decor"), encoding="utf-8").read())

# الريندر
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = cfg.get("samples", 64)
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.render.resolution_x, scene.render.resolution_y = cfg.get("res", [1600, 1000])
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = cfg.get("exposure", 0.0)
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 90
if HQ:
    # إضاءة غير مباشرة أدق (ارتدادات أكثر) + تنقية OIDN بالألوان والاتجاهات + جودة JPEG أعلى
    cy = scene.cycles
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 12, 6, 6
    cy.transmission_bounces, cy.transparent_max_bounces = 12, 12
    cy.adaptive_threshold = 0.006
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    cy.denoising_prefilter = "ACCURATE"
    cy.blur_glossy = 0.5
    cy.caustics_reflective = cy.caustics_refractive = False
    scene.view_settings.look = "AgX - Base Contrast"
    scene.render.image_settings.quality = 95
    sun.angle = math.radians(0.8)
    if cfg.get("night"):
        # توهّج خفيف حول اللمبات والفوانيس (مثل الكاميرا الحقيقية)
        scene.use_nodes = True
        ct = scene.node_tree
        rl, comp = ct.nodes["Render Layers"], ct.nodes["Composite"]
        gl = ct.nodes.new("CompositorNodeGlare")
        gl.glare_type = "FOG_GLOW"
        gl.quality = "HIGH"
        gl.threshold = 1.2
        gl.size = 7
        gl.mix = -0.75
        ct.links.new(rl.outputs["Image"], gl.inputs["Image"])
        ct.links.new(gl.outputs["Image"], comp.inputs["Image"])

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = cfg.get("lens", 32)
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
target = bpy.data.objects.new("target", None)
scene.collection.objects.link(target)
target.location = center + Vector((0, 0, -0.6))
tr = cam.constraints.new("TRACK_TO")
tr.target = target
tr.track_axis = "TRACK_NEGATIVE_Z"
tr.up_axis = "UP_Y"

# لقطات داخلية: كاميرا بموقع وهدف محدد (متر) — [name, [x,y,z], [tx,ty,tz], lens]
for name, cpos, tpos, lens, *rest in cfg.get("shots", []):
    cam_data.lens = lens
    cam_data.shift_y = rest[0] if rest else 0.0
    scene.view_settings.exposure = rest[1] if len(rest) > 1 else cfg.get("exposure", 0.0)
    cam.location = Vector(cpos)
    target.location = Vector(tpos)
    scene.render.filepath = f"{cfg['out_dir']}/{name}.jpg"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)
cam_data.lens = cfg.get("lens", 32)
cam_data.shift_y = 0.0
target.location = center + Vector((0, 0, -0.6))

# صور 360° (واقع افتراضي): كاميرا بانوراما متساوية المستطيلات — [name, [x,y,z], yaw]
for name, cpos, yaw in cfg.get("panos", []):
    cam_data.type = "PANO"
    try:
        cam_data.panorama_type = "EQUIRECTANGULAR"
    except AttributeError:
        cam_data.cycles.panorama_type = "EQUIRECTANGULAR"
    cam.constraints.clear()
    cam.location = Vector(cpos)
    cam.rotation_euler = (math.pi / 2, 0, math.radians(yaw))
    scene.view_settings.exposure = cfg.get("pano_exposure", 0.4)
    rx, ry = scene.render.resolution_x, scene.render.resolution_y
    scene.render.resolution_x, scene.render.resolution_y = cfg.get("pano_res", [2400, 1200])
    scene.render.filepath = f"{cfg['out_dir']}/pano-{name}{'-night' if cfg.get('night') else ''}.jpg"
    bpy.ops.render.render(write_still=True)
    print("RENDERED pano", name)
    scene.render.resolution_x, scene.render.resolution_y = rx, ry

for name, elev, azim, k in cfg["views"]:
    e, a = math.radians(elev), math.radians(azim)
    d = size * k
    cam.location = center + Vector((d * math.cos(e) * math.cos(a), d * math.cos(e) * math.sin(a),
                                    d * math.sin(e)))
    if cam.location.z < cfg["ground_z"] + 1.4:
        cam.location.z = cfg["ground_z"] + 1.6
    scene.render.filepath = f"{cfg['out_dir']}/{name}.jpg"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)


# فيديو جولة واقعية: كاميرا تمشي على مسار (نقاط + نقاط نظر) بحركة ناعمة، تُرندر صور ثم تُجمع فيديو
vid = cfg.get("video")
if vid:
    cam_data.type = "PERSP"
    cam_data.lens = vid.get("lens", 18)
    cam_data.shift_y = 0.0
    cam.constraints.clear()
    tr = cam.constraints.new("TRACK_TO")
    tr.target = target
    tr.track_axis = "TRACK_NEGATIVE_Z"
    tr.up_axis = "UP_Y"
    pts, looks = vid["path"], vid["look"]
    nfr = vid.get("frames", 288)

    def cr(P_, n):
        """منحنى Catmull-Rom مركزي يمر بالنقاط بالضبط (بدون تجاوز يدخّل الكاميرا بالجدران) — n نقطة بالتساوي حسب الطول."""
        P_ = [Vector(q) for q in P_]
        ext = [P_[0] * 2 - P_[1]] + P_ + [P_[-1] * 2 - P_[-2]]
        seg = [(P_[i + 1] - P_[i]).length for i in range(len(P_) - 1)]
        tot = sum(seg)
        out_ = []
        for k in range(n):
            d = tot * k / (n - 1)
            i = 0
            while i < len(seg) - 1 and d > seg[i]:
                d -= seg[i]
                i += 1
            t = d / seg[i] if seg[i] else 0
            p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
            a_ = 0.5
            t0 = 0.0
            t1 = t0 + max((p1 - p0).length, 1e-4) ** a_
            t2 = t1 + max((p2 - p1).length, 1e-4) ** a_
            t3 = t2 + max((p3 - p2).length, 1e-4) ** a_
            tt = t1 + (t2 - t1) * t
            A1 = p0 * ((t1 - tt) / (t1 - t0)) + p1 * ((tt - t0) / (t1 - t0))
            A2 = p1 * ((t2 - tt) / (t2 - t1)) + p2 * ((tt - t1) / (t2 - t1))
            A3 = p2 * ((t3 - tt) / (t3 - t2)) + p3 * ((tt - t2) / (t3 - t2))
            B1 = A1 * ((t2 - tt) / (t2 - t0)) + A2 * ((tt - t0) / (t2 - t0))
            B2 = A2 * ((t3 - tt) / (t3 - t1)) + A3 * ((tt - t1) / (t3 - t1))
            out_.append(B1 * ((t2 - tt) / (t2 - t1)) + B2 * ((tt - t1) / (t2 - t1)))
        return out_, seg

    cps, seg_ = cr(pts, nfr)
    # النظر يتبع نفس توزيع المسار (نفس المقطع ونفس النسبة داخله)
    tot_ = sum(seg_)
    lps = []
    for k in range(nfr):
        d = tot_ * k / (nfr - 1)
        i = 0
        while i < len(seg_) - 1 and d > seg_[i]:
            d -= seg_[i]
            i += 1
        t = d / seg_[i] if seg_[i] else 0
        t = t * t * (3 - 2 * t)                           # التفات ناعم
        lps.append(Vector(looks[i]).lerp(Vector(looks[i + 1]), t))
    for f_ in range(nfr):
        cam.location = cps[f_]
        cam.keyframe_insert("location", frame=f_ + 1)
        target.location = lps[f_]
        target.keyframe_insert("location", frame=f_ + 1)
    scene.frame_start, scene.frame_end = 1, nfr
    scene.render.fps = vid.get("fps", 12)
    scene.render.use_persistent_data = True
    scene.cycles.samples = vid.get("samples", 12)
    scene.render.resolution_x, scene.render.resolution_y = vid.get("res", [960, 540])
    scene.view_settings.exposure = vid.get("exposure", 0.3)
    scene.render.filepath = f"{cfg['out_dir']}/walk/f_"
    bpy.ops.render.render(animation=True)
    print("RENDERED video frames", nfr)
