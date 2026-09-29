"""راسم برمجي بـ z-buffer (بدون كرت شاشة): إخفاء صحيح، حواف واضحة، خطوط تلبيس وقرميد."""
import math

import numpy as np
from matplotlib.colors import to_rgb

SS = 2   # تنعيم (supersampling)


def _camera(elev, azim):
    e, a = math.radians(elev), math.radians(azim)
    d = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])  # نحو الكاميرا
    r = np.array([-math.sin(a), math.cos(a), 0.0])
    up = np.cross(d, r)
    if up[2] < 0:
        up = -up
    return r, up, d


def rasterize(scene, elev, azim, width, height, hidden=(), strip=18.67, pad=0.06,
              bg=(0.902, 0.929, 0.949)):
    r, up, d = _camera(elev, azim)
    light = np.array([-0.35, -0.75, 0.85])
    light /= np.linalg.norm(light)

    tris, fids = [], []
    fcol, fkind, fnorm = [], [], []
    for mat, (V, F) in scene.parts.items():
        if mat in hidden:
            continue
        col, _a = scene.colors[mat]
        base = np.array(to_rgb(col))
        kind = {"wood": 1, "wood_in": 1, "roof_tiles": 2, "glass": 3}.get(mat, 0)
        V = np.asarray(V, dtype=float)
        for f in F:
            P = V[f]
            n = np.cross(P[1] - P[0], P[2] - P[0])
            nn = np.linalg.norm(n)
            if nn < 1e-9:
                continue
            n = n / nn
            if np.dot(n, d) <= 0:          # إخفاء الأوجه الخلفية
                continue
            shade = 0.58 + 0.42 * max(0.0, float(np.dot(n, light)))
            fid = len(fcol)
            fcol.append(base * shade)
            fkind.append(kind if (kind != 1 or abs(n[2]) < 0.2) else 0)
            fnorm.append(n)
            for i in range(1, len(f) - 1):
                tris.append((P[0], P[i], P[i + 1]))
                fids.append(fid)
    T = np.array(tris)                      # (n,3,3)
    X = T @ r
    Y = T @ up
    Z = T @ d
    xmin, xmax, ymin, ymax = X.min(), X.max(), Y.min(), Y.max()
    W, H = width * SS, height * SS
    s = min(W * (1 - 2 * pad) / (xmax - xmin), H * (1 - 2 * pad) / (ymax - ymin))
    ox = (W - s * (xmax - xmin)) / 2 - s * xmin
    oy = (H - s * (ymax - ymin)) / 2 + s * ymax
    PX = X * s + ox
    PY = oy - Y * s

    zbuf = np.full((H, W), -np.inf)
    fbuf = np.full((H, W), -1, dtype=np.int32)
    wz = np.zeros((H, W))
    for k in range(len(T)):
        xs, ys, zs = PX[k], PY[k], Z[k]
        x0, x1 = max(int(xs.min()), 0), min(int(xs.max()) + 1, W - 1)
        y0, y1 = max(int(ys.min()), 0), min(int(ys.max()) + 1, H - 1)
        if x1 < x0 or y1 < y0:
            continue
        area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
        if abs(area) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((xs[1] - gx) * (ys[2] - gy) - (xs[2] - gx) * (ys[1] - gy)) / area
        w1 = ((xs[2] - gx) * (ys[0] - gy) - (xs[0] - gx) * (ys[2] - gy)) / area
        w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any():
            continue
        dep = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
        zb = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = m & (dep > zb + 0.05)
        zb[upd] = dep[upd]
        fbuf[y0:y1 + 1, x0:x1 + 1][upd] = fids[k]
        wzr = w0 * T[k, 0, 2] + w1 * T[k, 1, 2] + w2 * T[k, 2, 2]
        wz[y0:y1 + 1, x0:x1 + 1][upd] = wzr[upd]

    fcol = np.array(fcol)
    fkind = np.array(fkind)
    fnorm = np.array(fnorm)
    img = np.empty((H, W, 3))
    img[:] = bg
    hit = fbuf >= 0
    img[hit] = fcol[fbuf[hit]]
    kind = np.where(hit, fkind[np.clip(fbuf, 0, None)], -1)
    # خطوط التلبيس الأفقي
    wm = kind == 1
    ph = np.mod(wz, strip)
    img[wm & (ph < 1.4)] *= 0.72
    img[wm & (np.floor(wz / strip) % 2 == 0)] *= 0.96
    # صفوف القرميد
    rm = kind == 2
    img[rm & (np.mod(wz, 12) < 1.6)] *= 0.7
    # انعكاس بسيط على الزجاج
    gm = kind == 3
    yy = np.broadcast_to(np.linspace(1.25, 0.85, H)[:, None], (H, W))
    img[gm] = np.clip(img[gm] * yy[gm][:, None], 0, 1)
    # الحواف: تغير الوجه مع اختلاف المادة أو الاتجاه أو العمق
    np.seterr(invalid="ignore")
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a = fbuf[:H - dy, :W - dx]
        b = fbuf[dy:, dx:]
        diff = a != b
        both = (a >= 0) & (b >= 0)
        na = fnorm[np.clip(a, 0, None)]
        nb = fnorm[np.clip(b, 0, None)]
        crease = (np.einsum("ijk,ijk->ij", na, nb) < 0.97) | \
                 (np.abs(zbuf[:H - dy, :W - dx] - zbuf[dy:, dx:]) > 6)
        e = diff & ((~both) | crease)
        edge[:H - dy, :W - dx] |= e
    img[edge & hit] *= 0.45
    img = img.reshape(height, SS, width, SS, 3).mean(axis=(1, 3))
    return np.clip(img, 0, 1), hit.reshape(height, SS, width, SS).any(axis=(1, 3))


def render(scene, path, views, width_px, height_px, hidden=(), strip=18.67, tight=False, zoom=1.0):
    import matplotlib.pyplot as plt
    pad = max(0.01, 0.06 / zoom)
    imgs = []
    for el, az in views:
        img, mask = rasterize(scene, el, az, width_px // len(views), height_px, hidden, strip, pad)
        if tight:
            ys, xs = np.where(mask)
            p = 8
            img = img[max(ys.min() - p, 0):ys.max() + p, max(xs.min() - p, 0):xs.max() + p]
        imgs.append(img)
    if len(imgs) > 1:
        h = max(i.shape[0] for i in imgs)
        imgs = [np.pad(i, ((0, h - i.shape[0]), (0, 0), (0, 0)), constant_values=0.92) for i in imgs]
    plt.imsave(path, np.concatenate(imgs, axis=1))
