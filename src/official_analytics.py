from __future__ import annotations

import pandas as pd


FOCUS_REGION_IDS = ["R-06", "R-04"]
FOCUS_REGION_LABELS = {"R-06": "عسير", "R-04": "القصيم"}


def get_region_summary(filtered_data: dict) -> pd.DataFrame:
    return filtered_data["tables"].get("official_region_summary", pd.DataFrame()).copy()


def get_qassim_governorates(filtered_data: dict) -> pd.DataFrame:
    return filtered_data["tables"].get("qassim_governorates", pd.DataFrame()).copy()


def get_asir_clusters(filtered_data: dict) -> pd.DataFrame:
    return filtered_data["tables"].get("asir_clusters", pd.DataFrame()).copy()


def get_workforce_regional(filtered_data: dict) -> pd.DataFrame:
    return filtered_data["tables"].get("workforce_regional", pd.DataFrame()).copy()


def _weighted_average(frame: pd.DataFrame, column: str, weight_column: str = "population_total") -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    values = pd.to_numeric(frame[column], errors="coerce")
    weights = pd.to_numeric(frame.get(weight_column), errors="coerce")
    valid = values.notna() & weights.notna() & weights.gt(0)
    if not valid.any():
        return None
    return float((values[valid] * weights[valid]).sum() / weights[valid].sum())


def build_national_summary(region_summary: pd.DataFrame) -> pd.DataFrame:
    if region_summary.empty:
        return pd.DataFrame()

    total_population = pd.to_numeric(region_summary["population_total"], errors="coerce").sum()
    hospitals_total = pd.to_numeric(region_summary.get("hospitals_total"), errors="coerce").sum()
    beds_total = pd.to_numeric(region_summary.get("beds_total"), errors="coerce").sum()
    phc_total = pd.to_numeric(region_summary.get("phc_total"), errors="coerce").sum()
    pharmacies_total = pd.to_numeric(region_summary.get("private_pharmacies"), errors="coerce").sum()
    diabetic_visits_total = pd.to_numeric(region_summary.get("diabetic_visits_total"), errors="coerce").sum()

    national = {
        "region_id": "SA-00",
        "region_key": "saudi_arabia",
        "region_name_ar": "المملكة العربية السعودية",
        "region_name_en": "Saudi Arabia",
        "province_name_ar": "السعودية",
        "city_name_ar": "الرياض",
        "population_total": total_population,
        "latitude": 23.8859,
        "longitude": 45.0792,
        "hospitals_total": hospitals_total,
        "beds_total": beds_total,
        "phc_total": phc_total,
        "private_pharmacies": pharmacies_total,
        "hospitals_per_100k": hospitals_total / total_population * 100000 if total_population else None,
        "beds_per_1000": beds_total / total_population * 1000 if total_population else None,
        "phc_per_10k": phc_total / total_population * 10000 if total_population else None,
        "government_coverage_pct": _weighted_average(region_summary, "government_coverage_pct"),
        "private_insurance_pct": _weighted_average(region_summary, "private_insurance_pct"),
        "self_pay_pct": _weighted_average(region_summary, "self_pay_pct"),
        "adult_visit_rate": _weighted_average(region_summary, "adult_visit_rate"),
        "doctor_time_satisfaction_pct": _weighted_average(region_summary, "doctor_time_satisfaction_pct"),
        "adult_dental_consultation_pct": _weighted_average(region_summary, "adult_dental_consultation_pct"),
        "internet_health_info_pct": _weighted_average(region_summary, "internet_health_info_pct"),
        "teleconsultation_pct": _weighted_average(region_summary, "teleconsultation_pct"),
        "emr_access_pct": _weighted_average(region_summary, "emr_access_pct"),
        "diabetic_visits_total": diabetic_visits_total,
        "diabetic_visits_per_100k": diabetic_visits_total / total_population * 100000 if total_population else None,
        "community_pulse_index": _weighted_average(region_summary, "community_pulse_index"),
        "risk_prediction_score": _weighted_average(region_summary, "risk_prediction_score"),
        "avg_waiting_time_minutes": _weighted_average(region_summary, "avg_waiting_time_minutes"),
        "chronic_cases_rate": _weighted_average(region_summary, "chronic_cases_rate"),
        "priority_level": "وطني",
        "risk_level": "وطني",
    }

    for year in range(2020, 2025):
        national[f"phc_{year}"] = pd.to_numeric(region_summary.get(f"phc_{year}"), errors="coerce").sum()
        national[f"opd_{year}"] = pd.to_numeric(region_summary.get(f"opd_{year}"), errors="coerce").sum()

    return pd.DataFrame([national])


def get_focus_comparison(filtered_data: dict) -> pd.DataFrame:
    region_summary = get_region_summary(filtered_data)
    if region_summary.empty:
        return pd.DataFrame()

    focus = region_summary[region_summary["region_id"].isin(FOCUS_REGION_IDS)].copy()
    national = build_national_summary(region_summary)
    combined = pd.concat([national, focus], ignore_index=True)
    combined["display_name"] = combined["region_id"].map({"SA-00": "السعودية", **FOCUS_REGION_LABELS}).fillna(
        combined.get("province_name_ar")
    )
    order = {"SA-00": 0, "R-06": 1, "R-04": 2}
    combined["display_order"] = combined["region_id"].map(order).fillna(99)
    return combined.sort_values("display_order").reset_index(drop=True)


def build_executive_kpis(filtered_data: dict) -> list[dict[str, str]]:
    region_summary = get_region_summary(filtered_data)
    if region_summary.empty:
        return []

    total_population = pd.to_numeric(region_summary["population_total"], errors="coerce").sum()
    hospitals_total = pd.to_numeric(region_summary.get("hospitals_total"), errors="coerce").sum()
    pulse = _weighted_average(region_summary, "community_pulse_index")
    satisfaction = _weighted_average(region_summary, "doctor_time_satisfaction_pct")
    waiting = _weighted_average(region_summary, "avg_waiting_time_minutes")
    priority_areas = int(region_summary["priority_level"].astype(str).str.contains("عالي|متوسط", na=False).sum())

    return [
        {"label": "إجمالي السكان", "value": f"{total_population:,.0f}", "hint": "النطاق الجغرافي الحالي بعد تطبيق المرشحات"},
        {"label": "مؤشر الجاهزية المركب", "value": f"{pulse:.1f}" if pulse is not None else "غير متاح", "hint": "مؤشر مركب مشتق من الوصول والقدرة والرضا"},
        {"label": "رضا وقت الطبيب", "value": f"{satisfaction:.1f}%" if satisfaction is not None else "غير متاح", "hint": "مبني على مؤشرات الاستخدام والرضا الرسمية"},
        {"label": "عدد المستشفيات", "value": f"{hospitals_total:,.0f}", "hint": "إجمالي المستشفيات ضمن النطاق المختار"},
        {"label": "متوسط وقت الانتظار", "value": f"{waiting:.1f} دقيقة" if waiting is not None else "غير متاح", "hint": "تقدير تشغيلي معاير على المؤشرات الرسمية"},
        {"label": "مناطق الأولوية", "value": f"{priority_areas:,.0f}", "hint": "المناطق ذات الحاجة الأعلى للتدخل التشغيلي"},
    ]


def build_utilization_long(region_summary: pd.DataFrame, include_national: bool = True) -> pd.DataFrame:
    if region_summary.empty:
        return pd.DataFrame()

    frames = []
    if include_national:
        national = build_national_summary(region_summary)
        if not national.empty:
            frames.append(national)
    frames.append(region_summary[region_summary["region_id"].isin(FOCUS_REGION_IDS)].copy())
    summary = pd.concat(frames, ignore_index=True)
    if summary.empty:
        return pd.DataFrame()

    rows = []
    for _, row in summary.iterrows():
        label = "السعودية" if row["region_id"] == "SA-00" else FOCUS_REGION_LABELS.get(row["region_id"], row["province_name_ar"])
        for year in range(2020, 2025):
            phc_value = pd.to_numeric(row.get(f"phc_{year}"), errors="coerce")
            opd_value = pd.to_numeric(row.get(f"opd_{year}"), errors="coerce")
            combined_value = phc_value + opd_value if pd.notna(phc_value) and pd.notna(opd_value) else None
            rows.append({"entity": label, "year": year, "service_type": "الرعاية الأولية", "value": phc_value})
            rows.append({"entity": label, "year": year, "service_type": "العيادات الخارجية", "value": opd_value})
            rows.append({"entity": label, "year": year, "service_type": "إجمالي الطلب الصحي", "value": combined_value})
    frame = pd.DataFrame(rows)
    return frame.dropna(subset=["value"]).reset_index(drop=True)
