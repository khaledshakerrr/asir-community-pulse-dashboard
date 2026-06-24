from __future__ import annotations

from datetime import date

import pandas as pd
import requests

from src.config import LIVE_DATA_CACHE_SECONDS, LIVE_DATA_PROVIDER, NCM_API_PASSWORD, NCM_API_USERNAME, cache


OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
NCM_TOKEN_URL = "https://login.api-mm.ncm.gov.sa/api/v1/token"
NCM_BASE_URL = "https://api-mm.ncm.gov.sa"


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
        raise EnvironmentalDataError("تعذر تحميل أي بيانات بيئية حية من المزود الحالي.")

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
