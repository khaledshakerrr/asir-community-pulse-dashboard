from __future__ import annotations

import dash
from dash import Input, Output, callback, html

import pandas as pd

from src.charts import build_empty_figure
from src.data_cleaning import prepare_dashboard_data
from src.environmental_charts import build_alert_distribution_chart, build_environment_map, build_forecast_trend_chart
from src.environmental_models import build_early_warning_rows, build_environmental_current_frame, build_environmental_forecast_frame
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.ui_components import chart_card, metric_list_card, page_header, warning_card


dash.register_page(__name__, path="/early-warning", name="الإنذار المبكر", order=7)


def _build_warning_cards(current_frame, forecast_frame):
    return [
        metric_list_card(
            "تنبيهات الأولوية",
            "هذا السجل يجمع المدن الأعلى أولوية من منظور الهواء والغبار والحرارة والضغط التشغيلي المتوقع خلال 7 أيام.",
            build_early_warning_rows(current_frame, forecast_frame),
        )
    ]


def layout():
    return html.Div(
        [
            page_header(
                "الإنذار المبكر",
                "نظام إنذار بيئي وصحي مبكر يربط الرصد الحالي والتوقع القصير بالتحليل التنفيذي، بهدف كشف المدن التي قد تشهد ضغطًا أعلى على الخدمات الصحية قبل تفاقمه.",
                eyebrow="الإنذار المبكر",
            ),
            html.Div(id="early-warning-alert", className="message-stack"),
            html.Div(
                [
                    chart_card(
                        "early-warning-map-chart",
                        "خريطة الإنذار المبكر",
                        "تعكس التلوين الحالي وفق مستوى المخاطر التنفسية مع تفاصيل مختصرة حول محركات الخطر في كل مدينة.",
                        graph_height="520px",
                        graph_config={"displayModeBar": True, "scrollZoom": True, "responsive": True},
                    ),
                    html.Div(id="early-warning-side-cards", className="side-stack"),
                ],
                className="dashboard-two-col dashboard-two-col--wide",
            ),
            html.Div(
                [
                    chart_card(
                        "early-warning-distribution-chart",
                        "توزيع مستويات الإنذار",
                        "عدد المدن في كل مستوى إنذار ضمن النطاق الحالي لحظيًا.",
                        graph_height="380px",
                    ),
                    chart_card(
                        "early-warning-forecast-chart",
                        "اتجاه الضغط التشغيلي المتوقع",
                        "يتتبع هذا الرسم المدن الأشد ضغطًا في التوقع الأسبوعي المبكر.",
                        graph_height="380px",
                    ),
                ],
                className="dashboard-two-col",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("early-warning-alert", "children"),
    Output("early-warning-map-chart", "figure"),
    Output("early-warning-side-cards", "children"),
    Output("early-warning-distribution-chart", "figure"),
    Output("early-warning-forecast-chart", "figure"),
    Input("province-filter", "value"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_early_warning_page(province, _):
    try:
        datasets = load_dashboard_datasets()
        filtered_data = prepare_dashboard_data(datasets)
        current_frame = build_environmental_current_frame(filtered_data, province)
        forecast_frame = build_environmental_forecast_frame(filtered_data, province)
    except GoogleSheetsConnectionError as exc:
        empty = build_empty_figure("تعذر تحميل بيانات الإنذار المبكر.")
        return [warning_card(str(exc), title="تعذر تحميل البيانات الأساسية", tone="danger")], empty, _build_warning_cards(
            pd.DataFrame(), pd.DataFrame()
        ), empty, empty
    except Exception as exc:
        empty = build_empty_figure("تعذر تحميل بيانات الإنذار المبكر.")
        return [warning_card(str(exc), title="تعذر تحميل الإنذار المبكر", tone="danger")], empty, _build_warning_cards(
            pd.DataFrame(), pd.DataFrame()
        ), empty, empty

    alerts = []
    if province not in {None, "", "الكل", "عسير", "القصيم"}:
        alerts.append(
            warning_card(
                "يركز نظام الإنذار المبكر الحالي على مدن عسير والقصيم فقط.",
                title="نطاق التغطية الحالي",
                tone="warning",
            )
        )

    return (
        alerts,
        build_environment_map(current_frame, "respiratory_risk_index", "الخطر التنفسي"),
        _build_warning_cards(current_frame, forecast_frame),
        build_alert_distribution_chart(current_frame),
        build_forecast_trend_chart(forecast_frame, "operational_pressure_forecast", "الضغط التشغيلي المتوقع"),
    )
