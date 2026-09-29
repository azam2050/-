"""نموذج ثلاثي الأبعاد OBJ للهيكل — يُفتح في 3ds Max / Blender / SketchUp."""
import math


def _box(verts, faces, corners):
    base = len(verts)
    verts.extend(corners)
    for f in [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]:
        faces.append(tuple(base + i + 1 for i in f))


def write_obj(project, members, rules, path):
    depth = rules["members"]["stud"]["w"]
    z0 = rules["slab"]["height"]
    lines = [f"# {project.name} — framing (units: cm)"]
    verts, groups = [], []
    for w in project.walls:
        (x0, y0), (x1, y1) = w.start, w.end
        L = w.length
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        nx, ny = -uy * depth / 2, ux * depth / 2
        for i, m in enumerate(members[w.name]):
            faces = []
            c = []
            for zz in (m.y0, m.y1):
                for xx, s in ((m.x0, 1), (m.x1, 1), (m.x1, -1), (m.x0, -1)):
                    c.append((x0 + ux * xx + s * nx, y0 + uy * xx + s * ny, z0 + zz))
            # الترتيب: 4 سفلية ثم 4 علوية
            _box(verts, faces, c)
            groups.append((f"{w.name}_{m.kind}_{i}", faces))
    for v in verts:
        lines.append("v {:.2f} {:.2f} {:.2f}".format(v[0], v[2], -v[1]))  # Y-up
    for name, faces in groups:
        lines.append(f"g {name}")
        lines += ["f " + " ".join(map(str, f)) for f in faces]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
