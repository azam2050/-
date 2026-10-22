"""نسخة مستقلة من صفحة الجولة (للرابط العام بدون منصة): تضيف رأس HTML كامل (عربي، يمين لليسار، viewport).

python tools/site_page.py <vr/index.html> <vr/tour.html>
"""
import sys

src, dst = sys.argv[1], sys.argv[2]
body = open(src, encoding="utf-8").read()
head = ('<!doctype html>\n<html lang="ar" dir="rtl">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta property="og:title" content="مصنع وتد الأخشاب — جولة افتراضية">\n</head>\n<body>\n')
open(dst, "w", encoding="utf-8").write(head + body + "\n</body>\n</html>\n")
