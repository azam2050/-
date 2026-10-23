"""يركّب الإضاءة المخبوزة على صفحة الجولة: ينسخ web.glb + lm_*.jpg + lm.json من مجلد الخبز، ويضيف كود
خرائط الإضاءة للصفحة (مرة وحدة) — المبنى يطلع بإضاءة الرندر الحقيقية نهاراً وليلاً.

python tools/vr_lightmap.py <مجلد الخبز> <مجلد vr>
"""
import shutil
import sys
from pathlib import Path

JS = '''  /* إضاءة مخبوزة من Blender (Cycles): كل سطح ينضرب بخريطة إضاءته الحقيقية — نهار وليل — فيطلع مثل الرندر */
  let LM = null; const lmTex = {}, baked = [];
  const LMX = { day: 0.62, night: 0.75 };
  fetch("lm.json").then(r => r.ok ? r.json() : null).then(j => { LM = j; applyLM(); }).catch(() => {});
  function lmGroup(o) { for (let p = o; p; p = p.parent) if (p.userData && p.userData.lmgroup) return p.userData.lmgroup; return null; }
  function bakeLM(root) {
    const cache = {};
    root.traverse(o => {
      if (!o.isMesh || !o.geometry.attributes.uv2) return;
      const g = lmGroup(o); if (!g) return;
      const om = o.material, key = om.uuid + g;
      if (!cache[key]) { const m = new THREE.MeshBasicMaterial({ map: om.map || null, color: om.map ? 0xffffff : om.color.clone() });
        m.userData.g = g; cache[key] = m; baked.push(m); }
      o.material = cache[key]; o.castShadow = true; o.receiveShadow = false;
    });
  }
  function lmLoad(g, mode) { const k = g + mode; if (lmTex[k]) return lmTex[k];
    const t = texL.load(LM.groups[g][mode].file); t.flipY = false; if (THREE.sRGBEncoding) t.encoding = THREE.sRGBEncoding; return (lmTex[k] = t); }
  function applyLM() { if (!LM) return; const mode = NIGHT ? "night" : "day";
    baked.forEach(m => { const gg = LM.groups[m.userData.g]; if (!gg) return;
      m.lightMap = lmLoad(m.userData.g, mode); m.lightMapIntensity = gg[mode].k * LMX[mode]; m.needsUpdate = true; }); }
  modeHooks.push(applyLM);
'''


def main(bake, vr):
    bake, vr = Path(bake), Path(vr)
    for f in list(bake.glob("lm_*.jpg")) + [bake / "lm.json", bake / "web.glb"]:
        shutil.copy(f, vr / f.name)
    p = vr / "index.html"
    s = p.read_text(encoding="utf-8")
    if "bakeLM" not in s:
        a = "  const hemi = scene.children.find(o => o.isHemisphereLight);"
        assert a in s
        s = s.replace(a, JS + a, 1)
        b = "    dress(g.scene); scene.add(g.scene);"
        assert b in s
        s = s.replace(b, "    dress(g.scene); bakeLM(g.scene); scene.add(g.scene); applyLM();", 1)
        p.write_text(s, encoding="utf-8")
    return len(list(bake.glob("lm_*.jpg")))


if __name__ == "__main__":
    print(main(sys.argv[1], sys.argv[2]), "lightmaps")
