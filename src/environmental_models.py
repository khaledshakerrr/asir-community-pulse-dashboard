from __future__ import annotations

import math

import pandas as pd

from src.environmental_live import (
    get_population_source_map,
    get_qassim_population_lookup,
    load_environmental_bundle,
)
from src.official_analytics import get_region_summary


SUPPORTED_PROVINCES = {"عسير", "القصيم"}


def _clip(value: float | int | None, low: float, high: float) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return float(max(low, min(high, value)))


def _scale(value: float | int | None, low: float, high: float) -> float:
    if value is None or pd.isna(value) or high <= low:
        return 0.0
    value = float(value)
    if value <= low:
        return 0.0
    if value >= high:
        return 100.0
    return ((value - low) / (high - low)) * 100.0


def _inverse_scale(value: float | int | None, low: float, high: float) -> float:
    return 100.0 - _scale(value, low, high)


def _seasonal_flu_baseline(month_number: int) -> float:
    profile = {
        1: 86,
        2: 78,
        3: 60,
        4: 48,
        5: 32,
        6: 24,
        7: 20,
        8: 22,
        9: 35,
        10: 52,
        11: 70,
        12: 84,
    }
    return float(profile.get(month_number, 45))


def _cool_temperature_score(temp_c: float | int | None) -> float:
    if temp_c is None or pd.isna(temp_c):
        return 0.0
    temp_c = float(temp_c)
    if temp_c <= 8:
        return 55.0
    if temp_c <= 16:
        return 100.0
    if temp_c <= 22:
        return 72.0
    if temp_c <= 28:
        return 36.0
    return 10.0


def _humidity_respiratory_score(humidity_pct: float | int | None) -> float:
    if humidity_pct is None or pd.isna(humidity_pct):
        return 0.0
    humidity_pct = float(humidity_pct)
    if 35 <= humidity_pct <= 60:
        return 30.0
    if humidity_pct < 20 or humidity_pct > 80:
        return 90.0
    return 55.0


def _compose_current_scores(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    current = frame.copy()
    current["pm25_score"] = current["pm25"].apply(lambda value: _scale(value, 5, 75))
    current["pm10_score"] = current["pm10"].apply(lambda value: _scale(value, 15, 180))
    current["aqi_risk_score"] = current["aqi"].apply(lambda value: _scale(value, 15, 180))
    current["no2_score"] = current["no2"].apply(lambda value: _scale(value, 10, 200))
    current["so2_score"] = current["so2"].apply(lambda value: _scale(value, 4, 100))
    current["o3_score"] = current["o3"].apply(lambda value: _scale(value, 30, 180))
    current["dust_score"] = current["dust"].apply(lambda value: _scale(value, 10, 180))
    current["heat_component"] = current["apparent_temperature_c"].apply(lambda value: _scale(value, 20, 48))
    current["humidity_heat_component"] = current["humidity_pct"].apply(lambda value: _scale(value, 25, 95))
    current["wind_component"] = current["wind_speed_kmh"].apply(lambda value: _scale(value, 8, 42))
    current["uv_component"] = current["uv_index"].apply(lambda value: _scale(value, 2, 11))
    current["air_quality_score"] = (
        0.45 * current["aqi_risk_score"]
        + 0.25 * current["pm25_score"]
        + 0.15 * current["pm10_score"]
        + 0.10 * current["no2_score"]
        + 0.05 * current["o3_score"]
    ).round(1)
    current["heat_stress_index"] = (
        0.45 * current["heat_component"]
        + 0.20 * current["humidity_heat_component"]
        + 0.20 * current["uv_component"]
        + 0.15 * current["wind_component"]
    ).round(1)
    current["dust_impact_index"] = (
        0.55 * current["dust_score"]
        + 0.30 * current["pm10_score"]
        + 0.15 * current["wind_component"]
    ).round(1)
    current["pollution_exposure_score"] = (
        0.35 * current["pm25_score"]
        + 0.25 * current["pm10_score"]
        + 0.15 * current["no2_score"]
        + 0.10 * current["so2_score"]
        + 0.15 * current["o3_score"]
    ).round(1)
    current["respiratory_risk_index"] = (
        0.35 * current["pm25_score"]
        + 0.20 * current["pm10_score"]
        + 0.15 * current["dust_score"]
        + 0.10 * current["aqi_risk_score"]
        + 0.20 * current["chronic_burden_score"]
    ).round(1)
    current["asthma_risk_score"] = (
        0.28 * current["pm25_score"]
        + 0.22 * current["dust_score"]
        + 0.12 * current["wind_component"]
        + 0.18 * current["humidity_risk_component"]
        + 0.20 * current["chronic_burden_score"]
    ).round(1)
    current["flu_risk_score"] = (
        0.35 * current["seasonal_flu_component"]
        + 0.20 * current["cool_temp_component"]
        + 0.15 * current["humidity_risk_component"]
        + 0.30 * current["age_and_demand_component"]
    ).round(1)
    current["pneumonia_risk_index"] = (
        0.30 * current["seasonal_flu_component"]
        + 0.20 * current["cool_temp_component"]
        + 0.25 * current["pm25_score"]
        + 0.25 * current["age_and_demand_component"]
    ).round(1)
    current["environmental_health_score"] = (
        0.35 * current["air_quality_score"]
        + 0.30 * current["heat_stress_index"]
        + 0.20 * current["dust_impact_index"]
        + 0.15 * current["rainfall_risk_component"]
    ).round(1)
    current["operational_pressure_forecast"] = (
        0.35 * current["respiratory_risk_index"]
        + 0.25 * current["heat_stress_index"]
        + 0.20 * current["doctor_time_pressure_component"]
        + 0.20 * current["diabetes_demand_component"]
    ).round(1)
    current["risk_level"] = current["respiratory_risk_index"].apply(classify_risk_level)
    current["air_quality_level"] = current["air_quality_score"].apply(classify_risk_level)
    current["alert_text"] = current.apply(_compose_alert_text, axis=1)
    current["population_at_risk"] = current.apply(
        lambda row: int(round((row["population_total"] or 0) * (row["respiratory_risk_index"] / 100)))
        if pd.notna(row.get("population_total"))
        else None,
        axis=1,
    )
    return current


def _compose_forecast_scores(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    forecast = frame.copy()
    forecast["pm25_score"] = forecast["pm25"].apply(lambda value: _scale(value, 5, 75))
    forecast["pm10_score"] = forecast["pm10"].apply(lambda value: _scale(value, 15, 180))
    forecast["aqi_risk_score"] = forecast["aqi"].apply(lambda value: _scale(value, 15, 180))
    forecast["dust_score"] = forecast["dust"].apply(lambda value: _scale(value, 10, 180))
    forecast["heat_component"] = forecast["apparent_temperature_c"].apply(lambda value: _scale(value, 20, 48))
    forecast["humidity_risk_component"] = forecast["humidity_pct"].apply(_humidity_respiratory_score)
    forecast["wind_component"] = forecast["wind_speed_kmh"].apply(lambda value: _scale(value, 8, 42))
    forecast["seasonal_flu_component"] = forecast["forecast_date"].apply(lambda value: _seasonal_flu_baseline(value.month))
    forecast["cool_temp_component"] = forecast["temperature_c"].apply(_cool_temperature_score)
    forecast["respiratory_risk_index"] = (
        0.35 * forecast["pm25_score"]
        + 0.20 * forecast["pm10_score"]
        + 0.15 * forecast["dust_score"]
        + 0.10 * forecast["aqi_risk_score"]
        + 0.20 * forecast["chronic_burden_score"]
    ).round(1)
    forecast["asthma_risk_score"] = (
        0.30 * forecast["pm25_score"]
        + 0.25 * forecast["dust_score"]
        + 0.15 * forecast["wind_component"]
        + 0.10 * forecast["humidity_risk_component"]
        + 0.20 * forecast["chronic_burden_score"]
    ).round(1)
    forecast["flu_risk_score"] = (
        0.38 * forecast["seasonal_flu_component"]
        + 0.22 * forecast["cool_temp_component"]
        + 0.12 * forecast["humidity_risk_component"]
        + 0.28 * forecast["age_and_demand_component"]
    ).round(1)
    forecast["heat_stress_index"] = (
        0.50 * forecast["heat_component"]
        + 0.20 * forecast["humidity_risk_component"]
        + 0.15 * forecast["uv_index_score"]
        + 0.15 * forecast["wind_component"]
    ).round(1)
    forecast["operational_pressure_forecast"] = (
        0.35 * forecast["respiratory_risk_index"]
        + 0.25 * forecast["heat_stress_index"]
        + 0.20 * forecast["doctor_time_pressure_component"]
        + 0.20 * forecast["diabetes_demand_component"]
    ).round(1)
    forecast["risk_level"] = forecast["respiratory_risk_index"].apply(classify_risk_level)
    return forecast


def classify_risk_level(score: float | int | None) -> str:
    score = _clip(score, 0, 100)
    if score >= 75:
        return "مرتفع"
    if score >= 50:
        return "متوسط"
    return "منخفض"


def _compose_alert_text(row: pd.Series) -> str:
    drivers = []
    if row.get("pm25", 0) and row["pm25"] >= 35:
        drivers.append("ارتفاع الجسيمات الدقيقة")
    if row.get("dust", 0) and row["dust"] >= 80:
        drivers.append("نشاط الغبار")
    if row.get("apparent_temperature_c", 0) and row["apparent_temperature_c"] >= 38:
        drivers.append("إجهاد حراري مرتفع")
    if row.get("humidity_pct", 0) and (row["humidity_pct"] <= 20 or row["humidity_pct"] >= 80):
        drivers.append("رطوبة غير مواتية")
    if not drivers:
        drivers.append("استقرار نسبي في المحركات البيئية")
    return "، ".join(drivers)


def _attach_official_baseline(current_frame: pd.DataFrame, filtered_data: dict) -> pd.DataFrame:
    if current_frame.empty:
        return current_frame

    region_summary = get_region_summary(filtered_data)
    if region_summary.empty:
        frame = current_frame.copy()
        for column, value in {
            "chronic_burden_score": 50.0,
            "doctor_time_pressure_component": 50.0,
            "diabetes_demand_component": 50.0,
            "age_and_demand_component": 50.0,
            "regional_population_total": None,
        }.items():
            frame[column] = value
        return frame

    baseline = region_summary[region_summary["province_name_ar"].isin(SUPPORTED_PROVINCES)].copy()
    if baseline.empty:
        baseline = region_summary.copy()

    baseline["province_ar"] = baseline["province_name_ar"]
    baseline["chronic_burden_score"] = baseline["chronic_cases_rate"].apply(lambda value: _scale(value, 10, 100))
    baseline["doctor_time_pressure_component"] = baseline["avg_waiting_time_minutes"].apply(lambda value: _scale(value, 8, 45))
    baseline["diabetes_demand_component"] = baseline["diabetic_visits_per_100k"].apply(lambda value: _scale(value, 400, 4500))
    baseline["age_and_demand_component"] = baseline["adult_visit_rate"].apply(lambda value: _scale(value, 20, 85))
    baseline["regional_population_total"] = baseline["population_total"]

    columns = [
        "province_ar",
        "chronic_burden_score",
        "doctor_time_pressure_component",
        "diabetes_demand_component",
        "age_and_demand_component",
        "regional_population_total",
    ]
    return current_frame.merge(baseline[columns], on="province_ar", how="left")


def _enrich_current_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    enriched = frame.copy()
    population_lookup = get_qassim_population_lookup()
    population_source_map = get_population_source_map()
    enriched["population_total"] = enriched["city_key"].map(population_lookup)
    enriched["population_source"] = enriched["city_key"].map(population_source_map)
    enriched["humidity_risk_component"] = enriched["humidity_pct"].apply(_humidity_respiratory_score)
    enriched["seasonal_flu_component"] = enriched["updated_at"].apply(
        lambda value: _seasonal_flu_baseline(pd.to_datetime(value).month if pd.notna(value) else 1)
    )
    enriched["cool_temp_component"] = enriched["temperature_c"].apply(_cool_temperature_score)
    enriched["rainfall_risk_component"] = enriched["rainfall_mm"].apply(lambda value: _scale(value, 0, 12))
    return enriched


def _aggregate_forecast(frame: pd.DataFrame, filtered_data: dict) -> pd.DataFrame:
    if frame.empty:
        return frame

    grouped = (
        frame.groupby(["city_key", "city_ar", "province_ar", "forecast_date"], dropna=True)
        .agg(
            temperature_c=("temperature_c", "mean"),
            apparent_temperature_c=("apparent_temperature", "mean"),
            humidity_pct=("humidity_pct", "mean"),
            rainfall_mm=("rainfall_mm", "sum"),
            wind_speed_kmh=("wind_speed_kmh", "max"),
            pressure_hpa=("pressure_hpa", "mean"),
            uv_index_score=("uv_index", "max"),
            aqi=("european_aqi", "max"),
            pm25=("pm25", "mean"),
            pm10=("pm10", "mean"),
            dust=("dust", "mean"),
        )
        .reset_index()
    )
    grouped = _attach_official_baseline(grouped, filtered_data)
    population_lookup = get_qassim_population_lookup()
    grouped["population_total"] = grouped["city_key"].map(population_lookup)
    grouped["humidity_risk_component"] = grouped["humidity_pct"].apply(_humidity_respiratory_score)
    grouped["cool_temp_component"] = grouped["temperature_c"].apply(_cool_temperature_score)
    grouped["age_and_demand_component"] = grouped["age_and_demand_component"].fillna(50)
    grouped["doctor_time_pressure_component"] = grouped["doctor_time_pressure_component"].fillna(50)
    grouped["diabetes_demand_component"] = grouped["diabetes_demand_component"].fillna(50)
    grouped["chronic_burden_score"] = grouped["chronic_burden_score"].fillna(50)
    return grouped


def build_environmental_current_frame(filtered_data: dict, province: str | None = None) -> pd.DataFrame:
    bundle = load_environmental_bundle()
    current = bundle.get("current_frame", pd.DataFrame()).copy()
    if current.empty:
        return current

    current = _attach_official_baseline(current, filtered_data)
    current = _enrich_current_frame(current)
    current["chronic_burden_score"] = current["chronic_burden_score"].fillna(50)
    current["doctor_time_pressure_component"] = current["doctor_time_pressure_component"].fillna(50)
    current["diabetes_demand_component"] = current["diabetes_demand_component"].fillna(50)
    current["age_and_demand_component"] = current["age_and_demand_component"].fillna(50)
    current = _compose_current_scores(current)

    if province and province in SUPPORTED_PROVINCES:
        current = current[current["province_ar"] == province].copy()
    elif province and province not in SUPPORTED_PROVINCES and province != "الكل":
        return pd.DataFrame()

    return current.sort_values(["province_ar", "respiratory_risk_index"], ascending=[True, False]).reset_index(drop=True)


def build_environmental_forecast_frame(filtered_data: dict, province: str | None = None) -> pd.DataFrame:
    bundle = load_environmental_bundle()
    forecast = bundle.get("forecast_frame", pd.DataFrame()).copy()
    if forecast.empty:
        return forecast

    forecast = _aggregate_forecast(forecast, filtered_data)
    forecast = _compose_forecast_scores(forecast)

    if province and province in SUPPORTED_PROVINCES:
        forecast = forecast[forecast["province_ar"] == province].copy()
    elif province and province not in SUPPORTED_PROVINCES and province != "الكل":
        return pd.DataFrame()

    return forecast.sort_values(["forecast_date", "respiratory_risk_index"], ascending=[True, False]).reset_index(drop=True)


def build_early_warning_rows(current_frame: pd.DataFrame, forecast_frame: pd.DataFrame) -> list[dict[str, str]]:
    if current_frame.empty:
        return []

    rows: list[dict[str, str]] = []
    for _, row in current_frame.sort_values("respiratory_risk_index", ascending=False).head(5).iterrows():
        description = f"{row['city_ar']} - {row['province_ar']} | مخاطر تنفسية {row['respiratory_risk_index']:.1f}"
        if pd.notna(row.get("heat_stress_index")):
            description += f" | إجهاد حراري {row['heat_stress_index']:.1f}"
        rows.append(
            {
                "label": description,
                "value": row["alert_text"],
                "tone": "danger" if row["respiratory_risk_index"] >= 75 else "warning",
            }
        )

    if not forecast_frame.empty:
        weekly_peak = forecast_frame.sort_values("operational_pressure_forecast", ascending=False).iloc[0]
        rows.insert(
            0,
            {
                "label": f"أعلى ضغط تشغيلي متوقع خلال 7 أيام: {weekly_peak['city_ar']}",
                "value": f"{weekly_peak['forecast_date']} | {weekly_peak['operational_pressure_forecast']:.1f}",
                "tone": "danger" if weekly_peak["operational_pressure_forecast"] >= 75 else "warning",
            },
        )

    return rows


def build_environmental_kpis(current_frame: pd.DataFrame, forecast_frame: pd.DataFrame) -> list[dict[str, str]]:
    if current_frame.empty:
        return []

    hottest = current_frame.loc[current_frame["temperature_c"].idxmax()]
    worst_air = current_frame.loc[current_frame["aqi"].idxmax()]
    worst_respiratory = current_frame.loc[current_frame["respiratory_risk_index"].idxmax()]
    peak_forecast = forecast_frame.loc[forecast_frame["operational_pressure_forecast"].idxmax()] if not forecast_frame.empty else None

    return [
        {"label": "أعلى حرارة حالية", "value": f"{hottest['city_ar']} | {hottest['temperature_c']:.1f}°", "hint": "أعلى رصد حراري بين المدن المتابعة"},
        {"label": "أسوأ جودة هواء", "value": f"{worst_air['city_ar']} | AQI {worst_air['aqi']:.0f}", "hint": "أعلى ضغط هوائي حالي وفق مؤشر AQI"},
        {"label": "أعلى خطر تنفسي", "value": f"{worst_respiratory['city_ar']} | {worst_respiratory['respiratory_risk_index']:.1f}", "hint": "يربط الهواء والغبار والعبء المزمن"},
        {
            "label": "أعلى ضغط متوقع",
            "value": f"{peak_forecast['city_ar']} | {peak_forecast['operational_pressure_forecast']:.1f}" if peak_forecast is not None else "غير متاح",
            "hint": "أعلى ضغط تشغيلي خلال أفق التوقع القصير",
        },
    ]
