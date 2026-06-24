from __future__ import annotations

import dash
from dash import Input, Output, callback, html

from src.charts import build_empty_figure
from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.maps import build_regions_map
from src.official_analytics import build_executive_kpis
from src.official_charts import (
    build_focus_capacity_chart,
    build_regional_ranking_chart,
    build_utilization_focus_chart,
)
from src.ui_components import chart_card, kpi_card, page_header, warning_card
from src.validators import validate_datasets

dash.register_page(__name__, path="/", name="نظرة عامة", order=0)


def _build_alerts(messages: list[str], tone: str, title: str) -> list:
    return [warning_card(message, title=title, tone=tone) for message in messages]


def layout():
    return html.Div(
        [
            page_header(
                "نظرة عامة تنفيذية",
                "لوحة قيادة عربية تجمع البنية الصحية والطلب التشغيلي والمخاطر الإقليمية الرسمية، مع مقارنة مركزة بين السعودية وعسير والقصيم لدعم القرار على مستوى القيادة.",
                eyebrow="Executive Overview",
            ),
            html.Div(id="overview-alerts", className="message-stack"),
            html.Div(id="overview-kpis", className="kpi-grid"),
            html.Div(
                [
                    chart_card(
                        "overview-capacity-chart",
                        "مقارنة القدرة الصحية بين السعودية وعسير والقصيم",
                        "عرض مباشر لمؤشرات المستشفيات والأسرة والرعاية الأولية وفق معدلات سكانية معيارية تدعم القراءة التنفيذية السريعة.",
                        graph_height="360px",
                    ),
                    chart_card(
                        "overview-trend-chart",
                        "اتجاه الطلب الصحي 2020 - 2024",
                        "سلسلة رسمية ترصد حجم الطلب الصحي الكلي عبر السنوات وتبرز موقع عسير والقصيم مقارنة بالمشهد الوطني.",
                        graph_height="360px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    chart_card(
                        "overview-ranking-chart",
                        "ترتيب المناطق حسب الجاهزية المركبة",
                        "فرز وطني للمناطق يوازن بين المؤشر المركب وضغط المخاطر، ويكشف أين تتقدم المناطق وأين تتطلب دعماً أكبر.",
                        graph_height="470px",
                        graph_config={"displayModeBar": True, "scrollZoom": True, "responsive": True},
                    ),
                    chart_card(
                        "overview-map-chart",
                        "الخريطة التنفيذية للمناطق",
                        "خريطة ضوئية تركز على نقاط تمركز المناطق وتعرض الجاهزية والرضا والطاقة الصحية ضمن تلميحات واضحة وقابلة للعرض التنفيذي.",
                        graph_height="470px",
                    ),
                ],
                className="dashboard-two-col",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("overview-alerts", "children"),
    Output("overview-kpis", "children"),
    Output("overview-capacity-chart", "figure"),
    Output("overview-trend-chart", "figure"),
    Output("overview-ranking-chart", "figure"),
    Output("overview-map-chart", "figure"),
    Input("province-filter", "value"),
    Input("gender-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_overview(province, gender, start_date, end_date, _):
    try:
        datasets = load_dashboard_datasets()
        cleaned_data = prepare_dashboard_data(datasets)
        validation = validate_datasets(cleaned_data["tables"])
        filtered_data = apply_filters(cleaned_data, province, gender, start_date, end_date)
        kpis = build_executive_kpis(filtered_data)
    except GoogleSheetsConnectionError as exc:
        error_figure = build_empty_figure("تعذر تحميل البيانات الحالية.")
        placeholders = [
            kpi_card(label, "غير متاح", "تحقق من الاتصال بمصدر البيانات الرسمي.", accent="warning")
            for label in [
                "إجمالي السكان",
                "مؤشر الجاهزية المركب",
                "رضا وقت الطبيب",
                "عدد المستشفيات",
                "متوسط وقت الانتظار",
                "مناطق الأولوية",
            ]
        ]
        return [warning_card(str(exc), title="تعذر الاتصال بمصدر البيانات", tone="danger")], placeholders, error_figure, error_figure, error_figure, error_figure

    alerts = []
    alerts.extend(_build_alerts(validation["errors"], "danger", "خطأ جودة بيانات"))
    alerts.extend(_build_alerts(validation["warnings"], "warning", "تنبيه جودة بيانات"))

    kpi_cards = [
        kpi_card(metric["label"], metric["value"], metric["hint"], accent="teal" if index % 2 == 0 else "cyan")
        for index, metric in enumerate(kpis)
    ]

    return (
        alerts,
        kpi_cards,
        build_focus_capacity_chart(filtered_data),
        build_utilization_focus_chart(filtered_data),
        build_regional_ranking_chart(filtered_data),
        build_regions_map(filtered_data),
    )
