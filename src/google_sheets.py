from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

from src.config import (
    CACHE_TIMEOUT_SECONDS,
    EXPECTED_SHEETS,
    GOOGLE_SERVICE_ACCOUNT_JSON,
    GOOGLE_SERVICE_ACCOUNT_JSON_FILE,
    GOOGLE_SHEET_ID,
    LOCAL_DATA_WORKBOOK,
    PREFER_LOCAL_DEMO_DATA,
    SCOPES,
    cache,
)


class GoogleSheetsConnectionError(RuntimeError):
    """Raised when dashboard data access cannot be established cleanly."""


def _resolve_env_value(name: str, fallback: str = "") -> str:
    return os.getenv(name, fallback).strip()


def _resolve_google_credentials_source() -> tuple[str, str]:
    service_account_json = _resolve_env_value("GOOGLE_SERVICE_ACCOUNT_JSON", GOOGLE_SERVICE_ACCOUNT_JSON)
    service_account_json_file = _resolve_env_value("GOOGLE_SERVICE_ACCOUNT_JSON_FILE", GOOGLE_SERVICE_ACCOUNT_JSON_FILE)

    if service_account_json:
        return "json", service_account_json
    if service_account_json_file:
        return "file", service_account_json_file
    return "missing", ""


def _resolve_local_workbook_path() -> Path | None:
    workbook_value = _resolve_env_value("LOCAL_DATA_WORKBOOK", LOCAL_DATA_WORKBOOK)
    if not workbook_value:
        return None

    workbook_path = Path(workbook_value)
    if not workbook_path.is_absolute():
        workbook_path = Path.cwd() / workbook_path
    return workbook_path.resolve()


def _infer_local_source_label(path: Path) -> str:
    name = path.stem.lower()
    if "official" in name:
        return "ملف بيانات رسمي محلي"
    if "synthetic" in name:
        return "ملف بيانات تجريبي محلي"
    return "ملف بيانات محلي"


def _cache_is_ready() -> bool:
    return hasattr(cache, "app")


def _call_loader(loader, *args):
    if _cache_is_ready():
        return loader(*args)
    uncached = getattr(loader, "uncached", None) or getattr(loader, "__wrapped__", loader)
    return uncached(*args)


def _load_service_account_info(credential_mode: str, credential_value: str) -> dict:
    if credential_mode == "json":
        try:
            return json.loads(credential_value)
        except json.JSONDecodeError as exc:
            raise GoogleSheetsConnectionError(
                "تعذر قراءة GOOGLE_SERVICE_ACCOUNT_JSON. تأكد أن القيمة تحتوي على JSON صالح كامل."
            ) from exc

    credential_path = Path(credential_value).expanduser()
    if not credential_path.is_file():
        raise GoogleSheetsConnectionError(
            f"مسار ملف الاعتماد غير صالح: {credential_path}. تحقق من GOOGLE_SERVICE_ACCOUNT_JSON_FILE داخل ملف .env."
        )

    try:
        return json.loads(credential_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise GoogleSheetsConnectionError(f"تعذر قراءة ملف الاعتماد المحلي: {credential_path}.") from exc
    except json.JSONDecodeError as exc:
        raise GoogleSheetsConnectionError(f"ملف الاعتماد المحلي لا يحتوي على JSON صالح: {credential_path}.") from exc


def _build_client(sheet_id: str, credential_mode: str, credential_value: str) -> gspread.Client:
    if not sheet_id:
        raise GoogleSheetsConnectionError(
            "لم يتم ضبط GOOGLE_SHEET_ID. أضف معرّف ملف جوجل شيت داخل ملف .env أو إعدادات النشر ثم أعد تشغيل التطبيق."
        )
    if credential_mode == "missing" or not credential_value:
        raise GoogleSheetsConnectionError(
            "بيانات اعتماد جوجل شيت غير متوفرة. استخدم GOOGLE_SERVICE_ACCOUNT_JSON للنشر أو GOOGLE_SERVICE_ACCOUNT_JSON_FILE للتشغيل المحلي."
        )

    service_account_info = _load_service_account_info(credential_mode, credential_value)
    try:
        credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        return gspread.authorize(credentials)
    except Exception as exc:
        raise GoogleSheetsConnectionError(
            "فشل إنشاء اتصال جوجل شيت. تحقق من صلاحيات حساب الخدمة ومشاركة الملف مع البريد الخاص بحساب الخدمة."
        ) from exc


@cache.memoize(timeout=CACHE_TIMEOUT_SECONDS)
def _load_sheets_cached(sheet_id: str, credential_mode: str, credential_value: str) -> dict:
    client = _build_client(sheet_id, credential_mode, credential_value)

    try:
        workbook = client.open_by_key(sheet_id)
    except Exception as exc:
        raise GoogleSheetsConnectionError(
            "تعذر فتح ملف جوجل شيت. تحقق من GOOGLE_SHEET_ID ومشاركة الملف مع حساب الخدمة."
        ) from exc

    tables: dict[str, pd.DataFrame] = {}
    available_sheets = {worksheet.title for worksheet in workbook.worksheets()}

    for sheet_name in EXPECTED_SHEETS:
        if sheet_name not in available_sheets:
            tables[sheet_name] = pd.DataFrame()
            continue

        try:
            worksheet = workbook.worksheet(sheet_name)
            records = worksheet.get_all_records()
        except WorksheetNotFound:
            tables[sheet_name] = pd.DataFrame()
            continue
        except Exception as exc:
            raise GoogleSheetsConnectionError(f"تعذر قراءة الورقة '{sheet_name}' من جوجل شيت.") from exc

        tables[sheet_name] = pd.DataFrame(records)

    return {
        "tables": tables,
        "available_sheets": sorted(available_sheets),
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "source_label": "جوجل شيت",
    }


@cache.memoize(timeout=CACHE_TIMEOUT_SECONDS)
def _load_local_workbook_cached(workbook_path: str) -> dict:
    path = Path(workbook_path)
    if not path.is_file():
        raise GoogleSheetsConnectionError(
            f"تعذر العثور على ملف البيانات المحلية: {path}. شغّل مولد البيانات التجريبية أو عدّل LOCAL_DATA_WORKBOOK."
        )

    try:
        excel = pd.ExcelFile(path, engine="openpyxl")
    except Exception as exc:
        raise GoogleSheetsConnectionError(f"تعذر فتح ملف البيانات المحلية: {path}.") from exc

    tables: dict[str, pd.DataFrame] = {}
    available_sheets = set(excel.sheet_names)
    for sheet_name in EXPECTED_SHEETS:
        if sheet_name not in available_sheets:
            tables[sheet_name] = pd.DataFrame()
            continue
        tables[sheet_name] = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")

    return {
        "tables": tables,
        "available_sheets": sorted(available_sheets),
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "source_label": _infer_local_source_label(path),
    }


def load_dashboard_datasets() -> dict:
    sheet_id = _resolve_env_value("GOOGLE_SHEET_ID", GOOGLE_SHEET_ID)
    credential_mode, credential_value = _resolve_google_credentials_source()
    local_workbook_path = _resolve_local_workbook_path()
    prefer_local = _resolve_env_value("PREFER_LOCAL_DEMO_DATA", "1" if PREFER_LOCAL_DEMO_DATA else "0") == "1"

    google_configured = bool(sheet_id and credential_mode != "missing" and credential_value)
    local_available = bool(local_workbook_path and local_workbook_path.is_file())

    if prefer_local and local_available:
        return _call_loader(_load_local_workbook_cached, str(local_workbook_path))

    if google_configured:
        return _call_loader(_load_sheets_cached, sheet_id, credential_mode, credential_value)

    if local_available:
        return _call_loader(_load_local_workbook_cached, str(local_workbook_path))

    if not sheet_id:
        raise GoogleSheetsConnectionError(
            "لم يتم ضبط GOOGLE_SHEET_ID، كما لا يوجد ملف بيانات محلي جاهز. أضف إعدادات جوجل شيت أو استخدم ملف البيانات التجريبية."
        )

    raise GoogleSheetsConnectionError(
        "بيانات اعتماد جوجل شيت غير متوفرة، ولا يوجد ملف بيانات محلي بديل. تحقق من .env أو أنشئ البيانات التجريبية."
    )


def clear_dashboard_cache() -> None:
    cache.delete_memoized(_load_sheets_cached)
    cache.delete_memoized(_load_local_workbook_cached)
