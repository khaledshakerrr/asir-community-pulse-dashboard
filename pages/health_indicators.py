from __future__ import annotations

import dash
from dash import Input, Output, callback, html

from src.charts import build_empty_figure
from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.official_charts import (
    build_asir_cluster_capacity_chart,
    build_focus_access_chart,
    build_focus_capacity_chart,
    build_qassim_population_chart,
)
from src.ui_components import chart_card, page_header, warning_card

dash.register_page(__name__, path="/health-indicators", name="المقارنة الإقليمية", order=2)


def layout():
    return html.Div(
        [
            page_header(
                "المقارنة الإقليمية",
                "تحليل مباشر يضع السعودية وعسير والقصيم في إطار واحد، ثم يهبط إلى تفصيل محافظات القصيم وتجمعات عسير لإظهار الفروق التي تهم صانع القرار.",
                eyebrow="Regional Comparison",
            ),
            html.Div(id="regional-alert", className="message-stack"),
            html.Div(
                [
                    chart_card(
                        "regional-capacity-chart",
                        "مقارنة البنية الصحية المعيارية",
                        "ثلاثة مقاييس قياسية تقيس كثافة المستشفيات والأسرة والرعاية الأولية بين السعودية وعسير والقصيم.",
                        graph_height="360px",
                    ),
                    chart_card(
                        "regional-access-chart",
                        "الوصول الرقمي والرضا",
                        "قياس متكامل بين الرضا عن وقت الطبيب والاستفادة من الاستشارات عن بعد والوصول إلى السجل الطبي.",
                        graph_height="360px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    chart_card(
                        "regional-qassim-chart",
                        "تفصيل محافظات القصيم سكانياً",
                        "حجم المحافظات داخل القصيم يحدد أين يجب أن تتوزع الطاقة والخدمة عند بناء نماذج التدخل والاستهداف.",
                        graph_height="420px",
                    ),
                    chart_card(
                        "regional-asir-chart",
                        "تفصيل تجمعات عسير الصحية",
                        "مقارنة داخلية بين تجمع عسير وتجمع بيشة على مستوى الأسرة والعناية المركزة وزيارات عيادات السكري.",
                        graph_height="420px",
                    ),
                ],
                className="dashboard-two-col",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("regional-alert", "children"),
    Output("regional-capacity-chart", "figure"),
    Output("regional-access-chart", "figure"),
    Output("regional-qassim-chart", "figure"),
    Output("regional-asir-chart", "figure"),
    Input("province-filter", "value"),
    Input("gender-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_health_page(province, gender, start_date, end_date, _):
    try:
        datasets = load_dashboard_datasets()
        filtered_data = apply_filters(prepare_dashboard_data(datasets), province, gender, start_date, end_date)
    except GoogleSheetsConnectionError as exc:
        error_figure = build_empty_figure("تعذر تحميل بيانات المقارنة الإقليمية في الوقت الحالي.")
        return (
            [warning_card(str(exc), title="تعذر الاتصال بمصدر البيانات", tone="danger")],
            error_figure,
            error_figure,
            error_figure,
            error_figure,
        )

    return (
        [],
        build_focus_capacity_chart(filtered_data),
        build_focus_access_chart(filtered_data),
        build_qassim_population_chart(filtered_data),
        build_asir_cluster_capacity_chart(filtered_data),
    )
