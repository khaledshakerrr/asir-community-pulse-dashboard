
from __future__ import annotations

import os

from dotenv import load_dotenv
from flask_caching import Cache

load_dotenv()

APP_TITLE = "منصة نبض المجتمع"
APP_SUBTITLE = "Asir Community Pulse Platform"
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
GOOGLE_SERVICE_ACCOUNT_JSON_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_FILE", "").strip()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

CACHE_TIMEOUT_SECONDS = int(os.getenv("CACHE_TIMEOUT_SECONDS", "300"))
HIGH_RISK_THRESHOLD = float(os.getenv("HIGH_RISK_THRESHOLD", "75"))

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
}

COLORS = {
    "navy": "#071C2B",
    "navy_soft": "#0B2B3D",
    "navy_card": "#10384D",
    "teal": "#13C5C2",
    "cyan": "#43E6F4",
    "white": "#FFFFFF",
    "paper": "#F5F8FB",
    "ink": "#112533",
    "muted": "#6B7B88",
    "border": "#DCE6EE",
    "danger": "#E0565B",
    "warning": "#F5B642",
    "success": "#19A974",
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
