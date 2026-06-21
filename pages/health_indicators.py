from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import dash_bootstrap_components as dbc

from src.charts import build_risk_by_age_group, build_satisfaction_by_gender
from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets

dash.register_page(__name__, path="/health-indicators", name="المؤشرات الصحية", order=2)


def layout():
    return html.Div(
        [
            html.Div(id="health-alert"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="health-satisfaction-chart", config={"displayModeBar": False}), lg=6),
                    dbc.Col(dcc.Graph(id="health-risk-chart", config={"displayModeBar": False}), lg=6),
                ],
                class_name="g-4",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("health-alert", "children"),
    Output("health-satisfaction-chart", "figure"),
    Output("health-risk-chart", "figure"),
    Input("province-filter", "value"),
    Input("gender-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_health_page(province, gender, start_date, end_date, _):
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
        error_figure = build_empty_figure("تعذر تحميل المؤشرات الصحية.")
        return dbc.Alert(str(exc), color="danger", class_name="dashboard-alert"), error_figure, error_figure

    return None, build_satisfaction_by_gender(filtered_data), build_risk_by_age_group(filtered_data)
