"""تنزيل موديلات أثاث CC0 من Poly Haven (glTF 1k) إلى /opt/blender/models/<id>/"""
import json, os, sys, urllib.request
from pathlib import Path

DEST = Path(os.environ.get("BLENDER_MODELS", "/opt/blender/models"))
MODELS = ["sofa_02", "ArmChair_01", "modern_coffee_table_01", "wooden_table_02", "dining_chair_02",
          "modern_wooden_cabinet", "painted_wooden_nightstand", "potted_plant_01", "potted_plant_02",
          "modern_ceiling_lamp_01", "throw_pillows_01", "ceramic_vase_01", "hanging_picture_frame_01",
          "book_encyclopedia_set_01", "wooden_bowl_01", "side_table_01", "mid_century_lounge_chair"]


UA = {"User-Agent": "watad-cabin-designer/1.0"}


def _open(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA))


def get(url, path):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with _open(url) as r:
        path.write_bytes(r.read())


def fetch(mid):
    info = json.load(_open(f"https://api.polyhaven.com/files/{mid}"))
    g = info["gltf"]["1k"]["gltf"]
    d = DEST / mid
    get(g["url"], d / f"{mid}.gltf")
    for rel, f in g["include"].items():
        get(f["url"], d / rel)


if __name__ == "__main__":
    for m in sys.argv[1:] or MODELS:
        fetch(m)
        print("ok", m)
