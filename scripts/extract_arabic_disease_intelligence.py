from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "data" / "official_sources" / "moh_statistical_yearbook_2024.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "data" / "official_curated" / "diseases"


MONTH_ORDER = [
    ("يناير", 1),
    ("فبراير", 2),
    ("مارس", 3),
    ("ابريل", 4),
    ("أبريل", 4),
    ("مايو", 5),
    ("يونيه", 6),
    ("يونيو", 6),
    ("يوليو", 7),
    ("أغسطس", 8),
    ("اغسطس", 8),
    ("سبتمبر", 9),
    ("اكتوبر", 10),
    ("أكتوبر", 10),
    ("نوفمبر", 11),
    ("ديسمبر", 12),
]

MONTH_NUMBER_MAP = {name: month_number for name, month_number in MONTH_ORDER}
MONTH_AR_MAP = {month_number: name for name, month_number in MONTH_ORDER}

REGION_ALIASES = {
    "الرياض": "الرياض",
    "العاصمة المقدسة": "مكة المكرمة",
    "مكة المكرمة": "مكة المكرمة",
    "جدة": "مكة المكرمة",
    "الطائف": "مكة المكرمة",
    "القنفذة": "مكة المكرمة",
    "المدينة المنورة": "المدينة المنورة",
    "القصيم": "القصيم",
    "الشرقية": "الشرقية",
    "الأحساء": "الشرقية",
    "الاحساء": "الشرقية",
    "حفر الباطن": "الشرقية",
    "عسير": "عسير",
    "بيشة": "بيشة",
    "بيشه": "بيشة",
    "تبوك": "تبوك",
    "حائل": "حائل",
    "الحدود الشمالية": "الحدود الشمالية",
    "جازان": "جازان",
    "نجران": "نجران",
    "الباحة": "الباحة",
    "الجوف": "الجوف",
}

DISEASE_NAME_FIXES = {
    ".الأمراض المستهدفة بالبرنامج الموسع للتحصين": "الأمراض المستهدفة بالبرنامج الموسع للتحصين",
    "االسالمونيلا": "السالمونيلا",
    "الكزار الوليدي": "الكزاز الوليدي",
    "التهاب كبدي أ": "التهاب الكبد الوبائي أ",
    "التهاب كبدي ب": "التهاب الكبد الوبائي ب",
    "التهاب كبدي ج (الأجسام المضادة)": "التهاب الكبد الوبائي ج (الأجسام المضادة)",
    "التهاب كبدي ج  (بي سي آر)": "التهاب الكبد الوبائي ج (بي سي آر)",
    "التهاب كبدي د": "التهاب الكبد الوبائي د",
    "التهاب كبدي هـ": "التهاب الكبد الوبائي هـ",
    "التهاب كبدي (عدوى غير محددة)": "التهاب الكبد الوبائي (عدوى غير محددة)",
    "الحمى المالطية (بروسيلا )": "الحمى المالطية",
    "السالمونيلا  *": "السالمونيلا",
    "السالمونيلا*": "السالمونيلا",
    "الحصبة الألمانية": "الحصبة الألمانية",
    "الجديري المائي": "الجديري المائي",
    "داء المشوكات": "داء المشوكات",
    "حمى الخرمة": "حمى الخرمة",
}

NON_DISEASE_LABELS = {
    "الأمراض المستهدفة بالبرنامج الموسع للتحصين",
    "تشمل الحالات المتفرقة فقط دون الفاشيات",
}

DiseaseRecord = dict[str, object]


def _configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_sheet_key(value: str) -> str:
    text = _normalize_text(value).lower()
    return re.sub(r"[\s\-\._]+", "", text)


def _is_arabic_text(value: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", _normalize_text(value)))


def _to_number(value: object) -> float | None:
    if value in (None, "", "-", "—"):
        return None
    try:
        numeric = pd.to_numeric(value, errors="coerce")
    except Exception:
        return None
    if pd.isna(numeric):
        return None
    return float(numeric)


def _to_int(value: object) -> int | None:
    numeric = _to_number(value)
    if numeric is None:
        return None
    return int(round(numeric))


def _clean_disease_name_ar(value: object) -> str:
    name = _normalize_text(value)
    name = name.replace("*", "").strip()
    name = DISEASE_NAME_FIXES.get(name, name)
    return name


def _normalize_region_name(value: object) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    if text in {"المجموع", "Total", "Overall", "الإجمالي", "الكلي"}:
        return "السعودية"
    return REGION_ALIASES.get(text, text)


def _is_data_region(value: object) -> bool:
    text = _normalize_text(value)
    if not text:
        return False
    if text in {"المجموع", "Total", "Overall", "الإجمالي", "الكلي"}:
        return False
    if text.startswith("*"):
        return False
    if "reported cases" in text.lower():
        return False
    return True


def _find_sheet_name(sheet_names: list[str], *candidates: str) -> str:
    normalized = {_normalize_sheet_key(name): name for name in sheet_names}
    for candidate in candidates:
        candidate_key = _normalize_sheet_key(candidate)
        if candidate_key in normalized:
            return normalized[candidate_key]
    for candidate in candidates:
        candidate_key = _normalize_sheet_key(candidate)
        for key, actual_name in normalized.items():
            if candidate_key and candidate_key in key:
                return actual_name
    raise KeyError(f"تعذر العثور على الورقة: {candidates}")


def _save_csv(frame: pd.DataFrame, filename: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")


def _append_national_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "health_region_ar" not in frame.columns or "cases" not in frame.columns:
        return frame
    dimensions = [column for column in frame.columns if column not in {"health_region_ar", "cases", "source_sheet"}]
    national = (
        frame.groupby(dimensions, dropna=False, as_index=False)["cases"]
        .sum(min_count=1)
        .assign(health_region_ar="السعودية", source_sheet=frame["source_sheet"].iloc[0] if "source_sheet" in frame.columns else "")
    )
    return pd.concat([frame, national], ignore_index=True)


def _parse_region_disease_sheet(workbook, sheet_name: str) -> pd.DataFrame:
    ws = workbook[sheet_name]
    records: list[DiseaseRecord] = []
    header_row_4 = {column: ws.cell(row=4, column=column).value for column in range(1, ws.max_column + 1)}
    header_row_5 = {column: ws.cell(row=5, column=column).value for column in range(1, ws.max_column + 1)}

    for row_idx in range(6, ws.max_row + 1):
        region_value = ws.cell(row=row_idx, column=1).value
        if not _is_data_region(region_value):
            continue
        canonical_region = _normalize_region_name(region_value)
        if canonical_region is None:
            continue

        for column in range(2, ws.max_column, 2):
            disease_name_ar = _clean_disease_name_ar(header_row_4.get(column + 1) or header_row_5.get(column + 1))
            if not disease_name_ar:
                continue
            cases = _to_int(ws.cell(row=row_idx, column=column).value)
            if cases is None:
                continue
            records.append(
                {
                    "disease_name_ar": disease_name_ar,
                    "health_region_ar": canonical_region,
                    "cases": cases,
                    "source_sheet": sheet_name,
                }
            )

    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame
    frame = frame.groupby(["disease_name_ar", "health_region_ar", "source_sheet"], as_index=False)["cases"].sum()
    return _append_national_rows(frame)


def _parse_communicable_by_month(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4])
    disease_column = raw.columns[0]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        disease_name_ar = _clean_disease_name_ar(row[disease_column])
        if not disease_name_ar or disease_name_ar.lower().startswith("unnamed"):
            continue
        for month_ar, month_number in MONTH_ORDER:
            column = next((col for col in raw.columns if _normalize_text(col[0]) == month_ar), None)
            if column is None:
                continue
            cases = _to_int(row[column])
            if cases is None:
                continue
            records.append(
                {
                    "disease_name_ar": disease_name_ar,
                    "month_ar": month_ar,
                    "month_number": month_number,
                    "cases": cases,
                    "source_sheet": sheet_name,
                }
            )

    return pd.DataFrame.from_records(records)


def _parse_communicable_by_age(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5])
    disease_column = raw.columns[0]
    age_columns = [
        ("<1", "< سنة"),
        ("1 - < 5", "1 - أقل من 5"),
        ("5 - < 15", "5 - أقل من 15"),
        ("15 - < 45", "15 - أقل من 45"),
        ("≥ 45", "45 فأكثر"),
        ("غير معروف", "غير معروف"),
    ]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        disease_name_ar = _clean_disease_name_ar(row[disease_column])
        if not disease_name_ar or disease_name_ar.lower().startswith("unnamed"):
            continue
        for original_label, display_label in age_columns:
            column = next((col for col in raw.columns if _normalize_text(col[1]) == original_label), None)
            if column is None:
                continue
            cases = _to_int(row[column])
            if cases is None:
                continue
            records.append(
                {
                    "disease_name_ar": disease_name_ar,
                    "age_group_ar": display_label,
                    "cases": cases,
                    "source_sheet": sheet_name,
                }
            )

    return pd.DataFrame.from_records(records)


def _parse_communicable_by_gender_nationality(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5])
    disease_column = raw.columns[0]
    mapping = [
        (("سعودي S", "ذكر"), "ذكر", "سعودي"),
        (("سعودي S", "انثى"), "أنثى", "سعودي"),
        (("غير سعودي NS", "ذكر"), "ذكر", "غير سعودي"),
        (("غير سعودي NS", "انثى"), "أنثى", "غير سعودي"),
    ]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        disease_name_ar = _clean_disease_name_ar(row[disease_column])
        if not disease_name_ar or disease_name_ar.lower().startswith("unnamed"):
            continue
        for (group_name, gender_header), gender_ar, nationality_ar in mapping:
            column = next(
                (
                    col
                    for col in raw.columns
                    if _normalize_text(col[0]) == group_name and _normalize_text(col[1]) == gender_header
                ),
                None,
            )
            if column is None:
                continue
            cases = _to_int(row[column])
            if cases is None:
                continue
            records.append(
                {
                    "disease_name_ar": disease_name_ar,
                    "gender_ar": gender_ar,
                    "nationality_ar": nationality_ar,
                    "cases": cases,
                    "source_sheet": sheet_name,
                }
            )

    return pd.DataFrame.from_records(records)


def _parse_communicable_trend(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5])
    disease_column = raw.columns[0]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        disease_name_ar = _clean_disease_name_ar(row[disease_column])
        if not disease_name_ar or disease_name_ar.lower().startswith("unnamed"):
            continue
        for year in [2020, 2021, 2022, 2023, 2024]:
            cases_column = next(
                (col for col in raw.columns if _normalize_text(col[0]) == f"{year}G" and _normalize_text(col[1]) == "الحالات"),
                None,
            )
            incidence_column = next(
                (
                    col
                    for col in raw.columns
                    if _normalize_text(col[0]) == f"{year}G"
                    and "معدل الإصابة" in _normalize_text(col[1])
                ),
                None,
            )
            records.append(
                {
                    "disease_name_ar": disease_name_ar,
                    "year": year,
                    "cases": _to_int(row[cases_column]) if cases_column is not None else None,
                    "incidence_rate": _to_number(row[incidence_column]) if incidence_column is not None else None,
                    "source_sheet": sheet_name,
                }
            )

    return pd.DataFrame.from_records(records)


def _parse_tuberculosis(excel_path: Path, sheet_name: str, tb_type_ar: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5, 6])
    region_column = raw.columns[0]
    age_labels = ["<5", "5 - < 15", "15 - < 25", "25 - < 35", "35 - < 45", "45 - < 55", "55 - < 65", "≥ 65"]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        if not _is_data_region(row[region_column]):
            continue
        health_region_ar = _normalize_region_name(row[region_column])
        if health_region_ar is None:
            continue
        for age_label in age_labels:
            column = next((col for col in raw.columns if _normalize_text(col[2]) == age_label), None)
            if column is None:
                continue
            cases = _to_int(row[column])
            if cases is None:
                continue
            records.append(
                {
                    "tb_type_ar": tb_type_ar,
                    "health_region_ar": health_region_ar,
                    "age_group_ar": age_label,
                    "cases": cases,
                    "source_sheet": sheet_name,
                }
            )

    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame
    return _append_national_rows(frame)


def _parse_malaria_parasites(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5])
    region_column = raw.columns[0]
    mapping = [
        ("المتصورة المنجلية (الخبيثة)", "المتصورة المنجلية (الخبيثة)"),
        ("المتصورة النشيطة والبيضاوية (الثلاثية الحميدة)", "المتصورة النشيطة والبيضاوية"),
        ("المتصورة الملاريية (الرباعية الحميدة)", "المتصورة الملاريية"),
        ("مختلطة", "مختلطة"),
    ]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        if not _is_data_region(row[region_column]):
            continue
        health_region_ar = _normalize_region_name(row[region_column])
        if health_region_ar is None:
            continue
        for source_label, parasite_type_ar in mapping:
            column = next((col for col in raw.columns if _normalize_text(col[1]) == source_label), None)
            if column is None:
                continue
            cases = _to_int(row[column])
            if cases is None:
                continue
            records.append(
                {
                    "health_region_ar": health_region_ar,
                    "month_ar": None,
                    "month_number": None,
                    "parasite_type_ar": parasite_type_ar,
                    "age_group_ar": None,
                    "cases": cases,
                    "source_sheet": sheet_name,
                }
            )

    return pd.DataFrame.from_records(records)


def _parse_malaria_age(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5, 6])
    region_column = raw.columns[0]
    age_labels = ["< 1", "1 - < 5", "5 - < 10", "10 - < 15", "≥ 15"]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        if not _is_data_region(row[region_column]):
            continue
        health_region_ar = _normalize_region_name(row[region_column])
        if health_region_ar is None:
            continue
        for age_label in age_labels:
            column = next((col for col in raw.columns if _normalize_text(col[1]) == age_label), None)
            if column is None:
                continue
            cases = _to_int(row[column])
            if cases is None:
                continue
            records.append(
                {
                    "health_region_ar": health_region_ar,
                    "month_ar": None,
                    "month_number": None,
                    "parasite_type_ar": None,
                    "age_group_ar": age_label,
                    "cases": cases,
                    "source_sheet": sheet_name,
                }
            )

    return pd.DataFrame.from_records(records)


def _parse_malaria_month(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5])
    month_column = raw.columns[0]
    region_columns = [
        ("جازان Jazan", "مستقدمة Introdused", "جازان"),
        ("جازان Jazan", "وافدة Imported", "جازان"),
        ("عسير Aseer", "مستقدمة Introdused", "عسير"),
        ("عسير Aseer", "وافدة Imported", "عسير"),
    ]
    category_map = {
        "مستقدمة Introdused": "حالات مستقدمة",
        "وافدة Imported": "حالات وافدة",
        "محلية Indigenous": "حالات محلية",
    }
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        month_ar = _normalize_text(row[month_column])
        if month_ar not in MONTH_NUMBER_MAP:
            continue
        for region_group, series_name, health_region_ar in region_columns:
            column = next(
                (
                    col
                    for col in raw.columns
                    if _normalize_text(col[0]) == region_group and _normalize_text(col[1]) == series_name
                ),
                None,
            )
            if column is None:
                continue
            cases = _to_int(row[column])
            if cases is None:
                continue
            records.append(
                {
                    "health_region_ar": health_region_ar,
                    "month_ar": month_ar,
                    "month_number": MONTH_NUMBER_MAP[month_ar],
                    "parasite_type_ar": category_map.get(series_name, series_name),
                    "age_group_ar": None,
                    "cases": cases,
                    "source_sheet": sheet_name,
                }
            )

    return pd.DataFrame.from_records(records)


def _parse_bilharzia(excel_path: Path, sheet_name: str, trend_sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5, 6])
    region_column = raw.columns[0]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        if not _is_data_region(row[region_column]):
            continue
        health_region_ar = _normalize_region_name(row[region_column])
        if health_region_ar is None:
            continue
        records.append(
            {
                "health_region_ar": health_region_ar,
                "cases": _to_int(row[raw.columns[2]]),
                "positivity_pct": _to_number(row[raw.columns[3]]),
                "urinary_cases": _to_int(row[raw.columns[4]]),
                "intestinal_cases": _to_int(row[raw.columns[5]]),
                "mixed_cases": _to_int(row[raw.columns[6]]),
                "saudi_cases": _to_int(row[raw.columns[9]]),
                "non_saudi_cases": _to_int(row[raw.columns[12]]),
                "age_lt_5_cases": _to_int(row[raw.columns[13]]),
                "age_5_15_cases": _to_int(row[raw.columns[14]]),
                "age_15_40_cases": _to_int(row[raw.columns[15]]),
                "age_ge_40_cases": _to_int(row[raw.columns[16]]),
                "source_sheet": sheet_name,
            }
        )

    trend = pd.read_excel(excel_path, sheet_name=trend_sheet_name, header=None)
    trend_rows: list[DiseaseRecord] = []
    year_map: dict[int, int] = {}
    for _, row in trend.iterrows():
        first_cell = _normalize_text(row.iloc[0])
        if first_cell == "" and any(str(value).strip() in {"2020", "2021", "2022", "2023", "2024"} for value in row.tolist()):
            for position, value in enumerate(row.tolist()):
                year_candidate = str(value).strip()
                if year_candidate in {"2020", "2021", "2022", "2023", "2024"}:
                    year_map[int(year_candidate)] = position
            break

    for _, row in trend.iterrows():
        indicator = _normalize_text(row.iloc[0])
        if indicator == "عدد الحالات" and year_map:
            for year, position in sorted(year_map.items()):
                trend_rows.append(
                    {
                        "health_region_ar": "السعودية",
                        "cases": _to_int(row.iloc[position]),
                        "positivity_pct": None,
                        "urinary_cases": None,
                        "intestinal_cases": None,
                        "mixed_cases": None,
                        "saudi_cases": None,
                        "non_saudi_cases": None,
                        "age_lt_5_cases": None,
                        "age_5_15_cases": None,
                        "age_15_40_cases": None,
                        "age_ge_40_cases": None,
                        "year": year,
                        "source_sheet": trend_sheet_name,
                    }
                )

    return pd.concat([pd.DataFrame.from_records(records), pd.DataFrame.from_records(trend_rows)], ignore_index=True)


def _parse_leprosy_trend(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=3)
    region_column = raw.columns[0]
    year_columns = [column for column in raw.columns if str(column).strip() in {"2020G", "2021G", "2022G", "2023G", "2024G"}]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        health_region_ar = _normalize_region_name(row[region_column])
        if health_region_ar is None:
            continue
        for column in year_columns:
            year = int(str(column).strip().replace("G", ""))
            cases = _to_int(row[column])
            if cases is None:
                continue
            records.append(
                {
                    "disease_name_ar": "الجذام",
                    "year": year,
                    "cases": cases,
                    "incidence_rate": None,
                    "source_sheet": sheet_name,
                }
            )

    if not records:
        return pd.DataFrame(columns=["disease_name_ar", "year", "cases", "incidence_rate", "source_sheet"])

    frame = pd.DataFrame.from_records(records)
    return frame.groupby(["disease_name_ar", "year", "source_sheet"], as_index=False)["cases"].sum()


def _parse_leishmaniasis(excel_path: Path, region_sheet: str, month_sheet: str, visceral_sheet: str, nationality_sheet: str) -> pd.DataFrame:
    region_raw = pd.read_excel(excel_path, sheet_name=region_sheet, header=[3, 4, 5, 6])
    region_column = region_raw.columns[0]
    records: list[DiseaseRecord] = []

    for _, row in region_raw.iterrows():
        if not _is_data_region(row[region_column]):
            continue
        records.append(
            {
                "leishmaniasis_type_ar": "ليشمانيا جلدية",
                "health_region_ar": _normalize_region_name(row[region_column]),
                "month_ar": None,
                "month_number": None,
                "cases": _to_int(row[region_raw.columns[1]]),
                "saudi_cases": _to_int(row[region_raw.columns[2]]),
                "non_saudi_cases": _to_int(row[region_raw.columns[3]]),
                "male_cases": _to_int(row[region_raw.columns[4]]),
                "female_cases": _to_int(row[region_raw.columns[5]]),
                "resident_cases": _to_int(row[region_raw.columns[6]]),
                "non_resident_cases": _to_int(row[region_raw.columns[7]]),
                "age_lt_1_cases": _to_int(row[region_raw.columns[8]]),
                "age_1_5_cases": _to_int(row[region_raw.columns[9]]),
                "age_5_10_cases": _to_int(row[region_raw.columns[10]]),
                "age_10_15_cases": _to_int(row[region_raw.columns[11]]),
                "age_15_45_cases": _to_int(row[region_raw.columns[12]]),
                "age_ge_45_cases": _to_int(row[region_raw.columns[13]]),
                "source_sheet": region_sheet,
            }
        )

    month_raw = pd.read_excel(excel_path, sheet_name=month_sheet, header=[3, 4, 5])
    month_column = month_raw.columns[0]
    for _, row in month_raw.iterrows():
        month_ar = _normalize_text(row[month_column])
        if month_ar not in MONTH_NUMBER_MAP:
            continue
        records.append(
            {
                "leishmaniasis_type_ar": "ليشمانيا جلدية",
                "health_region_ar": "السعودية",
                "month_ar": month_ar,
                "month_number": MONTH_NUMBER_MAP[month_ar],
                "cases": _to_int(row[month_raw.columns[1]]),
                "saudi_cases": _to_int(row[month_raw.columns[2]]),
                "non_saudi_cases": _to_int(row[month_raw.columns[3]]),
                "male_cases": _to_int(row[month_raw.columns[4]]),
                "female_cases": _to_int(row[month_raw.columns[5]]),
                "resident_cases": _to_int(row[month_raw.columns[6]]),
                "non_resident_cases": _to_int(row[month_raw.columns[7]]),
                "age_lt_1_cases": _to_int(row[month_raw.columns[8]]),
                "age_1_5_cases": _to_int(row[month_raw.columns[9]]),
                "age_5_10_cases": _to_int(row[month_raw.columns[10]]),
                "age_10_15_cases": _to_int(row[month_raw.columns[11]]),
                "age_15_45_cases": _to_int(row[month_raw.columns[12]]),
                "age_ge_45_cases": _to_int(row[month_raw.columns[13]]),
                "source_sheet": month_sheet,
            }
        )

    visceral_raw = pd.read_excel(excel_path, sheet_name=visceral_sheet, header=3)
    region_column = visceral_raw.columns[0]
    for _, row in visceral_raw.iterrows():
        if not _is_data_region(row[region_column]):
            continue
        records.append(
            {
                "leishmaniasis_type_ar": "ليشمانيا حشوية",
                "health_region_ar": _normalize_region_name(row[region_column]),
                "month_ar": None,
                "month_number": None,
                "cases": _to_int(row["2024G"]),
                "saudi_cases": None,
                "non_saudi_cases": None,
                "male_cases": None,
                "female_cases": None,
                "resident_cases": None,
                "non_resident_cases": None,
                "age_lt_1_cases": None,
                "age_1_5_cases": None,
                "age_5_10_cases": None,
                "age_10_15_cases": None,
                "age_15_45_cases": None,
                "age_ge_45_cases": None,
                "source_sheet": visceral_sheet,
            }
        )

    nationality_raw = pd.read_excel(excel_path, sheet_name=nationality_sheet, header=[3, 4, 5, 6])
    region_column = nationality_raw.columns[0]
    for _, row in nationality_raw.iterrows():
        if not _is_data_region(row[region_column]):
            continue
        records.append(
            {
                "leishmaniasis_type_ar": "ليشمانيا جلدية/حشوية - مقارنة 2024",
                "health_region_ar": _normalize_region_name(row[region_column]),
                "month_ar": None,
                "month_number": None,
                "cases": _to_int(row[nationality_raw.columns[9]]),
                "saudi_cases": _to_int(row[nationality_raw.columns[7]]),
                "non_saudi_cases": _to_int(row[nationality_raw.columns[8]]),
                "male_cases": None,
                "female_cases": None,
                "resident_cases": None,
                "non_resident_cases": None,
                "age_lt_1_cases": None,
                "age_1_5_cases": None,
                "age_5_10_cases": None,
                "age_10_15_cases": None,
                "age_15_45_cases": None,
                "age_ge_45_cases": None,
                "source_sheet": nationality_sheet,
            }
        )
        records.append(
            {
                "leishmaniasis_type_ar": "ليشمانيا حشوية - مقارنة 2024",
                "health_region_ar": _normalize_region_name(row[region_column]),
                "month_ar": None,
                "month_number": None,
                "cases": _to_int(row[nationality_raw.columns[12]]),
                "saudi_cases": _to_int(row[nationality_raw.columns[10]]),
                "non_saudi_cases": _to_int(row[nationality_raw.columns[11]]),
                "male_cases": None,
                "female_cases": None,
                "resident_cases": None,
                "non_resident_cases": None,
                "age_lt_1_cases": None,
                "age_1_5_cases": None,
                "age_5_10_cases": None,
                "age_10_15_cases": None,
                "age_15_45_cases": None,
                "age_ge_45_cases": None,
                "source_sheet": nationality_sheet,
            }
        )

    return pd.DataFrame.from_records(records)


def _parse_foodborne_outbreaks(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5, 6])
    region_column = raw.columns[0]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        if not _is_data_region(row[region_column]):
            continue
        records.append(
            {
                "health_region_ar": _normalize_region_name(row[region_column]),
                "source_type_ar": "إجمالي",
                "outbreak_count": _to_int(row[raw.columns[1]]),
                "cases": _to_int(row[raw.columns[4]]),
                "male_cases": _to_int(row[raw.columns[7]]),
                "female_cases": _to_int(row[raw.columns[8]]),
                "saudi_cases": _to_int(row[raw.columns[9]]),
                "non_saudi_cases": _to_int(row[raw.columns[10]]),
                "age_lt_1_cases": _to_int(row[raw.columns[11]]),
                "age_1_4_cases": _to_int(row[raw.columns[12]]),
                "age_5_19_cases": _to_int(row[raw.columns[13]]),
                "age_20_49_cases": _to_int(row[raw.columns[14]]),
                "age_50_plus_cases": _to_int(row[raw.columns[15]]),
                "source_sheet": sheet_name,
            }
        )
        records.append(
            {
                "health_region_ar": _normalize_region_name(row[region_column]),
                "source_type_ar": "مصدر عام",
                "outbreak_count": _to_int(row[raw.columns[2]]),
                "cases": _to_int(row[raw.columns[5]]),
                "male_cases": None,
                "female_cases": None,
                "saudi_cases": None,
                "non_saudi_cases": None,
                "age_lt_1_cases": None,
                "age_1_4_cases": None,
                "age_5_19_cases": None,
                "age_20_49_cases": None,
                "age_50_plus_cases": None,
                "source_sheet": sheet_name,
            }
        )
        records.append(
            {
                "health_region_ar": _normalize_region_name(row[region_column]),
                "source_type_ar": "منزلي",
                "outbreak_count": _to_int(row[raw.columns[3]]),
                "cases": _to_int(row[raw.columns[6]]),
                "male_cases": None,
                "female_cases": None,
                "saudi_cases": None,
                "non_saudi_cases": None,
                "age_lt_1_cases": None,
                "age_1_4_cases": None,
                "age_5_19_cases": None,
                "age_20_49_cases": None,
                "age_50_plus_cases": None,
                "source_sheet": sheet_name,
            }
        )

    return pd.DataFrame.from_records(records)


def _parse_intoxication(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5, 6])
    region_column = raw.columns[0]
    records: list[DiseaseRecord] = []

    for _, row in raw.iterrows():
        if not _is_data_region(row[region_column]):
            continue
        records.append(
            {
                "health_region_ar": _normalize_region_name(row[region_column]),
                "total_cases": _to_int(row[raw.columns[1]]),
                "drug_intoxication_cases": _to_int(row[raw.columns[2]]),
                "chemical_intoxication_cases": _to_int(row[raw.columns[3]]),
                "unknown_intoxication_cases": _to_int(row[raw.columns[4]]),
                "male_cases": _to_int(row[raw.columns[5]]),
                "female_cases": _to_int(row[raw.columns[6]]),
                "saudi_cases": _to_int(row[raw.columns[7]]),
                "non_saudi_cases": _to_int(row[raw.columns[8]]),
                "source_sheet": sheet_name,
            }
        )

    return pd.DataFrame.from_records(records)


def _parse_environmental_health_diseases(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4])
    # The first logical row contains year labels, so we normalize manually.
    year_labels = []
    for column in raw.columns[1:6]:
        year_text = _normalize_text(raw.iloc[0][column])
        year_labels.append((column, int(year_text.replace("G", "")) if year_text else None))

    records: list[DiseaseRecord] = []
    for row_idx in range(1, len(raw)):
        disease_name_ar = _clean_disease_name_ar(raw.iloc[row_idx][raw.columns[0]])
        if not disease_name_ar:
            continue
        for column, year in year_labels:
            if year is None:
                continue
            records.append(
                {
                    "disease_name_ar": disease_name_ar,
                    "year": year,
                    "incidence_rate": _to_number(raw.iloc[row_idx][column]),
                    "source_sheet": sheet_name,
                }
            )

    return pd.DataFrame.from_records(records)


def _parse_immunization_gap(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=[3, 4, 5])
    disease_column = raw.columns[0]
    records: list[DiseaseRecord] = []
    for _, row in raw.iterrows():
        disease_name_ar = _clean_disease_name_ar(row[disease_column])
        if not disease_name_ar or disease_name_ar.startswith("معدل الإصابة"):
            continue
        rate_2024_column = next((col for col in raw.columns if _normalize_text(col[2]) == "2024G" and "معدل الإصابة" in _normalize_text(col[0])), None)
        coverage_column = next((col for col in raw.columns if "التغطية بالتحصينات" in _normalize_text(col[0])), None)
        records.append(
            {
                "disease_name_ar": disease_name_ar,
                "incidence_rate_2024": _to_number(row[rate_2024_column]) if rate_2024_column is not None else None,
                "immunization_coverage_pct": _to_number(row[coverage_column]) if coverage_column is not None else None,
                "source_sheet": sheet_name,
            }
        )
    return pd.DataFrame.from_records(records)


def _infer_disease_group(disease_name_ar: str) -> tuple[str, str]:
    name = disease_name_ar
    if any(keyword in name for keyword in ["درن"]):
        return "الدرن", "تنفسي"
    if any(keyword in name for keyword in ["ملاريا", "ليشمانيا", "بلهارسيا", "مشوكات", "ضنك", "الخرمة"]):
        return "أمراض طفيلية ومنقولة بالنواقل", "منقول بالنواقل"
    if any(keyword in name for keyword in ["سالمونيلا", "تيفوئيد", "باراتيفوئيد", "زحار", "كوليرا"]):
        return "أمراض مرتبطة بالمياه والغذاء", "غذائي وبيئي"
    if any(keyword in name for keyword in ["حصبة", "نكاف", "جديري", "دفتيريا", "سعال", "شلل", "كزاز"]):
        return "أمراض مستهدفة بالتحصين", "وقائي وتحصيني"
    if any(keyword in name for keyword in ["التهاب الكبد", "حمى"]):
        return "أمراض سارية", "عدوى مجتمعية"
    if any(keyword in name for keyword in ["فاشيات"]):
        return "سلامة الغذاء", "إنذار مبكر"
    if any(keyword in name for keyword in ["تسمم"]):
        return "التسممات", "مخاطر بيئية وكيميائية"
    return "أمراض معدية وصحة عامة", "رصد صحي"


def _build_disease_catalog(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    dimension_map: dict[str, set[str]] = {}
    sheet_map: dict[str, set[str]] = {}

    for table_name, frame in tables.items():
        if frame.empty:
            continue
        disease_columns = [column for column in frame.columns if column == "disease_name_ar"]
        if not disease_columns and table_name == "tuberculosis_ar":
            disease_values = frame["tb_type_ar"].dropna().astype(str).unique().tolist()
        elif not disease_columns and table_name == "leishmaniasis_ar":
            disease_values = frame["leishmaniasis_type_ar"].dropna().astype(str).unique().tolist()
        elif not disease_columns:
            continue
        else:
            disease_values = frame["disease_name_ar"].dropna().astype(str).unique().tolist()

        available_dimensions = []
        for column, label in {
            "health_region_ar": "المنطقة الصحية",
            "month_ar": "الشهر",
            "age_group_ar": "الفئة العمرية",
            "gender_ar": "الجنس",
            "nationality_ar": "الجنسية",
            "year": "الاتجاه الزمني",
            "parasite_type_ar": "نوع الطفيل",
        }.items():
            if column in frame.columns:
                available_dimensions.append(label)

        source_sheets = sorted({value for value in frame.get("source_sheet", pd.Series(dtype="object")).dropna().astype(str)})

        for disease_name_ar in disease_values:
            disease_name_ar = _clean_disease_name_ar(disease_name_ar)
            if not disease_name_ar or disease_name_ar in NON_DISEASE_LABELS:
                continue
            dimension_map.setdefault(disease_name_ar, set()).update(available_dimensions)
            sheet_map.setdefault(disease_name_ar, set()).update(source_sheets)

    records = []
    for disease_id, disease_name_ar in enumerate(sorted(dimension_map), start=1):
        disease_group_ar, risk_type_ar = _infer_disease_group(disease_name_ar)
        records.append(
            {
                "disease_id": f"D-{disease_id:03d}",
                "disease_name_ar": disease_name_ar,
                "disease_group_ar": disease_group_ar,
                "risk_type_ar": risk_type_ar,
                "source_sheet": " | ".join(sorted(sheet_map.get(disease_name_ar, set()))),
                "available_dimensions_ar": " | ".join(sorted(dimension_map.get(disease_name_ar, set()))),
            }
        )

    return pd.DataFrame.from_records(records)


def main() -> None:
    _configure_stdout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(f"ملف المصدر غير موجود: {SOURCE_PATH}")

    excel = pd.ExcelFile(SOURCE_PATH)
    workbook = load_workbook(SOURCE_PATH, data_only=True, read_only=True)
    print("عدد أوراق العمل المكتشفة:", len(excel.sheet_names))
    for index, sheet_name in enumerate(excel.sheet_names, start=1):
        print(f"{index:03d} | {sheet_name}")

    skipped_rows: list[dict[str, str]] = []
    generated_tables: dict[str, pd.DataFrame] = {}

    parsing_plan = {
        "communicable_diseases_by_region_ar.csv": lambda: pd.concat(
            [
                _parse_region_disease_sheet(workbook, _find_sheet_name(excel.sheet_names, "3-2")),
                _parse_region_disease_sheet(workbook, _find_sheet_name(excel.sheet_names, "3-2تكملة", "3-2 تكملة")),
            ],
            ignore_index=True,
        ).groupby(["disease_name_ar", "health_region_ar", "source_sheet"], as_index=False)["cases"].sum(),
        "communicable_diseases_by_month_ar.csv": lambda: _parse_communicable_by_month(
            SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-3")
        ),
        "communicable_diseases_by_age_ar.csv": lambda: _parse_communicable_by_age(
            SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-4")
        ),
        "communicable_diseases_by_gender_nationality_ar.csv": lambda: _parse_communicable_by_gender_nationality(
            SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-5")
        ),
        "communicable_diseases_5_year_trend_ar.csv": lambda: pd.concat(
            [
                _parse_communicable_trend(SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-6")),
                _parse_leprosy_trend(SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3.9", "3-9")),
            ],
            ignore_index=True,
        ),
        "tuberculosis_ar.csv": lambda: pd.concat(
            [
                _parse_tuberculosis(SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-7"), "درن رئوي"),
                _parse_tuberculosis(SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-8"), "درن غير رئوي"),
            ],
            ignore_index=True,
        ),
        "malaria_ar.csv": lambda: pd.concat(
            [
                _parse_malaria_parasites(SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-10")),
                _parse_malaria_age(SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-11")),
                _parse_malaria_month(SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-12")),
            ],
            ignore_index=True,
        ),
        "bilharzia_ar.csv": lambda: _parse_bilharzia(
            SOURCE_PATH,
            _find_sheet_name(excel.sheet_names, "3-13"),
            _find_sheet_name(excel.sheet_names, "3-14"),
        ),
        "leishmaniasis_ar.csv": lambda: _parse_leishmaniasis(
            SOURCE_PATH,
            _find_sheet_name(excel.sheet_names, "3-15"),
            _find_sheet_name(excel.sheet_names, "3-16"),
            _find_sheet_name(excel.sheet_names, "3-17"),
            _find_sheet_name(excel.sheet_names, "3-18"),
        ),
        "foodborne_outbreaks_ar.csv": lambda: _parse_foodborne_outbreaks(
            SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3.22", "3-22")
        ),
        "intoxication_ar.csv": lambda: _parse_intoxication(
            SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-23")
        ),
        "environmental_health_diseases_ar.csv": lambda: _parse_environmental_health_diseases(
            SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-21")
        ),
        "immunization_gap_ar.csv": lambda: _parse_immunization_gap(
            SOURCE_PATH, _find_sheet_name(excel.sheet_names, "3-1")
        ),
    }

    for filename, parser in parsing_plan.items():
        try:
            frame = parser()
            if frame is None:
                frame = pd.DataFrame()
            generated_tables[filename.replace(".csv", "")] = frame
            _save_csv(frame, filename)
            print(f"تم إنشاء: {filename} | الصفوف: {len(frame):,}")
        except Exception as exc:
            skipped_rows.append({"sheet_name": filename, "reason": str(exc)})
            print(f"تم تجاوز {filename}: {exc}")

    disease_catalog = _build_disease_catalog(generated_tables)
    generated_tables["disease_catalog_ar"] = disease_catalog
    _save_csv(disease_catalog, "disease_catalog_ar.csv")

    skipped_report = pd.DataFrame(skipped_rows)
    _save_csv(skipped_report, "skipped_tables_report.csv")

    print("اكتمل استخراج طبقة الأمراض المعدية إلى:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
