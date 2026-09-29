"""تجهيز مكتبة الرندر الواقعي بأمر واحد: Blender + خامات ambientCG + سماء HDRI + موديلات Poly Haven.
كل الأصول في library/assets.yaml. يتخطى الموجود، فتشغيله مرة ثانية سريع.
  python tools/setup_library.py
"""
import io
import os
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from fetch_models import fetch  # noqa: E402

BASE = Path(os.environ.get("BLENDER_HOME", "/opt/blender"))
TEX = Path(os.environ.get("BLENDER_TEX", BASE / "tex"))
UA = {"User-Agent": "watad-cabin-designer/1.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r:
        return r.read()


def main():
    lib = yaml.safe_load(open(ROOT / "library" / "assets.yaml", encoding="utf-8"))
    b = lib["blender"]
    exe = BASE / f"blender-{b['version']}-linux-x64" / "blender"
    if not exe.exists():
        print("تنزيل Blender …")
        BASE.mkdir(parents=True, exist_ok=True)
        tarfile.open(fileobj=io.BytesIO(get(b["url"])), mode="r:xz").extractall(BASE)
    TEX.mkdir(parents=True, exist_ok=True)
    if not (TEX / "sky.hdr").exists():
        (TEX / "sky.hdr").write_bytes(get(lib["hdri"]["sky"]))
    for tid in lib["textures"]:
        if not list((TEX / tid).glob("*_Color.jpg")):
            zipfile.ZipFile(io.BytesIO(get(f"https://ambientcg.com/get?file={tid}_2K-JPG.zip"))).extractall(TEX / tid)
        print("ok", tid)
    for group in lib["models"].values():
        for mid in group:
            fetch(mid)
            print("ok", mid)
    print("المكتبة جاهزة:", exe)


if __name__ == "__main__":
    main()
