# عقد تنفيذ وإنشاء كوخ خشبي (مرجع المصنع)

القالب المعتمد: `contracts/contract_template.html`، وهو نفس نص ونسق عقد مؤسسة وتد الأخشاب للصناعة
(الترويسة والتذييل والعلامة المائية في `contracts/assets/`، وخطوط Noto Sans Arabic و Arimo في `library/fonts/`).

## لما يطلب المصنع عقد
المصنع يرسل البيانات المعلّم عليها بالأحمر فقط:

| الحقل | المعنى |
|---|---|
| `date` | تاريخ العقد (اليوم يُكتب تلقائيًا) |
| `client_name` / `client_id` / `client_phone` / `client_address` | بيانات الطرف الأول (العميل) |
| `project_type` / `site` / `area` | نوع المشروع، موقع التنفيذ، المساحة التقريبية |
| `total` | القيمة الإجمالية. المبلغ كتابة يُحسب تلقائيًا |
| `payments` | نسب الدفعات الأربع (مجموعها 100%)، والمبالغ تُحسب تلقائيًا |
| `duration` / `warranty` | مدة التنفيذ (يوم، الافتراضي 35)، والضمان (سنوات، الافتراضي 10) |

الخطوات:
1. انسخ `contracts/contract_example.yaml` إلى `contracts/data/<التاريخ>_<المشروع>.yaml` وعبّي الحقول.
   مجلد `data/` ما يُرفع للمستودع، عشان بيانات العملاء الشخصية.
2. `python tools/contract.py contracts/data/<الملف>.yaml -o deliveries/<المجلد>/عقد.pdf`

## النسخة الفاضية القابلة للتعبئة
`python tools/contract.py --blank -o "contracts/عقد_تنفيذ_كوخ_خشبي_فاضي.pdf"`
تطلع PDF بحقول نص (AcroForm) مكان الحقول الحمراء، تتعبى من Adobe Acrobat Reader أو تطبيق الملفات في الآيفون.

## عقد زيارة وتصميم (صفحة واحدة)
- القالب: `contracts/visit_design_template.html` — في ملف البيانات: `template: visit_design`.
- المحتوى: زيارة الموقع ورفع المساحات + مخطط أوتوكاد + تصميم 3D، المساحة تُحدد بعد الرفع واعتماد التصميم،
  والمبلغ يُدفع عند التوقيع ويُخصم من الدفعة الأولى لعقد التنفيذ إذا اعتمد العميل التصميم وتعاقد على التنفيذ.
- نسخة فاضية قابلة للتعبئة: `contracts/عقد_زيارة_وتصميم_فاضي.pdf`
  (`python tools/contract.py --blank --template visit_design -o ...`).

## عرض سعر تسليم مفتاح (tools/quote.py)
- البيانات: `contracts/quotes/*.yaml` — أقسام وبنود بتكلفة المصنع (`base`) وهامش القسم `markup` (افتراضي 15%، الكوخ 0%).
- العميل يشوف سعر الوحدة بعد الهامش والإجمالي والدفعات والشروط وصفحة المواد بالصور (`contracts/assets/products/`).
- `python tools/quote.py contracts/quotes/X.yaml -o عرض.pdf`
- `python tools/quote.py contracts/quotes/X.yaml --internal` ← ملخص التكلفة والربح للمصنع فقط (ما يطلع بالـPDF).
- بدون اسم أو جوال العميل في الملف — يُكتب باليد على النسخة المطبوعة.
