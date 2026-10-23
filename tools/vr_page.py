"""يجهّز صفحة الجولة الافتراضية: ينسخ صور 360° واللقطات الواقعية المتوفرة ويكتب قوائمها في index.html.

python tools/vr_page.py <مجلد realistic> <مجلد vr>
"""
import json
import re
import shutil
import sys
from pathlib import Path

PANO_AR = {"majlis": "داخل المجلس", "front": "قدام المبنى", "room2": "غرفة النوم 2", "yard": "حوش الوحدة", "sunken": "الجلسة الشتوية المدفونة", "living": "الصالة", "master": "غرفة الماستر",
           "balcony": "البلكونة"}


def main(real, vr):
    real, vr = Path(real), Path(vr)
    (vr / "pano").mkdir(parents=True, exist_ok=True)
    (vr / "shots").mkdir(exist_ok=True)
    spots = {}
    for f in sorted(real.glob("pano-*.jpg")):
        key = f.stem[5:]
        shutil.copy(f, vr / "pano" / f"{key}.jpg")
        base = key.replace("-night", "")
        sp = spots.setdefault(base, {"id": base, "name": PANO_AR.get(base, base), "day": None, "night": None})
        sp["night" if key.endswith("-night") else "day"] = f"pano/{key}.jpg"
    order = list(PANO_AR)
    panos = sorted(spots.values(), key=lambda p: order.index(p["id"]) if p["id"] in order else 99)
    night = []
    meta = json.loads((real / "shots.json").read_text(encoding="utf-8")) if (real / "shots.json").exists() else {}
    shots = []
    for group in ("exterior", "dusk", "interior"):
        for fn, name in meta.get(group, []):
            if (real / fn).exists():
                shutil.copy(real / fn, vr / "shots" / fn)
                shots.append({"name": name, "file": f"shots/{fn}"})
    if not meta:
        for f in sorted(real.glob("x*.jpg")):
            shutil.copy(f, vr / "shots" / f.name)
            shots.append({"name": "منظور خارجي", "file": f"shots/{f.name}"})
    html = (vr / "index.html").read_text(encoding="utf-8")
    html = re.sub(r"/\*PANOS\*/.*?/\*END\*/", "/*PANOS*/" + json.dumps(panos + night, ensure_ascii=False) + "/*END*/",
                  html, flags=re.S)
    html = re.sub(r"/\*SHOTS\*/.*?/\*END\*/", "/*SHOTS*/" + json.dumps(shots, ensure_ascii=False) + "/*END*/",
                  html, flags=re.S)
    vid = (real / "walk.mp4").exists()
    if vid:
        shutil.copy(real / "walk.mp4", vr / "walk.mp4")
    html = re.sub(r"/\*VIDEO\*/.*?/\*END\*/", "/*VIDEO*/" + ("true" if vid or (vr / "walk.mp4").exists() else "false") + "/*END*/",
                  html, flags=re.S)
    (vr / "index.html").write_text(html, encoding="utf-8")
    return panos + night, shots


if __name__ == "__main__":
    p, s = main(sys.argv[1], sys.argv[2])
    print(len(p), "panos,", len(s), "shots")
