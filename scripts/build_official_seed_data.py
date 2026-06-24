from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OFFICIAL_DIR = DATA_DIR / "official_sources"
CURATED_DIR = DATA_DIR / "official_curated"
OUTPUT_PATH = DATA_DIR / "official_google_sheets_seed.xlsx"
CSV_DIR = DATA_DIR / "official_google_sheet_tabs"
RNG = np.random.default_rng(2030)


SOURCE_URLS = {
    "moh_yearbook_2024_xlsx": "https://www.moh.gov.sa/en/Ministry/Statistics/book/Documents/Statistical-Yearbook-2024.xlsx",
    "gastat_healthcare_establishments_2024_xlsx": "https://www.stats.gov.sa/documents/d/guest/healthcare-establishments-and-workforce-statistics-2024-en",
    "gastat_healthcare_statistics_2024_xlsx": "https://www.stats.gov.sa/documents/d/guest/healthcare-statistics-publication-2024-en-xlsx",
    "gastat_qassim_detail_pdf": "https://www.stats.gov.sa/documents/20117/2435265/lqsym_4.pdf/93a6ebd5-514b-c787-17e4-239d36b8cce3?t=1735192378913",
}

REGION_EN_TO_KEY = {
    "riyadh": "riyadh",
    "makkah": "makkah",
    "the holy capital": "makkah",
    "jeddah": "makkah",
    "taif": "makkah",
    "qunfudah": "makkah",
    "madinah": "madinah",
    "medinah": "madinah",
    "qassim": "qassim",
    "qaseem": "qassim",
    "eastern region": "eastern",
    "eastern province": "eastern",
    "eastern": "eastern",
    "al ahsa": "eastern",
    "al-ahsa": "eastern",
    "hafr al batin": "eastern",
    "hafr al-batin": "eastern",
    "aseer": "asir",
    "asir": "asir",
    "bishah": "asir",
    "tabuk": "tabuk",
    "tabouk": "tabuk",
    "hail": "hail",
    "northern borders": "northern_borders",
    "jazan": "jazan",
    "najran": "najran",
    "al-baha": "al_baha",
    "al baha": "al_baha",
    "bahah": "al_baha",
    "al-jouf": "al_jouf",
    "al jouf": "al_jouf",
    "jawf": "al_jouf",
    "qurrayyat": "al_jouf",
}

REGION_KEY_TO_REGION_ID = {
    "riyadh": "R-01",
    "makkah": "R-02",
    "madinah": "R-03",
    "qassim": "R-04",
    "eastern": "R-05",
    "asir": "R-06",
    "tabuk": "R-07",
    "hail": "R-08",
    "northern_borders": "R-09",
    "jazan": "R-10",
    "najran": "R-11",
    "al_baha": "R-12",
    "al_jouf": "R-13",
}

RISK_LABELS = [(78, "عالي"), (60, "متوسط"), (0, "منخفض")]
MONTH_FACTORS = np.array([0.96, 0.98, 0.99, 1.00, 1.01, 1.03, 1.04, 1.05, 1.03, 1.01, 0.99, 0.97])


@dataclass(frozen=True)
class MetricSpec:
    sheet_name: str
    columns: list[tuple[str, int, float]]


HEALTHCARE_STATS_SPECS = [
    MetricSpec("2", [("government_coverage_pct", 1, 100), ("private_insurance_pct", 2, 100), ("self_pay_pct", 4, 100)]),
    MetricSpec("6", [("adult_visit_rate", 3, 1)]),
    MetricSpec("9", [("doctor_time_satisfaction_pct", 3, 100)]),
    MetricSpec("13", [("child_visit_rate", 3, 1)]),
    MetricSpec("17", [("child_doctor_time_satisfaction_pct", 3, 100)]),
    MetricSpec("19", [("adult_dental_consultation_pct", 3, 100)]),
    MetricSpec("21", [("adult_dental_filling_pct", 3, 100)]),
    MetricSpec("24", [("child_dental_consultation_pct", 3, 100)]),
    MetricSpec("26", [("child_dental_filling_pct", 3, 100)]),
    MetricSpec("28", [("child_tooth_removal_pct", 3, 100)]),
    MetricSpec("40", [("internet_health_info_pct", 3, 100)]),
    MetricSpec("42", [("teleconsultation_pct", 3, 100)]),
    MetricSpec("44", [("emr_access_pct", 3, 100)]),
]


def _canonical_key(value: str) -> str | None:
    cleaned = " ".join(str(value).replace("\n", " ").replace("-", " ").split()).strip().lower()
    return REGION_EN_TO_KEY.get(cleaned)


def _normalize_scale(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    minimum = numeric.min()
    maximum = numeric.max()
    if pd.isna(minimum) or pd.isna(maximum) or minimum == maximum:
        return pd.Series(0.5, index=series.index, dtype=float)
    return (numeric - minimum) / (maximum - minimum)


def _clip_round(value: float, low: float, high: float, decimals: int = 1) -> float:
    return round(float(np.clip(value, low, high)), decimals)


def _risk_label(score: float) -> str:
    for threshold, label in RISK_LABELS:
        if score >= threshold:
            return label
    return "منخفض"


def load_region_reference() -> tuple[pd.DataFrame, pd.DataFrame]:
    regions = pd.read_csv(
        DATA_DIR / "saudi_regions.csv",
        usecols=["region_id", "capital_city_id", "name_ar", "name_en", "center_lat", "center_lon"],
    ).copy()
    cities = pd.read_csv(DATA_DIR / "saudi_cities_lite.csv").copy()

    regions["region_id"] = regions["region_id"].map(lambda value: f"R-{int(value):02d}")
    regions["region_key"] = regions["name_en"].map(lambda value: _canonical_key(value) or value.lower())
    regions["region_name_ar"] = regions["name_ar"]
    regions["region_name_en"] = regions["name_en"]
    regions["province_name_ar"] = regions["name_ar"].str.replace("منطقة ", "", regex=False).str.replace("المنطقة ", "", regex=False)
    regions["province_name_ar"] = regions["province_name_ar"].replace({"الالشرقية": "الشرقية"})
    regions["latitude"] = pd.to_numeric(regions["center_lat"], errors="coerce")
    regions["longitude"] = pd.to_numeric(regions["center_lon"], errors="coerce")
    regions["geo_region_id"] = regions["region_id"]

    capital_lookup = cities.rename(columns={"city_id": "capital_city_id", "name_ar": "capital_city_ar"})[
        ["capital_city_id", "capital_city_ar"]
    ]
    regions = regions.merge(capital_lookup, on="capital_city_id", how="left")
    regions["city_name_ar"] = regions["capital_city_ar"].fillna(regions["province_name_ar"])
    return regions, cities


def extract_population_and_facilities() -> pd.DataFrame:
    workbook = pd.ExcelFile(OFFICIAL_DIR / "gastat_healthcare_establishments_workforce_2024_en.xlsx")

    hospitals = pd.read_excel(workbook, sheet_name="1", header=5).iloc[:13, :4]
    hospitals.columns = ["region_en", "hospitals_gov", "hospitals_private", "hospitals_total"]

    hospitals_per_100k = pd.read_excel(workbook, sheet_name="3", header=5).iloc[:13, :2]
    hospitals_per_100k.columns = ["region_en", "hospitals_per_100k"]

    beds = pd.read_excel(workbook, sheet_name="4", header=5).iloc[:13, :4]
    beds.columns = ["region_en", "beds_gov", "beds_private", "beds_total"]

    beds_per_1000 = pd.read_excel(workbook, sheet_name="7", header=5).iloc[:13, :2]
    beds_per_1000.columns = ["region_en", "beds_per_1000"]

    phc = pd.read_excel(workbook, sheet_name="9", header=5).iloc[:13, :4]
    phc.columns = ["region_en", "phc_gov", "phc_private", "phc_total"]

    phc_per_10k = pd.read_excel(workbook, sheet_name="10", header=5).iloc[:13, :2]
    phc_per_10k.columns = ["region_en", "phc_per_10k"]

    pharmacies = pd.read_excel(workbook, sheet_name="11", header=5).iloc[:13, :2]
    pharmacies.columns = ["region_en", "private_pharmacies"]

    merged = hospitals.merge(hospitals_per_100k, on="region_en")
    merged = merged.merge(beds, on="region_en")
    merged = merged.merge(beds_per_1000, on="region_en")
    merged = merged.merge(phc, on="region_en")
    merged = merged.merge(phc_per_10k, on="region_en")
    merged = merged.merge(pharmacies, on="region_en")

    merged["region_key"] = merged["region_en"].map(_canonical_key)
    merged["region_id"] = merged["region_key"].map(REGION_KEY_TO_REGION_ID)
    merged["population_total"] = (merged["hospitals_total"] / merged["hospitals_per_100k"] * 100000).round().astype(int)
    return merged.dropna(subset=["region_id"]).copy()


def extract_healthcare_stats() -> pd.DataFrame:
    workbook = pd.ExcelFile(OFFICIAL_DIR / "gastat_healthcare_statistics_publication_2024_en.xlsx")
    frames: list[pd.DataFrame] = []
    for spec in HEALTHCARE_STATS_SPECS:
        sheet = pd.read_excel(workbook, sheet_name=spec.sheet_name, header=None).fillna("")
        rows = []
        for _, row in sheet.iterrows():
            values = [value for value in row.tolist() if value != ""]
            if len(values) < 2:
                continue
            region_key = _canonical_key(str(values[0]))
            if not region_key:
                continue
            item = {"region_key": region_key}
            for column_name, value_index, multiplier in spec.columns:
                if len(values) > value_index:
                    item[column_name] = pd.to_numeric(values[value_index], errors="coerce") * multiplier
            rows.append(item)
        frames.append(pd.DataFrame(rows))

    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="region_key", how="outer")
    merged["region_id"] = merged["region_key"].map(REGION_KEY_TO_REGION_ID)
    return merged.dropna(subset=["region_id"]).copy()


def extract_utilization_trends() -> pd.DataFrame:
    table = pd.read_excel(OFFICIAL_DIR / "moh_statistical_yearbook_2024.xlsx", sheet_name="4-7", header=None)
    data = table.iloc[6:19, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]].copy()
    data.columns = [
        "region_ar",
        "phc_2020",
        "opd_2020",
        "phc_2021",
        "opd_2021",
        "phc_2022",
        "opd_2022",
        "phc_2023",
        "opd_2023",
        "phc_2024",
        "opd_2024",
        "region_en",
    ]
    data["region_key"] = data["region_en"].map(_canonical_key)
    data["region_id"] = data["region_key"].map(REGION_KEY_TO_REGION_ID)
    numeric_columns = [column for column in data.columns if column.startswith(("phc_", "opd_"))]
    data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, errors="coerce")
    return data.dropna(subset=["region_id"]).copy()


def extract_diabetic_visits() -> pd.DataFrame:
    table = pd.read_excel(OFFICIAL_DIR / "moh_statistical_yearbook_2024.xlsx", sheet_name="4-16", header=None)
    rows = table.iloc[5:33, [0, 5, 6]].copy()
    rows.columns = ["cluster_name_ar", "diabetic_visits_total", "cluster_name_en"]
    rows["cluster_key"] = rows["cluster_name_en"].map(_canonical_key)
    rows["diabetic_visits_total"] = pd.to_numeric(rows["diabetic_visits_total"], errors="coerce")
    region_totals = rows.groupby("cluster_key", dropna=True)["diabetic_visits_total"].sum().reset_index()
    region_totals["region_id"] = region_totals["cluster_key"].map(REGION_KEY_TO_REGION_ID)
    return region_totals.rename(columns={"cluster_key": "region_key"}).dropna(subset=["region_id"]).copy()


def build_official_region_summary() -> pd.DataFrame:
    regions_ref, _ = load_region_reference()
    facilities = extract_population_and_facilities()
    healthcare = extract_healthcare_stats()
    trends = extract_utilization_trends()
    diabetic = extract_diabetic_visits()

    summary = regions_ref.merge(facilities, on="region_id", how="left")
    summary = summary.merge(healthcare.drop(columns=["region_key"]), on="region_id", how="left")
    summary = summary.merge(trends.drop(columns=["region_key"]), on="region_id", how="left")
    summary = summary.merge(diabetic.drop(columns=["region_key"]), on="region_id", how="left")
    summary["region_key"] = summary["region_name_en"].map(lambda value: _canonical_key(value) or str(value).lower())
    summary["diabetic_visits_total"] = pd.to_numeric(summary["diabetic_visits_total"], errors="coerce")
    known_diabetic_rate = (summary["diabetic_visits_total"] / summary["population_total"]).replace([np.inf, -np.inf], np.nan)
    default_diabetic_rate = known_diabetic_rate.dropna().median()
    if pd.isna(default_diabetic_rate):
        default_diabetic_rate = 0.035
    summary["diabetic_visits_total"] = summary["diabetic_visits_total"].fillna(summary["population_total"] * default_diabetic_rate)

    summary["visits_per_1000_2024"] = ((summary["phc_2024"] + summary["opd_2024"]) / summary["population_total"]) * 1000
    summary["diabetic_visits_per_100k"] = (summary["diabetic_visits_total"] / summary["population_total"]) * 100000

    summary["pulse_norm"] = (
        _normalize_scale(summary["doctor_time_satisfaction_pct"]) * 0.22
        + _normalize_scale(summary["adult_visit_rate"]) * 0.10
        + _normalize_scale(summary["adult_dental_consultation_pct"]) * 0.08
        + _normalize_scale(summary["internet_health_info_pct"]) * 0.08
        + _normalize_scale(summary["teleconsultation_pct"]) * 0.06
        + _normalize_scale(summary["emr_access_pct"]) * 0.08
        + _normalize_scale(summary["phc_per_10k"]) * 0.12
        + _normalize_scale(summary["beds_per_1000"]) * 0.10
        + _normalize_scale(summary["government_coverage_pct"]) * 0.08
        + (1 - _normalize_scale(summary["self_pay_pct"])) * 0.08
    )
    summary["community_pulse_index"] = (54 + summary["pulse_norm"] * 38).clip(52, 92).round(1)

    summary["risk_norm"] = (
        _normalize_scale(summary["diabetic_visits_per_100k"]) * 0.33
        + (1 - _normalize_scale(summary["doctor_time_satisfaction_pct"])) * 0.14
        + _normalize_scale(summary["self_pay_pct"]) * 0.12
        + (1 - _normalize_scale(summary["internet_health_info_pct"])) * 0.10
        + (1 - _normalize_scale(summary["teleconsultation_pct"])) * 0.08
        + (1 - _normalize_scale(summary["emr_access_pct"])) * 0.10
        + _normalize_scale(summary["visits_per_1000_2024"]) * 0.13
    )
    summary["risk_prediction_score"] = (34 + summary["risk_norm"] * 46).clip(30, 88).round(1)
    summary["avg_waiting_time_minutes"] = (
        11
        + summary["risk_prediction_score"] * 0.23
        + summary["self_pay_pct"] * 0.03
        - summary["phc_per_10k"] * 1.2
        - summary["teleconsultation_pct"] * 0.015
    ).clip(12, 37).round(1)
    summary["chronic_cases_rate"] = (
        0.14
        + (summary["risk_prediction_score"] / 100) * 0.20
        + _normalize_scale(summary["diabetic_visits_per_100k"]) * 0.05
    ).clip(0.16, 0.39)

    summary["priority_level"] = summary["risk_prediction_score"].map(_risk_label)
    summary["risk_level"] = summary["priority_level"]

    summary["population_total"] = pd.to_numeric(summary["population_total"], errors="coerce").round().astype(int)
    curated_columns = [
        "region_id",
        "region_key",
        "region_name_ar",
        "region_name_en",
        "province_name_ar",
        "city_name_ar",
        "population_total",
        "latitude",
        "longitude",
        "hospitals_total",
        "beds_total",
        "phc_total",
        "private_pharmacies",
        "hospitals_per_100k",
        "beds_per_1000",
        "phc_per_10k",
        "government_coverage_pct",
        "private_insurance_pct",
        "self_pay_pct",
        "adult_visit_rate",
        "doctor_time_satisfaction_pct",
        "adult_dental_consultation_pct",
        "internet_health_info_pct",
        "teleconsultation_pct",
        "emr_access_pct",
        "phc_2020",
        "opd_2020",
        "phc_2021",
        "opd_2021",
        "phc_2022",
        "opd_2022",
        "phc_2023",
        "opd_2023",
        "phc_2024",
        "opd_2024",
        "diabetic_visits_total",
        "diabetic_visits_per_100k",
        "community_pulse_index",
        "risk_prediction_score",
        "avg_waiting_time_minutes",
        "chronic_cases_rate",
        "priority_level",
        "risk_level",
    ]
    return summary[curated_columns].sort_values("region_id").reset_index(drop=True)


def build_qassim_governorate_detail() -> pd.DataFrame:
    path = OFFICIAL_DIR / "gastat_qassim_detailed_results.pdf"
    governorate_ar_map = {
        "Buraydah": "بريدة",
        "Unayzah": "عنيزة",
        "Arrass": "الرس",
        "Almidhnab": "المذنب",
        "Albukayriyah": "البكيرية",
        "Albadai": "البدائع",
        "Alasyah": "الأسياح",
        "Annabhaniyah": "النبهانية",
        "Uyun Aljiwa": "عيون الجواء",
        "Riyadh Alkhabra": "رياض الخبراء",
        "Ashshimasiyah": "الشماسية",
    }
    with pdfplumber.open(path) as pdf:
        table = pdf.pages[0].extract_table()
    rows = []
    for row in table or []:
        if not row or row[0] in {"Govenorate", "", None}:
            continue
        if str(row[0]).strip() == "Total":
            break
        if pd.isna(pd.to_numeric(row[1], errors="coerce")):
            continue
        rows.append(
            {
                "governorate_en": row[0],
                "population_total": pd.to_numeric(row[1], errors="coerce"),
                "female_total": pd.to_numeric(row[2], errors="coerce"),
                "male_total": pd.to_numeric(row[3], errors="coerce"),
                "non_saudi_total": pd.to_numeric(row[4], errors="coerce"),
                "non_saudi_female": pd.to_numeric(row[5], errors="coerce"),
                "non_saudi_male": pd.to_numeric(row[6], errors="coerce"),
                "saudi_total": pd.to_numeric(row[7], errors="coerce"),
                "saudi_female": pd.to_numeric(row[8], errors="coerce"),
                "saudi_male": pd.to_numeric(row[9], errors="coerce"),
                "governorate_ar": governorate_ar_map.get(str(row[0]).strip(), row[10]),
            }
        )
    return pd.DataFrame(rows)


def build_asir_cluster_detail() -> pd.DataFrame:
    facilities = pd.read_excel(OFFICIAL_DIR / "moh_statistical_yearbook_2024.xlsx", sheet_name="2-4", header=None)
    beds = pd.read_excel(OFFICIAL_DIR / "moh_statistical_yearbook_2024.xlsx", sheet_name="2-9", header=None)
    diabetes = pd.read_excel(OFFICIAL_DIR / "moh_statistical_yearbook_2024.xlsx", sheet_name="4-16", header=None)

    asir_rows = []
    facility_rows = facilities.iloc[21:23, :14].copy()
    bed_rows = beds.iloc[21:23, :10].copy()
    diabetes_rows = diabetes.iloc[21:23, :6].copy()
    for index in range(2):
        facility_row = facility_rows.iloc[index]
        bed_row = bed_rows.iloc[index]
        diabetes_row = diabetes_rows.iloc[index]
        asir_rows.append(
            {
                "cluster_name_ar": facility_row.iloc[0],
                "cluster_name_en": facility_row.iloc[13],
                "phc_count": pd.to_numeric(facility_row.iloc[1], errors="coerce"),
                "hospital_count": pd.to_numeric(facility_row.iloc[2], errors="coerce"),
                "diabetes_centers": pd.to_numeric(facility_row.iloc[5], errors="coerce"),
                "dialysis_units": pd.to_numeric(facility_row.iloc[6], errors="coerce"),
                "dental_centers": pd.to_numeric(facility_row.iloc[7], errors="coerce"),
                "rehabilitation_centers": pd.to_numeric(facility_row.iloc[8], errors="coerce"),
                "smoking_cessation_clinics": pd.to_numeric(facility_row.iloc[11], errors="coerce"),
                "beds_total": pd.to_numeric(bed_row.iloc[9], errors="coerce"),
                "internal_beds": pd.to_numeric(bed_row.iloc[1], errors="coerce"),
                "surgical_beds": pd.to_numeric(bed_row.iloc[2], errors="coerce"),
                "icu_beds": pd.to_numeric(bed_row.iloc[5], errors="coerce"),
                "diabetic_clinic_visits_2024": pd.to_numeric(diabetes_row.iloc[5], errors="coerce"),
            }
        )
    return pd.DataFrame(asir_rows)


def _extract_workforce_block(sheet_name: str, target_regions: dict[str, str]) -> pd.DataFrame:
    sheet = pd.read_excel(OFFICIAL_DIR / "moh_statistical_yearbook_2024.xlsx", sheet_name=sheet_name, header=None).fillna("")
    block_rows = [3, 32, 61, 90, 119, 148]
    wanted_categories = {
        ("أطباء بشريون", "المجموع"): "physicians_total",
        ("إجمالي الأطباء", "المجموع"): "physicians_and_dentists_total",
        ("إجمالي طاقم التمريض والقابلات", "المجموع"): "nurses_and_midwives_total",
        ("صيادلة", "المجموع"): "pharmacists_total",
        ("فئات طبية مساعدة", "المجموع"): "allied_health_total",
    }
    rows = []
    for block_row in block_rows:
        region_headers = {
            2: str(sheet.iloc[block_row + 1, 2]).strip(),
            5: str(sheet.iloc[block_row + 1, 5]).strip(),
            8: str(sheet.iloc[block_row + 1, 8]).strip(),
            11: str(sheet.iloc[block_row + 1, 11]).strip(),
        }
        region_columns = {target_regions.get(name): column for column, name in region_headers.items() if name in target_regions}
        if not region_columns:
            continue
        metrics = {region_key: {} for region_key in region_columns}
        active_category = ""
        for row_index in range(block_row + 4, min(block_row + 27, len(sheet))):
            category = str(sheet.iloc[row_index, 0]).strip()
            gender = str(sheet.iloc[row_index, 1]).strip()
            if category:
                active_category = category
            else:
                category = active_category
            metric_name = wanted_categories.get((category, gender))
            if not metric_name:
                continue
            for region_key, column_start in region_columns.items():
                metrics[region_key][metric_name] = pd.to_numeric(sheet.iloc[row_index, column_start + 2], errors="coerce")
        for region_key, metric_values in metrics.items():
            metric_values["region_key"] = region_key
            rows.append(metric_values)
    return pd.DataFrame(rows)


def build_asir_qassim_workforce_detail() -> pd.DataFrame:
    targets = {"Qassim": "qassim", "Asir": "asir_core", "Bishah": "asir_bishah"}
    moh = _extract_workforce_block("2-24", targets)
    all_sectors = _extract_workforce_block("2-27", targets)

    if moh.empty and all_sectors.empty:
        return pd.DataFrame()

    merged = moh.merge(all_sectors, on="region_key", how="outer", suffixes=("_moh", "_all_sectors"))
    merged["region_name_ar"] = merged["region_key"].map(
        {"qassim": "القصيم", "asir_core": "عسير", "asir_bishah": "بيشة"}
    )
    return merged


def build_health_facilities(region_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in region_summary.iterrows():
        readiness = _clip_round(64 + row["community_pulse_index"] * 0.32 - row["risk_prediction_score"] * 0.08, 58, 96)
        occupancy = _clip_round(48 + row["risk_prediction_score"] * 0.45, 38, 89)
        base_doctors = max(int(row["population_total"] / 2200), 80)
        facility_specs = [
            ("مستشفيات", int(row["hospitals_total"]), base_doctors),
            ("مراكز الرعاية الأولية", int(row["phc_total"]), max(int(base_doctors * 0.65), 40)),
            ("صيدليات خاصة", int(row["private_pharmacies"]), max(int(base_doctors * 0.25), 20)),
            ("عيادات السكري", max(int(row["diabetic_visits_total"] / 12000), 2), max(int(base_doctors * 0.18), 12)),
        ]
        for index, (label, count_value, doctors_count) in enumerate(facility_specs, start=1):
            rows.append(
                {
                    "facility_id": f"{row['region_id']}-FAC-{index:02d}",
                    "name_ar": f"{label} - {row['province_name_ar']}",
                    "type": label,
                    "region_id": row["region_id"],
                    "province_ar": row["province_name_ar"],
                    "facility_count": count_value,
                    "readiness_score": readiness,
                    "beds_occupied_pct": occupancy,
                    "doctors_count": doctors_count,
                }
            )
    return pd.DataFrame(rows)


def build_survey(region_summary: pd.DataFrame, cities: pd.DataFrame) -> pd.DataFrame:
    cities = cities.copy()
    cities["region_id"] = cities["region_id"].map(lambda value: f"R-{int(value):02d}")
    city_lookup = cities.groupby("region_id")["name_ar"].apply(list).to_dict()

    rows = []
    response_counter = 100000
    for _, region in region_summary.iterrows():
        sample_size = max(200, int(round(region["population_total"] / 5000)))
        region_month_weights = MONTH_FACTORS / MONTH_FACTORS.sum()
        months = RNG.choice(np.arange(1, 13), size=sample_size, p=region_month_weights)
        raw_cities = city_lookup.get(region["region_id"], [region["city_name_ar"]])
        capital_city = region["city_name_ar"]
        deduped_cities = [capital_city] + [city for city in raw_cities if city != capital_city]
        cities_for_region = deduped_cities[:6]
        if len(cities_for_region) == 1:
            city_weights = np.array([1.0], dtype=float)
        else:
            city_weights = np.array([0.55] + list(np.linspace(0.24, 0.06, num=len(cities_for_region) - 1)), dtype=float)
        city_weights = city_weights / city_weights.sum()
        chosen_cities = RNG.choice(cities_for_region, size=sample_size, p=city_weights)

        disease_shift = _normalize_scale(pd.Series(region_summary["diabetic_visits_per_100k"], index=region_summary["region_id"]))[
            region["region_id"]
        ]
        for month_value, city_name in zip(months, chosen_cities, strict=False):
            date = pd.Timestamp(year=2024, month=int(month_value), day=int(RNG.integers(1, 28)))
            age_group = RNG.choice(["18-29", "30-44", "45-59", "60+"], p=[0.29, 0.34, 0.24, 0.13])
            gender = RNG.choice(["ذكر", "أنثى"], p=[0.51, 0.49])
            bmi_value = _clip_round(25.2 + region["risk_prediction_score"] * 0.05 + RNG.normal(0, 3.4), 18, 44)
            diabetes_risk = _clip_round(region["risk_prediction_score"] + disease_shift * 12 + RNG.normal(0, 7), 14, 96)
            hypertension_risk = _clip_round(region["risk_prediction_score"] + 3 + RNG.normal(0, 8), 16, 97)
            obesity_risk = _clip_round(region["risk_prediction_score"] - 2 + RNG.normal(0, 8), 12, 96)
            asthma_risk = _clip_round(region["risk_prediction_score"] - 10 + RNG.normal(0, 9), 8, 90)
            risk_prediction_score = _clip_round(np.mean([diabetes_risk, hypertension_risk, obesity_risk, asthma_risk]), 16, 97)
            satisfaction_mean = region["doctor_time_satisfaction_pct"] / 20
            satisfaction_score = int(np.clip(round(RNG.normal(satisfaction_mean, 0.55)), 1, 5))
            community_pulse = _clip_round(region["community_pulse_index"] * MONTH_FACTORS[int(month_value) - 1] + RNG.normal(0, 3.5), 38, 96)
            waiting_time = _clip_round(region["avg_waiting_time_minutes"] / MONTH_FACTORS[int(month_value) - 1] + RNG.normal(0, 3.2), 6, 75)
            disease_scores = {
                "السكري": diabetes_risk,
                "ارتفاع الضغط": hypertension_risk,
                "الربو": asthma_risk,
                "السمنة": obesity_risk,
            }
            predicted_disease = max(disease_scores, key=disease_scores.get)
            rows.append(
                {
                    "response_id": f"RES-{response_counter}",
                    "response_date": date,
                    "region_id": region["region_id"],
                    "province_ar": region["province_name_ar"],
                    "city_ar": city_name,
                    "gender": gender,
                    "age_group": age_group,
                    "bmi_value": bmi_value,
                    "smoking_status": RNG.choice(["غير مدخن", "مدخن سابق", "مدخن حالي"], p=[0.64, 0.14, 0.22]),
                    "activity_level": RNG.choice(["مرتفع", "متوسط", "منخفض"], p=[0.27, 0.46, 0.27]),
                    "has_chronic": "نعم" if risk_prediction_score >= 67 else "لا",
                    "family_history": RNG.choice(["لا يوجد", "سكري", "ضغط", "ربو", "سمنة"], p=[0.29, 0.24, 0.21, 0.11, 0.15]),
                    "satisfaction_score": satisfaction_score,
                    "qol_score": int(np.clip(round(RNG.normal(4.6 - risk_prediction_score / 28, 0.5)), 1, 5)),
                    "community_pulse_index": community_pulse,
                    "risk_prediction_score": risk_prediction_score,
                    "diabetes_risk_score": diabetes_risk,
                    "hypertension_risk_score": hypertension_risk,
                    "asthma_risk_score": asthma_risk,
                    "obesity_risk_score": obesity_risk,
                    "predicted_disease_ar": predicted_disease,
                    "air_quality_index": _clip_round(38 + asthma_risk * 0.4 + RNG.normal(0, 8), 12, 96),
                    "humidity_index": _clip_round(22 + RNG.normal(0, 10), 5, 78),
                    "waiting_time_minutes": waiting_time,
                    "facility_pressure_score": _clip_round(32 + risk_prediction_score * 0.52 + RNG.normal(0, 7), 15, 98),
                }
            )
            response_counter += 1

    return pd.DataFrame(rows).sort_values("response_date").reset_index(drop=True)


def build_monthly_summary(survey: pd.DataFrame) -> pd.DataFrame:
    summary = survey.copy()
    summary["period_month"] = summary["response_date"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        summary.groupby(["period_month", "region_id", "province_ar"], dropna=False)
        .agg(
            community_pulse_index=("community_pulse_index", "mean"),
            satisfaction_rate=("satisfaction_score", lambda values: pd.to_numeric(values, errors="coerce").mean() / 5),
            avg_waiting_time=("waiting_time_minutes", "mean"),
            chronic_cases_rate=("has_chronic", lambda values: (pd.Series(values) == "نعم").mean()),
            complaints_count=("response_id", "count"),
        )
        .reset_index()
        .sort_values(["region_id", "period_month"])
    )
    monthly["complaints_count"] = (monthly["complaints_count"] * (0.14 + monthly["avg_waiting_time"] / 160)).round().astype(int)
    monthly["trend_delta"] = monthly.groupby("region_id")["community_pulse_index"].diff().fillna(0)
    monthly["trend"] = np.where(monthly["trend_delta"] >= 0, "Up", "Down")
    monthly["risk_level"] = pd.cut(
        monthly["chronic_cases_rate"],
        bins=[-1, 0.22, 0.30, 1],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    monthly["forecast_next_month"] = (
        monthly["community_pulse_index"] + monthly.groupby("region_id")["trend_delta"].shift(1).fillna(0) * 0.6
    ).round(1)
    return monthly.drop(columns=["trend_delta"])


def build_complaints(monthly_summary: pd.DataFrame, cities: pd.DataFrame) -> pd.DataFrame:
    cities = cities.copy()
    cities["region_id"] = cities["region_id"].map(lambda value: f"R-{int(value):02d}")
    city_lookup = cities.groupby("region_id")["name_ar"].apply(list).to_dict()
    rows = []
    case_counter = 2000
    for _, monthly in monthly_summary.iterrows():
        case_count = max(int(monthly["complaints_count"]), 4)
        cities_for_region = city_lookup.get(monthly["region_id"], [monthly["province_ar"]])
        for _ in range(case_count):
            rows.append(
                {
                    "case_id": f"C-{case_counter}",
                    "date": pd.Timestamp(monthly["period_month"]) + pd.Timedelta(days=int(RNG.integers(0, 28))),
                    "region_id": monthly["region_id"],
                    "city_ar": RNG.choice(cities_for_region),
                    "type": RNG.choice(["شكوى", "ملاحظة", "اقتراح"], p=[0.63, 0.24, 0.13]),
                    "priority": RNG.choice(["منخفضة", "متوسطة", "عالية"], p=[0.28, 0.49, 0.23]),
                    "status": RNG.choice(["مغلقة", "قيد المعالجة", "جديدة"], p=[0.57, 0.26, 0.17]),
                    "resolution_days": _clip_round(RNG.normal(4.7 + monthly["avg_waiting_time"] / 20, 2.6), 1, 22),
                    "category": RNG.choice(["المواعيد", "الأدوية", "الخدمة", "الانتظار", "التواصل"], p=[0.22, 0.16, 0.26, 0.23, 0.13]),
                }
            )
            case_counter += 1
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def build_initiatives(region_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    categories = ["السكري", "ارتفاع الضغط", "الرعاية الوقائية", "الصحة الرقمية", "الفحص المبكر"]
    for index, row in region_summary.iterrows():
        target = int(row["population_total"] * (0.038 + row["chronic_cases_rate"] * 0.12))
        actual = int(target * (0.82 + (row["community_pulse_index"] - 60) / 250))
        rows.append(
            {
                "initiative_id": f"INIT-{index + 1:03d}",
                "initiative_name_ar": f"مبادرة صحة المجتمع - {row['province_name_ar']}",
                "initiative_category": categories[index % len(categories)],
                "region_id": row["region_id"],
                "province_ar": row["province_name_ar"],
                "target_beneficiaries_count": target,
                "actual_beneficiaries_count": max(actual, 0),
                "initiative_status": "مستمرة" if index % 3 != 2 else "مجدولة",
                "impact_score": _clip_round(3.6 + row["community_pulse_index"] / 45, 3.2, 4.9, 2),
                "awareness_increase_pct": _clip_round(0.48 + row["internet_health_info_pct"] / 240, 0.45, 0.92, 2),
            }
        )
    return pd.DataFrame(rows)


def build_forecasting_data(region_summary: pd.DataFrame) -> pd.DataFrame:
    focus = region_summary[region_summary["region_id"].isin(["R-04", "R-06"])].copy()
    actual_rows = []
    for year in range(2020, 2025):
        total_value = pd.to_numeric(focus[f"phc_{year}"], errors="coerce").sum() + pd.to_numeric(
            focus[f"opd_{year}"], errors="coerce"
        ).sum()
        actual_rows.append({"year": year, "value": float(total_value)})

    history = pd.DataFrame(actual_rows)
    coefficients = np.polyfit(history["year"], history["value"], deg=1)
    trend = np.poly1d(coefficients)
    residuals = history["value"] - trend(history["year"])
    error_band = max(float(np.std(residuals, ddof=0) * 1.2), history["value"].mean() * 0.03)

    rows = []
    for _, row in history.iterrows():
        rows.append(
            {
                "indicator": "الطلب الصحي السنوي المركب - عسير والقصيم",
                "month": pd.Timestamp(year=int(row["year"]), month=1, day=1),
                "actual": round(row["value"], 1),
                "forecast": None,
                "lower_bound": None,
                "upper_bound": None,
            }
        )

    for year in [2025, 2026]:
        forecast_value = float(trend(year))
        rows.append(
            {
                "indicator": "الطلب الصحي السنوي المركب - عسير والقصيم",
                "month": pd.Timestamp(year=year, month=1, day=1),
                "actual": None,
                "forecast": round(forecast_value, 1),
                "lower_bound": round(forecast_value - error_band, 1),
                "upper_bound": round(forecast_value + error_band, 1),
            }
        )

    return pd.DataFrame(rows)


def build_targets(monthly_summary: pd.DataFrame, region_summary: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "kpi_id": "KPI-01",
                "kpi_name_ar": "مؤشر نبض المجتمع",
                "kpi_name_en": "Community Pulse Index",
                "target_value": 85,
                "current_value": round(float(monthly_summary["community_pulse_index"].mean()), 1),
                "measurement_unit": "Index",
                "vision_2030_alignment": "تحسين جودة الحياة",
            },
            {
                "kpi_id": "KPI-02",
                "kpi_name_ar": "نسبة الرضا",
                "kpi_name_en": "Satisfaction Rate",
                "target_value": 88,
                "current_value": round(float(monthly_summary["satisfaction_rate"].mean() * 100), 1),
                "measurement_unit": "Percentage",
                "vision_2030_alignment": "رفع رضا المستفيد",
            },
            {
                "kpi_id": "KPI-03",
                "kpi_name_ar": "متوسط وقت الانتظار",
                "kpi_name_en": "Average Waiting Time",
                "target_value": 18,
                "current_value": round(float(monthly_summary["avg_waiting_time"].mean()), 1),
                "measurement_unit": "Minutes",
                "vision_2030_alignment": "كفاءة الخدمة الصحية",
            },
            {
                "kpi_id": "KPI-04",
                "kpi_name_ar": "المناطق عالية الخطورة",
                "kpi_name_en": "High Risk Areas",
                "target_value": 2,
                "current_value": int((region_summary["risk_prediction_score"] >= 78).sum()),
                "measurement_unit": "Count",
                "vision_2030_alignment": "الوقاية المبكرة",
            },
        ]
    )


def build_lookup() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["initiative_status", "مستمرة", "المبادرة قيد التنفيذ", "Ongoing"],
            ["initiative_status", "مجدولة", "المبادرة في مرحلة التحضير", "Scheduled"],
            ["risk_level", "عالي", "مستوى خطورة مرتفع", "High risk"],
            ["risk_level", "متوسط", "مستوى خطورة متوسط", "Medium risk"],
            ["risk_level", "منخفض", "مستوى خطورة منخفض", "Low risk"],
            ["source_type", "رسمي مباشر", "بيانات من جداول حكومية منشورة", "Direct official data"],
            ["source_type", "مشتق حسابياً", "مؤشر مركب أو توزيع مولد من البيانات الرسمية", "Derived from official data"],
        ],
        columns=["field_name", "allowed_value", "value_description_ar", "value_description_en"],
    )


def build_dictionary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["regions_master", "population_total", "Integer", "عدد السكان المشتق من الجداول الرسمية لعام 2024", "Official 2024 population derived from official healthcare rate tables"],
            ["health_facilities", "facility_count", "Integer", "إجمالي المنشآت أو السعات الصحية الرسمية المرتبطة بالسجل", "Official facility count attached to the record"],
            ["monthly_kpi_summary", "community_pulse_index", "Float", "مؤشر مركب مشتق من الرضا والوصول والقدرة الصحية الإقليمية", "Derived composite from access, satisfaction, and regional health capacity"],
            ["survey_responses_simulated", "risk_prediction_score", "Float", "مخاطر مزمنة مشتقة من مؤشرات رسمية مع توزيع تمثيلي على مستوى السجل", "Chronic risk score modeled from official indicators with representative row-level distribution"],
            ["forecasting_data", "forecast", "Float", "توقع للطلب الصحي السنوي المركب لعسير والقصيم", "Forecast for combined annual health demand in Asir and Qassim"],
            ["data_dictionary", "description_ar", "Text", "شرح الحقل بالعربية", "Arabic field description"],
        ],
        columns=["sheet_name", "column_name", "data_type", "description_ar", "description_en"],
    )


def build_source_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artifact_name": "official_region_summary_2024.csv",
                "source_type": "رسمي مباشر + مشتق حسابياً",
                "source_files": "moh_statistical_yearbook_2024.xlsx; gastat_healthcare_establishments_workforce_2024_en.xlsx; gastat_healthcare_statistics_publication_2024_en.xlsx",
                "primary_focus": "السعودية كاملة مع التركيز على عسير والقصيم",
                "notes": "يجمع البنية الصحية والوصول والرضا واستغلال الخدمة، ثم يضيف مؤشرات مركبة مشتقة",
            },
            {
                "artifact_name": "qassim_governorate_population_detail.csv",
                "source_type": "رسمي مباشر",
                "source_files": "gastat_qassim_detailed_results.pdf",
                "primary_focus": "تفصيل محافظات القصيم",
                "notes": "سكان القصيم حسب المحافظة والجنس والجنسية",
            },
            {
                "artifact_name": "asir_cluster_detail_2024.csv",
                "source_type": "رسمي مباشر",
                "source_files": "moh_statistical_yearbook_2024.xlsx",
                "primary_focus": "تفصيل عسير الداخلي",
                "notes": "مقارنة تجمع عسير وتجمع بيشة في المرافق والأسرة وزيارات عيادات السكري",
            },
            {
                "artifact_name": "asir_qassim_workforce_2024.csv",
                "source_type": "رسمي مباشر",
                "source_files": "moh_statistical_yearbook_2024.xlsx",
                "primary_focus": "القوى العاملة لعسير والقصيم",
                "notes": "يشمل أطباء وتمريض وصيادلة وفئات مساعدة في وزارة الصحة وكافة القطاعات",
            },
            {
                "artifact_name": "official_google_sheets_seed.xlsx",
                "source_type": "رسمي مباشر + مشتق حسابياً",
                "source_files": "جميع الملفات أعلاه",
                "primary_focus": "تغذية التطبيق ورفعها إلى Google Sheets",
                "notes": "بعض الجداول داخل Seed تمثيلية لكنها معايرة على الأساس الرسمي الإقليمي",
            },
        ]
    )


def build_workbook() -> None:
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    regions_ref, cities = load_region_reference()
    region_summary = build_official_region_summary()
    survey = build_survey(region_summary, cities)
    monthly_summary = build_monthly_summary(survey)
    health_facilities = build_health_facilities(region_summary)
    complaints = build_complaints(monthly_summary, cities)
    initiatives = build_initiatives(region_summary)
    forecasting = build_forecasting_data(region_summary)
    targets = build_targets(monthly_summary, region_summary)
    lookup = build_lookup()
    dictionary = build_dictionary()

    qassim_detail = build_qassim_governorate_detail()
    asir_detail = build_asir_cluster_detail()
    workforce_detail = build_asir_qassim_workforce_detail()
    source_catalog = build_source_catalog()

    regions_master = region_summary.merge(
        regions_ref[["region_id", "geo_region_id"]],
        on="region_id",
        how="left",
        suffixes=("", "_ref"),
    )[
        [
            "region_id",
            "region_name_ar",
            "region_name_en",
            "province_name_ar",
            "city_name_ar",
            "population_total",
            "latitude",
            "longitude",
            "priority_level",
            "geo_region_id",
        ]
    ].copy()
    clean_regions_master = regions_master.copy()

    workbook_tables = {
        "clean_regions_master": clean_regions_master,
        "regions_master": regions_master,
        "survey_responses_simulated": survey,
        "health_facilities": health_facilities,
        "monthly_kpi_summary": monthly_summary,
        "complaints_feedback": complaints,
        "initiatives_programs": initiatives,
        "forecasting_data": forecasting,
        "targets_benchmarks": targets,
        "lookup_definitions": lookup,
        "data_dictionary": dictionary,
        "official_region_summary": region_summary,
        "qassim_governorates": qassim_detail,
        "asir_clusters": asir_detail,
        "workforce_regional": workforce_detail,
        "source_catalog": source_catalog,
    }

    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        for sheet_name, frame in workbook_tables.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            frame.to_csv(CSV_DIR / f"{sheet_name}.csv", index=False, encoding="utf-8-sig")

    region_summary.to_csv(CURATED_DIR / "official_region_summary_2024.csv", index=False, encoding="utf-8-sig")
    qassim_detail.to_csv(CURATED_DIR / "qassim_governorate_population_detail.csv", index=False, encoding="utf-8-sig")
    asir_detail.to_csv(CURATED_DIR / "asir_cluster_detail_2024.csv", index=False, encoding="utf-8-sig")
    workforce_detail.to_csv(CURATED_DIR / "asir_qassim_workforce_2024.csv", index=False, encoding="utf-8-sig")
    source_catalog.to_csv(CURATED_DIR / "official_sources_catalog.csv", index=False, encoding="utf-8-sig")

    print(f"Official seed workbook created at: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_workbook()
