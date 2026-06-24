from __future__ import annotations

import dash
from dash import Input, Output, callback, html

from src.charts import build_empty_figure
from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.official_analytics import get_focus_comparison
from src.official_charts import build_regional_ranking_chart, build_utilization_focus_chart
from src.ui_components import chart_card, metric_list_card, page_header, warning_card

dash.register_page(__name__, path="/initiatives", name="الخدمات والجودة", order=4)


def _build_focus_cards(filtered_data: dict):
    if not filtered_data or "tables" not in filtered_data:
        return [
            metric_list_card(
                "ملخص التركيز",
                "ستظهر هنا مقارنة موجزة لعسير والقصيم فور توفر البيانات الرسمية.",
                [],
            )
        ]

    focus = get_focus_comparison(filtered_data)
    if focus.empty:
        return [
            metric_list_card(
                "ملخص التركيز",
                "ستظهر هنا مقارنة موجزة لعسير والقصيم فور توفر البيانات الرسمية.",
                [],
            )
        ]

    focus = focus[focus["display_name"] != "السعودية"].copy()
    rows = []
    for _, row in focus.iterrows():
        rows.append(
            {
                "label": row["display_name"],
                "value": f"{row['community_pulse_index']:.1f} | {row['avg_waiting_time_minutes']:.1f} د",
                "tone": "success" if row["community_pulse_index"] >= 70 else "warning",
            }
        )

    quality_rows = []
    for _, row in focus.iterrows():
        quality_rows.append(
            {
                "label": f"رضا وقت الطبيب - {row['display_name']}",
                "value": f"{row['doctor_time_satisfaction_pct']:.1f}%",
                "tone": "success" if row["doctor_time_satisfaction_pct"] >= 80 else "warning",
            }
        )

    return [
        metric_list_card(
            "قراءة سريعة لعسير والقصيم",
            "القيمة الأولى تمثل الجاهزية المركبة، والثانية تمثل متوسط الانتظار التشغيلي.",
            rows,
        ),
        metric_list_card(
            "جودة التجربة والوصول",
            "مؤشر الرضا هنا يعتمد على وقت الطبيب ضمن البيانات الرسمية المتاحة.",
            quality_rows,
        ),
    ]


def layout():
    return html.Div(
        [
            page_header(
                "الخدمات والجودة",
                "صفحة مخصصة لفهم أين يذهب الطلب الصحي، وكيف تتحرك الجاهزية بين المناطق، وما الذي يجعل عسير والقصيم أكثر أو أقل استعداداً من غيرهما.",
                eyebrow="الخدمات والجودة",
            ),
            html.Div(id="quality-alert", className="message-stack"),
            html.Div(
                [
                    chart_card(
                        "quality-trend-chart",
                        "اتجاه الطلب الصحي السنوي",
                        "يتتبع هذا الرسم الحركة التاريخية للطلب الصحي الرسمي في السعودية وعسير والقصيم من 2020 إلى 2024.",
                        graph_height="400px",
                    ),
                    html.Div(id="quality-side-cards", className="side-stack"),
                ],
                className="dashboard-two-col dashboard-two-col--wide",
            ),
            chart_card(
                "quality-ranking-chart",
                "الترتيب الوطني للجاهزية والمخاطر",
                "ترتيب إقليمي يربط بين المؤشر المركب وضغط المخاطر لتحديد أولويات الدعم والتدخل وتوزيع البرامج.",
                graph_height="440px",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("quality-alert", "children"),
    Output("quality-trend-chart", "figure"),
    Output("quality-side-cards", "children"),
    Output("quality-ranking-chart", "figure"),
    Input("province-filter", "value"),
    Input("gender-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_initiatives_page(province, gender, start_date, end_date, _):
    try:
        datasets = load_dashboard_datasets()
        filtered_data = apply_filters(prepare_dashboard_data(datasets), province, gender, start_date, end_date)
    except GoogleSheetsConnectionError as exc:
        error_figure = build_empty_figure("تعذر تحميل بيانات الخدمات والجودة.")
        return [warning_card(str(exc), title="تعذر الاتصال بمصدر البيانات", tone="danger")], error_figure, _build_focus_cards({}), error_figure

    return [], build_utilization_focus_chart(filtered_data), _build_focus_cards(filtered_data), build_regional_ranking_chart(filtered_data)
