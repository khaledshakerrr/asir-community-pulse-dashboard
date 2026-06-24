from __future__ import annotations

import dash
from dash import Input, Output, callback, html

from src.data_cleaning import prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.official_data_pipeline import (
    build_catalog_records,
    build_methodology_rows,
    build_source_overview,
    build_source_reference_rows,
)
from src.ui_components import data_table_card, metric_list_card, page_header, warning_card


dash.register_page(__name__, path="/methodology", name="المصادر والمنهجية", order=9)


COLUMN_LABELS = {
    "artifact_name": "اسم المخرج",
    "source_type": "نوع المصدر",
    "primary_focus": "التركيز التنفيذي",
    "notes": "ملاحظات",
}

SOURCE_REFERENCE_LABELS = {
    "source_name": "اسم المصدر",
    "category": "الفئة",
    "status": "الحالة",
    "description": "وصف الاستخدام",
    "source_link": "الرابط",
}


def _build_empty_cards():
    return (
        metric_list_card(
            "ملخص المصادر",
            "ستظهر هنا حالة المصادر الرسمية والمخرجات المعتمدة فور توفر البيانات.",
            [],
        ),
        metric_list_card(
            "المنهجية التحليلية",
            "سيظهر هنا شرح مختصر لكيفية بناء المؤشرات والتنبؤات الحالية.",
            [],
        ),
        data_table_card(
            "سجل المخرجات المرجعية",
            "قائمة بالمخرجات والملفات التي تستند عليها هذه النسخة من المنصة.",
            ["artifact_name", "source_type", "primary_focus", "notes"],
            [],
            column_labels=COLUMN_LABELS,
        ),
        data_table_card(
            "سجل المصادر الفعلية",
            "ستظهر هنا جميع المصادر المستخدمة وروابطها المباشرة بمجرد تحميل الصفحة.",
            ["source_name", "category", "status", "description", "source_link"],
            [],
            column_labels=SOURCE_REFERENCE_LABELS,
        ),
    )


def _build_disease_methodology_card():
    return metric_list_card(
        "منهجية طبقة الأمراض المعدية",
        "تلخص هذه البطاقة ما هو رسمي مباشر وما هو مشتق حسابيًا داخل طبقة الأمراض المعدية الجديدة.",
        [
            {
                "label": "ما تم استخراجه رسميًا",
                "value": "جداول الأمراض المعدية حسب المنطقة والشهر والعمر والجنس والجنسية، إضافة إلى الدرن والملاريا والبلهارسيا والليشمانيا وفاشيات الغذاء والتسممات عند توفرها في الكتاب الإحصائي.",
                "tone": "success",
            },
            {
                "label": "الحالات لكل 100 ألف",
                "value": "يُحسب بالمعادلة: عدد الحالات ÷ عدد السكان × 100000، باستخدام بيانات السكان الرسمية المتاحة على مستوى المنطقة.",
                "tone": "neutral",
            },
            {
                "label": "مؤشر ضغط المرض على الطاقة الصحية",
                "value": "يربط عبء الحالات المعياري مع وقت الانتظار وكثافة المستشفيات والأسرة والأطباء لإخراج أولوية تدخل منخفضة أو متوسطة أو مرتفعة.",
                "tone": "warning",
            },
            {
                "label": "حدود التنبؤ",
                "value": "التوقعات الحالية تشغيلية استباقية مبنية على السلاسل الزمنية الرسمية المتاحة، ولا تعني تشخيصًا سريريًا مباشرًا أو سببية مؤكدة بين الطقس والمرض.",
                "tone": "warning",
            },
        ],
    )


def layout():
    return html.Div(
        [
            page_header(
                "المصادر والمنهجية",
                "صفحة توثيق تنفيذية داخل التطبيق توضح ما هو رسمي مباشر، وما هو مشتق تحليلي، وما الذي تعكسه المؤشرات الحالية قبل عرضها على العميل أو الجهات التنفيذية.",
                eyebrow="المصادر والمنهجية",
            ),
            html.Div(
                html.A("تحميل ملف التوثيق PDF", href="/documentation/pdf", target="_blank", className="download-link"),
                className="page-actions",
            ),
            html.Div(id="methodology-alert", className="message-stack"),
            html.Div(
                [
                    html.Div(id="methodology-source-summary"),
                    html.Div(id="methodology-approach-summary"),
                ],
                className="dashboard-two-col",
            ),
            html.Div(id="methodology-disease-summary"),
            html.Div(id="methodology-catalog", className="page-stack"),
        ],
        className="page-stack",
    )


@callback(
    Output("methodology-alert", "children"),
    Output("methodology-source-summary", "children"),
    Output("methodology-approach-summary", "children"),
    Output("methodology-disease-summary", "children"),
    Output("methodology-catalog", "children"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_methodology_page(_):
    try:
        datasets = load_dashboard_datasets()
        cleaned_data = prepare_dashboard_data(datasets)
    except GoogleSheetsConnectionError as exc:
        source_card, approach_card, catalog_card, reference_card = _build_empty_cards()
        return [warning_card(str(exc), title="تعذر تحميل سجل المصادر", tone="danger")], source_card, approach_card, _build_disease_methodology_card(), [catalog_card, reference_card]

    source_card = metric_list_card(
        "ملخص المصادر",
        "قراءة سريعة لحالة الملفات المرجعية والمخرجات الرسمية المستخدمة في المنصة الحالية.",
        build_source_overview(cleaned_data),
    )
    approach_card = metric_list_card(
        "المنهجية التحليلية",
        "هذه الصفحة تفرق بوضوح بين البيانات الرسمية المباشرة والمؤشرات المشتقة والتنبؤات الاسترشادية.",
        build_methodology_rows(cleaned_data),
    )
    catalog_card = data_table_card(
        "سجل المخرجات المرجعية",
        "يوضح هذا الجدول المخرجات الأساسية، ونوع المصدر، والغرض التنفيذي لكل ملف داخل طبقة البيانات الحالية.",
        ["artifact_name", "source_type", "primary_focus", "notes"],
        build_catalog_records(cleaned_data),
        column_labels=COLUMN_LABELS,
    )
    reference_card = data_table_card(
        "سجل المصادر الفعلية",
        "جميع المصادر المستخدمة أو المهيأة في هذه النسخة مع وصف واضح لطبيعة استخدامها ورابط مباشر لكل مصدر.",
        ["source_name", "category", "status", "description", "source_link"],
        build_source_reference_rows(),
        column_labels=SOURCE_REFERENCE_LABELS,
    )

    return [], source_card, approach_card, _build_disease_methodology_card(), [catalog_card, reference_card]
