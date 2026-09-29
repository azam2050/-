"""تشغيل كامل: مشروع YAML → PDF (لوحات) + DXF + OBJ + JSON."""
import json
from pathlib import Path

from .checks import review
from .dxf_out import write_dxf
from .height import suggest_height
from .model import load_project
from .obj_out import write_obj
from .quantities import build_quantities
from .rules import load_rules
from .model3d import build_scene, railing_catalog, render_preview
from .sheets import build_client_pdf, build_pdf
from .style import resolve_style


def open_questions(rules):
    qs = []
    if rules["roof"]["max_unsupported_span"] is None:
        qs.append("أقصى بحر للمداد بدون جدار داخلي قبل إضافة تقوية 7×5 (مداد 20×5)؟")
    qs += [
        "التغطية الصافية للوح التلبيس بعد التعشيق (مستنتجة مؤقتاً 18.67 سم من 280/15)؟",
        "هل يوضع أعمدة قصيرة فوق رأس الشباك/الباب إلى العلوي؟",
        "مكان الوصلة في القاعدة والعلوي إذا الجدار أطول من الطبلية؟",
    ]
    return qs


def build(project_path, out_dir, rules_path=None):
    rules = load_rules(rules_path)
    project = load_project(project_path, rules)
    hi = suggest_height(project.wall_height, rules)
    project.wall_height = hi["suggested"]
    heights = {w.name: (w.height or hi["suggested"]) for w in project.walls}
    members, q = build_quantities(project, rules, heights)
    issues = review(project, rules, heights, hi, q["pallets"]["roof"])
    qs = open_questions(rules)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = project.name.replace(" ", "_")
    files = {
        "pdf": out / f"{stem}.pdf",
        "client_pdf": out / f"{stem}_client.pdf",
        "dxf": out / f"{stem}.dxf",
        "model3d_obj": out / f"{stem}_3d.obj",
        "model3d_glb": out / f"{stem}_3d.glb",
        "preview": out / f"{stem}_3d.png",
        "obj": out / f"{stem}_frame.obj",
        "json": out / f"{stem}_bom.json",
    }
    style = resolve_style(project.style)
    scene = build_scene(project, rules, style, heights)
    scene.write_obj(files["model3d_obj"], project.title)
    scene.write_glb(files["model3d_glb"])
    render_preview(scene, files["preview"], strip=rules["cladding"]["effective_cover"])
    railings = railing_catalog(out, style)
    ctx = {"project": project, "rules": rules, "heights": heights, "members": members, "q": q,
           "height": hi, "issues": issues, "questions": qs, "style": style,
           "preview": files["preview"], "railings": railings}
    build_pdf(ctx, files["pdf"])
    build_client_pdf(ctx, files["client_pdf"])
    write_dxf(project, members, heights, rules, files["dxf"])
    write_obj(project, members, rules, files["obj"])
    files["json"].write_text(json.dumps({"height": hi, **q, "issues": issues, "open_questions": qs},
                                        ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for pth, _ in railings:
        pth.unlink(missing_ok=True)
    return files, q, hi, issues
