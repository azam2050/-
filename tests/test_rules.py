from watad.framing import frame_wall
from watad.height import suggest_height
from watad.model import Opening, Project, Roof, Wall
from watad.quantities import build_quantities
from watad.rules import load_rules

R = load_rules()


def test_default_height_needs_no_change():
    assert suggest_height(280, R)["suggested"] == 280


def test_height_rounds_up_to_full_board():
    h = suggest_height(300, R)
    assert h["suggested"] >= 300 and h["changed"]


def test_studs_every_60_and_single_top_plate():
    w = Wall("A", (0, 0), (600, 0))
    m = frame_wall(w, 280, R)
    studs = sorted((x.x0 + x.x1) / 2 for x in m if x.kind == "stud")
    assert studs == [60, 120, 180, 240, 300, 360, 420, 480, 540]
    assert sum(x.kind == "top_plate" for x in m) == 1
    assert sum(x.kind == "corner_stud" for x in m) == 2


def test_door_keeps_bottom_plate_continuous():
    w = Wall("A", (0, 0), (600, 0), openings=[Opening("door", 200, 100, 210)])
    m = frame_wall(w, 280, R)
    bp = [x for x in m if x.kind == "bottom_plate"]
    assert len(bp) == 1 and bp[0].length == 600 and bp[0].note


def test_window_has_cripples_under_sill():
    w = Wall("A", (0, 0), (600, 0), openings=[Opening("window", 100, 150, 120, sill=90)])
    m = frame_wall(w, 280, R)
    cr = [x for x in m if x.kind == "cripple"]
    assert [round((c.x0 + c.x1) / 2) for c in cr] == [120, 180, 240]
    assert not any(x.kind == "stud" and 95 < x.x0 < 255 for x in m)


def test_pallet_plan_one_method1_pallet_per_rafter():
    walls = [Wall("S", (0, 0), (600, 0)), Wall("E", (600, 0), (600, 400)),
             Wall("N", (600, 400), (0, 400)), Wall("W", (0, 400), (0, 0))]
    p = Project("t", "", walls, 280, Roof("x", 25))
    _, q = build_quantities(p, R, {w.name: 280 for w in walls})
    pp = q["pallets"]
    assert pp["method1_pallets"]["count"] == pp["roof"]["rafter_count"] == 22
    assert pp["total_pallets"] == pp["method1_pallets"]["count"] + pp["method2_pallets"]["count"] \
        + pp["method2_long_pallets"]["count"]


def test_reference_project_review_flags_known_errors(tmp_path):
    from watad.build import build
    files, q, hi, issues = build("projects/2026-09-28_farm-cabin-6.5x10.yaml", tmp_path)
    titles = " ".join(i["title"] for i in issues)
    assert "حمام ضيوف بدون جدار خارجي" in titles
    assert "عرض ممر" in titles
    assert "ب2 غرفة النوم" in titles
    assert q["pallets"]["roof"]["stock_length"] == 480
    assert all(f.exists() for f in files.values())
