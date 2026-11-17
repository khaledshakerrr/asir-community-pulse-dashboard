# Run, submit to GitHub, and update Render

This update replaces and enlarges the logo, removes the requested infectious-disease rate card, corrects the wording to **تجمع عسير**, and adds chronic-care information to the existing **المقارنة الإقليمية** page. Existing sections and operational data remain in place.

The chronic-care addition includes diabetes-clinic visits for 2023/2024 and specialized Ministry of Health facility capacity for 2022–2024. Visits count encounters, not unique patients or prevalence. Health-region boundaries in 2022/2023 and health-cluster boundaries in 2024 differ; these are published annual snapshots. The included CSV files run locally and on Render without new Google Sheets tabs.

At the bottom of **المقارنة الإقليمية**, below the existing chronic-care facilities chart, the **التأهيل المرتبط بالسكري والغسيل الكلوي** section adds:

- National diabetes-related post-amputation rehabilitation visits: 651 in 2023 (Table 4-37), 1,215 in 2024 (Table 4-45). These are visits at MoH rehabilitation centers/departments, not amputations, unique patients, or a complication rate.
- National dialysis patients in 2024 by treatment and sector: 17,734 hemodialysis and 1,208 peritoneal dialysis patients, totaling 18,942. Sector details use Table 4-42; the combined total is checked against Table 4-43. National totals are never added to their sector details.

These national charts have a fixed published scope, independent of the regional, date, and gender controls. The 2023 workbook's dialysis tables describe 2021 and are intentionally excluded. No additional downloads or Google Sheets changes are needed.

## 1. Run on Windows

Install Python **3.11** and Git if needed. Open PowerShell in the application folder containing `app.py` and `requirements.txt`.

If your plain `python app.py` shows `TypeError: Cannot convert numpy.ndarray to numpy.ndarray`, it is using a broken Anaconda pandas installation. For this existing workspace, the verified environment two folders above this application already loads the local workbook correctly. Stop the failing server with `Ctrl+C` and run:

```powershell
& '..\..\.venv\Scripts\python.exe' app.py
```

Use this exact Python path for subsequent commands in this workspace. For a fresh clone with a clean Python 3.11 installation, create its own environment with the commands below.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create a file named `.env` beside `app.py`, or edit these two keys in an existing file:

```env
PREFER_LOCAL_DEMO_DATA=1
LOCAL_DATA_WORKBOOK=data/official_google_sheets_seed.xlsx
```

Keep any other existing settings. This uses the prepared local workbook; rebuilding it is unnecessary. Start the app:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open [http://127.0.0.1:8050](http://127.0.0.1:8050). Leave PowerShell open while using the app; press `Ctrl+C` to stop it. Using the full Python path avoids PowerShell activation-policy changes.

Check the larger logo, the infectious-disease cards, the corrected wording, and the chronic-care information in **المقارنة الإقليمية**. Confirm existing pages and filters still work. The chronic-care section has its own published-year scope; the operational date and gender filters do not redefine those source snapshots.

Run the source-data and chart checks with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 2. Apply the update to a fresh GitHub clone

The supplied folder is nested inside a different local Git root. Use a fresh clone outside `Medical_LookerStudio_Dashboard` so unrelated local files are not submitted. The update ZIP contains only the intended changed/new files; it is not a complete standalone application.

Choose a new folder name if `asir-client-update` already exists:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\Projects"
Set-Location "$env:USERPROFILE\Projects"
git clone https://github.com/khaledshakerrr/asir-community-pulse-dashboard.git asir-client-update
Set-Location .\asir-client-update
git rev-parse --show-toplevel
git switch -c codex/client-chronic-care
```

The printed Git root must be this fresh `asir-client-update` folder. The command below uses the update ZIP created beside your current application. Extract **into this repository root**, so `app.py` is overwritten directly rather than placed in another nested folder:

```powershell
Expand-Archive -LiteralPath 'C:\Users\10\Downloads\Medical_LookerStudio_Dashboard\ASIR N\asir-community-pulse-dashboard-main\outputs\asir-client-update.zip' -DestinationPath . -Force
git status --short
git diff --stat
git diff --check
git diff
```

Review new files in your editor as well; `git diff` does not show their contents until staged. Run the local setup and checks from section 1 in this fresh clone before submitting it. Keep `.env`, credentials, the ZIP, and original source workbooks out of this commit.

Stage the explicit update files:

```powershell
$updateFiles = @(
    '.gitignore'
    'app.py'
    'assets/style.css'
    'assets/logo_final.jpeg'
    'src/disease_intelligence.py'
    'src/official_charts.py'
    'pages/health_indicators.py'
    'src/chronic_care.py'
    'src/chronic_charts.py'
    'scripts/build_chronic_care_data.py'
    'data/official_curated/chronic_care/diabetes_visits.csv'
    'data/official_curated/chronic_care/chronic_care_capacity.csv'
    'data/official_curated/chronic_care/diabetes_rehabilitation_visits.csv'
    'data/official_curated/chronic_care/dialysis_patients_2024.csv'
    'src/source_registry.py'
    'src/official_data_pipeline.py'
    'README.md'
    'docs/RUN_AND_DEPLOY.md'
    'tests/test_chronic_care.py'
)
git add -- $updateFiles
git diff --cached --stat
git diff --cached --check
git status --short
git commit -m "Update dashboard branding and add official chronic-care snapshots"
git push -u origin codex/client-chronic-care
```

On [the GitHub repository](https://github.com/khaledshakerrr/asir-community-pulse-dashboard), open a pull request from `codex/client-chronic-care` into `main`, review the files, and merge it. If Render deploys a different branch, use that branch as the pull request target instead.

## 3. Update the existing Render service

Open your existing service in the [Render Dashboard](https://dashboard.render.com). In **Settings**, check:

| Setting | Value/check |
| --- | --- |
| Repository | `khaledshakerrr/asir-community-pulse-dashboard` |
| Branch | The branch you merged into, normally `main` |
| Root Directory | Blank when `app.py` and `requirements.txt` are at repository root |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:server --bind 0.0.0.0:$PORT` |

Root Directory is relative to the GitHub repository, not your Windows folder path. Render runs build/start commands from that directory. See [Render's Root Directory documentation](https://render.com/docs/monorepo-support#setting-a-root-directory).

Preserve existing environment variables and secrets, including `GOOGLE_SHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `APP_PASSWORD`, and environmental-provider settings when present. A production Google Sheets connection should retain `PREFER_LOCAL_DEMO_DATA=0`. The local `.env` file is not uploaded. The new chronic-care CSV files are read directly from the application files in either mode.

Enter the Start Command exactly as shown, without `web:`; that prefix is only Procfile syntax. Render requires public web services to bind to `0.0.0.0` and recommends the `PORT` variable. See [Python deployment](https://render.com/docs/deploy-flask) and [port binding](https://render.com/docs/web-services#port-binding).

If auto-deploy is enabled, merging into the linked branch triggers deployment. Otherwise choose **Manual Deploy → Deploy latest commit**. Watch the build/deploy logs until the service is live and confirm the deployed commit matches the merged change. See [Render's deployment instructions](https://render.com/docs/deploys).

Open [the live dashboard](https://asir-community-pulse-dashboard.onrender.com/), refresh the page, and repeat the visual checks from section 1. If you see the old logo, try a hard refresh with `Ctrl+F5` after confirming the new commit is live.

## 4. Optional: rebuild only the chronic-care CSVs

Normal running and deployment use the included CSV files; the original Excel files are not required on Render. To re-extract the same source tables later, place these inputs at their original paths:

- `notes/2022-Chapter-II-Health-Resources (1).xlsx`
- `notes/Statistical-Yearbook-2023.xlsx`
- `data/official_sources/moh_statistical_yearbook_2024.xlsx`

Then run from the application folder:

```powershell
.\.venv\Scripts\python.exe scripts/build_chronic_care_data.py
```

This updates four CSVs under `data/official_curated/chronic_care/`: `diabetes_visits.csv`, `chronic_care_capacity.csv`, `diabetes_rehabilitation_visits.csv`, and `dialysis_patients_2024.csv`. Review their changes, submit them through GitHub, and redeploy. It does not rebuild the existing seed workbook. The 2024 extractor reuses the existing official workbook; the additional 2024 copy in `notes` is not required.
