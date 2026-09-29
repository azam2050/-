"""تشغيل كامل: مشروع YAML → DXF + PDF + OBJ + JSON."""
import json
from pathlib import Path

from .dxf_out import write_dxf
from .height import suggest_height
from .model import load_project
from .obj_out import write_obj
from .pdf_out import write_pdf
from .quantities import build_quantities
from .rules import load_rules


def open_questions(rules):
    qs = []
    if rules["roof"]["max_unsupported_span"] is None:
        qs.append("أقصى بحر للمداد بدون جدار داخلي قبل إضافة تقوية 7×5 (مداد 20×5)؟")
    qs += [
        "التغطية الصافية للوح التلبيس بعد التعشيق (مستنتجة مؤقتاً 18.67 سم من 280/15)؟",
        "هل يوضع أعمدة قصيرة فوق رأس الشباك/الباب إلى العلوي؟",
        "مكان الوصلة في القاعدة والعلوي إذا الجدار أطول من الطبلية؟",
        "بروز المداد خارج الجدار (الطرف)؟",
    ]
    return qs


def build(project_path, out_dir, rules_path=None):
    rules = load_rules(rules_path)
    project = load_project(project_path, rules)
    hi = suggest_height(project.wall_height, rules)
    heights = {w.name: (w.height or hi["suggested"]) for w in project.walls}
    members, q = build_quantities(project, rules, heights)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = project.name.replace(" ", "_")
    files = {
        "dxf": out / f"{stem}.dxf",
        "pdf": out / f"{stem}.pdf",
        "obj": out / f"{stem}_frame.obj",
        "json": out / f"{stem}_bom.json",
    }
    write_dxf(project, members, heights, rules, files["dxf"])
    write_obj(project, members, rules, files["obj"])
    qs = open_questions(rules)
    write_pdf(project, rules, members, heights, q, hi, qs, files["pdf"])
    files["json"].write_text(json.dumps({"height": hi, **q, "open_questions": qs},
                                        ensure_ascii=False, indent=2), encoding="utf-8")
    return files, q, hi
