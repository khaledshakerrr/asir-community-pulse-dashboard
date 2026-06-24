from __future__ import annotations

import dash
from dash import Input, Output, callback, html

import pandas as pd

from src.charts import build_empty_figure
from src.data_cleaning import prepare_dashboard_data
from src.disease_intelligence import build_environmental_context_cards
from src.environmental_charts import build_city_environment_bar, build_forecast_heatmap, build_forecast_trend_chart
from src.environmental_models import build_environmental_current_frame, build_environmental_forecast_frame
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.ui_components import chart_card, kpi_card, metric_list_card, page_header, warning_card


dash.register_page(__name__, path="/respiratory-risk", name="المخاطر التنفسية", order=6)


def _build_respiratory_side_cards(current_frame):
    if current_frame.empty:
        return [
            metric_list_card(
                "ملخص المخاطر التنفسية",
                "ستظهر هنا أعلى المدن تعرضًا للمخاطر التنفسية فور توفر الرصد البيئي.",
                [],
            )
        ]

    rows = []
    for _, row in current_frame.sort_values("respiratory_risk_index", ascending=False).head(5).iterrows():
        rows.append(
            {
                "label": f"{row['city_ar']} - {row['province_ar']}",
                "value": f"تنفسي {row['respiratory_risk_index']:.1f} | ربو {row['asthma_risk_score']:.1f}",
                "tone": "danger" if row["respiratory_risk_index"] >= 75 else "warning",
            }
        )

    return [
        metric_list_card(
            "أعلى المدن تعرضًا",
            "القيمة الأولى هي الخطر التنفسي الكلي، والثانية تمثل خطر الربو المرتبط بالهواء والغبار.",
            rows,
        )
    ]


def layout():
    return html.Div(
        [
            page_header(
                "المخاطر التنفسية",
                "صفحة مركزة على المخاطر المرتبطة بالهواء والغبار والموسمية والعبء المزمن، وتعرض مؤشرات تنفسية يومية وتوقعات أسبوعية قابلة للعرض التنفيذي.",
                eyebrow="المخاطر التنفسية",
            ),
            html.Div(id="respiratory-alert", className="message-stack"),
            html.Div(id="respiratory-live-context", className="kpi-grid"),
            html.Div(
                [
                    chart_card(
                        "respiratory-ranking-chart",
                        "ترتيب المدن حسب الخطر التنفسي",
                        "مؤشر مركب يربط PM2.5 وPM10 والغبار ومؤشر AQI والعبء المزمن في المنطقة.",
                        graph_height="430px",
                    ),
                    html.Div(id="respiratory-side-cards", className="side-stack"),
                ],
                className="dashboard-two-col dashboard-two-col--wide",
            ),
            html.Div(
                [
                    chart_card(
                        "respiratory-forecast-chart",
                        "توقع أسبوعي للمخاطر التنفسية",
                        "يتابع تطور المخاطر اليومية خلال الأيام السبعة القادمة في أكثر المدن حساسية للرصد.",
                        graph_height="390px",
                    ),
                    chart_card(
                        "respiratory-heatmap-chart",
                        "خريطة حرارية أسبوعية للخطر التنفسي",
                        "كلما اقترب اللون من الأحمر ارتفع الضغط التنفسي المتوقع على مستوى المدينة واليوم.",
                        graph_height="390px",
                    ),
                ],
                className="dashboard-two-col",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("respiratory-alert", "children"),
    Output("respiratory-live-context", "children"),
    Output("respiratory-ranking-chart", "figure"),
    Output("respiratory-side-cards", "children"),
    Output("respiratory-forecast-chart", "figure"),
    Output("respiratory-heatmap-chart", "figure"),
    Input("province-filter", "value"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_respiratory_page(province, _):
    try:
        datasets = load_dashboard_datasets()
        filtered_data = prepare_dashboard_data(datasets)
        current_frame = build_environmental_current_frame(filtered_data, province)
        forecast_frame = build_environmental_forecast_frame(filtered_data, province)
    except GoogleSheetsConnectionError as exc:
        empty = build_empty_figure("تعذر تحميل بيانات المخاطر التنفسية.")
        return [warning_card(str(exc), title="تعذر تحميل البيانات الأساسية", tone="danger")], [], empty, _build_respiratory_side_cards(
            pd.DataFrame()
        ), empty, empty
    except Exception as exc:
        empty = build_empty_figure("تعذر تحميل بيانات المخاطر التنفسية.")
        return [warning_card(str(exc), title="تعذر تحميل البيانات التنفسية الحية", tone="danger")], [], empty, _build_respiratory_side_cards(
            pd.DataFrame()
        ), empty, empty

    alerts = []
    if province not in {None, "", "الكل", "عسير", "القصيم"}:
        alerts.append(
            warning_card(
                "طبقة المخاطر التنفسية الحية تغطي حاليًا عسير والقصيم فقط.",
                title="نطاق التغطية الحالي",
                tone="warning",
            )
        )

    live_cards = [
        kpi_card(metric["label"], metric["value"], metric["hint"], accent="teal" if index % 2 == 0 else "cyan")
        for index, metric in enumerate(build_environmental_context_cards(filtered_data, province))
    ]

    return (
        alerts,
        live_cards,
        build_city_environment_bar(current_frame, "respiratory_risk_index", "الخطر التنفسي", "respiratory_risk_index"),
        _build_respiratory_side_cards(current_frame),
        build_forecast_trend_chart(forecast_frame, "respiratory_risk_index", "الخطر التنفسي المتوقع"),
        build_forecast_heatmap(forecast_frame, "respiratory_risk_index", "الخطر"),
    )
