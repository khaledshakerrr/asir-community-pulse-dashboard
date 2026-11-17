# asir-community-pulse-dashboard

لوحة عربية RTL مبنية بـ `Dash` لصالح **منصة نبض المجتمع**، مع دعم:

- `Google Sheets` كمصدر الإنتاج الأساسي
- ملف `Seed` محلي رسمي/مشتق للتشغيل السريع قبل رفع البيانات إلى Google Sheets

For the client update, follow the [Windows, GitHub, and Render guide](docs/RUN_AND_DEPLOY.md). It includes the safe fresh-clone workflow for applying `outputs/asir-client-update.zip` to the existing repository.

## What Is Included

- تطبيق Dash متعدد الصفحات مع `server = app.server`
- واجهة عربية RTL تنفيذية
- صفحة داخلية للمصادر والمنهجية تشرح الرسمي المباشر مقابل المؤشرات المشتقة
- صفحة عربية كاملة للأمراض المعدية مبنية على جداول الكتاب الإحصائي السنوي لوزارة الصحة
- تخزين مؤقت 5 دقائق لبيانات Google Sheets
- دعم `GOOGLE_SERVICE_ACCOUNT_JSON` للنشر و `GOOGLE_SERVICE_ACCOUNT_JSON_FILE` للتشغيل المحلي
- ملف `official_google_sheets_seed.xlsx` مبني من مصادر سعودية رسمية ومهيأ لرفعه إلى Google Sheets
- ملفات تفصيلية إضافية لعسير والقصيم داخل `data/official_curated/`
- قسم رعاية الأمراض المزمنة داخل صفحة المقارنة الإقليمية: زيارات عيادات السكري لعامي 2023 و2024، وطاقة المرافق المتخصصة للأعوام 2022–2024
- مؤشرات وطنية إضافية: زيارات التأهيل بعد البتر المرتبط بالسكري 2023 و2024، ومرضى الغسيل الكلوي حسب نوع التنقية والقطاع الصحي لعام 2024
- شعار نبض المجتمع الجديد بحجم واضح، وتصحيح مسمى تجمع عسير، وإزالة بطاقة معدل الحالات لكل 100 ألف من مؤشرات الأمراض المعدية
- جميع النصوص الظاهرة داخل التطبيق بالعربية فقط

The chronic-care CSVs are included in `data/official_curated/chronic_care/` and work with either local data or the existing Google Sheets connection; no new Google Sheets tabs are required. Visits are clinic encounters, not unique patients or disease prevalence. The source uses health regions in 2022/2023 and health clusters in 2024, so the annual figures are presented as published snapshots rather than a continuous comparable trend.

At the bottom of **المقارنة الإقليمية**, the **التأهيل المرتبط بالسكري والغسيل الكلوي** section shows national data independently of regional filters. Diabetes-related post-amputation rehabilitation counts are **visits**, not operations or unique patients. Dialysis data count **patients** across all sectors in 2024; national treatment totals are kept separate from sector details. The dialysis tables inside the 2023 book are labeled 2021 and are excluded from this view.

## Project Structure

```text
app.py
requirements.txt
Procfile
README.md
.gitignore
assets/
data/
  official_google_sheets_seed.xlsx
  official_google_sheet_tabs/
  official_curated/
  official_sources/
pages/
scripts/
  build_official_seed_data.py
  extract_arabic_disease_intelligence.py
  generate_synthetic_demo_data.py
src/
  disease_intelligence.py
  official_data_pipeline.py
```

## Environment Variables

أنشئ ملف `.env` داخل مجلد المشروع.

### 1. تشغيل محلي باستخدام ملف Seed الرسمي

```env
PREFER_LOCAL_DEMO_DATA=1
LOCAL_DATA_WORKBOOK=data/official_google_sheets_seed.xlsx
```

### 2. تشغيل محلي مع Google Sheets

```env
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON_FILE=C:\path\to\service-account.json
PREFER_LOCAL_DEMO_DATA=0
APP_PASSWORD=optional_password
```

### 3. النشر على Render

```env
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account", ...}
PREFER_LOCAL_DEMO_DATA=0
APP_PASSWORD=optional_password
```

## Windows Local Setup

### 1. تثبيت الحزم

```powershell
pip install -r requirements.txt
```

### 2. إعادة بناء ملف البيانات الرسمي المحلي (اختياري)

ملف البيانات المحلي المجهز موجود بالفعل؛ لا تحتاج إلى إعادة بنائه لتشغيل تحديث العميل. عند تحديث المصادر الأصلية فقط، هذا الأمر يولد:

- `data/official_google_sheets_seed.xlsx`
- ملفات CSV موافقة لتبويبات Google Sheets داخل `data/official_google_sheet_tabs/`
- ملفات تحليلية إضافية داخل `data/official_curated/`

```powershell
.venv\Scripts\python.exe scripts\build_official_seed_data.py
```

### 3. استخراج طبقة الأمراض المعدية من الكتاب الإحصائي (اختياري)

يشغل هذا الأمر الاستخراج الآلي لجداول الأمراض المعدية من ملف وزارة الصحة الرسمي:

```powershell
.venv\Scripts\python.exe scripts\extract_arabic_disease_intelligence.py
```

سينتج ملفات CSV داخل:

```text
data/official_curated/diseases/
```

وأهم الملفات الناتجة:

- `disease_catalog_ar.csv`
- `communicable_diseases_by_region_ar.csv`
- `communicable_diseases_by_month_ar.csv`
- `communicable_diseases_by_age_ar.csv`
- `communicable_diseases_by_gender_nationality_ar.csv`
- `communicable_diseases_5_year_trend_ar.csv`
- `tuberculosis_ar.csv`
- `malaria_ar.csv`
- `bilharzia_ar.csv`
- `leishmaniasis_ar.csv`
- `foodborne_outbreaks_ar.csv`
- `intoxication_ar.csv`
- `environmental_health_diseases_ar.csv`
- `skipped_tables_report.csv` عند تعذر قراءة جدول مركب مع استمرار التنفيذ

## Live Environmental Data

The environmental, respiratory risk, and early warning pages support live refreshable data with caching.

Recommended `.env` settings:

```env
LIVE_DATA_PROVIDER=open_meteo
LIVE_DATA_CACHE_SECONDS=900
OPENWEATHER_API_KEY=
NCM_API_USERNAME=
NCM_API_PASSWORD=
```

Notes:

- `open_meteo` is the default live provider in the current version and works without a paid token.
- `NCM` credentials are prepared at the configuration layer for future direct integration.
- Clicking the in-app refresh button clears both Google Sheets cache and live environmental cache.

## Documentation PDF

Generate the Arabic PDF documentation for the client with:

```powershell
.venv\Scripts\python.exe scripts\generate_documentation_pdf.py
```

Output file:

```text
docs/asir_community_pulse_documentation_ar.pdf
```

### 3. إنشاء `.env`

للتشغيل السريع محليًا:

```env
PREFER_LOCAL_DEMO_DATA=1
LOCAL_DATA_WORKBOOK=data/official_google_sheets_seed.xlsx
```

أو للتشغيل من Google Sheets:

```env
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON_FILE=C:\path\to\service-account.json
PREFER_LOCAL_DEMO_DATA=0
```

### 4. تشغيل التطبيق

```powershell
.venv\Scripts\python.exe app.py
```

### 5. فتح المتصفح

```text
http://127.0.0.1:8050
```

## Official Data Outputs Added

بعد تشغيل `scripts/build_official_seed_data.py` ستجد:

- `data/official_curated/official_region_summary_2024.csv`
  - ملخص إقليمي للسعودية مع سكان 2024، المرافق الصحية، الوصول للخدمة، الرضا، الاتجاهات الصحية، ومؤشرات مركبة
- `data/official_curated/qassim_governorate_population_detail.csv`
  - تفصيل محافظات القصيم حسب السكان والجنس والجنسية
- `data/official_curated/asir_cluster_detail_2024.csv`
  - تفصيل داخلي لعسير بين تجمع عسير وتجمع بيشة
- `data/official_curated/asir_qassim_workforce_2024.csv`
  - قوى عاملة صحية مختصرة لعسير والقصيم
- `data/official_curated/diseases/*.csv`
  - طبقة أمراض معدية عربية مستخرجة من الكتاب الإحصائي السنوي لوزارة الصحة 2024

## Direct Official Sources Used

- Ministry of Health Statistical Yearbook 2024
  - [MOH official file](https://www.moh.gov.sa/en/Ministry/Statistics/book/Documents/Statistical-Yearbook-2024.xlsx)
- GASTAT Healthcare Establishments and Workforce Statistics 2024
  - [GASTAT official file](https://www.stats.gov.sa/documents/d/guest/healthcare-establishments-and-workforce-statistics-2024-en)
- GASTAT Healthcare Statistics Publication 2024
  - [GASTAT official file](https://www.stats.gov.sa/documents/d/guest/healthcare-statistics-publication-2024-en-xlsx)
- GASTAT Qassim detailed regional results
  - [GASTAT official file](https://www.stats.gov.sa/documents/20117/2435265/lqsym_4.pdf/93a6ebd5-514b-c787-17e4-239d36b8cce3?t=1735192378913)

## Important Data Honesty Notes

- ليست كل الحقول داخل ملف الـ Seed أرقامًا رسمية مباشرة.
- الجداول التالية تعتمد مباشرة على مصادر حكومية منشورة أو اشتقاق حسابي مباشر منها:
  - `regions_master`
  - `clean_regions_master`
  - أجزاء كبيرة من `health_facilities`
  - الملفات داخل `data/official_curated/`
  - ملفات `data/official_curated/diseases/` المستخرجة من جداول وزارة الصحة الرسمية
- الجداول التالية **تمثيلية/مشتقة** ولكنها **معايرة على الأساس الرسمي الإقليمي** حتى يعمل التطبيق الحالي ويعرض خرائط وبطاقات ورسومًا على مستوى السجل:
  - `survey_responses_simulated`
  - `complaints_feedback`
  - `initiatives_programs`
  - أجزاء من `monthly_kpi_summary`
  - `forecasting_data`

بمعنى آخر:

- البنية الصحية والسكان والوصول والرضا والاتجاهات الأساسية مبنية على مصادر رسمية
- بيانات السجل الفردي والتوزيعات الدقيقة والتنبؤ داخل واجهة العرض الحالية هي طبقة مشتقة لخدمة المنتج والعرض

## ملاحظات مهمة حول واجهة الأمراض المعدية والتنبؤ

- جميع النصوص الظاهرة للمستخدم داخل التطبيق باللغة العربية فقط
- ليست كل الأمراض متاحة حسب المنطقة والشهر والعمر والجنس والجنسية في الوقت نفسه؛ يختلف ذلك حسب الجدول الرسمي الأصلي
- التوقعات المرضية الحالية تشغيلية واستباقية، وتعتمد على السلاسل الزمنية الرسمية المتاحة، ولا تمثل تشخيصًا سريريًا مباشرًا
- التحليل البيئي المرتبط بالمرض داخل الصفحة هو تحليل سياقي داعم للقرار، وليس إثباتًا سببيًا مباشرًا بين الطقس والمرض

## Google Sheets Tabs Expected

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

## Deploying to Render

Use the existing Render web service and preserve its working environment variables, including Google Sheets credentials. For production using Google Sheets, retain `PREFER_LOCAL_DEMO_DATA=0`.

Build Command:

```text
pip install -r requirements.txt
```

Start Command:

```text
gunicorn app:server --bind 0.0.0.0:$PORT
```

The `web:` prefix belongs only in `Procfile`; do not enter it in Render's Start Command field. Follow the [deployment guide](docs/RUN_AND_DEPLOY.md#3-update-the-existing-render-service) for repository, branch, Root Directory, and verification steps. These commands follow Render's [Python deployment](https://render.com/docs/deploy-flask) and [port binding](https://render.com/docs/web-services#port-binding) guidance.

## Notes

- التطبيق لا يقرأ Google Sheets عند كل تغيير فلتر؛ يتم استخدام الكاش لمدة 5 دقائق
- لا ترفع `.env` أو ملفات الاعتماد JSON إلى Git
- إذا لم تكن إعدادات Google Sheets موجودة، سيعرض التطبيق رسالة واضحة بدل الانهيار
- إذا أردت إعادة توليد الملف الرسمي بعد تحديث المصادر، شغل:

```powershell
.venv\Scripts\python.exe scripts\build_official_seed_data.py
```
