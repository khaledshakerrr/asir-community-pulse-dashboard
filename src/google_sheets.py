from __future__ import annotations

import json
from datetime import datetime, timezone

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

from src.config import (
    CACHE_TIMEOUT_SECONDS,
    EXPECTED_SHEETS,
    GOOGLE_SERVICE_ACCOUNT_JSON,
    GOOGLE_SHEET_ID,
    SCOPES,
    cache,
)


class GoogleSheetsConnectionError(RuntimeError):
    """Raised when Google Sheets access cannot be established cleanly."""


def _validate_env_settings(sheet_id: str, service_account_json: str) -> None:
    if not sheet_id:
        raise GoogleSheetsConnectionError(
            "المتغير البيئي GOOGLE_SHEET_ID غير مضبوط. أضفه قبل تشغيل التطبيق."
        )

    if not service_account_json:
        raise GoogleSheetsConnectionError(
            "المتغير البيئي GOOGLE_SERVICE_ACCOUNT_JSON غير مضبوط. أضف محتوى حساب الخدمة بصيغة JSON."
        )


def _build_client(sheet_id: str, service_account_json: str) -> gspread.Client:
    _validate_env_settings(sheet_id, service_account_json)

    try:
        service_account_info = json.loads(service_account_json)
    except json.JSONDecodeError as exc:
        raise GoogleSheetsConnectionError(
            "تعذر قراءة GOOGLE_SERVICE_ACCOUNT_JSON. تأكد أن القيمة JSON صالحة."
        ) from exc

    try:
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES,
        )
        return gspread.authorize(credentials)
    except Exception as exc:
        raise GoogleSheetsConnectionError(
            "فشل إنشاء اتصال Google Sheets. تحقق من صلاحيات حساب الخدمة ونطاقات الوصول."
        ) from exc


@cache.memoize(timeout=CACHE_TIMEOUT_SECONDS)
def _load_sheets_cached(sheet_id: str, service_account_json: str) -> dict:
    client = _build_client(sheet_id, service_account_json)

    try:
        workbook = client.open_by_key(sheet_id)
    except Exception as exc:
        raise GoogleSheetsConnectionError(
            "تعذر فتح ملف Google Sheets. تحقق من GOOGLE_SHEET_ID ومشاركة الملف مع حساب الخدمة."
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
            raise GoogleSheetsConnectionError(
                f"تعذر قراءة الورقة '{sheet_name}' من Google Sheets."
            ) from exc

        tables[sheet_name] = pd.DataFrame(records)

    return {
        "tables": tables,
        "available_sheets": sorted(available_sheets),
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }


def load_dashboard_datasets() -> dict:
    return _load_sheets_cached(GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON)


def clear_dashboard_cache() -> None:
    cache.delete_memoized(_load_sheets_cached)
