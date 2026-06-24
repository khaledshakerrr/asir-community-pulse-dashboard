from __future__ import annotations

import dash
import pandas as pd
from dash import Input, Output, callback, dcc, html

from src.charts import build_empty_figure
from src.data_cleaning import prepare_dashboard_data
from src.disease_intelligence import (
    build_disease_filter_options,
    build_disease_forecast_figure,
    build_disease_forecast_frame,
    build_environmental_context_cards,
    build_malaria_seasonal_forecast_figure,
    build_malaria_seasonal_forecast_frame,
    build_operational_recommendations_rows,
    load_disease_curated_tables,
)
from src.environmental_charts import build_forecast_heatmap, build_forecast_trend_chart
from src.environmental_models import build_environmental_forecast_frame
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.ui_components import chart_card, data_table_card, kpi_card, metric_list_card, page_header, warning_card


dash.register_page(__name__, path="/forecasting", name="التنبؤات الصحية", order=8)

RECOMMENDATION_LABELS = {
    "disease_name_ar": "المرض",
    "health_region_ar": "المنطقة",
    "risk_level_ar": "مستوى الخطر",
    "recommendation_ar": "التوصية",
}


def _dropdown_options(values: list[str]) -> list[dict[str, str]]:
    return [{"label": "الكل", "value": ""}] + [{"label": value, "value": value} for value in values]


def _build_forecast_filter_card() -> html.Div:
    bundle = load_disease_curated_tables()
    options = build_disease_filter_options(bundle)
    return html.Div(
        [
            html.Div("مرشحات التنبؤات الصحية", className="chart-card-title"),
            html.P(
                "اختر المرض أو المنطقة الصحية للانتقال بين التوقعات السنوية الرسمية والنمط الموسمي للملاريا وطبقة الإنذار البيئي الحي.",
                className="chart-card-subtitle",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("المرض", className="filter-label filter-label--dark"),
                            dcc.Dropdown(
                                id="forecast-disease-filter",
                                options=_dropdown_options(options["diseases"]),
                                value="",
                                clearable=False,
                                className="filter-dropdown",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("المنطقة الصحية", className="filter-label filter-label--dark"),
                            dcc.Dropdown(
                                id="forecast-region-filter",
                                options=_dropdown_options(options["regions"]),
                                value="",
                                clearable=False,
                                className="filter-dropdown",
                            ),
                        ]
                    ),
                ],
                className="page-filter-grid page-filter-grid--two",
            ),
        ],
        className="chart-card page-filter-card",
    )


def _build_disease_summary_card(frame: pd.DataFrame, disease_name_ar: str | None):
    if frame.empty:
        return metric_list_card(
            "ملخص توقعات المرض",
            "تظهر القيم الفعلية والتوقعات السنوية عندما تتوفر سلسلة زمنية رسمية كافية لخمس سنوات أو أكثر.",
            [],
        )

    disease_label = disease_name_ar if disease_name_ar else str(frame["disease_name_ar"].iloc[0])
    actual = frame.dropna(subset=["actual"]).sort_values("year")
    forecast = frame.dropna(subset=["forecast"]).sort_values("year")
    rows = []
    if not actual.empty:
        rows.append({"label": "آخر سنة فعلية", "value": str(int(actual.iloc[-1]["year"])), "tone": "neutral"})
        rows.append({"label": "عدد الحالات الفعلية", "value": f"{actual.iloc[-1]['actual']:,.0f}", "tone": "warning"})
    if not forecast.empty:
        rows.append({"label": "أول سنة متوقعة", "value": str(int(forecast.iloc[0]["year"])), "tone": "success"})
        rows.append({"label": "أقرب توقع متاح", "value": f"{forecast.iloc[0]['forecast']:,.0f}", "tone": "success"})
    rows.append({"label": "المرض المرجعي", "value": disease_label, "tone": "neutral"})
    return metric_list_card(
        "ملخص توقعات المرض",
        "يعتمد هذا القسم على اتجاهات الحالات الرسمية المتاحة، ويستخدم انحدارًا خطيًا خفيفًا مع متوسط متحرك لإخراج قراءة تشغيلية مبسطة.",
        rows,
    )


def _build_malaria_summary_card(frame: pd.DataFrame, region_label: str | None):
    if frame.empty:
        return metric_list_card(
            "ملخص توقعات الملاريا",
            "يظهر النمط الشهري وتوقع الأشهر الثلاثة القادمة عندما تتوفر البيانات الشهرية الرسمية للملاريا.",
            [],
        )
    forecast = frame.dropna(subset=["forecast"]).sort_values("month_number")
    rows = [{"label": "المنطقة المرجعية", "value": region_label or "الكل", "tone": "neutral"}]
    for _, row in forecast.head(3).iterrows():
        rows.append({"label": f"توقع {row['month_ar']}", "value": f"{row['forecast']:,.0f}", "tone": "warning"})
    return metric_list_card(
        "ملخص توقعات الملاريا الموسمية",
        "هذه القراءة تُظهر النمط الموسمي المعروف للملاريا مع توقع تشغيلي للأشهر الثلاثة التالية داخل النطاق المختار.",
        rows,
    )


def layout():
    return html.Div(
        [
            page_header(
                "التنبؤات الصحية والإنذار المبكر",
                "صفحة تشغيلية تشرح ما المتوقع مرضيًا وبيئيًا خلال الفترات القادمة، مع ربط التوقعات الرسمية التاريخية بالإنذار المبكر والرصد الحي داخل المملكة.",
                eyebrow="التنبؤات الصحية",
            ),
            _build_forecast_filter_card(),
            html.Div(id="forecast-alert", className="message-stack"),
            warning_card(
                "هذه التوقعات تشغيلية واستباقية وليست تشخيصًا سريريًا مباشرًا. تتحسن دقتها عند توفر سلاسل زمنية رسمية أطول للحالات أو زيارات الطوارئ أو الأمراض الموسمية حسب المنطقة.",
                title="تنبيه منهجي",
                tone="warning",
            ),
            html.Div(id="forecast-environment-cards", className="kpi-grid"),
            html.Div(
                [
                    chart_card(
                        "forecast-disease-chart",
                        "توقعات الأمراض",
                        "يعرض القيم الفعلية الرسمية والتوقعات السنوية للمرض المختار عندما تتوفر سلسلة زمنية كافية.",
                        graph_height="430px",
                    ),
                    html.Div(id="forecast-disease-summary", className="side-stack"),
                ],
                className="dashboard-two-col dashboard-two-col--wide",
            ),
            html.Div(
                [
                    chart_card(
                        "forecast-malaria-chart",
                        "توقعات الملاريا الموسمية",
                        "يبين النمط الشهري الفعلي ويضيف توقعًا تشغيلـيًا للأشهر الثلاثة القادمة للمنطقة المختارة.",
                        graph_height="390px",
                    ),
                    html.Div(id="forecast-malaria-summary", className="side-stack"),
                ],
                className="dashboard-two-col dashboard-two-col--wide",
            ),
            html.Div(
                [
                    chart_card(
                        "forecast-respiratory-chart",
                        "توقعات المخاطر التنفسية والبيئية",
                        "اتجاه أسبوعي قصير المدى يوضح أين قد يرتفع الضغط التنفسي والتشغيلي في المدن المرصودة.",
                        graph_height="390px",
                    ),
                    chart_card(
                        "forecast-respiratory-heatmap",
                        "الخريطة الحرارية الأسبوعية للمخاطر",
                        "تعرض تغير الخطر التنفسي يومًا بيوم داخل المدن المتاحة في طبقة الرصد البيئي.",
                        graph_height="390px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(id="forecast-recommendations-table"),
        ],
        className="page-stack",
    )


@callback(
    Output("forecast-alert", "children"),
    Output("forecast-environment-cards", "children"),
    Output("forecast-disease-chart", "figure"),
    Output("forecast-disease-summary", "children"),
    Output("forecast-malaria-chart", "figure"),
    Output("forecast-malaria-summary", "children"),
    Output("forecast-respiratory-chart", "figure"),
    Output("forecast-respiratory-heatmap", "figure"),
    Output("forecast-recommendations-table", "children"),
    Input("forecast-disease-filter", "value"),
    Input("forecast-region-filter", "value"),
    Input("province-filter", "value"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_forecasting_page(disease_name_ar, health_region_ar, province, _):
    bundle = load_disease_curated_tables()
    alerts: list = []
    effective_region = health_region_ar if health_region_ar not in {None, ""} else province

    try:
        filtered_data = prepare_dashboard_data(load_dashboard_datasets())
        environment_metrics = build_environmental_context_cards(filtered_data, effective_region)
        environmental_forecast = build_environmental_forecast_frame(filtered_data, effective_region)
    except GoogleSheetsConnectionError as exc:
        environment_metrics = build_environmental_context_cards({}, effective_region)
        environmental_forecast = pd.DataFrame()
        alerts.append(warning_card(str(exc), title="تعذر تحميل الرصد البيئي الحي", tone="warning"))
    except Exception as exc:
        environment_metrics = build_environmental_context_cards({}, effective_region)
        environmental_forecast = pd.DataFrame()
        alerts.append(warning_card(f"تعذر تحديث طبقة الرصد البيئي: {exc}", title="تنبيه بيئي", tone="warning"))

    environment_cards = [
        kpi_card(metric["label"], metric["value"], metric["hint"], accent="teal" if index % 2 == 0 else "cyan")
        for index, metric in enumerate(environment_metrics)
    ]

    disease_forecast_frame = build_disease_forecast_frame(bundle, disease_name_ar)
    malaria_forecast_frame = build_malaria_seasonal_forecast_frame(bundle, health_region_ar)
    disease_summary = _build_disease_summary_card(disease_forecast_frame, disease_name_ar)
    malaria_summary = _build_malaria_summary_card(malaria_forecast_frame, health_region_ar or None)

    respiratory_chart = (
        build_forecast_trend_chart(environmental_forecast, "respiratory_risk_index", "الخطر التنفسي المتوقع")
        if not environmental_forecast.empty
        else build_empty_figure("لا تتوفر توقعات بيئية حية للنطاق الحالي.")
    )
    respiratory_heatmap = (
        build_forecast_heatmap(environmental_forecast, "respiratory_risk_index", "الخطر")
        if not environmental_forecast.empty
        else build_empty_figure("لا تتوفر خريطة حرارية بيئية للنطاق الحالي.")
    )

    recommendations_table = data_table_card(
        "التوصيات التشغيلية",
        "جدول موجز يربط المرض أو النطاق المختار بأولوية التدخل والتوصية التنفيذية المقترحة.",
        ["disease_name_ar", "health_region_ar", "risk_level_ar", "recommendation_ar"],
        build_operational_recommendations_rows(bundle, disease_name_ar or None, health_region_ar or None),
        column_labels=RECOMMENDATION_LABELS,
    )

    return (
        alerts,
        environment_cards,
        build_disease_forecast_figure(bundle, disease_name_ar),
        disease_summary,
        build_malaria_seasonal_forecast_figure(bundle, health_region_ar),
        malaria_summary,
        respiratory_chart,
        respiratory_heatmap,
        recommendations_table,
    )
