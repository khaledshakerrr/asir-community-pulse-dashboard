from __future__ import annotations

from pathlib import Path

import pandas as pd
from dash import html

from src.source_registry import get_source_registry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_FALLBACK_PATH = PROJECT_ROOT / "data" / "official_google_sheet_tabs" / "source_catalog.csv"


def load_source_catalog(data_bundle: dict | None = None) -> pd.DataFrame:
    if data_bundle and "tables" in data_bundle:
        catalog = data_bundle["tables"].get("source_catalog", pd.DataFrame()).copy()
        if not catalog.empty:
            return catalog.fillna("")

    if CATALOG_FALLBACK_PATH.is_file():
        return pd.read_csv(CATALOG_FALLBACK_PATH).fillna("")

    return pd.DataFrame(columns=["artifact_name", "source_type", "source_files", "primary_focus", "notes"])


def build_source_overview(data_bundle: dict | None = None) -> list[dict[str, str]]:
    catalog = load_source_catalog(data_bundle)
    if catalog.empty:
        return [
            {"label": "ملفات المصادر", "value": "غير متاح", "tone": "warning"},
            {"label": "توثيق المنهجية", "value": "قيد التهيئة", "tone": "warning"},
        ]

    source_types = sorted({value for value in catalog["source_type"].astype(str) if value.strip()})
    direct_count = int(catalog["source_type"].astype(str).str.contains("رسمي مباشر", na=False).sum())

    return [
        {"label": "عدد الملفات المرجعية", "value": f"{len(catalog):,}", "tone": "neutral"},
        {"label": "المخرجات ذات المصدر الرسمي المباشر", "value": f"{direct_count:,.0f}", "tone": "success"},
        {"label": "أنماط المصادر", "value": " | ".join(source_types) if source_types else "غير متاح", "tone": "neutral"},
    ]


def build_methodology_rows(data_bundle: dict | None = None) -> list[dict[str, str]]:
    rows = [
        {
            "label": "البيانات الرسمية المباشرة",
            "value": "السكان، البنية الصحية، القوى العاملة، والوصول للخدمة من المصادر الحكومية المنشورة",
            "tone": "success",
        },
        {
            "label": "المؤشرات المشتقة",
            "value": "مؤشرات مركبة تشغيلية تربط القدرة الصحية والرضا والضغط الخدمي لدعم القرار",
            "tone": "warning",
        },
        {
            "label": "التنبؤات الحالية",
            "value": "تنبؤات تشغيلية استرشادية للطلب الصحي، وليست تشخيصًا سريريًا مباشرًا للأمراض",
            "tone": "neutral",
        },
    ]

    catalog = load_source_catalog(data_bundle)
    if not catalog.empty:
        rows.append(
            {
                "label": "التركيز التنفيذي",
                "value": "مقارنة المملكة مع عسير والقصيم مع تفصيلات داخلية قابلة للعرض أمام الجهات التنفيذية",
                "tone": "success",
            }
        )
    return rows


def build_catalog_records(data_bundle: dict | None = None) -> list[dict[str, str]]:
    catalog = load_source_catalog(data_bundle)
    if catalog.empty:
        return []

    records: list[dict[str, str]] = []
    for _, row in catalog.iterrows():
        records.append(
            {
                "artifact_name": str(row.get("artifact_name", "")).strip(),
                "source_type": str(row.get("source_type", "")).strip(),
                "primary_focus": str(row.get("primary_focus", "")).strip(),
                "notes": str(row.get("notes", "")).strip(),
            }
        )
    return records


def build_source_reference_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in get_source_registry():
        rows.append(
            {
                "source_name": item["source_name"],
                "category": item["category"],
                "status": item["status"],
                "description": item["description"],
                "source_link": html.A("فتح المصدر", href=item["url"], target="_blank", className="source-link"),
            }
        )
    return rows
