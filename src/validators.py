
from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
import pandas as pd

from src.config import EXPECTED_COLUMNS, REQUIRED_SHEETS


def validate_datasets(tables: dict) -> dict[str, list[str]]:
    warnings: list[str] = []
    errors: list[str] = []

    if not tables:
        errors.append("لا توجد جداول محملة من المصدر.")
        return {"warnings": warnings, "errors": errors}

    for sheet_name, required_columns in EXPECTED_COLUMNS.items():
        frame = tables.get(sheet_name)

        if frame is None or frame.empty:
            if sheet_name == "clean_regions_master" and not tables.get("regions_master", pd.DataFrame()).empty:
                warnings.append(
                    "ورقة clean_regions_master غير متوفرة، وتم استخدام regions_master كبديل."
                )
                continue

            if sheet_name in REQUIRED_SHEETS:
                errors.append(f"ورقة البيانات المطلوبة '{sheet_name}' غير متوفرة أو فارغة.")
            else:
                warnings.append(f"ورقة البيانات '{sheet_name}' غير متوفرة أو فارغة.")
            continue

        missing_columns = sorted(set(required_columns) - set(frame.columns))
        if missing_columns:
            warnings.append(
                f"الورقة '{sheet_name}' تفتقد الأعمدة التالية: {', '.join(missing_columns)}"
            )

    return {"warnings": warnings, "errors": errors}
