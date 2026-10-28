"""مخطط محمية الطيور 30 × 15 م: المسقط بالتوزيع + المقاطع والواجهات + جدول المواصفات (PDF A3) + DXF.
تشغيل: python tools/aviary/aviary_plan.py <out_dir>
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Ellipse, Polygon, Rectangle, Circle  # noqa: E402
from watad import sheets as SH  # noqa: E402  (الخطوط والإطار والأبعاد)
import layout as Y  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)
C_STEEL, C_MESH, C_WATER, C_PATH, C_GREEN = "#5E6670", "#8A9099", "#5AA8D6", "#CDBFA6", "#7DAA5E"


class _P:   # بيانات إطار العنوان
    title = "محمية طيور — 30.00 × 15.00 م (450 م²)"
    client = "مشروع — محمية طيور"
    meta = {"date": "2026-10-28"}


CTX = {"project": _P}
SHEETS = ["المسقط الأفقي والتوزيع", "الواجهات والمقطع", "المواصفات والكميات"]


def dim(ax, a, b, off, text=None, fs=7, color=SH.C_DIM):
    """خط بُعد بالمتر (نسخة من SH.dim بمقياس المتر)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return
    nx, ny = -dy / L, dx / L
    pa = (a[0] + nx * off, a[1] + ny * off)
    pb = (b[0] + nx * off, b[1] + ny * off)
    ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color=color, lw=0.6)
    k = 0.12 if off >= 0 else -0.12
    for p, q in ((a, pa), (b, pb)):
        ax.plot([p[0] + nx * k * 0.6, q[0] + nx * k], [p[1] + ny * k * 0.6, q[1] + ny * k], color=color, lw=0.35)
        s = 0.1
        ax.plot([q[0] - (dx / L + nx) * s, q[0] + (dx / L + nx) * s],
                [q[1] - (dy / L + ny) * s, q[1] + (dy / L + ny) * s], color=color, lw=0.9)
    ang = math.degrees(math.atan2(dy, dx))
    if ang > 90.1 or ang < -89.9:
        ang -= 180
    t = f"{L:.2f}" if text is None else text
    sgn = 1 if off >= 0 else -1
    mx, my = (pa[0] + pb[0]) / 2 + nx * 0.25 * sgn, (pa[1] + pb[1]) / 2 + ny * 0.25 * sgn
    ax.text(mx, my, t, rotation=ang, ha="center", va="center", fontsize=fs, color=color, rotation_mode="anchor")


def chain(ax, pts, off, fs=7):
    for a, b in zip(pts, pts[1:]):
        dim(ax, a, b, off, fs=fs)


def frame(fig, i, name, scale):
    SH.title_block(fig, CTX, name, f"AV-0{i}", i, len(SHEETS), scale)


def path_poly(pts, w):
    """شريط الممر حول خط المنتصف."""
    left, right = [], []
    for k, (x, y) in enumerate(pts):
        a = pts[max(k - 1, 0)]
        b = pts[min(k + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        nx, ny = -dy / n * w / 2, dx / n * w / 2
        left.append((x + nx, y + ny))
        right.append((x - nx, y - ny))
    return left + right[::-1]


def smooth(pts, n=8):
    """Catmull-Rom لنعومة الممر والمجرى."""
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in [j / n for j in range(n)]:
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in (0, 1)))
    out.append(pts[-1])
    return out


def plan(ax):
    # تربة/زراعة
    ax.add_patch(Rectangle((0, 0), Y.L, Y.W, fc="#EEF3E4", ec="none", zorder=0))
    # الممر
    sp = smooth(Y.PATH)
    ax.add_patch(Polygon(path_poly(sp, Y.PATH_W), closed=True, fc=C_PATH, ec="#9C8A6C", lw=0.6, zorder=2))
    for spur in Y.SPURS:
        ax.add_patch(Polygon(path_poly(smooth(spur), Y.PATH_W * 0.85), closed=True, fc=C_PATH, ec="#9C8A6C", lw=0.6, zorder=2))
    # البحيرة + المجرى + الشلال
    st = smooth(Y.STREAM)
    ax.add_patch(Polygon(path_poly(st, 0.55), closed=True, fc=C_WATER, ec="#2F78A8", lw=0.5, zorder=3))
    cx, cy, rx, ry = Y.POND
    ax.add_patch(Ellipse((cx, cy), 2 * rx, 2 * ry, fc=C_WATER, ec="#2F78A8", lw=0.8, zorder=3))
    fx, fy, fr, fh = Y.FALL
    ax.add_patch(Circle((fx, fy), fr, fc="#B9AC96", ec="#7A6A55", lw=0.7, hatch="..", zorder=3))
    ax.text(fx, fy, "شلال\nصخري", ha="center", va="center", fontsize=7, zorder=6)
    ax.text(cx, cy, f"بحيرة ضحلة\n{2 * rx:.1f} × {2 * ry:.1f} م (عمق 30–40 سم)", ha="center", va="center", fontsize=7, zorder=6)
    # منصة المشاهدة
    d = Y.DECK
    ax.add_patch(Rectangle((d[0], d[1]), d[2] - d[0], d[3] - d[1], fc="#D9B98A", ec="#7A5232", lw=0.8, zorder=4))
    ax.text((d[0] + d[2]) / 2, (d[1] + d[3]) / 2, "منصة مشاهدة\nخشب + جلسة\n3.00 × 3.00", ha="center", va="center",
            fontsize=7, zorder=6)
    # أشجار وشجيرات
    for x, y, k in Y.TREES:
        ax.add_patch(Circle((x, y), 1.1 if k != "palm" else 0.9, fc=C_GREEN, ec="#4F7A3A", lw=0.6, alpha=0.75, zorder=4))
        ax.add_patch(Circle((x, y), 0.12, fc="#6B4A2E", zorder=5))
    for x, y in Y.SHRUBS:
        ax.add_patch(Circle((x, y), 0.5, fc="#9CC27A", ec="#5F8A45", lw=0.5, zorder=4))
    for x, y in Y.PERCHES:
        ax.plot([x - 0.7, x + 0.7], [y - 0.3, y + 0.3], color="#6B4A2E", lw=3, zorder=5)
        ax.text(x, y - 0.6, "مجثم", ha="center", fontsize=6, zorder=6)
    for x, y in Y.FEEDERS:
        ax.add_patch(Rectangle((x - 0.6, y - 0.6), 1.2, 1.2, fc="#F2E2C2", ec="#8B6A3E", lw=0.8, zorder=5))
        ax.text(x, y, "أكل\nوماء", ha="center", va="center", fontsize=6, zorder=6)
    for x, y in Y.NESTS:
        ax.add_patch(Rectangle((x - 0.25, y - 0.45), 0.5, 0.4, fc="#C08A55", ec="#6B4A2E", lw=0.6, zorder=5))
    ax.text(13.5, 14.2, "بيوت تعشيش على الجدار الخلفي (ارتفاع 2.20 م)", ha="center", fontsize=6.5, zorder=6)
    for x, y in Y.FANS:
        ax.add_patch(Circle((x, y), 0.6, fill=False, ec="#444", lw=0.6, ls="--", zorder=6))
        ax.text(x, y + 0.75, "مروحة سقف", ha="center", fontsize=6, zorder=6)
    for my in Y.MIST_Y:
        ax.plot([0.3, Y.L - 0.3], [my, my], color="#2F78A8", lw=0.6, ls=(0, (2, 3)), zorder=6)
    ax.text(0.5, Y.MIST_Y[0] + 0.15, "خط رذاذ (اختياري)", fontsize=6, color="#2F78A8", zorder=6)
    # إنارة الممر
    acc, last = 0.0, sp[0]
    for p in sp[1:]:
        acc += math.hypot(p[0] - last[0], p[1] - last[1])
        if acc >= Y.BOLLARDS_EVERY:
            acc = 0
            ax.add_patch(Circle(p, 0.12, fc="#F5C04A", ec="#8A6A10", lw=0.5, zorder=7))
        last = p
    # غرفة الخدمة
    s = Y.SERVICE
    ax.add_patch(Rectangle((s[0], s[1]), s[2] - s[0], s[3] - s[1], fc="#E8E2D8", ec="k", lw=1.6, hatch="////", zorder=6))
    ax.add_patch(Rectangle((s[0] + 0.15, s[1] + 0.15), s[2] - s[0] - 0.3, s[3] - s[1] - 0.3, fc="white", ec="k", lw=0.8, zorder=7))
    ax.text((s[0] + s[2]) / 2, (s[1] + s[3]) / 2, "غرفة خدمة\nوأعلاف\n3.60 × 3.50", ha="center", va="center", fontsize=7, zorder=8)
    ax.plot([s[2], s[2]], [s[1] + 0.6, s[1] + 1.5], color="white", lw=4, zorder=8)
    ax.plot([s[2], s[2]], [s[1] + 0.6, s[1] + 1.5], color=SH.C_DOOR, lw=1.4, zorder=9)
    ax.plot([0, 0], [s[1] + 1.2, s[1] + 2.2], color="white", lw=4, zorder=8)
    ax.plot([0, 0], [s[1] + 1.2, s[1] + 2.2], color=SH.C_DOOR, lw=1.4, zorder=9)
    ax.text(-0.35, s[1] + 1.7, "باب خدمة خارجي", rotation=90, ha="center", va="center", fontsize=6, color=SH.C_DOOR)
    # المحيط: شبك + أعمدة
    ax.add_patch(Rectangle((0, 0), Y.L, Y.W, fill=False, ec=C_MESH, lw=2.2, zorder=8))
    for x in Y.COL_X:
        for y in (0, Y.W):
            ax.add_patch(Rectangle((x - 0.1, y - 0.1), 0.2, 0.2, fc=C_STEEL, ec="k", lw=0.4, zorder=9))
    for y in Y.COL_Y[1:-1]:
        for x in (0, Y.L):
            ax.add_patch(Rectangle((x - 0.1, y - 0.1), 0.2, 0.2, fc=C_STEEL, ec="k", lw=0.4, zorder=9))
    # غرفة الأمان (بابين)
    a = Y.AIRLOCK
    ax.add_patch(Rectangle((a[0], a[1]), a[2] - a[0], a[3] - a[1], fc="#F4F4F4", ec=C_STEEL, lw=1.6, zorder=8))
    for yy, (d0, d1) in ((a[1], Y.DOOR_OUT), (0.0, Y.DOOR_IN)):
        ax.plot([d0, d1], [yy, yy], color="white", lw=5, zorder=9)
        ax.plot([d0, d1], [yy, yy], color=SH.C_DOOR, lw=1.5, zorder=10)
        arc = [(d0 + 1.0 * math.cos(t), yy + 1.0 * math.sin(t)) for t in [k * math.pi / 40 for k in range(21)]]
        ax.plot(*zip(*arc), color=SH.C_DOOR, lw=0.6, zorder=10)
    ax.text((a[0] + a[2]) / 2, (a[1] + a[3]) / 2 - 0.25, "غرفة أمان\nبابين (2.40 × 2.20)", ha="center", va="center", fontsize=6.5, zorder=11)
    ax.annotate("المدخل", ((a[0] + a[2]) / 2, a[1] - 0.2), ((a[0] + a[2]) / 2, a[1] - 1.3), ha="center", fontsize=9,
                weight="bold", arrowprops=dict(arrowstyle="->", lw=1.2), zorder=11)
    # أبعاد: الإجمالي ثم التقسيمات
    dim(ax, (0, Y.W), (Y.L, Y.W), 2.2, "30.00", fs=9)
    chain(ax, [(x, Y.W) for x in Y.COL_X], 1.1, fs=6.5)
    dim(ax, (Y.L, 0), (Y.L, Y.W), -2.2, "15.00", fs=9)
    chain(ax, [(Y.L, y) for y in Y.COL_Y], -1.1, fs=6.5)
    ax.text(Y.L / 2, -4.4, "عرض الممر 1.40 م — حجر طبيعي على قاعدة رمل مدكوك", ha="center", fontsize=7.5)
    ax.set_xlim(-3.5, Y.L + 3.5)
    ax.set_ylim(-5.0, Y.W + 3.5)


def elevation(ax, front=True):
    span = Y.L if front else Y.W
    cols = Y.COL_X if front else Y.COL_Y
    gx = -0.5
    ax.plot([gx - 1, span + 1], [0, 0], color="k", lw=1.2)
    ax.add_patch(Rectangle((0, 0), span, Y.PLINTH, fc="#D8CDBB", ec="k", lw=0.8, hatch="xx"))
    top = Y.H_EAVE
    ax.add_patch(Rectangle((0, Y.PLINTH), span, top - Y.PLINTH, fc="#F0F2F4", ec=C_MESH, lw=0.8, hatch="++", alpha=0.6))
    for c in cols:
        ax.add_patch(Rectangle((c - 0.08, 0), 0.16, top, fc=C_STEEL, ec="k", lw=0.5))
    if front:
        ax.add_patch(Rectangle((0, top), span, 0.12, fc=C_STEEL, ec="k", lw=0.5))
        ax.add_patch(Rectangle((0, top + 0.12), span, Y.H_RIDGE - top - 0.12, fc="#C9955E", ec="#7A5232", lw=0.7))
        a = Y.AIRLOCK
        ax.add_patch(Rectangle((a[0], 0), a[2] - a[0], 2.4, fc="#E6E6E6", ec=C_STEEL, lw=1.2))
        ax.add_patch(Rectangle((Y.DOOR_OUT[0], 0), Y.DOOR_OUT[1] - Y.DOOR_OUT[0], 2.1, fc="white", ec=SH.C_DOOR, lw=1.2))
        ax.text(15, 2.6, "غرفة الأمان", ha="center", fontsize=7)
    else:
        ax.add_patch(Polygon([(0, top), (span / 2, Y.H_RIDGE), (span, top)], closed=True, fc="#C9955E", ec="#7A5232", lw=0.8))
    dim(ax, (0, 0), (span, 0), -0.9, f"{span:.2f}", fs=8)
    dim(ax, (span, 0), (span, top), -0.8, f"{top:.2f}", fs=7)
    dim(ax, (span + 0.9, 0), (span + 0.9, Y.H_RIDGE), -0.6, f"{Y.H_RIDGE:.2f}", fs=7)
    ax.set_xlim(-2, span + 2.5)
    ax.set_ylim(-1.8, Y.H_RIDGE + 1.0)


def section(ax):
    span = Y.W
    ax.plot([-1, span + 1], [0, 0], color="k", lw=1.2)
    for x in (0, span):
        ax.add_patch(Rectangle((x - 0.1, 0), 0.2, Y.H_EAVE, fc=C_STEEL, ec="k", lw=0.6))
    ax.add_patch(Rectangle((-0.1, -0.6), 0.2, 0.6, fc="#BBB", ec="k", lw=0.5, hatch="//"))
    ax.add_patch(Rectangle((span - 0.1, -0.6), 0.2, 0.6, fc="#BBB", ec="k", lw=0.5, hatch="//"))
    for x in Y.COL_Y[1:-1]:
        ax.add_patch(Rectangle((x - 0.06, 0), 0.12, Y.H_EAVE + (Y.H_RIDGE - Y.H_EAVE) * (1 - abs(x - span / 2) / (span / 2)),
                               fc="#88909A", ec="k", lw=0.4))
    ax.plot([0, span / 2, span], [Y.H_EAVE, Y.H_RIDGE, Y.H_EAVE], color="#8A7448", lw=3)
    ax.plot([0, span], [Y.H_EAVE - 0.05] * 2, color=C_STEEL, lw=1)
    for my in Y.MIST_Y:
        ax.add_patch(Circle((my, Y.H_EAVE - 0.2), 0.06, fc="#2F78A8"))
    ax.add_patch(Ellipse((Y.POND[1] + 0.0, -0.15), 2 * Y.POND[3], 0.3, fc=C_WATER, ec="#2F78A8"))
    ax.text(span / 2, Y.H_RIDGE + 0.25, "سقف خشب: ألواح خشب معالج + عزل مائي على جسور ومدادات خشب", ha="center", fontsize=7.5)
    ax.text(0.3, 1.7, "شبك حديد مجلفن\nفتحة 12.5 × 12.5 مم", fontsize=7)
    ax.text(span - 0.3, -0.45, "قاعدة خرسانية\n+ جدار حجر 50 سم", ha="right", fontsize=6.5)
    dim(ax, (0, 0), (span, 0), -1.1, "15.00", fs=8)
    dim(ax, (span, 0), (span, Y.H_EAVE), -0.8, "3.00", fs=7)
    dim(ax, (span / 2, 0), (span / 2, Y.H_RIDGE), 0.6, "3.50", fs=7)
    ax.set_xlim(-2, span + 2)
    ax.set_ylim(-2, Y.H_RIDGE + 1)


SPEC = [
    ["المساحة الإجمالية", "450 م² (30.00 × 15.00) + غرفة أمان 5.3 م²"],
    ["ارتفاع السقف", "3.00 م عند الأطراف — 3.50 م بالقمة (جملون منخفض يصرّف المطر)"],
    ["الهيكل", "تيوبات حديد مجلفن: أعمدة 100×100×3 مم كل 3.00 م، جسور 100×50، مدادات 50×50"],
    ["الشبك", "شبك حديد مجلفن ملحوم 12.5 × 12.5 مم (يمنع العصافير الصغيرة والثعابين)"],
    ["القاعدة", "قواعد خرسانية + جدار حجر 50 سم على المحيط (ضد الحفر والقوارض)"],
    ["تغطية السقف", "خشب: ألواح خشب معالج (لسان ومجرى) + عزل مائي وطبقة حماية، على جسور خشب كل 3.00 م ومدادات خشب — تظليل كامل"],
    ["التهوية والتلطيف", "3 مراوح سقف + خطين رذاذ ماء بطول 30 م (اختياري)"],
    ["الماء", "شلال صخري + مجرى 10 م + بحيرة ضحلة 6.6 × 3.8 م (30–40 سم) بمضخة وفلتر"],
    ["الإضاءة", "LED: إنارة أرضية على الممر كل 3.2 م + شريط دافي تحت الجسور + سبوت للشلال"],
    ["الزراعة", "16 شجرة (برتقال، مانجو، نخل قزم) + 14 شجيرة بأحواض ري بالتنقيط"],
    ["الممرات", "ممر دائري حجر طبيعي عرض 1.40 م ≈ 75 م طولي + منصة مشاهدة خشب 3×3"],
    ["مرافق الطيور", "4 مجاثم جذوع + 2 محطة أكل مظللة + 6 بيوت تعشيش + حمّام رمل"],
    ["الأمان", "غرفة أمان بابين (ما ينفتح الباب الثاني إلا بعد قفل الأول) + غرفة خدمة بباب خارجي"],
]


def specs(fig):
    ax = fig.add_axes([0.12, 0.2, 0.76, 0.66])
    SH.table(ax, ["البند", "المواصفات"], [[a, b] for a, b in SPEC], [2.2, 7.5], fs=11)
    ax.set_title("مواصفات محمية الطيور", fontsize=16, weight="bold", color=SH.BRAND, loc="right")


def main():
    pdf_path = os.path.join(OUT, "aviary-30x15-autocad.pdf")
    with PdfPages(pdf_path) as pdf:
        fig = SH.new_page()
        ax = SH.drawing_ax(fig, [0.04, 0.1, 0.92, 0.82])
        plan(ax)
        SH.title(ax, "المسقط الأفقي والتوزيع — محمية الطيور", "الأبعاد بالمتر  |  الأعمدة كل 3.00 م بالطول و 3.75 م بالعرض")
        frame(fig, 1, SHEETS[0], "1:100")
        pdf.savefig(fig)
        plt.close(fig)
        fig = SH.new_page()
        ax1 = SH.drawing_ax(fig, [0.04, 0.55, 0.92, 0.36])
        elevation(ax1, True)
        SH.title(ax1, "الواجهة الأمامية (الجنوبية) — المدخل")
        ax2 = SH.drawing_ax(fig, [0.04, 0.12, 0.44, 0.36])
        elevation(ax2, False)
        SH.title(ax2, "الواجهة الجانبية")
        ax3 = SH.drawing_ax(fig, [0.52, 0.12, 0.44, 0.36])
        section(ax3)
        SH.title(ax3, "مقطع عرضي")
        frame(fig, 2, SHEETS[1], "1:100")
        pdf.savefig(fig)
        plt.close(fig)
        fig = SH.new_page()
        specs(fig)
        frame(fig, 3, SHEETS[2], "—")
        pdf.savefig(fig)
        plt.close(fig)
    # DXF
    import ezdxf
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (Y.L, 0), (Y.L, Y.W), (0, Y.W)], close=True, dxfattribs={"layer": "MESH"})
    a = Y.AIRLOCK
    msp.add_lwpolyline([(a[0], a[1]), (a[2], a[1]), (a[2], a[3]), (a[0], a[3])], close=True, dxfattribs={"layer": "AIRLOCK"})
    s = Y.SERVICE
    msp.add_lwpolyline([(s[0], s[1]), (s[2], s[1]), (s[2], s[3]), (s[0], s[3])], close=True, dxfattribs={"layer": "SERVICE"})
    for x in Y.COL_X:
        for y in (0, Y.W):
            msp.add_circle((x, y), 0.07, dxfattribs={"layer": "COLUMNS"})
    sp = smooth(Y.PATH)
    msp.add_lwpolyline(path_poly(sp, Y.PATH_W), close=True, dxfattribs={"layer": "PATH"})
    msp.add_ellipse((Y.POND[0], Y.POND[1]), major_axis=(Y.POND[2], 0), ratio=Y.POND[3] / Y.POND[2], dxfattribs={"layer": "WATER"})
    msp.add_lwpolyline(path_poly(smooth(Y.STREAM), 0.55), close=True, dxfattribs={"layer": "WATER"})
    for x, y, _k in Y.TREES:
        msp.add_circle((x, y), 1.1, dxfattribs={"layer": "TREES"})
    d = Y.DECK
    msp.add_lwpolyline([(d[0], d[1]), (d[2], d[1]), (d[2], d[3]), (d[0], d[3])], close=True, dxfattribs={"layer": "DECK"})
    doc.saveas(os.path.join(OUT, "aviary-30x15.dxf"))
    print(pdf_path)


if __name__ == "__main__":
    main()
