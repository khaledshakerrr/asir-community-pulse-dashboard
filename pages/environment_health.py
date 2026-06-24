from __future__ import annotations

import dash
from dash import Input, Output, callback, html

from src.data_cleaning import prepare_dashboard_data
from src.charts import build_empty_figure
from src.environmental_charts import (
    build_city_environment_bar,
    build_environment_map,
    build_forecast_trend_chart,
    build_multi_metric_scatter,
)
from src.environmental_models import build_environmental_current_frame, build_environmental_forecast_frame, build_environmental_kpis
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.ui_components import chart_card, kpi_card, page_header, warning_card


dash.register_page(__name__, path="/environment-health", name="البيئة والصحة", order=5)


def _build_kpi_cards(current_frame, forecast_frame):
    metrics = build_environmental_kpis(current_frame, forecast_frame)
    return [
        kpi_card(metric["label"], metric["value"], metric["hint"], accent="teal" if index % 2 == 0 else "cyan")
        for index, metric in enumerate(metrics)
    ]


def layout():
    return html.Div(
        [
            page_header(
                "البيئة والصحة",
                "لوحة تنفيذية حية تربط الحرارة والرطوبة والرياح والأمطار والجودة الهوائية بالمشهد الصحي في عسير والقصيم، مع قراءة مكانية للمخاطر البيئية الأشد تأثيرًا على التشغيل الصحي.",
                eyebrow="البيئة والصحة",
            ),
            html.Div(id="environment-alert", className="message-stack"),
            html.Div(id="environment-kpis", className="kpi-grid kpi-grid--four"),
            html.Div(
                [
                    chart_card(
                        "environment-map-chart",
                        "خريطة الصحة البيئية",
                        "توضح تمركز المدن المستهدفة وتلونها بحسب مستوى المخاطر الحالية، مع إظهار الحرارة والرطوبة والهواء في التلميحات.",
                        graph_height="520px",
                        graph_config={"displayModeBar": True, "scrollZoom": True, "responsive": True},
                    ),
                    chart_card(
                        "environment-air-chart",
                        "ترتيب المدن حسب ضغط جودة الهواء",
                        "كلما ارتفعت القيمة زاد الضغط البيئي على التنفس والتشغيل الصحي في المدينة المعنية.",
                        graph_height="520px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    chart_card(
                        "environment-scatter-chart",
                        "العلاقة بين PM2.5 والحرارة",
                        "تجمع هذه القراءة بين الجسيمات الدقيقة والحرارة الحالية وحجم المخاطر التنفسية في كل مدينة.",
                        graph_height="400px",
                    ),
                    chart_card(
                        "environment-forecast-chart",
                        "اتجاه الضغط البيئي خلال 7 أيام",
                        "توقع قصير المدى يبرز المدن الأشد تأثرًا بيئيًا في الأفق القريب بالاعتماد على الرصد والتوقعات العامة الحية.",
                        graph_height="400px",
                    ),
                ],
                className="dashboard-two-col",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("environment-alert", "children"),
    Output("environment-kpis", "children"),
    Output("environment-map-chart", "figure"),
    Output("environment-air-chart", "figure"),
    Output("environment-scatter-chart", "figure"),
    Output("environment-forecast-chart", "figure"),
    Input("province-filter", "value"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_environment_page(province, _):
    try:
        datasets = load_dashboard_datasets()
        filtered_data = prepare_dashboard_data(datasets)
        current_frame = build_environmental_current_frame(filtered_data, province)
        forecast_frame = build_environmental_forecast_frame(filtered_data, province)
    except GoogleSheetsConnectionError as exc:
        figure = build_empty_figure("تعذر تحميل البيانات البيئية الحية.")
        return [warning_card(str(exc), title="تعذر تحميل البيانات الأساسية", tone="danger")], [], figure, figure, figure, figure
    except Exception as exc:
        figure = build_empty_figure("تعذر تحميل البيانات البيئية الحية.")
        return [warning_card(str(exc), title="تعذر تحميل البيانات البيئية الحية", tone="danger")], [], figure, figure, figure, figure

    alerts = []
    if province not in {None, "", "الكل", "عسير", "القصيم"}:
        alerts.append(
            warning_card(
                "تغطي هذه الصفحة حاليًا مدن عسير والقصيم فقط ضمن طبقة الرصد البيئي الحية.",
                title="نطاق التغطية الحالي",
                tone="warning",
            )
        )

    if current_frame.empty:
        figure = build_environment_map(current_frame, "environmental_health_score", "المؤشر البيئي")
        alerts.append(
            warning_card(
                "لا توجد مدن بيئية مطابقة للمرشح الحالي. اختر الكل أو عسير أو القصيم لعرض الرصد الحي.",
                title="لا توجد بيانات مطابقة",
                tone="warning",
            )
        )
        return alerts, [], figure, figure, figure, figure

    return (
        alerts,
        _build_kpi_cards(current_frame, forecast_frame),
        build_environment_map(current_frame, "environmental_health_score", "مؤشر الصحة البيئية"),
        build_city_environment_bar(current_frame, "air_quality_score", "ضغط جودة الهواء", "air_quality_score"),
        build_multi_metric_scatter(current_frame),
        build_forecast_trend_chart(forecast_frame, "operational_pressure_forecast", "الضغط التشغيلي المتوقع"),
    )
