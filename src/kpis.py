from __future__ import annotations

import pandas as pd

from src.config import HIGH_RISK_THRESHOLD


def _format_number(value: float | int | None, suffix: str = "", decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "غير متاح"
    return f"{value:,.{decimals}f}{suffix}"


def _find_waiting_time_from_targets(targets: pd.DataFrame) -> float | None:
    if targets.empty:
        return None

    lookup = targets.fillna("")
    if "kpi_name_ar" not in lookup.columns and "kpi_name_en" not in lookup.columns:
        return None

    mask = pd.Series(False, index=lookup.index)
    if "kpi_name_ar" in lookup.columns:
        mask = mask | lookup["kpi_name_ar"].astype(str).str.contains("انتظار", case=False, na=False)
    if "kpi_name_en" in lookup.columns:
        mask = mask | lookup["kpi_name_en"].astype(str).str.contains("waiting", case=False, na=False)

    if not mask.any() or "current_value" not in lookup.columns:
        return None

    return pd.to_numeric(lookup.loc[mask, "current_value"], errors="coerce").dropna().mean()


def calculate_overview_kpis(filtered_data: dict) -> list[dict[str, str]]:
    tables = filtered_data["tables"]
    survey = tables.get("survey_responses_simulated", pd.DataFrame())
    complaints = tables.get("complaints_feedback", pd.DataFrame())
    monthly = tables.get("monthly_kpi_summary", pd.DataFrame())
    targets = tables.get("targets_benchmarks", pd.DataFrame())
    regions = tables.get("clean_regions_master", pd.DataFrame())

    total_responses = int(survey["response_id"].nunique()) if "response_id" in survey.columns else len(survey)
    pulse_score = pd.to_numeric(survey.get("community_pulse_index"), errors="coerce").mean()
    if pd.isna(pulse_score):
        pulse_score = pd.to_numeric(monthly.get("community_pulse_index"), errors="coerce").mean()

    satisfaction_rate = None
    if "satisfaction_score" in survey.columns and not survey.empty:
        satisfaction_rate = pd.to_numeric(survey["satisfaction_score"], errors="coerce").mean() / 5 * 100
    elif "satisfaction_rate" in monthly.columns:
        satisfaction_rate = pd.to_numeric(monthly["satisfaction_rate"], errors="coerce").mean()

    complaints_count = int(complaints["case_id"].nunique()) if "case_id" in complaints.columns else len(complaints)
    waiting_time = _find_waiting_time_from_targets(targets)

    high_risk_areas = 0
    if "priority_level" in regions.columns:
        high_risk_areas = int(
            regions["priority_level"].astype(str).str.contains("مرتفع|High", case=False, na=False).sum()
        )
    elif "risk_prediction_score" in survey.columns and "region_id" in survey.columns:
        region_risk = survey.groupby("region_id", dropna=True)["risk_prediction_score"].mean()
        high_risk_areas = int((region_risk >= HIGH_RISK_THRESHOLD).sum())

    return [
        {"label": "إجمالي الاستجابات", "value": _format_number(total_responses), "hint": "عدد المشاركات بعد تطبيق المرشحات"},
        {"label": "متوسط مؤشر نبض المجتمع", "value": _format_number(pulse_score, decimals=1), "hint": "متوسط community pulse index"},
        {"label": "معدل الرضا", "value": _format_number(satisfaction_rate, suffix="%", decimals=1), "hint": "مستخرج من التقييمات أو الملخص الشهري"},
        {"label": "عدد الشكاوى والملاحظات", "value": _format_number(complaints_count), "hint": "إجمالي الحالات المسجلة"},
        {"label": "متوسط وقت الانتظار", "value": _format_number(waiting_time, suffix=" دقيقة", decimals=0), "hint": "من جدول الأهداف والمؤشرات عند توفره"},
        {"label": "المناطق عالية الخطورة", "value": _format_number(high_risk_areas), "hint": "حسب أولوية المنطقة أو متوسط مؤشر المخاطر"},
    ]
