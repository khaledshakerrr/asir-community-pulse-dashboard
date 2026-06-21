from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import dash_bootstrap_components as dbc

from src.charts import build_monthly_pulse_trend, build_pulse_by_province_bar
from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.kpis import calculate_overview_kpis
from src.maps import build_regions_map
from src.validators import validate_datasets

dash.register_page(__name__, path="/", name="نظرة عامة", order=0)


def _build_alerts(messages: list[str], color: str) -> list:
    return [dbc.Alert(message, color=color, class_name="dashboard-alert") for message in messages]


def layout():
    return html.Div(
        [
            html.Div(id="overview-alerts"),
            html.Div(id="overview-kpis", className="kpi-grid"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="overview-bar-chart", config={"displayModeBar": False}), lg=6),
                    dbc.Col(dcc.Graph(id="overview-line-chart", config={"displayModeBar": False}), lg=6),
                ],
                class_name="g-4",
            ),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="overview-map-chart", config={"displayModeBar": False}), lg=12),
                ],
                class_name="g-4 mt-1",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("overview-alerts", "children"),
    Output("overview-kpis", "children"),
    Output("overview-bar-chart", "figure"),
    Output("overview-line-chart", "figure"),
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
        kpis = calculate_overview_kpis(filtered_data)
    except GoogleSheetsConnectionError as exc:
        message = dbc.Alert(str(exc), color="danger", class_name="dashboard-alert")
        placeholder = html.Div(className="kpi-empty", children="تعذر تحميل المؤشرات حالياً")
        from src.charts import build_empty_figure

        error_figure = build_empty_figure("تعذر تحميل البيانات من Google Sheets.")
        return [message], [placeholder] * 6, error_figure, error_figure, error_figure

    alerts = []
    alerts.extend(_build_alerts(validation["errors"], "danger"))
    alerts.extend(_build_alerts(validation["warnings"], "warning"))

    kpi_cards = [
        html.Div(
            [
                html.Div(metric["label"], className="kpi-label"),
                html.Div(metric["value"], className="kpi-value"),
                html.Div(metric["hint"], className="kpi-hint"),
            ],
            className="kpi-card",
        )
        for metric in kpis
    ]

    return (
        alerts,
        kpi_cards,
        build_pulse_by_province_bar(filtered_data),
        build_monthly_pulse_trend(filtered_data),
        build_regions_map(filtered_data),
    )
