"""مراجعة التصميم مقابل قواعد المصنع — مثل مراجعة المهندس قبل الاعتماد."""
import math

from .model import wall_thickness
from .roof import rafter_positions, roof_geometry

ERROR, WARN, INFO = "خطأ", "تنبيه", "ملاحظة"


def _on_wall(w, p, tol=1.0):
    """يرجع t إذا النقطة p على محور الجدار w."""
    ux, uy = w.u
    dx, dy = p[0] - w.start[0], p[1] - w.start[1]
    t = dx * ux + dy * uy
    d = abs(-dx * uy + dy * ux)
    if d <= tol and -tol <= t <= w.length + tol:
        return t
    return None


def junctions(project, w):
    """مواقع التقاء جدران أخرى بهذا الجدار (غير أطرافه)."""
    out = []
    for o in project.walls:
        if o is w or o.floor != w.floor:
            continue
        for p in (o.start, o.end):
            t = _on_wall(w, p)
            if t is not None and 1 < t < w.length - 1:
                out.append((t, o.name))
    return out


def _room_edges(r):
    x0, y0, x1, y1 = r.rect
    return [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]


def room_faces(project, room, rules):
    """الجدران التي تحد الغرفة: [(wall, t0, t1, side)] side = +1 يسار / -1 يمين."""
    half = wall_thickness(rules) / 2
    out = []
    for a, b in _room_edges(room):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        for w in project.walls:
            if w.floor != room.floor:
                continue
            ux, uy = w.u
            nx, ny = w.n
            dx, dy = mid[0] - w.start[0], mid[1] - w.start[1]
            s = dx * nx + dy * ny
            if abs(abs(s) - half) > 1.5:
                continue
            ta = (a[0] - w.start[0]) * ux + (a[1] - w.start[1]) * uy
            tb = (b[0] - w.start[0]) * ux + (b[1] - w.start[1]) * uy
            # الحافة لازم تكون موازية للجدار
            if abs(abs(tb - ta) - math.dist(a, b)) > 1:
                continue
            t0, t1 = max(min(ta, tb), 0), min(max(ta, tb), w.length)
            if t1 - t0 > 1:
                out.append((w, t0, t1, 1 if s > 0 else -1))
    return out


def is_front(project, w):
    """الواجهة الأمامية: عنوانها فيه «الأمامية» أو أمامها تراس/دكة."""
    if "الأمامية" in (w.title or ""):
        return True
    nx, ny = w.n
    for d in project.decks:
        cx, cy = (d.rect[0] + d.rect[2]) / 2, (d.rect[1] + d.rect[3]) / 2
        sd = (cx - w.start[0]) * nx + (cy - w.start[1]) * ny
        if sd < 0 and abs(sd) < 400 and (d.rect[3] - d.rect[1]) < (d.rect[2] - d.rect[0]) * 2:
            return True
    return False


def review(project, rules, heights, height_info, rafters):
    issues = []
    add = lambda lvl, title, detail, fix="": issues.append(  # noqa: E731
        {"level": lvl, "title": title, "detail": detail, "fix": fix})
    t = rules["members"]["stud"]["t"]
    half = wall_thickness(rules) / 2

    # 1) الارتفاع
    if height_info["changed"]:
        add(INFO, "تعديل الارتفاع", f"الارتفاع المطلوب {height_info['requested']:.0f} سم "
            f"← المعتمد {height_info['suggested']:.0f} سم.", height_info["reason"])

    # 2) الفتحات: داخل الجدار وبعيدة عن التقاء الجدران (لازم مكان لجنب الإطار 7×5)
    for w in project.walls:
        js = junctions(project, w)
        edge = half + t
        for o in w.openings:
            a, b = o.offset, o.offset + o.width
            if a - t < half or b + t > w.length - half:
                add(ERROR, f"{o.name} في {w.name}", "الفتحة ملاصقة لطرف الجدار — ما فيه مكان لإطار 7×5.",
                    "تُزاح الفتحة 10 سم على الأقل عن الزاوية.")
            hits = [(jt, jn) for jt, jn in js if a - edge < jt < b + edge]
            if hits:
                names = "، ".join(f"{jn} (عند {jt:.0f} سم)" for jt, jn in hits)
                add(ERROR, f"{o.name} في {w.name}",
                    f"الفتحة تقع على التقاء الجدار {names} — الباب يصطدم بالجدار "
                    "ولا يوجد مكان لجنب الإطار 7×5.",
                    f"تُبعد حافة الفتحة {edge:.0f} سم على الأقل عن محور الجدار الملتقي، "
                    "أو يُعاد توزيع الجدران الداخلية.")
        for i, o1 in enumerate(w.openings):
            for o2 in w.openings[i + 1:]:
                if o1.offset < o2.offset + o2.width + 2 * t and o2.offset < o1.offset + o1.width + 2 * t:
                    add(ERROR, f"{o1.name} و {o2.name}", f"فتحتين متلاصقتين في {w.name} — "
                        f"المسافة بينهما أقل من إطارين 7×5 ({2 * t:.0f} سم).")

    # 3) الغرف: تداخل (حساب مساحة مرتين) وعرض الممرات
    rooms = project.rooms
    for i, r1 in enumerate(rooms):
        for r2 in rooms[i + 1:]:
            if r1.floor != r2.floor:
                continue
            ix = min(r1.rect[2], r2.rect[2]) - max(r1.rect[0], r2.rect[0])
            iy = min(r1.rect[3], r2.rect[3]) - max(r1.rect[1], r2.rect[1])
            for c in r1.cut + r2.cut:     # الجزء المخصوم من غرفة L ليس تداخلاً
                cx = min(r1.rect[2], r2.rect[2], c[2]) - max(r1.rect[0], r2.rect[0], c[0])
                cy = min(r1.rect[3], r2.rect[3], c[3]) - max(r1.rect[1], r2.rect[1], c[1])
                if cx > 0 and cy > 0:
                    ix, iy = 0, 0
            if ix > 1 and iy > 1:
                add(ERROR, "مساحة محسوبة مرتين", f"{r1.name} و {r2.name} متداخلين بمساحة "
                    f"{ix * iy / 1e4:.2f} م².")
        if r1.kind == "corridor" and min(r1.w, r1.h) < 90:
            add(WARN, f"عرض {r1.name}", f"العرض الصافي {min(r1.w, r1.h):.0f} سم أقل من 90 سم "
                "(ضيق للحركة ولفتح باب 80 سم).", "يُوسَّع الممر إلى 90 سم على الأقل.")

    # 4) دورات المياه: السباكة خارجية → لازم تلمس جدار خارجي + تهوية
    for r in rooms:
        if not r.wet:
            continue
        faces = room_faces(project, r, rules)
        ext = [f for f in faces if f[0].exterior]
        if not ext:
            add(ERROR, f"{r.name} بدون جدار خارجي",
                "السباكة في المصنع تمشي من الخارج والصبة مفرغة تحت دورات المياه — "
                "هذا الحمام محصور داخل المبنى.",
                "يُنقل الحمام ليلمس جدار خارجي، أو يُعتمد مسار سباكة تحت الصبة بقرار من المصنع.")
        has_window = any(o.kind == "window" and any(
            f[1] - 1 <= o.offset and o.offset + o.width <= f[2] + 1 for f in ext if f[0] is w)
            for w in project.walls if w.floor == r.floor for o in w.openings)
        if not has_window:
            add(WARN, f"تهوية {r.name}", "لا يوجد شباك — يحتاج شفاط هواء.", "إضافة شفاط أو شباك صغير.")

    # 4أ) شباك دورة المياه ما ينحط في الواجهة الأمامية (قاعدة ثابتة من المصنع)
    if rules.get("design", {}).get("no_wet_window_on_front", True):
        for r in rooms:
            if not r.wet:
                continue
            for w, t0, t1, side in room_faces(project, r, rules):
                if not (w.exterior and is_front(project, w)):
                    continue
                for o in w.openings:
                    if o.kind == "window" and t0 - 1 <= o.offset and o.offset + o.width <= t1 + 1:
                        add(ERROR, f"{o.name} في الواجهة الأمامية",
                            f"شباك {r.name} على {w.title or w.name} — ممنوع حسب قاعدة المصنع.",
                            "يُنقل الشباك للواجهة الجانبية أو الخلفية.")

    # 4ب) تكديس الحمامات فوق بعض في الدورين (9)
    if project.top_floor > 0:
        up = [r for r in rooms if r.wet and r.floor > 0]
        down = [r for r in rooms if r.wet and r.floor == 0]
        for r in up:
            stacked = any(min(r.rect[2], d.rect[2]) - max(r.rect[0], d.rect[0]) > 30 and
                          min(r.rect[3], d.rect[3]) - max(r.rect[1], d.rect[1]) > 30 for d in down)
            if not stacked:
                add(INFO, f"{r.name} غير مكدّس", "دورة المياه العلوية ليست فوق دورة مياه أرضية — "
                    "تحتاج خط صرف خارجي مستقل على الجدار.", "يُفضّل تكديس الحمامات فوق بعض (قاعدة المصنع).")

    # 5) المدادات: هل يوجد جدار داخلي يحملها؟ (8)
    g = roof_geometry(project, rules)
    ax = project.roof.ridge_axis
    x0, y0, x1, y1 = g["bbox"]
    ridge_c = (x0 + x1) / 2 if ax == "y" else (y0 + y1) / 2
    lo_edge, hi_edge = ((x0, x1) if ax == "y" else (y0, y1))
    supports = []   # جدران داخلية موازية للجملون
    for w in project.walls:
        if w.exterior or w.floor != project.top_floor:
            continue
        ux, uy = w.u
        if (ax == "y" and abs(ux) < 1e-6) or (ax == "x" and abs(uy) < 1e-6):
            c = w.start[0] if ax == "y" else w.start[1]
            a, b = sorted((w.start[1], w.end[1]) if ax == "y" else (w.start[0], w.end[0]))
            supports.append((c, a, b, w.name))
    limit = rules["roof"]["max_unsupported_span"]
    worst = {}
    unsupported = 0
    inside = [p for p in rafter_positions(project, rules)
              if (y0 if ax == "y" else x0) < p < (y1 if ax == "y" else x1)]
    for p in inside:
        for side, (e, r_) in (("أ", (lo_edge, ridge_c)), ("ب", (hi_edge, ridge_c))):
            lo, hi = sorted((e, r_))
            pts = sorted([e, r_] + [c for c, a, b, _ in supports if a <= p <= b and lo < c < hi])
            span = max(bb - aa for aa, bb in zip(pts, pts[1:]))
            key = side
            worst[key] = max(worst.get(key, 0), span)
            if limit and span > limit:
                unsupported += 1
    if limit:
        if unsupported:
            add(WARN, "تقوية مدادات", f"{unsupported} مداد بحرها بدون حامل أكبر من {limit} سم.",
                "يُضاف عمود 7×5 على المداد (يصير 20×5) حسب قاعدة المصنع.")
    else:
        add(INFO, "بحر المدادات", "أطول بحر بدون جدار داخلي يحمل المداد: "
            + "، ".join(f"جهة {k}: {v:.0f} سم" for k, v in worst.items())
            + ". يحتاج رقم المصنع لأقصى بحر مسموح لتحديد المدادات اللي تُقوّى 20×5.")

    # 5ب) الدرج حسب ارتفاع الصبة (قائمة 15 سم — من فيديو الموقع)
    riser = rules["slab"].get("riser", 15)
    sh = project.slab_height
    n = max(1, round(sh / riser))
    msg = f"ارتفاع الصبة {sh:.0f} سم ← {n} درجة بقائمة {sh / n:.1f} سم."
    if sh < 30:
        add(INFO, "الصبة والدرج", msg + " بارتفاع 20 سم ما يطلع إلا درجة وحدة؛ للدكة المرتفعة 45 سم = 3 درجات.")
    else:
        add(INFO, "الصبة والدرج", msg)

    # 6) تنسيق ارتفاع رؤوس الفتحات
    tops = {o.sill + o.height for w in project.walls for o in w.openings}
    if len(tops) > 1:
        add(INFO, "مناسيب رؤوس الفتحات", "رؤوس الأبواب والشبابيك على مناسيب مختلفة: "
            + "، ".join(f"{v:.0f}" for v in sorted(tops)) + " سم.")

    if rafters["warning"]:
        add(ERROR, "طول المداد", rafters["warning"])
    return issues
