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
    else:
        L.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    r = img("Roughness", True)
    if r and rough is None:
        L.new(r.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = rough if rough is not None else 0.6
    d = img("Displacement", True)
    if d and bump:
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
    "roof_tiles": tex_material("W_roof", "RoofingTiles006", 1.0, C["roof"], 1.0, bump=1.0, metal=0.05),
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
    "glass": flat_material("W_glass", "#8FA3B0", rough=0.02, transmission=1.0, ior=1.5),
}
MATS["joist"] = MATS["ceiling"]
if cfg.get("furnish") or cfg.get("landscape"):
    # الداخل مثل كبائن المصنع: الجدران وتطبيق السقف والمدادات بنفس خشب الأرضية (صنوبر طبيعي)
    pine = tex_material("W_pine", "WoodFloor043", 0.8, None, bump=0.08)
    beam = tex_material("W_beam", "WoodFloor043", 0.9, "#E2B27C", 0.2, bump=0.05)
    MATS.update({"wood_in": pine, "ceiling": pine, "sheathing": pine, "joist": beam, "rafters": beam})
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
bpy.ops.mesh.primitive_plane_add(size=120, location=(center.x, center.y, cfg["ground_z"] - 0.005))
ground = bpy.context.active_object
ground.data.materials.append(tex_material("W_grass", "Grass004", cfg.get("grass_tile", 2.5), cfg.get("grass_tint"), 0.35, rough=1.0, bump=0.6))

# السماء + الشمس
world = bpy.data.worlds.new("sky")
scene.world = world
world.use_nodes = True
wn = world.node_tree
env = wn.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(f"{TEX}/sky.hdr")
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

# فرش حقيقي للقطات الداخلية
if cfg.get("furnish") or cfg.get("landscape"):
    import os as _os
    exec(open(cfg["furnish_py"], encoding="utf-8").read())

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
    cam.location = Vector(cpos)
    target.location = Vector(tpos)
    scene.render.filepath = f"{cfg['out_dir']}/{name}.jpg"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)
cam_data.lens = cfg.get("lens", 32)
cam_data.shift_y = 0.0
target.location = center + Vector((0, 0, -0.6))

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
