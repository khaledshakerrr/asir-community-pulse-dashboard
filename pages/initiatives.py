from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import dash_bootstrap_components as dbc

from src.charts import build_initiatives_progress_chart, build_initiatives_status_chart
from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets

dash.register_page(__name__, path="/initiatives", name="المبادرات", order=4)


def layout():
    return html.Div(
        [
            html.Div(id="initiatives-alert"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="initiatives-progress-chart", config={"displayModeBar": False}), lg=7),
                    dbc.Col(dcc.Graph(id="initiatives-status-chart", config={"displayModeBar": False}), lg=5),
                ],
                class_name="g-4",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("initiatives-alert", "children"),
    Output("initiatives-progress-chart", "figure"),
    Output("initiatives-status-chart", "figure"),
    Input("province-filter", "value"),
    Input("gender-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_initiatives_page(province, gender, start_date, end_date, _):
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
        error_figure = build_empty_figure("تعذر تحميل بيانات المبادرات.")
        return dbc.Alert(str(exc), color="danger", class_name="dashboard-alert"), error_figure, error_figure

    return None, build_initiatives_progress_chart(filtered_data), build_initiatives_status_chart(filtered_data)
