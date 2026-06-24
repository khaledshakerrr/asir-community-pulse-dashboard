from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from src.config import LIVE_DATA_CACHE_SECONDS, LIVE_DATA_PROVIDER, NCM_API_PASSWORD, NCM_API_USERNAME, cache


OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
NCM_TOKEN_URL = "https://login.api-mm.ncm.gov.sa/api/v1/token"
NCM_BASE_URL = "https://api-mm.ncm.gov.sa"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_SURVEY_PATH = PROJECT_ROOT / "data" / "official_google_sheet_tabs" / "survey_responses_simulated.csv"
LOCAL_REGION_SUMMARY_PATH = PROJECT_ROOT / "data" / "official_google_sheet_tabs" / "official_region_summary.csv"


TARGET_CITIES = [
    {"city_key": "abha", "city_ar": "أبها", "city_en": "Abha", "province_ar": "عسير", "latitude": 18.2164, "longitude": 42.5053},
    {"city_key": "khamis_mushait", "city_ar": "خميس مشيط", "city_en": "Khamis Mushait", "province_ar": "عسير", "latitude": 18.3000, "longitude": 42.7333},
    {"city_key": "ahad_rafidah", "city_ar": "أحد رفيدة", "city_en": "Ahad Rafidah", "province_ar": "عسير", "latitude": 18.1975, "longitude": 42.9414},
    {"city_key": "muhayil", "city_ar": "محايل عسير", "city_en": "Muhayil Aseer", "province_ar": "عسير", "latitude": 18.5439, "longitude": 42.0486},
    {"city_key": "bisha", "city_ar": "بيشة", "city_en": "Bisha", "province_ar": "عسير", "latitude": 19.9841, "longitude": 42.6050},
    {"city_key": "buraydah", "city_ar": "بريدة", "city_en": "Buraydah", "province_ar": "القصيم", "latitude": 26.3592, "longitude": 43.9818},
    {"city_key": "unaizah", "city_ar": "عنيزة", "city_en": "Unaizah", "province_ar": "القصيم", "latitude": 26.0900, "longitude": 43.9930},
    {"city_key": "ar_rass", "city_ar": "الرس", "city_en": "Ar Rass", "province_ar": "القصيم", "latitude": 25.8694, "longitude": 43.4973},
    {"city_key": "albukayriyah", "city_ar": "البكيرية", "city_en": "Al Bukayriyah", "province_ar": "القصيم", "latitude": 26.1442, "longitude": 43.6578},
    {"city_key": "almidhnab", "city_ar": "المذنب", "city_en": "Al Midhnab", "province_ar": "القصيم", "latitude": 25.8601, "longitude": 44.2223},
]


class EnvironmentalDataError(RuntimeError):
    """Raised when live environmental data cannot be fetched cleanly."""


def _cache_is_ready() -> bool:
    return hasattr(cache, "app")


def _call_loader(loader, *args):
    if _cache_is_ready():
        return loader(*args)
    uncached = getattr(loader, "uncached", None) or getattr(loader, "__wrapped__", loader)
    return uncached(*args)


def _safe_get_json(session: requests.Session, url: str, params: dict | None = None, headers: dict | None = None) -> dict:
    response = session.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def _normalize_arabic_key(value: object) -> str:
    text = str(value or "").strip()
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
        "ة": "ه",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    for token in ["منطقة", "المنطقة", "محافظة", "المحافظة", "مدينة", "العربية", "السعودية"]:
        text = text.replace(token, "")
    return "".join(text.split())


def _clip(value: float | int | None, low: float, high: float, default: float) -> float:
    if value is None or pd.isna(value):
        return float(default)
    return float(max(low, min(high, float(value))))


def _safe_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _load_local_environment_sources() -> tuple[pd.DataFrame, pd.DataFrame]:
    survey = pd.DataFrame()
    region_summary = pd.DataFrame()

    if LOCAL_SURVEY_PATH.exists():
        survey = pd.read_csv(LOCAL_SURVEY_PATH)
        survey = _safe_numeric(
            survey,
            [
                "air_quality_index",
                "humidity_index",
                "waiting_time_minutes",
                "community_pulse_index",
                "risk_prediction_score",
                "asthma_risk_score",
                "facility_pressure_score",
            ],
        )

    if LOCAL_REGION_SUMMARY_PATH.exists():
        region_summary = pd.read_csv(LOCAL_REGION_SUMMARY_PATH)
        region_summary = _safe_numeric(
            region_summary,
            [
                "avg_waiting_time_minutes",
                "community_pulse_index",
                "risk_prediction_score",
                "chronic_cases_rate",
            ],
        )

    return survey, region_summary


def _build_local_summary_maps() -> tuple[dict[str, dict], dict[str, dict]]:
    survey, region_summary = _load_local_environment_sources()

    city_map: dict[str, dict] = {}
    province_map: dict[str, dict] = {}

    if not survey.empty and {"province_ar", "city_ar"}.issubset(survey.columns):
        city_summary = (
            survey.groupby(["province_ar", "city_ar"], dropna=True)
            .agg(
                air_quality_index=("air_quality_index", "mean"),
                humidity_index=("humidity_index", "mean"),
                waiting_time_minutes=("waiting_time_minutes", "mean"),
                community_pulse_index=("community_pulse_index", "mean"),
                risk_prediction_score=("risk_prediction_score", "mean"),
                asthma_risk_score=("asthma_risk_score", "mean"),
                facility_pressure_score=("facility_pressure_score", "mean"),
            )
            .reset_index()
        )
        for row in city_summary.to_dict("records"):
            province_key = _normalize_arabic_key(row.get("province_ar"))
            city_key = _normalize_arabic_key(row.get("city_ar"))
            city_map[f"{province_key}:{city_key}"] = row
            city_map[city_key] = row

        province_summary = (
            survey.groupby("province_ar", dropna=True)
            .agg(
                air_quality_index=("air_quality_index", "mean"),
                humidity_index=("humidity_index", "mean"),
                waiting_time_minutes=("waiting_time_minutes", "mean"),
                community_pulse_index=("community_pulse_index", "mean"),
                risk_prediction_score=("risk_prediction_score", "mean"),
                asthma_risk_score=("asthma_risk_score", "mean"),
                facility_pressure_score=("facility_pressure_score", "mean"),
            )
            .reset_index()
        )
        for row in province_summary.to_dict("records"):
            province_map[_normalize_arabic_key(row.get("province_ar"))] = row

    if not region_summary.empty and "province_name_ar" in region_summary.columns:
        for row in region_summary.to_dict("records"):
            key = _normalize_arabic_key(row.get("province_name_ar"))
            province_map.setdefault(key, {})
            province_map[key] = {
                **province_map[key],
                "waiting_time_minutes": row.get("avg_waiting_time_minutes", province_map[key].get("waiting_time_minutes")),
                "community_pulse_index": row.get("community_pulse_index", province_map[key].get("community_pulse_index")),
                "risk_prediction_score": row.get("risk_prediction_score", province_map[key].get("risk_prediction_score")),
                "chronic_cases_rate": row.get("chronic_cases_rate", province_map[key].get("chronic_cases_rate")),
            }

    return city_map, province_map


def _lookup_local_city_profile(city: dict, city_map: dict[str, dict], province_map: dict[str, dict]) -> dict:
    province_key = _normalize_arabic_key(city["province_ar"])
    city_key = _normalize_arabic_key(city["city_ar"])
    profile = city_map.get(f"{province_key}:{city_key}") or city_map.get(city_key) or {}
    province_profile = province_map.get(province_key, {})
    return {**province_profile, **profile}


def _local_environment_baseline(city: dict, city_index: int, profile: dict) -> dict:
    humidity_raw = profile.get("humidity_index")
    humidity_pct = humidity_raw * 100 if humidity_raw is not None and pd.notna(humidity_raw) and float(humidity_raw) <= 1 else humidity_raw

    is_qassim = city["province_ar"] == "القصيم"
    base_temp = 37.0 if is_qassim else 27.5
    temperature_c = _clip(base_temp + (city_index % 5) * 0.9 - (0.4 if not is_qassim else 0.0), 20, 45, base_temp)
    aqi = _clip(profile.get("air_quality_index"), 18, 180, 68 if is_qassim else 54)
    humidity_pct = _clip(humidity_pct, 12, 92, 29 if is_qassim else 46)
    waiting_time = _clip(profile.get("waiting_time_minutes"), 6, 60, 24)
    pulse = _clip(profile.get("community_pulse_index"), 35, 100, 67)
    risk_score = _clip(profile.get("risk_prediction_score"), 20, 100, 58)
    asthma_score = _clip(profile.get("asthma_risk_score"), 20, 100, 54)
    facility_pressure = _clip(profile.get("facility_pressure_score"), 15, 100, 56)
    chronic_rate = _clip(profile.get("chronic_cases_rate"), 5, 100, 42)

    rainfall_mm = 0.6 if city["province_ar"] == "عسير" else 0.1
    wind_speed_kmh = _clip(11 + (aqi / 18) + (city_index % 3) * 2.5, 8, 38, 18)
    pressure_hpa = _clip(1006 + (city_index % 4) * 1.7, 998, 1026, 1012)
    uv_index = _clip(8.2 + (city_index % 3) * 0.5, 4, 12, 9.0)
    apparent_temperature_c = _clip(temperature_c + max((humidity_pct - 40) / 14, 0) + 0.4, 21, 52, temperature_c + 1.2)
    pm25 = _clip((aqi * 0.36) + (risk_score * 0.09), 6, 95, 22)
    pm10 = _clip(pm25 * 1.72 + (9 if is_qassim else 6), 14, 180, 38)
    no2 = _clip(11 + aqi * 0.22, 5, 160, 28)
    so2 = _clip(4 + aqi * 0.05, 2, 65, 9)
    o3 = _clip(35 + aqi * 0.28, 20, 180, 52)
    dust = _clip(pm10 * (0.82 if is_qassim else 0.64) + (8 if is_qassim else 3), 8, 190, 32)
    aerosol_optical_depth = round(_clip(0.18 + (aqi / 350), 0.05, 1.2, 0.26), 3)

    return {
        "temperature_c": round(temperature_c, 1),
        "humidity_pct": round(humidity_pct, 1),
        "rainfall_mm": round(rainfall_mm, 2),
        "wind_speed_kmh": round(wind_speed_kmh, 1),
        "pressure_hpa": round(pressure_hpa, 1),
        "uv_index": round(uv_index, 1),
        "apparent_temperature_c": round(apparent_temperature_c, 1),
        "aqi": round(aqi, 1),
        "pm25": round(pm25, 1),
        "pm10": round(pm10, 1),
        "no2": round(no2, 1),
        "so2": round(so2, 1),
        "o3": round(o3, 1),
        "dust": round(dust, 1),
        "aerosol_optical_depth": aerosol_optical_depth,
        "waiting_time_minutes": round(waiting_time, 1),
        "community_pulse_index": round(pulse, 1),
        "risk_prediction_score": round(risk_score, 1),
        "asthma_risk_score": round(asthma_score, 1),
        "facility_pressure_score": round(facility_pressure, 1),
        "chronic_cases_rate": round(chronic_rate, 1),
    }


def _build_local_fallback_bundle() -> dict:
    city_map, province_map = _build_local_summary_maps()
    today = pd.Timestamp.utcnow().tz_localize(None)
    current_rows: list[dict] = []
    forecast_rows: list[dict] = []

    for index, city in enumerate(TARGET_CITIES):
        profile = _lookup_local_city_profile(city, city_map, province_map)
        baseline = _local_environment_baseline(city, index, profile)
        current_rows.append(
            {
                **city,
                "provider": "local_fallback",
                "updated_at": today.isoformat(timespec="minutes"),
                "observed_at": today.isoformat(timespec="minutes"),
                "temperature_c": baseline["temperature_c"],
                "humidity_pct": baseline["humidity_pct"],
                "rainfall_mm": baseline["rainfall_mm"],
                "wind_speed_kmh": baseline["wind_speed_kmh"],
                "pressure_hpa": baseline["pressure_hpa"],
                "uv_index": baseline["uv_index"],
                "apparent_temperature_c": baseline["apparent_temperature_c"],
                "aqi": baseline["aqi"],
                "pm25": baseline["pm25"],
                "pm10": baseline["pm10"],
                "no2": baseline["no2"],
                "so2": baseline["so2"],
                "o3": baseline["o3"],
                "dust": baseline["dust"],
                "aerosol_optical_depth": baseline["aerosol_optical_depth"],
            }
        )

        for day_offset in range(7):
            forecast_date = (today + timedelta(days=day_offset)).date()
            heat_shift = [0.0, 0.7, 1.2, 0.4, -0.3, 0.5, 0.9][day_offset]
            pollution_shift = [0.0, 2.0, 4.0, 1.0, -2.0, 1.5, 3.0][day_offset]
            humidity_shift = [0.0, -2.0, 1.0, 2.0, 0.0, -1.0, 1.5][day_offset]
            forecast_rows.append(
                {
                    "time": (today + timedelta(days=day_offset)).replace(hour=12, minute=0, second=0, microsecond=0),
                    "forecast_date": forecast_date,
                    "city_key": city["city_key"],
                    "city_ar": city["city_ar"],
                    "province_ar": city["province_ar"],
                    "temperature_c": round(_clip(baseline["temperature_c"] + heat_shift, 18, 47, baseline["temperature_c"]), 1),
                    "humidity_pct": round(_clip(baseline["humidity_pct"] + humidity_shift, 10, 96, baseline["humidity_pct"]), 1),
                    "rainfall_mm": round(_clip(baseline["rainfall_mm"] + (0.15 if city["province_ar"] == "عسير" and day_offset in {1, 4} else 0.0), 0, 15, baseline["rainfall_mm"]), 2),
                    "wind_speed_kmh": round(_clip(baseline["wind_speed_kmh"] + ((day_offset % 3) - 1) * 1.5, 7, 42, baseline["wind_speed_kmh"]), 1),
                    "pressure_hpa": round(_clip(baseline["pressure_hpa"] + ((day_offset % 4) - 1.5) * 0.8, 995, 1028, baseline["pressure_hpa"]), 1),
                    "uv_index": round(_clip(baseline["uv_index"] + (0.2 if day_offset in {2, 6} else -0.1 if day_offset == 4 else 0.0), 3, 12, baseline["uv_index"]), 1),
                    "apparent_temperature": round(_clip(baseline["apparent_temperature_c"] + heat_shift + max(humidity_shift / 10, -0.5), 18, 52, baseline["apparent_temperature_c"]), 1),
                    "european_aqi": round(_clip(baseline["aqi"] + pollution_shift, 15, 190, baseline["aqi"]), 1),
                    "pm25": round(_clip(baseline["pm25"] + pollution_shift * 0.42, 5, 110, baseline["pm25"]), 1),
                    "pm10": round(_clip(baseline["pm10"] + pollution_shift * 0.8, 10, 190, baseline["pm10"]), 1),
                    "dust": round(_clip(baseline["dust"] + pollution_shift * 0.75, 6, 200, baseline["dust"]), 1),
                }
            )

    return {
        "current_frame": pd.DataFrame(current_rows),
        "forecast_frame": pd.DataFrame(forecast_rows),
        "provider": "local_fallback",
        "errors": [],
        "loaded_at": today.isoformat(timespec="minutes"),
    }


def _open_meteo_current_payload(city: dict, session: requests.Session) -> tuple[dict, pd.DataFrame]:
    weather_payload = _safe_get_json(
        session,
        OPEN_METEO_WEATHER_URL,
        params={
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "timezone": "Asia/Riyadh",
            "forecast_days": 7,
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "pressure_msl",
                    "uv_index",
                    "apparent_temperature",
                ]
            ),
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "pressure_msl",
                    "uv_index",
                    "apparent_temperature",
                ]
            ),
        },
    )
    air_payload = _safe_get_json(
        session,
        OPEN_METEO_AIR_URL,
        params={
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "timezone": "Asia/Riyadh",
            "forecast_days": 7,
            "current": ",".join(
                [
                    "european_aqi",
                    "pm2_5",
                    "pm10",
                    "nitrogen_dioxide",
                    "sulphur_dioxide",
                    "ozone",
                    "dust",
                    "aerosol_optical_depth",
                ]
            ),
            "hourly": ",".join(
                [
                    "european_aqi",
                    "pm2_5",
                    "pm10",
                    "nitrogen_dioxide",
                    "sulphur_dioxide",
                    "ozone",
                    "dust",
                    "aerosol_optical_depth",
                ]
            ),
        },
    )

    current_row = {
        **city,
        "provider": "Open-Meteo",
        "updated_at": weather_payload.get("current", {}).get("time"),
        "observed_at": weather_payload.get("current", {}).get("time"),
        "temperature_c": weather_payload.get("current", {}).get("temperature_2m"),
        "humidity_pct": weather_payload.get("current", {}).get("relative_humidity_2m"),
        "rainfall_mm": weather_payload.get("current", {}).get("precipitation"),
        "wind_speed_kmh": weather_payload.get("current", {}).get("wind_speed_10m"),
        "pressure_hpa": weather_payload.get("current", {}).get("pressure_msl"),
        "uv_index": weather_payload.get("current", {}).get("uv_index"),
        "apparent_temperature_c": weather_payload.get("current", {}).get("apparent_temperature"),
        "aqi": air_payload.get("current", {}).get("european_aqi"),
        "pm25": air_payload.get("current", {}).get("pm2_5"),
        "pm10": air_payload.get("current", {}).get("pm10"),
        "no2": air_payload.get("current", {}).get("nitrogen_dioxide"),
        "so2": air_payload.get("current", {}).get("sulphur_dioxide"),
        "o3": air_payload.get("current", {}).get("ozone"),
        "dust": air_payload.get("current", {}).get("dust"),
        "aerosol_optical_depth": air_payload.get("current", {}).get("aerosol_optical_depth"),
    }

    weather_hourly = pd.DataFrame(weather_payload.get("hourly", {}))
    air_hourly = pd.DataFrame(air_payload.get("hourly", {}))
    if weather_hourly.empty or air_hourly.empty:
        hourly = pd.DataFrame()
    else:
        hourly = weather_hourly.merge(air_hourly, on="time", how="inner", suffixes=("", "_air"))
        hourly["time"] = pd.to_datetime(hourly["time"], errors="coerce")
        hourly["forecast_date"] = hourly["time"].dt.date
        hourly["city_key"] = city["city_key"]
        hourly["city_ar"] = city["city_ar"]
        hourly["province_ar"] = city["province_ar"]
        hourly = hourly.rename(
            columns={
                "temperature_2m": "temperature_c",
                "relative_humidity_2m": "humidity_pct",
                "precipitation": "rainfall_mm",
                "wind_speed_10m": "wind_speed_kmh",
                "pressure_msl": "pressure_hpa",
                "pm2_5": "pm25",
                "pm10": "pm10",
                "nitrogen_dioxide": "no2",
                "sulphur_dioxide": "so2",
                "ozone": "o3",
            }
        )

    return current_row, hourly


def _ncm_placeholder_payload(city: dict, session: requests.Session) -> tuple[dict, pd.DataFrame]:
    if not NCM_API_USERNAME or not NCM_API_PASSWORD:
        raise EnvironmentalDataError("بيانات اعتماد المركز الوطني للأرصاد غير متوفرة.")

    token_response = session.get(
        NCM_TOKEN_URL,
        auth=(NCM_API_USERNAME, NCM_API_PASSWORD),
        timeout=30,
    )
    token_response.raise_for_status()
    token = token_response.json().get("access_token")
    if not token:
        raise EnvironmentalDataError("تعذر الحصول على رمز وصول من المركز الوطني للأرصاد.")

    raise EnvironmentalDataError(
        "تم تفعيل اعتماد المركز الوطني للأرصاد، لكن طبقة الربط التفصيلية لهذه الواجهة لم تُستكمل بعد. استخدم مزود Open-Meteo مؤقتًا أو أكمل إعداد المسارات التفصيلية لـ NCM."
    )


def _fetch_city_payload(city: dict, provider: str, session: requests.Session) -> tuple[dict, pd.DataFrame]:
    if provider == "ncm":
        return _ncm_placeholder_payload(city, session)
    return _open_meteo_current_payload(city, session)


def _build_bundle(provider: str) -> dict:
    rows: list[dict] = []
    forecast_frames: list[pd.DataFrame] = []

    session = requests.Session()
    session.headers.update({"User-Agent": "asir-community-pulse-dashboard/1.0"})

    errors: list[str] = []
    for city in TARGET_CITIES:
        try:
            current_row, forecast_frame = _fetch_city_payload(city, provider, session)
            rows.append(current_row)
            if not forecast_frame.empty:
                forecast_frames.append(forecast_frame)
        except Exception as exc:
            errors.append(f"{city['city_ar']}: {exc}")

    if not rows:
        fallback_bundle = _build_local_fallback_bundle()
        fallback_bundle["errors"] = errors
        fallback_bundle["fallback_reason"] = "live_provider_unavailable"
        return fallback_bundle

    current_frame = pd.DataFrame(rows)
    forecast_frame = pd.concat(forecast_frames, ignore_index=True) if forecast_frames else pd.DataFrame()
    return {
        "current_frame": current_frame,
        "forecast_frame": forecast_frame,
        "provider": provider,
        "errors": errors,
        "loaded_at": pd.Timestamp.utcnow().isoformat(),
    }


@cache.memoize(timeout=LIVE_DATA_CACHE_SECONDS)
def _load_environment_bundle_cached(provider: str) -> dict:
    return _build_bundle(provider)


def load_environmental_bundle(provider: str | None = None) -> dict:
    selected_provider = (provider or LIVE_DATA_PROVIDER or "open_meteo").strip().lower()
    return _call_loader(_load_environment_bundle_cached, selected_provider)


def clear_environmental_cache() -> None:
    cache.delete_memoized(_load_environment_bundle_cached)


def get_city_metadata_frame() -> pd.DataFrame:
    return pd.DataFrame(TARGET_CITIES)


def get_supported_city_keys() -> set[str]:
    return {item["city_key"] for item in TARGET_CITIES}


def get_qassim_population_lookup() -> dict[str, int]:
    return {
        "buraydah": 619739,
        "unaizah": 163441,
        "ar_rass": 133837,
        "albukayriyah": 56922,
        "almidhnab": 42890,
    }


def get_population_source_map() -> dict[str, str]:
    source_map = {key: "رسمي مباشر - نتائج تفصيلية للقصيم" for key in get_qassim_population_lookup()}
    for city in TARGET_CITIES:
        source_map.setdefault(city["city_key"], "غير متاح رسميًا على مستوى المدينة في النسخة الحالية")
    return source_map


def get_supported_forecast_horizon_days() -> int:
    return 7


def get_today_date() -> date:
    return pd.Timestamp.utcnow().date()
