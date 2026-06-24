from __future__ import annotations

import dash
from dash import Input, Output, callback, html

from src.charts import build_empty_figure
from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.official_charts import build_service_mix_chart, build_workforce_share_chart, build_workforce_totals_chart
from src.ui_components import chart_card, page_header, warning_card

dash.register_page(__name__, path="/complaints", name="القوى العاملة والطاقة", order=3)


def layout():
    return html.Div(
        [
            page_header(
                "القوى العاملة والطاقة الاستيعابية",
                "رؤية تنفيذية لهيكل الكوادر الصحية ومزيج الخدمة في عسير والقصيم، مع إبراز أين تقود وزارة الصحة وأين يعتمد المشهد على بقية القطاعات.",
                eyebrow="القوى العاملة والطاقة",
            ),
            html.Div(id="workforce-alert", className="message-stack"),
            html.Div(
                [
                    chart_card(
                        "workforce-totals-chart",
                        "إجمالي الكوادر الصحية حسب المنطقة",
                        "مقارنة مباشرة بين الأطباء والتمريض والصيادلة في عسير وبيشة والقصيم عبر كافة القطاعات الصحية.",
                        graph_height="380px",
                    ),
                    chart_card(
                        "workforce-share-chart",
                        "حصة وزارة الصحة من الأطباء",
                        "يوضح هذا الرسم مدى اعتماد كل منطقة على كوادر وزارة الصحة مقارنة بإجمالي الطاقة الطبية المتاحة في جميع القطاعات.",
                        graph_height="380px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            chart_card(
                "workforce-service-mix-chart",
                "مزيج الخدمات بين عسير والقصيم",
                "توزيع المستشفيات ومراكز الرعاية والصيدليات الخاصة داخل المنطقتين لإظهار شكل البنية الصحية التي يستند عليها التشغيل والتوسع.",
                graph_height="420px",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("workforce-alert", "children"),
    Output("workforce-totals-chart", "figure"),
    Output("workforce-share-chart", "figure"),
    Output("workforce-service-mix-chart", "figure"),
    Input("province-filter", "value"),
    Input("gender-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_complaints_page(province, gender, start_date, end_date, _):
    try:
        datasets = load_dashboard_datasets()
        filtered_data = apply_filters(prepare_dashboard_data(datasets), province, gender, start_date, end_date)
    except GoogleSheetsConnectionError as exc:
        error_figure = build_empty_figure("تعذر تحميل بيانات القوى العاملة والطاقة الاستيعابية.")
        return [warning_card(str(exc), title="تعذر الاتصال بمصدر البيانات", tone="danger")], error_figure, error_figure, error_figure

    return [], build_workforce_totals_chart(filtered_data), build_workforce_share_chart(filtered_data), build_service_mix_chart(filtered_data)
