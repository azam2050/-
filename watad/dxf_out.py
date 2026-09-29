"""ملف أوتوكاد DXF: المسقط + واجهة تأطير لكل جدار، طبقات منفصلة."""
import math

import ezdxf

LAYERS = {
    "WALL": 7, "OPENING": 4, "FRAME-PLATE": 1, "FRAME-STUD": 3,
    "FRAME-OPENING": 5, "FRAME-CRIPPLE": 6, "DIM": 8, "TEXT": 2, "FURNITURE": 6,
}
KIND_LAYER = {
    "bottom_plate": "FRAME-PLATE", "top_plate": "FRAME-PLATE",
    "stud": "FRAME-STUD", "corner_stud": "FRAME-STUD",
    "jamb": "FRAME-OPENING", "header": "FRAME-OPENING", "sill": "FRAME-OPENING",
    "cripple": "FRAME-CRIPPLE",
}


def _rect(msp, x0, y0, x1, y1, layer):
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                       dxfattribs={"layer": layer})


def write_dxf(project, members, heights, rules, path):
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.CM
    for name, color in LAYERS.items():
        doc.layers.add(name, color=color)
    msp = doc.modelspace()
    thick = rules["members"]["stud"]["w"] + 2 * rules["cladding"]["thickness"]

    # المسقط
    for w in project.walls:
        (x0, y0), (x1, y1) = w.start, w.end
        L = w.length
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        nx, ny = -uy * thick / 2, ux * thick / 2
        msp.add_lwpolyline([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny),
                            (x0 - nx, y0 - ny)], close=True, dxfattribs={"layer": "WALL"})
        for o in w.openings:
            a, b = o.offset, o.offset + o.width
            _pts = [(x0 + ux * a + nx, y0 + uy * a + ny), (x0 + ux * b + nx, y0 + uy * b + ny),
                    (x0 + ux * b - nx, y0 + uy * b - ny), (x0 + ux * a - nx, y0 + uy * a - ny)]
            msp.add_lwpolyline(_pts, close=True, dxfattribs={"layer": "OPENING"})
        d = msp.add_aligned_dim(p1=(x0, y0), p2=(x1, y1), distance=-60,
                                dxfattribs={"layer": "DIM"})
        d.render()
        msp.add_text(w.name, height=15, dxfattribs={"layer": "TEXT"}).set_placement(
            ((x0 + x1) / 2 - nx * 4, (y0 + y1) / 2 - ny * 4))

    for r in project.rooms:
        cx, cy = (r.rect[0] + r.rect[2]) / 2, (r.rect[1] + r.rect[3]) / 2
        msp.add_text(f"{r.name}  {r.area_m2:.2f} m2", height=12,
                     dxfattribs={"layer": "TEXT"}).set_placement(
            (cx, cy), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    for f in project.furniture:
        _rect(msp, *f.rect, "FURNITURE")

    # الواجهات تحت المسقط
    ys = [p[1] for w in project.walls for p in (w.start, w.end)]
    oy = min(ys) - 500
    ox = 0
    for w in project.walls:
        H = heights[w.name]
        for m in members[w.name]:
            _rect(msp, ox + m.x0, oy - H + m.y0, ox + m.x1, oy - H + m.y1, KIND_LAYER[m.kind])
        for o in w.openings:
            yb = rules["members"]["stud"]["t"]
            b = yb + (o.sill if o.kind == "window" else 0)
            _rect(msp, ox + o.offset, oy - H + b, ox + o.offset + o.width,
                  oy - H + b + o.height, "OPENING")
        msp.add_text(f"{w.name}  L={w.length:.0f}  H={H:.0f}", height=15,
                     dxfattribs={"layer": "TEXT"}).set_placement((ox, oy + 30))
        msp.add_linear_dim(base=(ox, oy - H - 50), p1=(ox, oy - H), p2=(ox + w.length, oy - H),
                           dxfattribs={"layer": "DIM"}).render()
        ox += math.ceil(w.length) + 200
    doc.saveas(path)
