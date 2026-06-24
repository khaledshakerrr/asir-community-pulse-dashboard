# asir-community-pulse-dashboard

لوحة عربية RTL مبنية بـ `Dash` لصالح **منصة نبض المجتمع**، مع دعم:

- `Google Sheets` كمصدر الإنتاج الأساسي
- ملف `Seed` محلي رسمي/مشتق للتشغيل السريع قبل رفع البيانات إلى Google Sheets

## What Is Included

- تطبيق Dash متعدد الصفحات مع `server = app.server`
- واجهة عربية RTL تنفيذية
- تخزين مؤقت 5 دقائق لبيانات Google Sheets
- دعم `GOOGLE_SERVICE_ACCOUNT_JSON` للنشر و `GOOGLE_SERVICE_ACCOUNT_JSON_FILE` للتشغيل المحلي
- ملف `official_google_sheets_seed.xlsx` مبني من مصادر سعودية رسمية ومهيأ لرفعه إلى Google Sheets
- ملفات تفصيلية إضافية لعسير والقصيم داخل `data/official_curated/`

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
  generate_synthetic_demo_data.py
src/
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

### 2. بناء ملف البيانات الرسمي المحلي

هذا الأمر يولد:

- `data/official_google_sheets_seed.xlsx`
- ملفات CSV موافقة لتبويبات Google Sheets داخل `data/official_google_sheet_tabs/`
- ملفات تحليلية إضافية داخل `data/official_curated/`

```powershell
.venv\Scripts\python.exe scripts\build_official_seed_data.py
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
- الجداول التالية **تمثيلية/مشتقة** ولكنها **معايرة على الأساس الرسمي الإقليمي** حتى يعمل التطبيق الحالي ويعرض خرائط وبطاقات ورسومًا على مستوى السجل:
  - `survey_responses_simulated`
  - `complaints_feedback`
  - `initiatives_programs`
  - أجزاء من `monthly_kpi_summary`
  - `forecasting_data`

بمعنى آخر:

- البنية الصحية والسكان والوصول والرضا والاتجاهات الأساسية مبنية على مصادر رسمية
- بيانات السجل الفردي والتوزيعات الدقيقة والتنبؤ داخل واجهة العرض الحالية هي طبقة مشتقة لخدمة المنتج والعرض

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

- استخدم `GOOGLE_SHEET_ID`
- استخدم `GOOGLE_SERVICE_ACCOUNT_JSON`
- عطل المصدر المحلي عبر `PREFER_LOCAL_DEMO_DATA=0`
- أمر التشغيل:

```text
web: gunicorn app:server
```

## Notes

- التطبيق لا يقرأ Google Sheets عند كل تغيير فلتر؛ يتم استخدام الكاش لمدة 5 دقائق
- لا ترفع `.env` أو ملفات الاعتماد JSON إلى Git
- إذا لم تكن إعدادات Google Sheets موجودة، سيعرض التطبيق رسالة واضحة بدل الانهيار
- إذا أردت إعادة توليد الملف الرسمي بعد تحديث المصادر، شغل:

```powershell
.venv\Scripts\python.exe scripts\build_official_seed_data.py
```
