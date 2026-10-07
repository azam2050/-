"""برجولة / جلسة خشب مفتوحة بسقف جملون وجمالونات مكشوفة (مثل صور العملاء).

مشروع YAML بـ kind: pavilion:
  size: [600, 600]        # خارج الأعمدة (x عرض الواجهة، y العمق) — الجملون يواجه الأمام (y=0)
  post: 15                # عمود مركّب من 3 طبقات 5×15
  post_height: 280        # لأسفل الجسر
  bays_y: 2               # عدد الفتحات على الجانب (أعمدة وسطية)
  pitch_deg: 30
  overhang: 50            # رفرف جهة المرازيب
  gable_overhang: 40      # بروز السقف عند الجملون
السقف طبقتين فقط (طلب العميل): تطبيق خشب 2.5 سم (يبان من تحت) + قرميد معدني — على مدادات 5×15 كل 60.
"""
import math
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon, Rectangle

from .model3d import Scene, render_preview
from .rules import load_rules
from .sheets import (BRAND, C_ROOF, dim, drawing_ax, level, lift_content, new_page, table, title, title_block)
from .style import resolve_style

A3L = (16.54, 11.69)


class _P:          # بيانات المشروع لإطار العنوان
    def __init__(self, d):
        self.title, self.client, self.meta = d["title"], d.get("client", ""), d.get("meta", {})


def geometry(d, rules):
    W, D = d.get("size", [600, 600])
    ps = d.get("post", 15)
    Hp = d.get("post_height", 280)
    if d.get("ridge_height"):          # قمة الجملون من الأرض (أعلى القرميد) — يُحسب منه ارتفاع العمود
        p_ = math.radians(d.get("pitch_deg", 30))
        Hp = d["ridge_height"] - rules["pallet"]["width"] - W / 2 * math.tan(p_) \
            - (rules["members"]["rafter"]["w"] + 6) / math.cos(p_)
    bays = d.get("bays_y", 2)
    pitch = math.radians(d.get("pitch_deg", 30))
    t = math.tan(pitch)
    ov, gov = d.get("overhang", 50), d.get("gable_overhang", 40)
    beam_d = rules["pallet"]["width"]                  # جسر طرفي: طبقتين 5×22.5
    tie_d = rules["members"]["rafter"]["w"]            # شداد الجمالون: طبقتين 5×15
    raf_d = rules["members"]["rafter"]["w"]
    spacing = rules["roof"]["rafter_spacing"]
    xs = [ps / 2, W - ps / 2]
    ys = [ps / 2 + (D - ps) * k / bays for k in range(bays + 1)]
    z_plate = Hp + beam_d                              # أعلى الجسر = جلسة المداد
    half = W / 2
    rise = half * t
    z_ridge = z_plate + rise                           # أسفل المداد عند القمة
    rafter_len = (half + ov) / math.cos(pitch)
    rpos = [-gov + k * spacing for k in range(int((D + 2 * gov) / spacing) + 1)]
    if rpos[-1] < D + gov - 1:
        rpos.append(D + gov)
    return dict(W=W, D=D, ps=ps, Hp=Hp, xs=xs, ys=ys, t=t, pitch=pitch, ov=ov, gov=gov, beam_d=beam_d,
                tie_d=tie_d, raf_d=raf_d, z_plate=z_plate, half=half, rise=rise, z_ridge=z_ridge,
                rafter_len=rafter_len, rpos=rpos, kv=1 / math.cos(pitch))


def zr(g, x):
    """أسفل المداد عند x."""
    return g["z_plate"] + min(x, g["W"] - x) * g["t"]


def build_scene(d, rules, style):
    g = geometry(d, rules)
    S = Scene()
    for m in ("trim", "rafters", "sheathing"):
        S.material(m, style["trim"] if m != "sheathing" else style["wood"])
    S.material("roof_tiles", style["roof"])
    S.material("slab", style["slab"])
    S.material("frame", style["frame"])
    W, D, ps, Hp = g["W"], g["D"], g["ps"], g["Hp"]
    gov, ov, kv = g["gov"], g["ov"], g["kv"]
    S.box("slab", -20, -20, -12, W + 20, D + 20, 0)                       # أرضية الجلسة (حسب العميل)
    for x in g["xs"]:
        for y in g["ys"]:
            S.box("trim", x - ps / 2, y - ps / 2, 0, x + ps / 2, y + ps / 2, Hp)             # عمود للأرض
            S.box("frame", x - ps / 2 - 3, y - ps / 2 - 3, 0, x + ps / 2 + 3, y + ps / 2 + 3, 8)  # قاعدة حديد
    for x in g["xs"]:                                                      # جسور طرفية
        S.box("trim", x - 5, -gov, Hp, x + 5, D + gov, g["z_plate"])
    for y in g["ys"]:                                                      # الجمالونات
        zt = g["z_plate"]
        S.box("trim", -ov * 0.4, y - 5, zt, W + ov * 0.4, y + 5, zt + g["tie_d"])              # شداد
        S.box("trim", W / 2 - 7.5, y - 5, zt + g["tie_d"], W / 2 + 7.5, y + 5, g["z_ridge"] - g["beam_d"])  # قائم
        for sg in (-1, 1):                                                 # أذرع مائلة
            xa, za = W / 2 + sg * 7.5, zt + g["tie_d"] + 25
            xb = W / 2 + sg * W * 0.25
            zb = zr(g, xb)
            S.poly("trim", *_bar((xa, y, za), (xb, y, zb), 7, 5))
    S.box("trim", W / 2 - 5, -gov, g["z_ridge"] - g["beam_d"], W / 2 + 5, D + gov, g["z_ridge"])  # جسر القمة
    for x in g["xs"]:                                                      # كوابيل أعمدة
        for y in g["ys"]:
            for dy in (-1, 1):
                if (y + dy * 60) < 0 or (y + dy * 60) > D:
                    continue
                S.poly("trim", *_bar((x, y + dy * 6, Hp - 70), (x, y + dy * 66, Hp - 2), 7, 7))
            dx = 1 if x < W / 2 else -1
            S.poly("trim", *_bar((x + dx * 6, y, Hp - 70), (x + dx * 66, y, g["z_plate"] - 2), 7, 7))

    def slope(mat, xa, xb, ya, yb, z0, z1):
        pts = []
        for zo in (z0, z1):
            for x, y in ((xa, ya), (xb, ya), (xb, yb), (xa, yb)):
                pts.append((x, y, zr(g, min(max(x, -1e9), W)) if 0 <= x <= W else None))
        # الرفرف: امتداد خطي للميل
        out = []
        for i, (x, y, _z) in enumerate(pts):
            z = g["z_plate"] + (min(x, W - x)) * g["t"]
            out.append((x, y, z + (z0 if i < 4 else z1) * kv))
        S.hexa(mat, out)
    for xa, xb in ((-ov, W / 2), (W / 2, W + ov)):
        for p in g["rpos"]:
            slope("rafters", xa, xb, max(p - 2.5, -gov), min(p + 2.5, D + gov), 0, g["raf_d"])
        slope("sheathing", xa, xb, -gov, D + gov, g["raf_d"], g["raf_d"] + 2.5)         # الطبقة 1: تطبيق خشب
        slope("roof_tiles", xa, xb, -gov, D + gov, g["raf_d"] + 2.5, g["raf_d"] + 5)    # الطبقة 2: قرميد معدني
        for yb in (-gov - 3, D + gov):                                     # ألواح حافة الجملون
            slope("trim", xa, xb, yb, yb + 3, g["raf_d"] - 8, g["raf_d"] + 6)
    return S, g


def _bar(a, b, w, h):
    ax_, ay, az = a
    bx, by, bz = b
    if abs(bx - ax_) >= abs(by - ay):
        off = [(0, -w / 2, -h / 2), (0, w / 2, -h / 2), (0, w / 2, h / 2), (0, -w / 2, h / 2)]
    else:
        off = [(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)]
    v = [(ax_ + o[0], ay + o[1], az + o[2]) for o in off] + [(bx + o[0], by + o[1], bz + o[2]) for o in off]
    return v, [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


# ------------------------------------------------------------ الكميات
def quantities(d, rules, g):
    ps = g["ps"]
    plies_post = round(ps / 5)                 # طبقات 5 سم
    post_sec = "5×15" if ps <= 15 else "5×22.5"  # 20×20 = 4 طبقات من 5×22.5 تُقص لعرض 20
    n_posts = len(g["xs"]) * len(g["ys"])
    n_tr = len(g["ys"])
    D, W = g["D"], g["W"]
    beam_len = (D + 2 * g["gov"]) / 2                   # الجسر من نصين يلتقون فوق العمود الأوسط
    kp = g["z_ridge"] - g["beam_d"] - g["z_plate"] - g["tie_d"]
    strut = math.hypot(W * 0.25, zr(g, W / 2 - W * 0.25) - (g["z_plate"] + g["tie_d"] + 25))
    rows = [
        (f"أعمدة {ps:.0f}×{ps:.0f} ({plies_post} طبقات {'5×15' if ps <= 15 else f'5×{ps:.0f} مقصوصة من 5×22.5'} مبرغية)",
         f"{n_posts} عمود × {g['Hp']:.0f} سم", n_posts * plies_post, g["Hp"] + 10, post_sec),
        ("جسور طرفية (طبقتين 5×22.5) — وصلة فوق العمود الأوسط", f"2 خط × {D + 2 * g['gov']:.0f} سم", 2 * 2 * 2, beam_len, "5×22.5"),
        ("جسر القمة (طبقتين 5×22.5)", f"{D + 2 * g['gov']:.0f} سم", 2 * 2, beam_len, "5×22.5"),
        ("شداد الجمالون (طبقتين 5×15) — نصين", f"{n_tr} جمالون", n_tr * 2 * 2, W / 2 + g["ov"] * 0.4, "5×15"),
        ("قائم الجمالون (طبقتين 5×15)", f"{n_tr} جمالون", n_tr * 2, kp, "5×15"),
        ("أذرع الجمالون المائلة 5×15", f"{n_tr} × 2", n_tr * 2, strut, "5×15"),
        ("مدادات 5×15 كل 60 سم", f"{len(g['rpos'])} × 2 جهة", len(g["rpos"]) * 2, g["rafter_len"], "5×15"),
        ("كوابيل الأعمدة 7×5", "", sum(1 + sum(1 for dy in (-1, 1) if 0 <= y + dy * 60 <= D)
                                     for _x in g["xs"] for y in g["ys"]), 95, "7×5"),
    ]
    slope_len = g["rafter_len"]
    area_roof = 2 * slope_len * (D + 2 * g["gov"]) / 1e4
    cover = rules["cladding"]["effective_cover"]
    board_L = 400
    rows_per_side = math.ceil(slope_len / cover)
    boards = 2 * rows_per_side * math.ceil((D + 2 * g["gov"]) / board_L)
    # الطبليات: كل قطعة 5×15 من طبلية 5×22.5 (الطريقة الأولى: 5×15 + 7×5) — القطع القصيرة اثنتين بطبلية
    lens = sorted(rules["pallet"]["lengths"])
    stock = lambda L: next((s for s in lens if s >= L), None)  # noqa: E731
    pal = Counter()
    for _n, _d, cnt, L, sec in rows:
        if sec == "7×5":
            continue
        s = stock(L)
        per = 2 if (s and 2 * L + 1 <= s) else 1
        pal[(s, sec)] += math.ceil(cnt / per)
    return {"rows": rows, "area_roof": area_roof, "boards": boards, "board_L": board_L, "pallets": pal,
            "area": W * D / 1e4, "n_posts": n_posts}


# ------------------------------------------------------------ اللوحات
def _plan(fig, g, d):
    ax = drawing_ax(fig, [0.06, 0.12, 0.55, 0.8])
    title(ax, "المسقط الأفقي ومسقط السقف", "مقياس 1:50  |  الوحدة: سم")
    W, D, ov, gov, ps = g["W"], g["D"], g["ov"], g["gov"], g["ps"]
    ax.add_patch(Rectangle((-ov, -gov), W + 2 * ov, D + 2 * gov, fc="#fff8ee", ec=C_ROOF, lw=1, ls="--"))
    ax.add_patch(Rectangle((-20, -20), W + 40, D + 40, fill=False, ec="#999", lw=0.6, ls=":"))
    for p in g["rpos"]:
        ax.plot([-ov, W + ov], [p, p], color="#c9b79c", lw=0.5)
    ax.plot([W / 2, W / 2], [-gov - 15, D + gov + 15], color=C_ROOF, lw=1.3)
    ax.text(W / 2 + 8, D * 0.82, "جسر القمة (حرف الجملون)", rotation=90, fontsize=8, color=C_ROOF, va="center")
    for x in g["xs"]:
        ax.add_patch(Rectangle((x - 5, -gov), 10, D + 2 * gov, fc="#e9d9c4", ec="#8b5a2b", lw=0.8))
    for y in g["ys"]:
        ax.add_patch(Rectangle((-ov * 0.4, y - 5), W + ov * 0.8, 10, fc="#e9d9c4", ec="#8b5a2b", lw=0.8))
        ax.text(W * 0.22, y + 9, "جمالون", fontsize=7, color="#8b5a2b", ha="center")
    for x in g["xs"]:
        for y in g["ys"]:
            ax.add_patch(Rectangle((x - ps / 2, y - ps / 2), ps, ps, fc="#3b2a1a", ec="k"))
            ax.add_patch(Rectangle((x - 25, y - 25), 50, 50, fill=False, ec="#777", lw=0.6, ls="--"))
    for s in (-1, 1):
        ax.annotate("", (W / 2 + s * W * 0.38, D * 0.12), (W / 2 + s * 30, D * 0.12),
                    arrowprops=dict(arrowstyle="->", color="red"))
        ax.text(W / 2 + s * W * 0.22, D * 0.12 + 10, f"ميل {d.get('pitch_deg', 30)}°", ha="center", fontsize=9,
                color="red")
    ax.text(W / 2, -gov - 40, "الواجهة الأمامية (الجملون)", ha="center", fontsize=10, weight="bold")
    ax.text(W / 2, D / 2, f"جلسة مفتوحة\n{W / 100:.2f} × {D / 100:.2f} م", ha="center", va="center", fontsize=11,
            bbox=dict(fc="white", ec="none", alpha=0.8))
    dim(ax, (0, D + gov), (W, D + gov), 45)
    dim(ax, (-ov, D + gov), (W + ov, D + gov), 80, fs=6)
    ys = g["ys"]
    for a, b in zip([0] + ys[1:-1], ys[1:-1] + [D]):
        dim(ax, (W + ov, b), (W + ov, a), 40, fs=6)
    dim(ax, (W + ov, D), (W + ov, 0), 75)
    ax.text(-ov, -gov - 75, f"▪ عمود {ps:.0f}×{ps:.0f} على قاعدة حديد ومسمار تثبيت في قاعدة خرسانة 50×50 (المتقطع)  "
            "▪ الرفرف المتقطع = حدود السقف", fontsize=7.5, color="#444")
    ax.set_xlim(-ov - 60, W + ov + 140)
    ax.set_ylim(-gov - 110, D + gov + 140)


def _truss_view(ax, g, d, label=True):
    """الواجهة الأمامية: جمالون مكشوف + أعمدة + كوابيل."""
    W, ov, Hp, ps = g["W"], g["ov"], g["Hp"], g["ps"]
    ax.plot([-ov - 80, W + ov + 80], [0, 0], color="k", lw=1)
    for x in g["xs"]:
        ax.add_patch(Rectangle((x - ps / 2, 0), ps, Hp, fc="#c9a27c", ec="k", lw=0.8))
        ax.add_patch(Rectangle((x - ps / 2 - 3, 0), ps + 6, 8, fc="#333", ec="k", lw=0.5))
        ax.add_patch(Rectangle((x - 5, Hp), 10, g["beam_d"], fc="#e9d9c4", ec="k", lw=0.6))
        dx = 1 if x < W / 2 else -1
        ax.add_patch(Polygon([(x + dx * ps / 2, Hp - 70), (x + dx * ps / 2, Hp - 60), (x + dx * 66, g["z_plate"] - 2),
                              (x + dx * 56, g["z_plate"] - 2)], closed=True, fc="#c9a27c", ec="k", lw=0.6))
    zt = g["z_plate"]
    ax.add_patch(Rectangle((-ov * 0.4, zt), W + ov * 0.8, g["tie_d"], fc="#c9a27c", ec="k", lw=0.8))
    ax.add_patch(Rectangle((W / 2 - 7.5, zt + g["tie_d"]), 15, g["z_ridge"] - g["beam_d"] - zt - g["tie_d"],
                           fc="#c9a27c", ec="k", lw=0.8))
    ax.add_patch(Rectangle((W / 2 - 5, g["z_ridge"] - g["beam_d"]), 10, g["beam_d"], fc="#e9d9c4", ec="k", lw=0.6))
    for sg in (-1, 1):
        xa, za = W / 2 + sg * 7.5, zt + g["tie_d"] + 25
        xb = W / 2 + sg * W * 0.25
        zb = zr(g, xb)
        nx, nz = -(zb - za), (xb - xa)
        L = math.hypot(nx, nz)
        nx, nz = nx / L * 4, nz / L * 4
        ax.add_patch(Polygon([(xa - nx, za - nz), (xb - nx, zb - nz), (xb + nx, zb + nz), (xa + nx, za + nz)],
                             closed=True, fc="#c9a27c", ec="k", lw=0.6))
    kv, t = g["kv"], g["t"]
    lo = [(-ov, g["z_plate"] - ov * t), (W / 2, g["z_ridge"]), (W + ov, g["z_plate"] - ov * t)]
    for (z0, z1, fc) in ((0, g["raf_d"], "#e8cfa9"), (g["raf_d"], g["raf_d"] + 2.5, "#d9b98a"),
                         (g["raf_d"] + 2.5, g["raf_d"] + 6, "#555")):
        a = [(x, z + z0 * kv) for x, z in lo]
        b = [(x, z + z1 * kv) for x, z in lo]
        ax.add_patch(Polygon(a + b[::-1], closed=True, fc=fc, ec="k", lw=0.5))
    if label:
        ax.annotate("قرميد معدني", (W * 0.2, zr(g, W * 0.2) + (g["raf_d"] + 5) * kv), (W * 0.02, g["z_ridge"] + 80),
                    fontsize=8, arrowprops=dict(arrowstyle="-", lw=0.5))
        ax.annotate("تطبيق خشب 2.5 (يبان من تحت)", (W * 0.75, zr(g, W * 0.75) + (g["raf_d"] + 1) * kv),
                    (W * 0.72, g["z_ridge"] + 80), fontsize=8, arrowprops=dict(arrowstyle="-", lw=0.5))
        ax.text(W / 2, zt + g["tie_d"] / 2, "شداد 2×(5×15)", ha="center", va="center", fontsize=7)
    top = g["z_ridge"] + (g["raf_d"] + 6) * kv
    lx = -ov - 60
    level(ax, lx, 0, 0.0001, "الأرض")
    level(ax, lx, Hp, Hp / 100, "أسفل الجسر")
    level(ax, lx, top, top / 100, "أعلى السقف")
    dim(ax, (0, -5), (W, -5), -30)
    dim(ax, (W + ov, 0), (W + ov, Hp), -45)
    dim(ax, (W + ov, Hp), (W + ov, top), -45)
    ax.set_xlim(-ov - 140, W + ov + 110)
    ax.set_ylim(-80, top + 130)
    return top


def _side_view(ax, g, d):
    D, gov, Hp, ps = g["D"], g["gov"], g["Hp"], g["ps"]
    ax.plot([-gov - 80, D + gov + 80], [0, 0], color="k", lw=1)
    for y in g["ys"]:
        ax.add_patch(Rectangle((y - ps / 2, 0), ps, Hp, fc="#c9a27c", ec="k", lw=0.8))
        ax.add_patch(Rectangle((y - ps / 2 - 3, 0), ps + 6, 8, fc="#333", ec="k", lw=0.5))
        for dy in (-1, 1):
            if 0 <= y + dy * 60 <= D:
                ax.add_patch(Polygon([(y + dy * ps / 2, Hp - 70), (y + dy * ps / 2, Hp - 60), (y + dy * 66, Hp - 2),
                                      (y + dy * 56, Hp - 2)], closed=True, fc="#c9a27c", ec="k", lw=0.6))
    ax.add_patch(Rectangle((-gov, Hp), D + 2 * gov, g["beam_d"], fc="#e9d9c4", ec="k", lw=0.8))
    kv, t = g["kv"], g["t"]
    ze = g["z_plate"] - g["ov"] * t
    top = g["z_ridge"] + (g["raf_d"] + 6) * kv
    ax.add_patch(Rectangle((-gov, ze), D + 2 * gov, top - ze, fc="#fff3e0", ec=C_ROOF, lw=0.9))
    yy = ze + 12
    while yy < top - 4:
        ax.plot([-gov, D + gov], [yy, yy], color=C_ROOF, lw=0.3)
        yy += 12
    ax.text(D / 2, Hp + g["beam_d"] / 2, "جسر طرفي 2×(5×22.5)", ha="center", va="center", fontsize=7)
    ys = g["ys"]
    for a, b in zip(ys, ys[1:]):
        dim(ax, (a, -5), (b, -5), -30, fs=6)
    dim(ax, (-gov, -5), (D + gov, -5), -60, fs=6)
    ax.set_xlim(-gov - 100, D + gov + 100)
    ax.set_ylim(-110, top + 60)


def _details(fig, g):
    ps = g["ps"]
    ax = drawing_ax(fig, [0.06, 0.12, 0.4, 0.36])
    title(ax, "تفصيلة السقف — طبقتين فقط", "مقياس 1:5")
    t = g["t"]
    ca, sa = math.cos(g["pitch"]), math.sin(g["pitch"])

    def band(z0, z1, fc, lab):
        pts = [(0, z0), (70 * ca, z0 + 70 * sa), (70 * ca - (z1 - z0) * sa, z1 + 70 * sa), (-(z1 - z0) * sa, z1)]
        pts = [(x, z0 + (x * t)) for x, _ in [(0, 0)]] and pts
        ax.add_patch(Polygon(pts, closed=True, fc=fc, ec="k", lw=0.8))
        ax.text(78 * ca, z0 + 75 * sa + (z1 - z0) / 2, lab, fontsize=8, va="center")
    ax.add_patch(Polygon([(0, 0), (70 * ca, 70 * sa), (70 * ca - 15 * sa, 70 * sa + 15 * ca), (-15 * sa, 15 * ca)],
                         closed=True, fc="#e8cfa9", ec="k", lw=0.8))
    ax.text(78 * ca, 70 * sa + 7, "مداد 5×15 كل 60 سم", fontsize=8, va="center")
    o1 = 15
    ax.add_patch(Polygon([(-o1 * sa, o1 * ca), (70 * ca - o1 * sa, 70 * sa + o1 * ca),
                          (70 * ca - (o1 + 2.5) * sa, 70 * sa + (o1 + 2.5) * ca), (-(o1 + 2.5) * sa, (o1 + 2.5) * ca)],
                         closed=True, fc="#d9b98a", ec="k", lw=0.8))
    ax.text(78 * ca, 70 * sa + o1 + 3, "1) تطبيق خشب لسان ونقر 2.5 سم (السقف الداخلي)", fontsize=8, va="center")
    o2 = o1 + 2.5
    ax.add_patch(Polygon([(-o2 * sa, o2 * ca), (70 * ca - o2 * sa, 70 * sa + o2 * ca),
                          (70 * ca - (o2 + 1.5) * sa, 70 * sa + (o2 + 1.5) * ca), (-(o2 + 1.5) * sa, (o2 + 1.5) * ca)],
                         closed=True, fc="#444", ec="k", lw=0.8))
    ax.text(78 * ca, 70 * sa + o2 + 8, "2) قرميد معدني مثبت ببراغي على التطبيق", fontsize=8, va="center")
    ax.set_xlim(-30, 150)
    ax.set_ylim(-15, 75)
    ax2 = drawing_ax(fig, [0.52, 0.12, 0.42, 0.36])
    title(ax2, "تفصيلة قاعدة العمود", "مقياس 1:10")
    ax2.add_patch(Rectangle((-25, -60), 50, 60, fc="#ddd", ec="k", hatch="..", lw=0.8))
    h2 = ps / 2
    ax2.add_patch(Rectangle((-h2 - 1.5, 0), ps + 3, 1.5, fc="#333", ec="k"))
    ax2.add_patch(Rectangle((-h2 - 1.5, 0), 2, 20, fc="#333", ec="k"))
    ax2.add_patch(Rectangle((h2 - 0.5, 0), 2, 20, fc="#333", ec="k"))
    ax2.add_patch(Rectangle((-h2, 3), ps, 70, fc="#c9a27c", ec="k"))
    for x in (-5, 5):
        ax2.plot([x, x], [-15, 0], color="k", lw=1.5)
    ax2.text(30, 40, f"عمود {ps:.0f}×{ps:.0f} ({round(ps / 5)} طبقات 5 سم مبرغية)", fontsize=8)
    ax2.text(30, 12, "قاعدة حديد U مجلفنة + برغيين M12\nترفع الخشب 3 سم عن الأرض (ما يلمس المويه)", fontsize=8)
    ax2.text(30, -30, "قاعدة خرسانة 50×50×60 + مسامير تثبيت", fontsize=8)
    ax2.set_xlim(-40, 140)
    ax2.set_ylim(-70, 80)


def build(project_path, out_dir):
    rules = load_rules(None)
    d = yaml.safe_load(open(project_path, encoding="utf-8"))
    style = resolve_style(d.get("style", "walnut_black"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = d["name"]
    S, g = build_scene(d, rules, style)
    q = quantities(d, rules, g)
    S.write_glb(out / f"{stem}_3d.glb")
    S.write_obj(out / f"{stem}_3d.obj", d["title"])
    prev = out / f"{stem}_3d.png"
    render_preview(S, prev, strip=rules["cladding"]["effective_cover"])
    views = out / f"{stem}_views.png"
    render_preview(S, views, views=((12, -90), (25, -40)), size=(16, 7), strip=rules["cladding"]["effective_cover"])
    ctx = {"project": _P(d)}
    pages = []
    fig = new_page(A3L)
    _plan(fig, g, d)
    ax = fig.add_axes([0.64, 0.5, 0.33, 0.4])
    ax.imshow(plt.imread(prev))
    ax.axis("off")
    pages.append((fig, "المسقط ومسقط السقف", "1:50"))
    fig = new_page(A3L)
    ax = drawing_ax(fig, [0.04, 0.14, 0.46, 0.76])
    _truss_view(ax, g, d)
    ax.set_title("الواجهة الأمامية — جمالون مكشوف\nمقياس 1:50", fontsize=13)
    ax = drawing_ax(fig, [0.52, 0.14, 0.46, 0.76])
    _side_view(ax, g, d)
    ax.set_title("الواجهة الجانبية\nمقياس 1:50", fontsize=13)
    pages.append((fig, "الواجهات", "1:50"))
    fig = new_page(A3L)
    ax = drawing_ax(fig, [0.25, 0.52, 0.5, 0.4])
    _truss_view(ax, g, d, label=True)
    ax.set_title("قطاع الجمالون (كل جمالون)", fontsize=13)
    _details(fig, g)
    pages.append((fig, "الجمالون والتفاصيل", "1:50 / 1:5"))
    # جدول الكميات + البيانات + السعر
    fig = new_page(A3L)
    fig.text(0.5, 0.945, "جدول الكميات وبيانات المشروع", ha="center", fontsize=18, weight="bold", color=BRAND)
    rows = [[n, desc, str(cnt), f"{L:.0f}", sec] for n, desc, cnt, L, sec in q["rows"]]
    rows.append(["تطبيق خشب 2.5 سم (الطبقة 1)", f"{q['area_roof']:.1f} م²", str(q["boards"]), str(q["board_L"]), "لوح"])
    rows.append(["قرميد معدني (الطبقة 2) + غطاء الحرف وحواف الجملون", f"{q['area_roof']:.1f} م²",
                 "—", f"حرف {g['D'] + 2 * g['gov']:.0f}", "م²"])
    rows.append(["قواعد حديد U مجلفنة + قواعد خرسانة 50×50×60", "", str(q["n_posts"]), "—", "طقم"])
    ax = fig.add_axes([0.03, 0.36, 0.58, 0.52])
    table(ax, ["البند", "الوصف", "العدد", "الطول (سم)", "المقطع"], rows, [4.6, 2.2, 0.8, 1.1, 0.9], fs=8.5)
    ax.set_title("الكميات", fontsize=13, weight="bold", color=BRAND, loc="right")
    pal = [[f"طبلية {s} سم ({sec})", str(n)] for (s, sec), n in sorted(q["pallets"].items(), key=lambda kv: str(kv))]
    pal.append(["الإجمالي", str(sum(q["pallets"].values()))])
    ax = fig.add_axes([0.03, 0.12, 0.3, 0.2])
    table(ax, ["الطبليات 5×22.5", "العدد"], pal, [2.6, 1], fs=9, bold_last=1)
    m = d.get("meta", {})
    info = [["المشروع", d["title"]], ["العميل", d.get("client", "")], ["التاريخ", str(m.get("date", ""))],
            ["المقاس", f"{g['W'] / 100:.2f} × {g['D'] / 100:.2f} م = {q['area']:.1f} م²"],
            ["الأعمدة", f"{q['n_posts']} أعمدة {g['ps']:.0f}×{g['ps']:.0f} نازلة للأرض على قواعد حديد"],
            ["السقف", f"جملون {d.get('pitch_deg', 30)}° — طبقتين: تطبيق خشب + قرميد معدني"],
            ["الجمالونات", f"{len(g['ys'])} جمالون مكشوف (شداد + قائم + ذراعين)"]]
    ax = fig.add_axes([0.65, 0.5, 0.32, 0.38])
    table(ax, ["البند", "البيان"], info, [1.2, 3.6], fs=9)
    ax.set_title("بيانات المشروع", fontsize=13, weight="bold", color=BRAND, loc="right")
    price = d.get("price_per_m2")
    prow = ([["المساحة (م²)", f"{q['area']:.2f}"], ["سعر المتر", f"{price:,.0f} ريال"],
             ["الإجمالي", f"{q['area'] * price:,.0f} ريال"]] if price else
            [["المساحة (م²)", f"{q['area']:.2f}"], ["سعر المتر", "يُحدد بعد الاعتماد"], ["الإجمالي", "—"]])
    ax = fig.add_axes([0.65, 0.22, 0.32, 0.2])
    table(ax, ["البند", "القيمة"], prow, [2.2, 2], fs=10, bold_last=1)
    ax.set_title("التسعير", fontsize=13, weight="bold", color=BRAND, loc="right")
    fig.text(0.97, 0.16, "• الأرضية (بلاط/خرسانة) على العميل ما لم يُذكر غير ذلك.  • الطبليات حسب طرق المصنع — TO_CONFIRM",
             ha="right", fontsize=8.5, color="#444")
    pages.append((fig, "الكميات والتسعير", "—"))
    fig = new_page(A3L)
    fig.text(0.5, 0.94, "المنظور ثلاثي الأبعاد", ha="center", fontsize=18, weight="bold", color=BRAND)
    ax = fig.add_axes([0.03, 0.12, 0.94, 0.78])
    ax.imshow(plt.imread(views))
    ax.axis("off")
    pages.append((fig, "المنظور", "—"))
    pdf = out / f"{stem}_client.pdf"
    with PdfPages(pdf) as P:
        for i, (fig, sheet, scale) in enumerate(pages, 1):
            lift_content(fig)
            title_block(fig, ctx, sheet, f"A-{i:02d}", i, len(pages), scale)
            P.savefig(fig)
            plt.close(fig)
    dxf = out / f"{stem}.dxf"
    _dxf(g, dxf)
    return {"pdf": pdf, "dxf": dxf, "preview": prev, "views": views}, q


def _dxf(g, path):
    import ezdxf
    doc = ezdxf.new("R2010")
    for name, col in (("POSTS", 1), ("BEAMS", 30), ("RAFTERS", 8), ("ROOF", 2), ("ELEV", 7)):
        doc.layers.add(name, color=col)
    ms = doc.modelspace()
    W, D, ps, ov, gov = g["W"], g["D"], g["ps"], g["ov"], g["gov"]
    rect = lambda x0, y0, x1, y1, layer: ms.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,  # noqa: E731
                                                          dxfattribs={"layer": layer})
    for x in g["xs"]:
        for y in g["ys"]:
            rect(x - ps / 2, y - ps / 2, x + ps / 2, y + ps / 2, "POSTS")
        rect(x - 5, -gov, x + 5, D + gov, "BEAMS")
    for y in g["ys"]:
        rect(-ov * 0.4, y - 5, W + ov * 0.4, y + 5, "BEAMS")
    for p in g["rpos"]:
        ms.add_line((-ov, p), (W + ov, p), dxfattribs={"layer": "RAFTERS"})
    rect(-ov, -gov, W + ov, D + gov, "ROOF")
    ms.add_line((W / 2, -gov), (W / 2, D + gov), dxfattribs={"layer": "ROOF"})
    # الواجهة الأمامية بجانب المسقط
    ox = W + 300
    for x in g["xs"]:
        rect(ox + x - ps / 2, 0, ox + x + ps / 2, g["Hp"], "ELEV")
    rect(ox - ov * 0.4, g["z_plate"], ox + W + ov * 0.4, g["z_plate"] + g["tie_d"], "ELEV")
    t = g["t"]
    ms.add_lwpolyline([(ox - ov, g["z_plate"] - ov * t), (ox + W / 2, g["z_ridge"]), (ox + W + ov, g["z_plate"] - ov * t)],
                      dxfattribs={"layer": "ROOF"})
    ms.add_line((ox + W / 2, g["z_plate"] + g["tie_d"]), (ox + W / 2, g["z_ridge"]), dxfattribs={"layer": "ELEV"})
    doc.saveas(path)
