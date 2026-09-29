"""(3)(4) تأطير الجدار: قاعدة سفلية، أعمدة كل 60، إطارات الفتحات، علوي واحد.

إحداثيات الواجهة: x على طول الجدار من بدايته، y من أعلى الصبة.
TO_CONFIRM: القاعدة والعلوي مفترضين مسطّحين (5 سم ارتفاع في الواجهة)
والعمود 5 سم في الواجهة و 7 سم عمق الجدار.
"""
from dataclasses import dataclass


@dataclass
class Member:
    kind: str       # bottom_plate | top_plate | stud | corner_stud | jamb | header | sill | cripple
    x0: float
    y0: float
    x1: float
    y1: float
    note: str = ""      # ملاحظة تظهر على الرسمة
    ref: str = ""       # اسم الفتحة التابع لها

    @property
    def horizontal(self):
        return (self.x1 - self.x0) > (self.y1 - self.y0)

    @property
    def length(self):
        return round(max(self.x1 - self.x0, self.y1 - self.y0), 1)


def frame_wall(wall, height, rules, is_corner_start=True):
    s = rules["members"]["stud"]
    t = s["t"]                       # 5 سم في الواجهة
    spacing = rules["wall"]["stud_spacing"]
    L, H = wall.length, height
    yb, yt = t, H - t                # أعلى القاعدة / أسفل العلوي
    m = []

    # القاعدة السفلية — تمر كاملة تحت الأبواب وتُقطع لاحقاً
    note = ""
    if any(o.kind == "door" for o in wall.openings):
        note = "تمر تحت الباب — تُقطع بعد ربط الجدران وتماسك الكوخ"
    m.append(Member("bottom_plate", 0, 0, L, t, note))
    m.append(Member("top_plate", 0, yt, L, H))   # واحد فقط

    # أعمدة الأطراف (كل جدار ينتهي بعمود → عمودين في كل زاوية)
    m.append(Member("corner_stud", 0, yb, t, yt))
    m.append(Member("corner_stud", L - t, yb, L, yt))
    if rules["wall"]["corner_studs"] == 3 and is_corner_start:
        m.append(Member("corner_stud", t, yb, 2 * t, yt, "عمود ثالث للزاوية"))

    # مناطق الفتحات (مع الإطار) — لا توضع فيها أعمدة الشبكة
    blocked = [(0, 2 * t if rules["wall"]["corner_studs"] == 3 else t), (L - t, L)]
    for o in wall.openings:
        a, b = o.offset - t, o.offset + o.width + t
        blocked.append((a, b))
        top = o.sill + o.height if o.kind == "window" else o.height
        head_y = yb + top
        m.append(Member("jamb", a, yb, o.offset, yt, ref=o.name))
        m.append(Member("jamb", o.offset + o.width, yb, b, yt, ref=o.name))
        m.append(Member("header", o.offset, head_y, o.offset + o.width, head_y + t, ref=o.name))
        if o.kind == "window":
            sill_y = yb + o.sill
            m.append(Member("sill", o.offset, sill_y - t, o.offset + o.width, sill_y, ref=o.name))
            # أعمدة قصيرة تحت الجلسة على نفس شبكة 60
            k = int(o.offset // spacing) + 1
            while k * spacing < o.offset + o.width:
                c = k * spacing
                if o.offset + t / 2 <= c <= o.offset + o.width - t / 2:
                    m.append(Member("cripple", c - t / 2, yb, c + t / 2, sill_y - t, ref=o.name))
                k += 1

    # أعمدة الشبكة كل 60
    k = 1
    while k * spacing < L:
        c = k * spacing
        a, b = c - t / 2, c + t / 2
        if not any(a < hb and b > ha for ha, hb in blocked):
            m.append(Member("stud", a, yb, b, yt))
        k += 1
    return m
