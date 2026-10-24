"""يصغّر صور الخامات المضمّنة في GLB (حد Cloudflare Pages 25 م.ب للملف) بدون ما يلمس الهندسة أو قنوات UV.

python tools/glb_shrink.py <in.glb> <out.glb> [أقصى_بكسل=512] [جودة=82]
"""
import io
import json
import struct
import sys

from PIL import Image


def shrink(src, dst, max_px=512, q=82):
    data = open(src, "rb").read()
    _, _, _ = struct.unpack_from("<III", data, 0)
    jl, _ = struct.unpack_from("<II", data, 12)
    js = json.loads(data[20:20 + jl])
    off = 20 + jl
    bl, _ = struct.unpack_from("<II", data, off)
    binc = data[off + 8:off + 8 + bl]
    views = js["bufferViews"]
    img_views = {im["bufferView"]: im for im in js.get("images", []) if "bufferView" in im}
    out = bytearray()
    for i, v in enumerate(views):
        chunk = binc[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]]
        if i in img_views:
            im = Image.open(io.BytesIO(chunk))
            if max(im.size) > max_px or len(chunk) > 200_000:
                alpha = im.mode in ("RGBA", "LA") and im.getextrema()[-1][0] < 255
                im.thumbnail((max_px, max_px))
                b = io.BytesIO()
                if alpha:
                    im.save(b, "PNG", optimize=True)
                    img_views[i]["mimeType"] = "image/png"
                else:
                    im.convert("RGB").save(b, "JPEG", quality=q)
                    img_views[i]["mimeType"] = "image/jpeg"
                chunk = b.getvalue()
        while len(out) % 4:
            out += b"\0"
        v["byteOffset"] = len(out)
        v["byteLength"] = len(chunk)
        out += chunk
    while len(out) % 4:
        out += b"\0"
    js["buffers"][0]["byteLength"] = len(out)
    jb = json.dumps(js, separators=(",", ":")).encode()
    while len(jb) % 4:
        jb += b" "
    total = 12 + 8 + len(jb) + 8 + len(out)
    with open(dst, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(jb), 0x4E4F534A) + jb)
        f.write(struct.pack("<II", len(out), 0x004E4942) + bytes(out))
    return total


if __name__ == "__main__":
    a = sys.argv[1:]
    print(shrink(a[0], a[1], int(a[2]) if len(a) > 2 else 512, int(a[3]) if len(a) > 3 else 82))
