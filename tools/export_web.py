# يُشغّل داخل Blender: blender -b -P tools/export_web.py -- config.json
# يجهّز مجسم الويب للجولة الافتراضية: الكوخ + الموقع + الفرش الحقيقي + ديكورات الخشب، ويصدّره GLB خفيف
# (الصور مصغّرة JPEG، بدون إضاءة/كاميرات). الخامات المعمارية تأخذ صورها في المتصفح بأسمائها.
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
    return [x ** 2.2 for x in c] + [1.0]


def tex_material(name, asset, tile_m, tint=None, tint_mix=0.85, rough=None, bump=0.25, metal=0.0):
    """نسخة الويب: صورة الخامة موصولة مباشرة (يصدّرها glTF) + لون الصبغة كمعامل تقريبي."""
    import glob
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N["Principled BSDF"]
    f = glob.glob(f"{TEX}/{asset}/{asset}_2K-JPG_Color.jpg")
    if f:
        n = N.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(f[0], check_existing=True)
        L.new(n.outputs["Color"], b.inputs["Base Color"])
    elif tint:
        b.inputs["Base Color"].default_value = hex2rgb(tint)
    b.inputs["Roughness"].default_value = rough if rough is not None else 0.6
    b.inputs["Metallic"].default_value = metal
    return m


def flat_material(name, color, rough=0.5, metal=0.0, transmission=0.0, ior=1.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hex2rgb(color)
    b.inputs["Roughness"].default_value = rough
    return m


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=cfg["glb"])
scene = bpy.context.scene
MATS = {"glass": bpy.data.materials.get("glass")}
if cfg.get("furnish"):
    exec(open(cfg["furnish_py"], encoding="utf-8").read())
if cfg.get("decor"):
    exec(open(cfg["furnish_py"].replace("blender_furnish", "blender_decor"), encoding="utf-8").read())
for ob in list(scene.objects):                 # بدون إضاءة ولا أجسام قص
    if ob.type in ("LIGHT", "CAMERA") or ob.hide_render:
        bpy.data.objects.remove(ob, do_unlink=True)
for img in bpy.data.images:                     # صور خفيفة للجوال
    if img.size[0] > cfg.get("max_tex", 512):
        k = cfg.get("max_tex", 512) / img.size[0]
        img.scale(int(img.size[0] * k), int(img.size[1] * k))
bpy.ops.export_scene.gltf(filepath=cfg["out"], export_format="GLB", export_apply=True, export_lights=False,
                          export_cameras=False, export_image_format="JPEG", export_yup=True)
print("EXPORTED", cfg["out"])
