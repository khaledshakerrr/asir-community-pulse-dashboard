
from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
from collections.abc import Iterable

import pandas as pd


def _normalize_percentage(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.dropna().le(1).all():
        return numeric * 100
    return numeric


def _coerce_dates(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def _coerce_numeric(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def prepare_dashboard_data(data_bundle: dict) -> dict:
    tables = {
        sheet_name: frame.copy() for sheet_name, frame in data_bundle.get("tables", {}).items()
    }

    if tables.get("clean_regions_master", pd.DataFrame()).empty:
        tables["clean_regions_master"] = tables.get("regions_master", pd.DataFrame()).copy()

    survey = tables.get("survey_responses_simulated", pd.DataFrame())
    survey = _coerce_dates(survey, ["response_date"])
    survey = _coerce_numeric(
        survey,
        ["bmi_value", "satisfaction_score", "qol_score", "community_pulse_index", "risk_prediction_score"],
    )
    tables["survey_responses_simulated"] = survey

    monthly = tables.get("monthly_kpi_summary", pd.DataFrame())
    monthly = _coerce_dates(monthly, ["period_month"])
    monthly = _coerce_numeric(monthly, ["community_pulse_index", "satisfaction_rate"])
    if "satisfaction_rate" in monthly.columns:
        monthly["satisfaction_rate"] = _normalize_percentage(monthly["satisfaction_rate"])
    tables["monthly_kpi_summary"] = monthly

    complaints = tables.get("complaints_feedback", pd.DataFrame())
    complaints = _coerce_dates(complaints, ["date"])
    complaints = _coerce_numeric(complaints, ["resolution_days"])
    tables["complaints_feedback"] = complaints

    initiatives = tables.get("initiatives_programs", pd.DataFrame())
    initiatives = _coerce_numeric(
        initiatives,
        ["target_beneficiaries_count", "actual_beneficiaries_count", "impact_score", "awareness_increase_pct"],
    )
    if "awareness_increase_pct" in initiatives.columns:
        initiatives["awareness_increase_pct"] = _normalize_percentage(initiatives["awareness_increase_pct"])
    tables["initiatives_programs"] = initiatives

    facilities = tables.get("health_facilities", pd.DataFrame())
    facilities = _coerce_numeric(
        facilities,
        ["readiness_score", "beds_occupied_pct", "doctors_count"],
    )
    for column in ["readiness_score", "beds_occupied_pct"]:
        if column in facilities.columns:
            facilities[column] = _normalize_percentage(facilities[column])
    tables["health_facilities"] = facilities

    regions = tables.get("clean_regions_master", pd.DataFrame())
    regions = _coerce_numeric(regions, ["population_total", "latitude", "longitude"])
    tables["clean_regions_master"] = regions

    forecast = tables.get("forecasting_data", pd.DataFrame())
    forecast = _coerce_dates(forecast, ["month"])
    forecast = _coerce_numeric(forecast, ["actual", "forecast", "lower_bound", "upper_bound"])
    tables["forecasting_data"] = forecast

    targets = tables.get("targets_benchmarks", pd.DataFrame())
    targets = _coerce_numeric(targets, ["target_value", "current_value"])
    tables["targets_benchmarks"] = targets

    return {
        "tables": tables,
        "available_sheets": data_bundle.get("available_sheets", []),
        "loaded_at": data_bundle.get("loaded_at"),
    }


def get_filter_options(cleaned_data: dict) -> dict:
    tables = cleaned_data["tables"]
    survey = tables.get("survey_responses_simulated", pd.DataFrame())
    regions = tables.get("clean_regions_master", pd.DataFrame())
    monthly = tables.get("monthly_kpi_summary", pd.DataFrame())

    province_series = pd.Series(dtype="object")
    if "province_ar" in survey.columns:
        province_series = pd.concat([province_series, survey["province_ar"]], ignore_index=True)
    if "province_name_ar" in regions.columns:
        province_series = pd.concat([province_series, regions["province_name_ar"]], ignore_index=True)

    provinces = sorted({value for value in province_series.dropna().astype(str) if value.strip()})
    genders = sorted({value for value in survey.get("gender", pd.Series(dtype="object")).dropna().astype(str) if value.strip()})

    date_series = pd.Series(dtype="datetime64[ns]")
    for column in ["response_date"]:
        if column in survey.columns:
            date_series = pd.concat([date_series, survey[column]], ignore_index=True)
    if "period_month" in monthly.columns:
        date_series = pd.concat([date_series, monthly["period_month"]], ignore_index=True)

    date_series = pd.to_datetime(date_series, errors="coerce").dropna()
    min_date = date_series.min() if not date_series.empty else None
    max_date = date_series.max() if not date_series.empty else None

    return {
        "provinces": provinces,
        "genders": genders,
        "min_date": min_date,
        "max_date": max_date,
    }


def apply_filters(
    cleaned_data: dict,
    province: str | None,
    gender: str | None,
    start_date: str | None,
    end_date: str | None,
) -> dict:
    tables = {name: frame.copy() for name, frame in cleaned_data["tables"].items()}

    regions = tables.get("clean_regions_master", pd.DataFrame())
    survey = tables.get("survey_responses_simulated", pd.DataFrame())
    monthly = tables.get("monthly_kpi_summary", pd.DataFrame())
    complaints = tables.get("complaints_feedback", pd.DataFrame())
    initiatives = tables.get("initiatives_programs", pd.DataFrame())
    facilities = tables.get("health_facilities", pd.DataFrame())

    selected_region_ids = None
    if province and province != "الكل":
        region_candidates = set()
        if "province_name_ar" in regions.columns and "region_id" in regions.columns:
            region_candidates.update(regions.loc[regions["province_name_ar"] == province, "region_id"].astype(str))
        if "province_ar" in survey.columns and "region_id" in survey.columns:
            region_candidates.update(survey.loc[survey["province_ar"] == province, "region_id"].astype(str))
        selected_region_ids = {value for value in region_candidates if value}

    if not survey.empty:
        if province and province != "الكل" and "province_ar" in survey.columns:
            survey = survey[survey["province_ar"] == province]
        if gender and gender != "الكل" and "gender" in survey.columns:
            survey = survey[survey["gender"] == gender]
        if start_date and "response_date" in survey.columns:
            survey = survey[survey["response_date"] >= pd.to_datetime(start_date)]
        if end_date and "response_date" in survey.columns:
            survey = survey[survey["response_date"] <= pd.to_datetime(end_date)]

    tables["survey_responses_simulated"] = survey

    for table_name, date_column in [
        ("monthly_kpi_summary", "period_month"),
        ("complaints_feedback", "date"),
        ("forecasting_data", "month"),
    ]:
        frame = tables.get(table_name, pd.DataFrame())
        if selected_region_ids and "region_id" in frame.columns:
            frame = frame[frame["region_id"].astype(str).isin(selected_region_ids)]
        if start_date and date_column in frame.columns:
            frame = frame[frame[date_column] >= pd.to_datetime(start_date)]
        if end_date and date_column in frame.columns:
            frame = frame[frame[date_column] <= pd.to_datetime(end_date)]
        tables[table_name] = frame

    for table_name in ["initiatives_programs", "health_facilities", "clean_regions_master"]:
        frame = tables.get(table_name, pd.DataFrame())
        if selected_region_ids and "region_id" in frame.columns:
            frame = frame[frame["region_id"].astype(str).isin(selected_region_ids)]
        elif province and province != "الكل":
            province_column = "province_ar" if "province_ar" in frame.columns else "province_name_ar"
            if province_column in frame.columns:
                frame = frame[frame[province_column] == province]
        tables[table_name] = frame

    return {
        "tables": tables,
        "available_sheets": cleaned_data.get("available_sheets", []),
        "loaded_at": cleaned_data.get("loaded_at"),
    }
