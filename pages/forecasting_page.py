from __future__ import annotations

import dash
from dash import Input, Output, callback, html

from src.charts import build_empty_figure
from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.forecasting import build_forecast_figure, build_forecast_frame
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.ui_components import chart_card, metric_list_card, page_header, warning_card

dash.register_page(__name__, path="/forecasting", name="التنبؤات", order=5)


def _build_forecast_summary(frame):
    if getattr(frame, "empty", True):
        return [
            metric_list_card(
                "ملخص التوقعات",
                "ستظهر هنا القيم الفعلية والتوقعات الزمنية فور توفر سلسلة تاريخية صالحة للتحليل.",
                [],
            )
        ]

    latest_forecast = frame.dropna(subset=["forecast"]).sort_values("month").tail(1)
    latest_actual = frame.dropna(subset=["actual"]).sort_values("month").tail(1)

    rows = []
    if not latest_actual.empty:
        rows.append({"label": "آخر قيمة فعلية", "value": f"{latest_actual['actual'].iloc[0]:,.1f}", "tone": "neutral"})
    if not latest_forecast.empty:
        rows.append({"label": "أحدث تنبؤ", "value": f"{latest_forecast['forecast'].iloc[0]:,.1f}", "tone": "success"})
        if latest_forecast["lower_bound"].notna().iloc[0]:
            rows.append({"label": "الحد الأدنى", "value": f"{latest_forecast['lower_bound'].iloc[0]:,.1f}", "tone": "warning"})
        if latest_forecast["upper_bound"].notna().iloc[0]:
            rows.append({"label": "الحد الأعلى", "value": f"{latest_forecast['upper_bound'].iloc[0]:,.1f}", "tone": "success"})

    return [
        metric_list_card(
            "ملخص التوقعات",
            "قراءة استشرافية مبنية على السلسلة الزمنية المتاحة، مع إظهار القيم الفعلية ونطاق الثقة المتوقع.",
            rows,
        ),
        warning_card(
            "تعرض هذه الصفحة توقعات تشغيلية استرشادية مبنية على السلاسل الزمنية المتاحة، ولا تمثل تقديرًا سريريًا مباشرًا لانتشار الأمراض المزمنة ما لم تتوفر بيانات رسمية زمنية كافية لذلك.",
            title="تنبيه منهجي",
            tone="warning",
        ),
    ]


def layout():
    return html.Div(
        [
            page_header(
                "توقعات الطلب الصحي والاتجاهات المستقبلية",
                "تعكس هذه الصفحة توقعات الطلب الصحي التشغيلي المستندة إلى السلاسل الزمنية الرسمية المتاحة، مع إبراز القيم الفعلية ونطاق الثقة لدعم التخطيط المبكر.",
                eyebrow="Operational Forecasting",
            ),
            html.Div(id="forecast-alert", className="message-stack"),
            html.Div(
                [
                    chart_card(
                        "forecast-main-chart",
                        "توقعات الطلب الصحي التشغيلي",
                        "رسم زمني يدمج القيم الفعلية بتوقعات الطلب الصحي القادمة، ولا يمثل تقديراً سريرياً مباشراً لانتشار مرض بعينه.",
                        graph_height="430px",
                    ),
                    html.Div(id="forecast-summary-card", className="side-stack"),
                ],
                className="dashboard-two-col dashboard-two-col--wide",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("forecast-alert", "children"),
    Output("forecast-main-chart", "figure"),
    Output("forecast-summary-card", "children"),
    Input("province-filter", "value"),
    Input("gender-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_forecasting_page(province, gender, start_date, end_date, _):
    try:
        datasets = load_dashboard_datasets()
        filtered_data = apply_filters(prepare_dashboard_data(datasets), province, gender, start_date, end_date)
    except GoogleSheetsConnectionError as exc:
        return [warning_card(str(exc), title="تعذر الاتصال بمصدر البيانات", tone="danger")], build_empty_figure(
            "تعذر تحميل بيانات التنبؤات."
        ), _build_forecast_summary(None)

    forecast_frame = build_forecast_frame(filtered_data)
    return [], build_forecast_figure(filtered_data), _build_forecast_summary(forecast_frame)
