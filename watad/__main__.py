import argparse

from .build import build


def main():
    ap = argparse.ArgumentParser(prog="watad", description="مصمم أكواخ مصنع وتد")
    ap.add_argument("project", help="ملف المشروع YAML")
    ap.add_argument("-o", "--out", default="out")
    ap.add_argument("--rules", default=None)
    a = ap.parse_args()
    files, q, hi = build(a.project, a.out, a.rules)
    p = q["pallets"]
    print(f"height: {hi['requested']} -> {hi['suggested']} ({hi['rows']} rows)")
    print(f"rafters: {p['roof']['rafter_count']} x {p['roof']['rafter_length']}cm")
    print(f"pallets: m1={p['method1_pallets']['count']} m2={p['method2_pallets']['count']} "
          f"total={p['total_pallets']}")
    print(f"cladding boards: {q['cladding']['boards']}, cement board: "
          f"{q['cladding']['cement_board_sheets']}")
    for k, v in files.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
