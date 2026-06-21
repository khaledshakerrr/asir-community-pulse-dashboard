# asir-community-pulse-dashboard

لوحة معلومات عربية RTL مبنية بـ Dash لصالح **منصة نبض المجتمع - Asir Community Pulse Platform**، مع تصميم تنفيذي مستلهم من ملف العرض المرفق وربط مباشر مع Google Sheets.

## الميزات

- تطبيق Dash متعدد الصفحات مع `server = app.server` للنشر.
- واجهة عربية `RTL` بخلفية كحلية داكنة وبطاقات بيضاء ولمسات تركوازية.
- شريط جانبي للتنقل والمرشحات العامة.
- قراءة البيانات من Google Sheets عبر `gspread` و `google-auth`.
- تخزين مؤقت للبيانات لمدة 5 دقائق باستخدام `Flask-Caching` لتقليل الطلبات المتكررة.
- تحذيرات جودة البيانات عند غياب الأوراق أو الأعمدة المطلوبة.
- رسائل خطأ واضحة عند فشل الاتصال بـ Google Sheets.
- صفحات للمؤشرات التنفيذية، الخريطة، المؤشرات الصحية، الشكاوى، المبادرات، والتنبؤات.

## هيكل المشروع

```text
app.py
requirements.txt
Procfile
README.md
.gitignore
assets/
  style.css
  asir-logo.png
src/
  config.py
  google_sheets.py
  data_cleaning.py
  kpis.py
  charts.py
  maps.py
  forecasting.py
  validators.py
pages/
  overview.py
  map_dashboard.py
  health_indicators.py
  complaints.py
  initiatives.py
  forecasting_page.py
```

## متغيرات البيئة

أنشئ ملف `.env` محلياً وأضف القيم التالية:

```env
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON_FILE=C:\path\to\service-account.json
APP_PASSWORD=optional_password
```

ملاحظات:

- في بيئة Windows المحلية استخدم `GOOGLE_SERVICE_ACCOUNT_JSON_FILE` وأشر إلى ملف حساب الخدمة المحلي.
- في Render أو أي نشر سحابي استخدم `GOOGLE_SERVICE_ACCOUNT_JSON` وضع فيه **محتوى** JSON كاملاً كسلسلة نصية.
- إذا قمت بضبط `APP_PASSWORD` فسيتم تفعيل حماية Basic Auth بسيطة للتطبيق.
- لا تقم برفع ملفات اعتماد JSON للمستودع. تمت إضافة `*.json` و `.env` إلى `.gitignore`.

## أوراق Google Sheets المتوقعة

- `clean_regions_master`
- `regions_master`
- `survey_responses_simulated`
- `health_facilities`
- `monthly_kpi_summary`
- `complaints_feedback`
- `initiatives_programs`
- `forecasting_data`
- `targets_benchmarks`
- `lookup_definitions`
- `data_dictionary`

إذا لم تكن `clean_regions_master` متاحة، فسيستخدم التطبيق `regions_master` كبديل مع إظهار تحذير جودة بيانات.

## التشغيل المحلي على Windows

1. أنشئ ملف `.env` داخل مجلد المشروع.

2. أضف القيم الأساسية:

   ```env
   GOOGLE_SHEET_ID=your_google_sheet_id
   GOOGLE_SERVICE_ACCOUNT_JSON_FILE=C:\path\to\service-account.json
   APP_PASSWORD=optional_password
   ```

3. أنشئ البيئة الافتراضية وثبت الحزم:

   ```bash
   pip install -r requirements.txt
   ```

4. شغّل التطبيق باستخدام بايثون البيئة الافتراضية:

   ```bash
   .venv\Scripts\python.exe app.py
   ```

5. افتح المتصفح على:

   ```text
   http://127.0.0.1:8050
   ```

إذا ظهر تحذير داخل الواجهة بخصوص `GOOGLE_SHEET_ID` أو ملف الاعتماد، راجع قيم ملف `.env` ثم أعد تشغيل التطبيق.

## النشر على Render

1. أضف نفس متغيرات البيئة في إعدادات الخدمة على Render.
   استخدم `GOOGLE_SHEET_ID` و `GOOGLE_SERVICE_ACCOUNT_JSON`.
2. استخدم أمر البناء المعتاد لتثبيت `requirements.txt`.
3. يستخدم Render الملف:

   ```text
   Procfile
   ```

4. أمر التشغيل:

   ```text
   web: gunicorn app:server
   ```

## ملاحظات هندسية

- لا يتم جلب Google Sheets عند كل ضغطة على المرشحات؛ تتم إعادة استخدام النسخة المخزنة مؤقتاً لمدة 5 دقائق.
- جميع المؤشرات الأساسية مشتقة من البيانات الحالية، وليست أرقاماً ثابتة داخل الكود.
- تمت كتابة الوحدات بشكل مستقل لتسهيل التوسع لاحقاً بإضافة صفحات أو مؤشرات جديدة.
