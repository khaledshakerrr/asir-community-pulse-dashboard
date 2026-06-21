from __future__ import annotations

import base64
import secrets
from datetime import datetime

from flask import Response, request
import dash
from dash import Dash, Input, Output, State, ctx, dcc, html, page_container
import dash_bootstrap_components as dbc

from src.config import APP_PASSWORD, APP_SUBTITLE, APP_TITLE, init_cache
from src.data_cleaning import get_filter_options, prepare_dashboard_data
from src.google_sheets import (
    GoogleSheetsConnectionError,
    clear_dashboard_cache,
    load_dashboard_datasets,
)

external_stylesheets = [dbc.themes.BOOTSTRAP]

app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
    title=APP_TITLE,
)
server = app.server
init_cache(server)

app.index_string = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


def _is_authorized() -> bool:
    if not APP_PASSWORD:
        return True

    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False

    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        _, password = decoded.split(":", 1)
    except Exception:
        return False

    return secrets.compare_digest(password, APP_PASSWORD)


@server.before_request
def protect_dashboard():
    if _is_authorized():
        return None

    return Response(
        "Authentication required.",
        401,
        {"WWW-Authenticate": 'Basic realm="Asir Community Pulse Dashboard"'},
    )


def _build_nav_links():
    pages = sorted(
        dash.page_registry.values(),
        key=lambda page: (page.get("order", 999), page["name"]),
    )
    return [
        dbc.NavLink(
            page["name"],
            href=page["relative_path"],
            active="exact",
            class_name="sidebar-link",
        )
        for page in pages
    ]


app.layout = html.Div(
    [
        dcc.Interval(id="data-refresh-interval", interval=300000, n_intervals=0),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Img(src="/assets/asir-logo.png", className="brand-logo", alt="Asir Logo"),
                                html.Div(
                                    [
                                        html.H1(APP_TITLE, className="brand-title"),
                                        html.P(APP_SUBTITLE, className="brand-subtitle"),
                                    ],
                                    className="brand-copy",
                                ),
                            ],
                            className="brand-block",
                        ),
                        html.Div(
                            [
                                html.Div("مرشحات البيانات", className="sidebar-section-title"),
                                html.Label("المحافظة", className="filter-label"),
                                dcc.Dropdown(
                                    id="province-filter",
                                    options=[{"label": "الكل", "value": "الكل"}],
                                    value="الكل",
                                    clearable=False,
                                    className="filter-dropdown",
                                ),
                                html.Label("الجنس", className="filter-label"),
                                dcc.Dropdown(
                                    id="gender-filter",
                                    options=[{"label": "الكل", "value": "الكل"}],
                                    value="الكل",
                                    clearable=False,
                                    className="filter-dropdown",
                                ),
                                html.Label("النطاق الزمني", className="filter-label"),
                                dcc.DatePickerRange(
                                    id="date-range-filter",
                                    start_date_placeholder_text="من",
                                    end_date_placeholder_text="إلى",
                                    display_format="YYYY-MM-DD",
                                    className="date-picker",
                                ),
                                html.Button("تحديث البيانات", id="refresh-data-button", className="refresh-button"),
                                html.Div(id="connection-status", className="status-chip"),
                            ],
                            className="sidebar-panel",
                        ),
                        html.Div(
                            [
                                html.Div("التنقل", className="sidebar-section-title"),
                                dbc.Nav(_build_nav_links(), vertical=True, pills=True, class_name="sidebar-nav"),
                            ],
                            className="sidebar-panel sidebar-nav-panel",
                        ),
                    ],
                    className="sidebar",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H2("لوحة تنفيذية لمؤشرات المجتمع", className="page-heading"),
                                        html.P(
                                            "منصة عربية تفاعلية تربط مؤشرات نبض المجتمع ببيانات Google Sheets مع تحديث مؤقت كل 5 دقائق.",
                                            className="page-subheading",
                                        ),
                                    ]
                                ),
                            ],
                            className="content-header",
                        ),
                        html.Div(page_container, className="page-content"),
                    ],
                    className="content-shell",
                ),
            ],
            className="app-shell",
        ),
    ]
)


@app.callback(
    Output("province-filter", "options"),
    Output("province-filter", "value"),
    Output("gender-filter", "options"),
    Output("gender-filter", "value"),
    Output("date-range-filter", "min_date_allowed"),
    Output("date-range-filter", "max_date_allowed"),
    Output("date-range-filter", "start_date"),
    Output("date-range-filter", "end_date"),
    Output("connection-status", "children"),
    Input("data-refresh-interval", "n_intervals"),
    Input("refresh-data-button", "n_clicks"),
    State("province-filter", "value"),
    State("gender-filter", "value"),
    State("date-range-filter", "start_date"),
    State("date-range-filter", "end_date"),
)
def refresh_sidebar_filters(_, refresh_clicks, current_province, current_gender, current_start, current_end):
    if ctx.triggered_id == "refresh-data-button" and refresh_clicks:
        clear_dashboard_cache()

    try:
        datasets = load_dashboard_datasets()
        cleaned = prepare_dashboard_data(datasets)
        options = get_filter_options(cleaned)
    except GoogleSheetsConnectionError as exc:
        today = datetime.utcnow().date().isoformat()
        fallback = [{"label": "الكل", "value": "الكل"}]
        return fallback, "الكل", fallback, "الكل", today, today, today, today, str(exc)

    province_options = [{"label": "الكل", "value": "الكل"}] + [
        {"label": province, "value": province} for province in options["provinces"]
    ]
    gender_options = [{"label": "الكل", "value": "الكل"}] + [
        {"label": gender, "value": gender} for gender in options["genders"]
    ]

    min_date = options["min_date"].date().isoformat() if options["min_date"] is not None else None
    max_date = options["max_date"].date().isoformat() if options["max_date"] is not None else None
    province_values = {item["value"] for item in province_options}
    gender_values = {item["value"] for item in gender_options}
    selected_province = current_province if current_province in province_values else "الكل"
    selected_gender = current_gender if current_gender in gender_values else "الكل"

    if current_start and min_date and current_start < min_date:
        current_start = min_date
    if current_end and max_date and current_end > max_date:
        current_end = max_date

    selected_start = current_start or min_date
    selected_end = current_end or max_date

    loaded_at = datetime.fromisoformat(cleaned["loaded_at"]).strftime("%Y-%m-%d %H:%M")
    status = f"آخر مزامنة ناجحة: {loaded_at} UTC"

    return (
        province_options,
        selected_province,
        gender_options,
        selected_gender,
        min_date,
        max_date,
        selected_start,
        selected_end,
        status,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
