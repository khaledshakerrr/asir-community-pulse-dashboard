from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import dash_bootstrap_components as dbc

from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.maps import build_regions_map

dash.register_page(__name__, path="/map", name="الخريطة", order=1)


def layout():
    return html.Div(
        [
            html.Div(id="map-alert"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="regions-map-full", config={"displayModeBar": False}), lg=8),
                    dbc.Col(html.Div(id="map-top-areas"), lg=4),
                ],
                class_name="g-4",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("map-alert", "children"),
    Output("regions-map-full", "figure"),
    Output("map-top-areas", "children"),
    Input("province-filter", "value"),
    Input("gender-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_map_page(province, gender, start_date, end_date, _):
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
            "تعذر تحميل الخريطة."
        ), html.Div("لا توجد بيانات.")

    survey = filtered_data["tables"].get("survey_responses_simulated")
    top_areas = html.Div("لا توجد بيانات متاحة حالياً.", className="insight-card")
    if survey is not None and not survey.empty and {"province_ar", "community_pulse_index"}.issubset(survey.columns):
        summary = (
            survey.groupby("province_ar", dropna=True)["community_pulse_index"]
            .mean()
            .sort_values(ascending=False)
            .head(5)
        )
        top_areas = html.Div(
            [
                html.H4("أفضل المحافظات أداءً", className="section-title"),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span(area, className="insight-title"),
                                html.Span(f"{score:.1f}", className="insight-value"),
                            ],
                            className="insight-row",
                        )
                        for area, score in summary.items()
                    ],
                    className="insight-card",
                ),
            ]
        )

    return None, build_regions_map(filtered_data), top_areas
