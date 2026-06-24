from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_PATH = DATA_DIR / "synthetic_google_sheets_demo.xlsx"
CSV_DIR = DATA_DIR / "synthetic_google_sheet_tabs"
RNG = np.random.default_rng(2030)


def _load_reference_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    regions_path = DATA_DIR / "saudi_regions.csv"
    cities_path = DATA_DIR / "saudi_cities_lite.csv"

    if not regions_path.is_file() or not cities_path.is_file():
        raise FileNotFoundError(
            "Reference CSV files are missing. Expected data/saudi_regions.csv and data/saudi_cities_lite.csv."
        )

    regions = pd.read_csv(regions_path)
    cities = pd.read_csv(cities_path)
    return regions, cities


def _prepare_regions(regions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    regions = regions.copy()
    regions["region_id"] = regions["region_id"].map(lambda value: f"R-{int(value):02d}")
    regions["region_name_ar"] = regions["name_ar"]
    regions["region_name_en"] = regions["name_en"]
    regions["province_name_ar"] = regions["name_ar"].str.replace("منطقة ", "", regex=False)
    regions["population_total"] = regions["population"]
    regions["latitude"] = pd.to_numeric(regions["center_lat"], errors="coerce")
    regions["longitude"] = pd.to_numeric(regions["center_lon"], errors="coerce")
    regions["priority_level"] = pd.cut(
        regions["population_total"],
        bins=[0, 1200000, 3000000, 10000000],
        labels=["منخفضة", "متوسطة", "مرتفعة"],
    ).astype(str)
    regions["city_name_ar"] = regions["province_name_ar"]
    regions["geo_region_id"] = regions["region_id"]

    master_columns = [
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
    regions_master = regions[master_columns].copy()
    clean_regions_master = regions_master.copy()
    return regions_master, clean_regions_master


def _prepare_cities(cities: pd.DataFrame, regions_master: pd.DataFrame) -> pd.DataFrame:
    cities = cities.copy()
    cities["region_id"] = cities["region_id"].map(lambda value: f"R-{int(value):02d}")
    cities = cities.merge(
        regions_master[["region_id", "province_name_ar", "latitude", "longitude"]],
        on="region_id",
        how="left",
    )
    city_counts = cities.groupby("region_id")["city_id"].transform("count")
    city_order = cities.groupby("region_id").cumcount() - (city_counts - 1) / 2
    cities["latitude"] = cities["latitude"] + city_order * 0.11
    cities["longitude"] = cities["longitude"] + city_order * 0.13
    return cities


def _weighted_pick(options: list[str], weights: list[float], size: int) -> np.ndarray:
    normalized = np.array(weights, dtype=float)
    normalized = normalized / normalized.sum()
    return RNG.choice(options, size=size, p=normalized)


def _build_survey(cities: pd.DataFrame, regions_master: pd.DataFrame, size: int = 12000) -> pd.DataFrame:
    city_weights = regions_master.set_index("region_id")["population_total"]
    city_lookup = cities["region_id"].map(city_weights).fillna(city_weights.mean())
    city_prob = city_lookup / city_lookup.sum()
    selected_indices = RNG.choice(cities.index.to_numpy(), size=size, p=city_prob.to_numpy())
    chosen_cities = cities.loc[selected_indices].reset_index(drop=True)

    start_date = np.datetime64("2024-01-01")
    end_date = np.datetime64("2026-06-01")
    date_offsets = RNG.integers(0, int((end_date - start_date).astype(int)), size=size)
    response_dates = start_date + date_offsets.astype("timedelta64[D]")

    genders = _weighted_pick(["ذكر", "أنثى"], [0.52, 0.48], size)
    age_groups = _weighted_pick(["18-29", "30-44", "45-59", "60+"], [0.28, 0.34, 0.24, 0.14], size)
    smoking = _weighted_pick(["غير مدخن", "مدخن سابق", "مدخن حالي"], [0.63, 0.14, 0.23], size)
    activity = _weighted_pick(
        ["مرتفع (5 أيام+)", "متوسط (3 أيام)", "منخفض (يومين أو أقل)"],
        [0.25, 0.43, 0.32],
        size,
    )
    family_history = _weighted_pick(["لا يوجد", "سكري", "ضغط", "ربو", "سمنة"], [0.26, 0.24, 0.22, 0.12, 0.16], size)

    age_midpoint = pd.Series(age_groups).map({"18-29": 24, "30-44": 37, "45-59": 52, "60+": 66}).to_numpy()
    bmi = np.clip(RNG.normal(28.7, 5.8, size), 18.0, 45.0)
    smoker_factor = pd.Series(smoking).map({"غير مدخن": 0, "مدخن سابق": 6, "مدخن حالي": 12}).to_numpy()
    activity_factor = pd.Series(activity).map({"مرتفع (5 أيام+)": -10, "متوسط (3 أيام)": -2, "منخفض (يومين أو أقل)": 8}).to_numpy()
    family_factor = pd.Series(family_history).map({"لا يوجد": 0, "سكري": 12, "ضغط": 10, "ربو": 8, "سمنة": 9}).to_numpy()

    diabetes_risk = np.clip(18 + (age_midpoint - 20) * 0.78 + (bmi - 22) * 1.7 + smoker_factor * 0.45 + family_factor, 5, 98)
    hypertension_risk = np.clip(16 + (age_midpoint - 18) * 0.88 + (bmi - 21) * 1.25 + smoker_factor * 0.6 + family_factor * 0.75, 4, 99)
    asthma_risk = np.clip(14 + RNG.normal(0, 7, size) + smoker_factor * 0.7 + np.maximum(0, 36 - age_midpoint) * 0.25, 3, 95)
    obesity_risk = np.clip(12 + (bmi - 20) * 3.1 + activity_factor * 1.2 + family_factor * 0.4, 5, 99)

    risk_matrix = np.vstack([diabetes_risk, hypertension_risk, asthma_risk, obesity_risk]).T
    disease_labels = np.array(["السكري", "ارتفاع الضغط", "الربو", "السمنة"])
    predicted_disease = disease_labels[risk_matrix.argmax(axis=1)]
    overall_risk = np.clip(risk_matrix.mean(axis=1) + RNG.normal(0, 4, size), 5, 99)
    has_chronic = np.where(overall_risk >= 60, "نعم", "لا")

    satisfaction = np.clip(5 - overall_risk / 28 + RNG.normal(0, 0.45, size), 1, 5).round()
    qol_score = np.clip(5 - overall_risk / 30 + RNG.normal(0, 0.5, size), 1, 5).round()
    pulse_index = np.clip(96 - overall_risk * 0.42 + satisfaction * 3.1 + RNG.normal(0, 4, size), 35, 96)
    waiting_minutes = np.clip(14 + overall_risk * 0.32 + RNG.normal(0, 6, size), 6, 85)
    air_quality = np.clip(48 + RNG.normal(0, 18, size) + (predicted_disease == "الربو") * 12, 15, 95)
    humidity = np.clip(32 + RNG.normal(0, 14, size), 8, 78)
    facility_pressure = np.clip(35 + overall_risk * 0.4 + RNG.normal(0, 8, size), 12, 98)

    survey = pd.DataFrame(
        {
            "response_id": [f"RES-{100000 + index}" for index in range(size)],
            "response_date": pd.to_datetime(response_dates),
            "region_id": chosen_cities["region_id"].to_numpy(),
            "province_ar": chosen_cities["province_name_ar"].to_numpy(),
            "city_ar": chosen_cities["name_ar"].to_numpy(),
            "gender": genders,
            "age_group": age_groups,
            "bmi_value": bmi.round(1),
            "smoking_status": smoking,
            "activity_level": activity,
            "has_chronic": has_chronic,
            "family_history": family_history,
            "satisfaction_score": satisfaction.astype(int),
            "qol_score": qol_score.astype(int),
            "community_pulse_index": pulse_index.round(1),
            "risk_prediction_score": overall_risk.round(1),
            "diabetes_risk_score": diabetes_risk.round(1),
            "hypertension_risk_score": hypertension_risk.round(1),
            "asthma_risk_score": asthma_risk.round(1),
            "obesity_risk_score": obesity_risk.round(1),
            "predicted_disease_ar": predicted_disease,
            "air_quality_index": air_quality.round(1),
            "humidity_index": humidity.round(1),
            "waiting_time_minutes": waiting_minutes.round(1),
            "facility_pressure_score": facility_pressure.round(1),
        }
    )
    return survey.sort_values("response_date").reset_index(drop=True)


def _build_monthly_summary(survey: pd.DataFrame) -> pd.DataFrame:
    monthly = survey.copy()
    monthly["period_month"] = monthly["response_date"].dt.to_period("M").dt.to_timestamp()
    summary = (
        monthly.groupby(["period_month", "region_id", "province_ar"], dropna=False)
        .agg(
            community_pulse_index=("community_pulse_index", "mean"),
            satisfaction_rate=("satisfaction_score", lambda series: series.mean() / 5),
            avg_waiting_time=("waiting_time_minutes", "mean"),
            chronic_cases_rate=("has_chronic", lambda series: (series == "نعم").mean()),
            complaints_count=("response_id", "count"),
        )
        .reset_index()
    )
    summary["risk_level"] = pd.cut(
        100 - summary["community_pulse_index"],
        bins=[-1, 20, 35, 100],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    summary["trend"] = summary.groupby("region_id")["community_pulse_index"].diff().fillna(0).map(
        lambda value: "Up" if value >= 0 else "Down"
    )
    summary["forecast_next_month"] = summary["community_pulse_index"] + RNG.normal(1.2, 2.0, len(summary))
    return summary.sort_values(["period_month", "region_id"]).reset_index(drop=True)


def _build_facilities(regions_master: pd.DataFrame) -> pd.DataFrame:
    facility_types = ["مستشفى عام", "مستشفى تخصصي", "مركز رعاية أولية"]
    rows = []
    facility_id = 1
    for _, row in regions_master.iterrows():
        facility_count = 5 if row["population_total"] > 3000000 else 4
        for index in range(facility_count):
            rows.append(
                {
                    "facility_id": f"F-{facility_id:03d}",
                    "name_ar": f"{facility_types[index % len(facility_types)]} {row['province_name_ar']} {index + 1}",
                    "type": facility_types[index % len(facility_types)],
                    "region_id": row["region_id"],
                    "province_ar": row["province_name_ar"],
                    "readiness_score": round(float(np.clip(RNG.normal(0.84, 0.08), 0.58, 0.98)), 2),
                    "beds_occupied_pct": round(float(np.clip(RNG.normal(0.67, 0.12), 0.24, 0.96)), 2),
                    "doctors_count": int(np.clip(RNG.normal(70, 22), 18, 180)),
                }
            )
            facility_id += 1
    return pd.DataFrame(rows)


def _build_complaints(cities: pd.DataFrame, size: int = 950) -> pd.DataFrame:
    selected_indices = RNG.choice(cities.index.to_numpy(), size=size)
    chosen_cities = cities.loc[selected_indices].reset_index(drop=True)
    dates = pd.to_datetime("2024-01-01") + pd.to_timedelta(RNG.integers(0, 900, size), unit="D")
    priorities = _weighted_pick(["منخفضة", "متوسطة", "عالية"], [0.28, 0.48, 0.24], size)
    statuses = _weighted_pick(["مغلقة", "قيد المعالجة", "جديدة"], [0.54, 0.28, 0.18], size)
    complaint_types = _weighted_pick(["شكوى", "ملاحظة", "اقتراح"], [0.58, 0.24, 0.18], size)
    resolution = np.clip(RNG.normal(5, 3.4, size), 1, 22)
    resolution = np.where(statuses == "جديدة", np.nan, resolution)
    categories = _weighted_pick(["المواعيد", "الأدوية", "الخدمة", "النظافة", "الانتظار"], [0.2, 0.18, 0.28, 0.12, 0.22], size)

    return pd.DataFrame(
        {
            "case_id": [f"C-{1000 + index}" for index in range(size)],
            "date": dates,
            "region_id": chosen_cities["region_id"].to_numpy(),
            "city_ar": chosen_cities["name_ar"].to_numpy(),
            "type": complaint_types,
            "priority": priorities,
            "status": statuses,
            "resolution_days": np.round(resolution, 1),
            "category": categories,
        }
    ).sort_values("date")


def _build_initiatives(regions_master: pd.DataFrame) -> pd.DataFrame:
    categories = [
        "السكري",
        "ارتفاع الضغط",
        "الربو والحساسية",
        "التغذية والنشاط البدني",
        "الفحص المبكر",
    ]
    statuses = ["مستمرة", "مكتملة", "مجدولة"]
    rows = []
    for idx, (_, row) in enumerate(regions_master.iterrows(), start=1):
        target = int(row["population_total"] * RNG.uniform(0.06, 0.16))
        actual = int(target * RNG.uniform(0.78, 1.08))
        rows.append(
            {
                "initiative_id": f"INIT-{idx:03d}",
                "initiative_name_ar": f"مبادرة صحة المجتمع - {row['province_name_ar']}",
                "initiative_category": categories[idx % len(categories)],
                "region_id": row["region_id"],
                "province_ar": row["province_name_ar"],
                "target_beneficiaries_count": target,
                "actual_beneficiaries_count": actual,
                "initiative_status": statuses[idx % len(statuses)],
                "impact_score": round(float(np.clip(RNG.normal(4.2, 0.35), 3.4, 4.9)), 2),
                "awareness_increase_pct": round(float(np.clip(RNG.normal(0.72, 0.1), 0.48, 0.94)), 2),
            }
        )
    return pd.DataFrame(rows)


def _build_forecasting(monthly_summary: pd.DataFrame) -> pd.DataFrame:
    indicator_map = {
        "السكري": "diabetes_risk_score",
        "ارتفاع الضغط": "hypertension_risk_score",
        "الربو": "asthma_risk_score",
        "السمنة": "obesity_risk_score",
    }
    forecast_rows = []
    future_months = pd.date_range("2026-07-01", periods=6, freq="MS")
    for indicator, base_column in indicator_map.items():
        for month in future_months:
            baseline = monthly_summary["community_pulse_index"].mean() if base_column not in monthly_summary else monthly_summary[base_column].mean()
            actual = np.nan
            forecast = np.clip(62 + RNG.normal(0, 5), 40, 95) if indicator != "السمنة" else np.clip(58 + RNG.normal(0, 4), 38, 88)
            spread = np.clip(RNG.normal(7, 1.5), 4, 11)
            forecast_rows.append(
                {
                    "indicator": indicator,
                    "month": month,
                    "actual": actual,
                    "forecast": round(float(forecast), 1),
                    "lower_bound": round(float(forecast - spread), 1),
                    "upper_bound": round(float(forecast + spread), 1),
                }
            )
    return pd.DataFrame(forecast_rows)


def _build_targets(monthly_summary: pd.DataFrame) -> pd.DataFrame:
    pulse_current = monthly_summary["community_pulse_index"].mean()
    satisfaction_current = monthly_summary["satisfaction_rate"].mean()
    waiting_current = monthly_summary["avg_waiting_time"].mean()
    chronic_current = monthly_summary["chronic_cases_rate"].mean() * 100
    return pd.DataFrame(
        [
            {
                "kpi_id": "KPI-01",
                "kpi_name_ar": "مؤشر نبض المجتمع",
                "kpi_name_en": "Community Pulse Index",
                "target_value": 88,
                "current_value": round(float(pulse_current), 1),
                "measurement_unit": "Index (1-100)",
                "vision_2030_alignment": "تحسين جودة الحياة",
            },
            {
                "kpi_id": "KPI-02",
                "kpi_name_ar": "نسبة الرضا",
                "kpi_name_en": "Satisfaction Rate",
                "target_value": 90,
                "current_value": round(float(satisfaction_current), 1),
                "measurement_unit": "Percentage",
                "vision_2030_alignment": "رفع جودة الخدمات الصحية",
            },
            {
                "kpi_id": "KPI-03",
                "kpi_name_ar": "متوسط وقت الانتظار",
                "kpi_name_en": "Average Waiting Time",
                "target_value": 18,
                "current_value": round(float(waiting_current), 1),
                "measurement_unit": "Minutes",
                "vision_2030_alignment": "تحسين تجربة المستفيد",
            },
            {
                "kpi_id": "KPI-04",
                "kpi_name_ar": "معدل الحالات المزمنة عالية الخطورة",
                "kpi_name_en": "High Risk Chronic Cases Rate",
                "target_value": 22,
                "current_value": round(float(chronic_current), 1),
                "measurement_unit": "Percentage",
                "vision_2030_alignment": "الوقاية المبكرة",
            },
        ]
    )


def _build_lookup() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["initiative_status", "مستمرة", "المبادرة قيد التنفيذ حالياً", "Ongoing"],
            ["initiative_status", "مكتملة", "تم تنفيذ المبادرة وإغلاقها", "Completed"],
            ["initiative_status", "مجدولة", "مبادرة مجدولة للإطلاق", "Scheduled"],
            ["risk_level", "عالي", "مستوى خطر مرتفع", "High risk"],
            ["risk_level", "متوسط", "مستوى خطر متوسط", "Medium risk"],
            ["risk_level", "منخفض", "مستوى خطر منخفض", "Low risk"],
        ],
        columns=["field_name", "allowed_value", "value_description_ar", "value_description_en"],
    )


def _build_dictionary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["survey_responses_simulated", "predicted_disease_ar", "Text", "المرض المزمن المرجح لكل مشارك", "Predicted chronic disease"],
            ["survey_responses_simulated", "risk_prediction_score", "Float", "درجة المخاطر العامة من 100", "Overall risk score out of 100"],
            ["monthly_kpi_summary", "avg_waiting_time", "Float", "متوسط وقت الانتظار الشهري", "Average monthly waiting time"],
            ["forecasting_data", "forecast", "Float", "القيمة المتوقعة للمؤشر المستقبلي", "Forecast value"],
        ],
        columns=["sheet_name", "column_name", "data_type", "description_ar", "description_en"],
    )


def build_workbook() -> None:
    regions, cities = _load_reference_data()
    regions_master, clean_regions_master = _prepare_regions(regions)
    prepared_cities = _prepare_cities(cities, regions_master)
    survey = _build_survey(prepared_cities, regions_master)
    monthly_summary = _build_monthly_summary(survey)
    facilities = _build_facilities(regions_master)
    complaints = _build_complaints(prepared_cities)
    initiatives = _build_initiatives(regions_master)
    forecasting = _build_forecasting(monthly_summary)
    targets = _build_targets(monthly_summary)
    lookup = _build_lookup()
    dictionary = _build_dictionary()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    tables = {
        "clean_regions_master": clean_regions_master,
        "regions_master": regions_master,
        "survey_responses_simulated": survey,
        "health_facilities": facilities,
        "monthly_kpi_summary": monthly_summary,
        "complaints_feedback": complaints,
        "initiatives_programs": initiatives,
        "forecasting_data": forecasting,
        "targets_benchmarks": targets,
        "lookup_definitions": lookup,
        "data_dictionary": dictionary,
    }

    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        for sheet_name, frame in tables.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            frame.to_csv(CSV_DIR / f"{sheet_name}.csv", index=False, encoding="utf-8-sig")

    print(f"Synthetic workbook created at: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_workbook()
