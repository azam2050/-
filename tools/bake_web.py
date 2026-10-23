# يُنفَّذ داخل render_blender.py (cfg["bake"]): بعد ما ينبني المشهد الواقعي كامل (الخامات + السماء + الشمس +
# الإنارة + الفرش + الديكورات) نخبز الإضاءة الحقيقية (Cycles: مباشر + غير مباشر + ظلال ناعمة) في خرائط إضاءة
# (lightmaps) نهار وليل، ونصدّر مجسم ويب بقناة UV ثانية — الصفحة تلبس الخامات وتضربها بالإضاءة المخبوزة
# فيطلع المشي بنفس واقعية الرندر.
# المخرجات: web.glb + lm_day_gN.jpg + lm_night_gN.jpg + lm.json  (في B["out_dir"])
import json as _json
import math as _m
import os as _os

import bmesh as _bm

B = cfg["bake"]
OUT = B["out_dir"]
RES = B.get("res", 2048)
_os.makedirs(OUT, exist_ok=True)

SKIP = ("W_glass", "glass", "W_water", "water", "W_spot")


def _is_skip(o):
    ms = [s.material for s in o.material_slots if s.material]
    return bool(ms) and all(m.name.startswith(SKIP) for m in ms)


def _area(o):
    me = o.data
    sx, sy, sz = (abs(v) for v in o.matrix_world.to_scale())
    k = max(sx * sy, sy * sz, sx * sz)
    return sum(p.area for p in me.polygons) * k


# الأرض والقص والإنارة ما تنخبز (الأرض مرسومة بالمتصفح بظل حي)
objs = [o for o in scene.objects if o.type == "MESH" and not o.hide_render and o != ground]
for o in objs:   # أي مجسم بمعدّلات (Boolean...) نثبّته
    if o.modifiers:
        bpy.context.view_layer.objects.active = o
        for md in list(o.modifiers):
            try:
                bpy.ops.object.modifier_apply(modifier=md.name)
            except Exception:
                o.modifiers.remove(md)
bpy.ops.object.select_all(action="DESELECT")
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.make_single_user(object=True, obdata=True, material=False)
# نخبز المبنى (جدران/أرضيات/أسقف/أبواب/درج/خشب): أسطح كبيرة تحتاج إضاءة حقيقية؛ الفرش يبقى بخاماته وإضاءة حية
bake_objs = [o for o in objs if o.get("wkey") and not _is_skip(o) and len(o.data.polygons)]

# تقسيم لمجموعات متوازنة المساحة (كل مجموعة أطلس RES×RES)
G = max(1, min(6, round(sum(_area(o) for o in bake_objs) / B.get("m2_per_atlas", 220))))
groups = [[] for _ in range(G)]
gar = [0.0] * G
for o in sorted(bake_objs, key=_area, reverse=True):
    i = gar.index(min(gar))
    groups[i].append(o)
    gar[i] += _area(o)

# قناة UV ثانية "lm" لكل مجسم (الأولى تبقى للخامات)، وفرد + رص كل مجموعة في أطلس واحد
for gi, grp in enumerate(groups):
    for o in grp:
        me = o.data
        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        uv = me.uv_layers.new(name="lm")
        me.uv_layers.active = uv
        o["lmgroup"] = f"g{gi}"
    bpy.ops.object.select_all(action="DESELECT")
    for o in grp:
        o.select_set(True)
    bpy.context.view_layer.objects.active = grp[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    # فرد خاص بخرائط الإضاءة: كل وجه مستطيل بنسبته الحقيقية، والكل في أطلس واحد بهامش
    bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False,
                             PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)

# خامة مستقلة لكل مجموعة + عقدة صورة نشطة (هدف الخبز)
imgs = {}
for gi, grp in enumerate(groups):
    img = bpy.data.images.new(f"lm_g{gi}", RES, RES, float_buffer=True)
    imgs[gi] = img
    cache = {}
    for o in grp:
        for s in o.material_slots:
            m = s.material
            if not m:
                continue
            if m.name not in cache:
                c = m.copy()
                if not c.use_nodes:
                    c.use_nodes = True
                n = c.node_tree.nodes.new("ShaderNodeTexImage")
                n.name = "LM_TARGET"
                n.image = img
                for x in c.node_tree.nodes:
                    x.select = False
                n.select = True
                c.node_tree.nodes.active = n
                cache[m.name] = c
            s.material = cache[m.name]

scene.cycles.samples = B.get("samples", 128)
scene.cycles.use_denoising = False
scene.render.bake.margin = 8
scene.render.bake.use_pass_direct = True
scene.render.bake.use_pass_indirect = True
scene.render.bake.use_pass_color = False

world_bg = scene.world.node_tree.nodes["Background"]
env_node = next(n for n in scene.world.node_tree.nodes if n.type == "TEX_ENVIRONMENT")
night_state = {"sky": world_bg.inputs["Strength"].default_value, "img": env_node.image, "sun": sun.energy,
               "rot": tuple(sun_ob.rotation_euler),
               "lights": {o.name: o.data.energy for o in scene.objects if o.type == "LIGHT" and o != sun_ob}}


def _set_mode(mode):
    if mode == "night":
        world_bg.inputs["Strength"].default_value = night_state["sky"]
        env_node.image = night_state["img"]
        sun.energy = night_state["sun"]
        sun_ob.rotation_euler = night_state["rot"]
        for n_, e in night_state["lights"].items():
            scene.objects[n_].data.energy = e
    else:
        D = B["day"]
        world_bg.inputs["Strength"].default_value = D.get("sky", 1.0)
        if D.get("sky_hdr"):
            env_node.image = bpy.data.images.load(f"{TEX}/{D['sky_hdr']}", check_existing=True)
        sun.energy = D.get("sun", 4.0)
        sun_ob.rotation_euler = (_m.radians(90 - D.get("sun_elev", 35)), 0, _m.radians(D.get("sun_azim", -40)))
        for n_, e in night_state["lights"].items():
            scene.objects[n_].data.energy = e * D.get("lamps", 0.25)


def _denoise(img):
    """تنقية OIDN لخريطة الإضاءة عبر مشهد فاضي (Workbench سريع) + مُركّب الصور."""
    sc_ = bpy.data.scenes.new("dn")
    sc_.render.engine = "BLENDER_WORKBENCH"
    sc_.render.resolution_x = sc_.render.resolution_y = RES
    sc_.render.resolution_percentage = 100
    cam_ = bpy.data.objects.new("dncam", bpy.data.cameras.new("dncam"))
    sc_.collection.objects.link(cam_)
    sc_.camera = cam_
    sc_.use_nodes = True
    nt = sc_.node_tree
    for n_ in list(nt.nodes):
        nt.nodes.remove(n_)
    i_ = nt.nodes.new("CompositorNodeImage")
    i_.image = img
    d_ = nt.nodes.new("CompositorNodeDenoise")
    c_ = nt.nodes.new("CompositorNodeComposite")
    v_ = nt.nodes.new("CompositorNodeViewer")
    nt.links.new(i_.outputs["Image"], d_.inputs["Image"])
    nt.links.new(d_.outputs["Image"], c_.inputs["Image"])
    nt.links.new(d_.outputs["Image"], v_.inputs["Image"])
    sc_.view_settings.view_transform = "Standard"
    sc_.render.filepath = f"{OUT}/_dn.exr"
    sc_.render.image_settings.file_format = "OPEN_EXR"
    bpy.ops.render.render(scene=sc_.name, write_still=True)
    r_ = bpy.data.images.load(f"{OUT}/_dn.exr", check_existing=False)
    import numpy as _np
    a = _np.empty(RES * RES * 4, dtype=_np.float32)
    r_.pixels.foreach_get(a)
    bpy.data.images.remove(r_)
    bpy.data.scenes.remove(sc_)
    _os.remove(f"{OUT}/_dn.exr")
    return a


meta = {"groups": {}}
for mode in ("day", "night"):
    _set_mode(mode)
    for gi, grp in enumerate(groups):
        img = imgs[gi]
        bpy.ops.object.select_all(action="DESELECT")
        for o in grp:
            o.select_set(True)
        bpy.context.view_layer.objects.active = grp[0]
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, margin=8, use_clear=True)
        import numpy as _np
        px = _np.empty(RES * RES * 4, dtype=_np.float32)
        img.pixels.foreach_get(px)
        try:
            dn = _denoise(img)
            if dn.shape == px.shape and _np.isfinite(dn).all() and dn[:].max() > 0:
                px = dn
        except Exception as e_:
            print("DENOISE FAILED", e_)
        rgb = px.reshape(-1, 4)[:, :3]
        lum = rgb.max(axis=1)
        p99 = float(_np.quantile(lum[lum > 0], 0.995)) if (lum > 0).any() else 1.0
        sc = 0.92 / (p99 or 1.0)
        v = _np.clip(rgb * sc, 0, 1)
        v = _np.where(v <= 0.0031308, 12.92 * v, 1.055 * _np.power(v, 1 / 2.4) - 0.055)
        enc = _np.concatenate([v, _np.ones((v.shape[0], 1), dtype=_np.float32)], axis=1).astype(_np.float32).ravel()
        out = bpy.data.images.new(f"lm_{mode}_g{gi}_8", RES, RES, alpha=False)
        out.colorspace_settings.name = "sRGB"
        out.pixels.foreach_set(enc)
        fn = f"lm_{mode}_g{gi}.jpg"
        out.filepath_raw = f"{OUT}/{fn}"
        out.file_format = "JPEG"
        scene.render.image_settings.quality = 88
        out.save()
        meta["groups"].setdefault(f"g{gi}", {})[mode] = {"file": fn, "k": round(1 / sc, 4)}
        print("BAKED", mode, gi, round(1 / sc, 3))

# تصدير مجسم الويب: الخامات ترجع لأسماء المحرك (الصفحة تلبس صورها)، والفرش يحتفظ بصوره (مصغّرة)
rev = {}
for k_, m_ in MATS.items():
    rev.setdefault(m_.name, k_)
plain = {}
for o in objs:
    for s in o.material_slots:
        m = s.material
        if not m:
            continue
        base = m.name.split(".")[0]
        key = o.get("wkey") or rev.get(base)
        if key:
            if key not in plain:
                pm = bpy.data.materials.new(key)
                pm.use_nodes = True
                plain[key] = pm
            s.material = plain[key]
        elif "LM_TARGET" in m.node_tree.nodes if m.use_nodes else False:
            m.node_tree.nodes.remove(m.node_tree.nodes["LM_TARGET"])
for ob in list(scene.objects):
    if ob.type in ("LIGHT", "CAMERA") or ob == ground or ob.hide_render:
        bpy.data.objects.remove(ob, do_unlink=True)
for img in list(bpy.data.images):
    if img.name.startswith("lm_"):
        continue
    if img.size[0] > B.get("max_tex", 1024):
        k = B.get("max_tex", 1024) / img.size[0]
        img.scale(int(img.size[0] * k), int(img.size[1] * k))
bpy.ops.export_scene.gltf(filepath=f"{OUT}/web.glb", export_format="GLB", export_apply=True, export_lights=False,
                          export_cameras=False, export_image_format="JPEG", export_yup=True, export_extras=True)
_json.dump(meta, open(f"{OUT}/lm.json", "w"))
print("EXPORTED baked web", OUT, meta)
