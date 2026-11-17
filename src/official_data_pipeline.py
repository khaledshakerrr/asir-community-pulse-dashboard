from __future__ import annotations

from pathlib import Path

import pandas as pd
from dash import html

from src.source_registry import get_source_registry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_FALLBACK_PATH = PROJECT_ROOT / "data" / "official_google_sheet_tabs" / "source_catalog.csv"
CHRONIC_CARE_CATALOG_ROWS = [
    {
        "artifact_name": "لقطات خدمات رعاية السكري والمرافق المتخصصة",
        "source_type": "رسمي مباشر",
        "source_files": "الكتب الإحصائية السنوية لوزارة الصحة 2022 و2023 و2024",
        "primary_focus": "الطلب على عيادات السكري والطاقة المتخصصة في السعودية وعسير وبيشة والقصيم",
        "notes": "زيارات السكري 2023 و2024، ومرافق الوزارة 2022–2024. تُحفظ جغرافية المصدر ويُفصل إجمالي تجمع عسير عن صفّي عسير وبيشة.",
    },
    {
        "artifact_name": "زيارات التأهيل بعد البتر المرتبط بالسكري",
        "source_type": "رسمي مباشر",
        "source_files": "الكتاب الإحصائي لوزارة الصحة 2023، جدول 4-37؛ و2024، جدول 4-45",
        "primary_focus": "زيارات التأهيل الطبي المرتبطة بالسكري على مستوى المملكة لعامي 2023 و2024",
        "notes": "زيارات خدمة بوزارة الصحة، وليست أعداد عمليات البتر أو المرضى الفريدين أو معدل المضاعفات. لا يوجد تفصيل إقليمي في الجدولين.",
    },
    {
        "artifact_name": "مرضى الغسيل الكلوي حسب نوع التنقية والقطاع",
        "source_type": "رسمي مباشر",
        "source_files": "الكتاب الإحصائي لوزارة الصحة 2024، جدول 4-42؛ مطابقة الإجمالي بالجدول 4-43",
        "primary_focus": "مرضى التنقية الدموية والبريتونية حسب القطاع الصحي على مستوى المملكة لعام 2024",
        "notes": "أعداد مرضى بجميع القطاعات. الإجمالي المنشور منفصل عن تفاصيل القطاعات ولا يجمع معها مرة أخرى. يُستخدم عام 2024 فقط.",
    },
]


def load_source_catalog(data_bundle: dict | None = None) -> pd.DataFrame:
    if data_bundle and "tables" in data_bundle:
        catalog = data_bundle["tables"].get("source_catalog", pd.DataFrame()).copy()
        if not catalog.empty:
            return pd.concat([catalog, pd.DataFrame(CHRONIC_CARE_CATALOG_ROWS)], ignore_index=True).fillna("")

    if CATALOG_FALLBACK_PATH.is_file():
        return pd.concat([pd.read_csv(CATALOG_FALLBACK_PATH), pd.DataFrame(CHRONIC_CARE_CATALOG_ROWS)], ignore_index=True).fillna("")

    return pd.DataFrame(CHRONIC_CARE_CATALOG_ROWS)


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
        {
            "label": "بيانات الرعاية المزمنة الرسمية",
            "value": "زيارات عيادات السكري تقيس استخدام الخدمة وليست أعداد مرضى أو نسب انتشار. المرافق تشمل وزارة الصحة فقط. بيانات المناطق الصحية والتجمعات الصحية لقطات سنوية مستقلة، دون افتراض تطابق الحدود أو تحويلها إلى سلسلة شهرية.",
            "tone": "neutral",
        },
        {
            "label": "مؤشرات التأهيل والغسيل الكلوي الوطنية",
            "value": "التأهيل يقيس زيارات ما بعد البتر المرتبط بالسكري، وبيانات الغسيل الكلوي تقيس أعداد المرضى بجميع القطاعات. لا تُنسب هذه القيم الوطنية إلى عسير ولا تتأثر بالمرشحات الإقليمية. إجماليات المرضى منفصلة عن تفاصيل القطاعات لمنع التكرار.",
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
