from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import dash_bootstrap_components as dbc

from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.forecasting import build_forecast_figure, build_forecast_frame
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets

dash.register_page(__name__, path="/forecasting", name="التنبؤات", order=5)


def layout():
    return html.Div(
        [
            html.Div(id="forecast-alert"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="forecast-main-chart", config={"displayModeBar": False}), lg=8),
                    dbc.Col(html.Div(id="forecast-summary-card"), lg=4),
                ],
                class_name="g-4",
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
    from src.charts import build_empty_figure

    try:
        datasets = load_dashboard_datasets()
        filtered_data = apply_filters(
            prepare_dashboard_data(datasets),
            province,
            gender,
            start_date,
            end_date,
        )
    except GoogleSheetsConnectionError as exc:
        return dbc.Alert(str(exc), color="danger", class_name="dashboard-alert"), build_empty_figure(
            "تعذر تحميل بيانات التنبؤات."
        ), html.Div("لا توجد بيانات.")

    forecast_frame = build_forecast_frame(filtered_data)
    summary = html.Div("لا توجد بيانات تنبؤية كافية.", className="insight-card")
    if not forecast_frame.empty:
        latest_forecast = forecast_frame.dropna(subset=["forecast"]).sort_values("month").tail(1)
        latest_actual = forecast_frame.dropna(subset=["actual"]).sort_values("month").tail(1)

        summary_rows = []
        if not latest_actual.empty:
            summary_rows.append(
                html.Div(
                    [
                        html.Span("آخر قيمة فعلية", className="insight-title"),
                        html.Span(f"{latest_actual['actual'].iloc[0]:,.1f}", className="insight-value"),
                    ],
                    className="insight-row",
                )
            )
        if not latest_forecast.empty:
            summary_rows.append(
                html.Div(
                    [
                        html.Span("أحدث تنبؤ", className="insight-title"),
                        html.Span(f"{latest_forecast['forecast'].iloc[0]:,.1f}", className="insight-value"),
                    ],
                    className="insight-row",
                )
            )

        summary = html.Div(
            [
                html.H4("ملخص التوقعات", className="section-title"),
                html.Div(summary_rows, className="insight-card"),
            ]
        )

    return None, build_forecast_figure(filtered_data), summary
