from __future__ import annotations

import os

from dotenv import load_dotenv
from flask_caching import Cache

load_dotenv()

APP_TITLE = "منصة نبض المجتمع"
APP_SUBTITLE = "منصة تحليلية تنفيذية للمؤشرات الصحية داخل المملكة"
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
GOOGLE_SERVICE_ACCOUNT_JSON_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_FILE", "").strip()
LOCAL_DATA_WORKBOOK = os.getenv("LOCAL_DATA_WORKBOOK", "data/official_google_sheets_seed.xlsx").strip()
PREFER_LOCAL_DEMO_DATA = os.getenv("PREFER_LOCAL_DEMO_DATA", "1").strip() == "1"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

CACHE_TIMEOUT_SECONDS = int(os.getenv("CACHE_TIMEOUT_SECONDS", "300"))
HIGH_RISK_THRESHOLD = float(os.getenv("HIGH_RISK_THRESHOLD", "75"))
FONT_FAMILY = "Cairo, Tajawal, 'Segoe UI', sans-serif"

EXPECTED_SHEETS = [
    "clean_regions_master",
    "regions_master",
    "survey_responses_simulated",
    "health_facilities",
    "monthly_kpi_summary",
    "complaints_feedback",
    "initiatives_programs",
    "forecasting_data",
    "targets_benchmarks",
    "lookup_definitions",
    "data_dictionary",
    "official_region_summary",
    "qassim_governorates",
    "asir_clusters",
    "workforce_regional",
    "source_catalog",
]

REQUIRED_SHEETS = {
    "regions_master",
    "survey_responses_simulated",
    "monthly_kpi_summary",
    "complaints_feedback",
    "initiatives_programs",
    "forecasting_data",
}

EXPECTED_COLUMNS = {
    "clean_regions_master": [
        "region_id",
        "province_name_ar",
        "latitude",
        "longitude",
    ],
    "regions_master": [
        "region_id",
        "province_name_ar",
        "latitude",
        "longitude",
        "priority_level",
    ],
    "survey_responses_simulated": [
        "response_id",
        "response_date",
        "region_id",
        "province_ar",
        "gender",
        "community_pulse_index",
        "satisfaction_score",
        "risk_prediction_score",
    ],
    "health_facilities": [
        "facility_id",
        "name_ar",
        "region_id",
        "province_ar",
        "readiness_score",
    ],
    "monthly_kpi_summary": [
        "period_month",
        "region_id",
        "community_pulse_index",
        "satisfaction_rate",
    ],
    "complaints_feedback": [
        "case_id",
        "date",
        "region_id",
        "type",
        "status",
    ],
    "initiatives_programs": [
        "initiative_id",
        "initiative_name_ar",
        "region_id",
        "province_ar",
        "target_beneficiaries_count",
        "actual_beneficiaries_count",
    ],
    "forecasting_data": [
        "indicator",
        "month",
        "actual",
        "forecast",
        "lower_bound",
        "upper_bound",
    ],
    "targets_benchmarks": [
        "kpi_name_ar",
        "kpi_name_en",
        "target_value",
        "current_value",
    ],
    "official_region_summary": [
        "region_id",
        "province_name_ar",
        "population_total",
        "community_pulse_index",
        "risk_prediction_score",
    ],
    "qassim_governorates": [
        "governorate_ar",
        "population_total",
        "saudi_total",
        "non_saudi_total",
    ],
    "asir_clusters": [
        "cluster_name_ar",
        "phc_count",
        "hospital_count",
        "beds_total",
    ],
    "workforce_regional": [
        "region_key",
        "region_name_ar",
        "physicians_total_all_sectors",
        "nurses_and_midwives_total_all_sectors",
    ],
}

COLORS = {
    "bg_main": "#071A2C",
    "bg_panel": "#0B243D",
    "card_bg": "#FFFFFF",
    "card_soft": "#F5F9FC",
    "accent_teal": "#00A88F",
    "accent_cyan": "#28D6C4",
    "text_dark": "#102A43",
    "text_muted": "#6B7280",
    "danger": "#E74C3C",
    "warning": "#F2B84B",
    "success": "#00A88F",
    "border": "#D9E2EC",
    "grid": "rgba(16,42,67,0.08)",
    "white": "#FFFFFF",
    "paper": "#F5F9FC",
    "ink": "#102A43",
    "muted": "#6B7280",
    "teal": "#00A88F",
    "cyan": "#28D6C4",
    "navy": "#071A2C",
    "navy_soft": "#0B243D",
    "navy_card": "#12324F",
}

cache = Cache()


def init_cache(server) -> None:
    cache.init_app(
        server,
        config={
            "CACHE_TYPE": "SimpleCache",
            "CACHE_DEFAULT_TIMEOUT": CACHE_TIMEOUT_SECONDS,
        },
    )
