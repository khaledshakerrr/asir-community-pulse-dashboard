from __future__ import annotations

from dotenv import load_dotenv

# Load environment variables before importing project modules.
load_dotenv()

import base64
import secrets
from datetime import datetime
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, ctx, dcc, html, page_container
from flask import Response, request, send_file

from src.config import APP_PASSWORD, APP_SUBTITLE, APP_TITLE, init_cache
from src.data_cleaning import get_filter_options, prepare_dashboard_data
from src.environmental_live import clear_environmental_cache
from src.google_sheets import GoogleSheetsConnectionError, clear_dashboard_cache, load_dashboard_datasets

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

DOCUMENTATION_PDF_PATH = Path(__file__).resolve().parent / "docs" / "asir_community_pulse_documentation_ar.pdf"

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
        "يتطلب هذا التطبيق كلمة مرور للوصول.",
        401,
        {"WWW-Authenticate": 'Basic realm="Asir Community Pulse Dashboard"'},
    )


@server.route("/documentation/pdf")
def download_documentation_pdf():
    if not DOCUMENTATION_PDF_PATH.is_file():
        return Response("ملف التوثيق PDF غير متاح حاليًا. قم بتوليده أولًا من المجلد docs.", status=404, mimetype="text/plain; charset=utf-8")
    return send_file(DOCUMENTATION_PDF_PATH, as_attachment=True, download_name="asir_community_pulse_documentation_ar.pdf")


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
                html.Aside(
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
                                html.Div("التنقل", className="sidebar-section-title"),
                                dbc.Nav(_build_nav_links(), vertical=True, pills=True, class_name="sidebar-nav"),
                            ],
                            className="sidebar-panel sidebar-nav-panel",
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
                                html.Label("الفترة الزمنية", className="filter-label"),
                                dcc.DatePickerRange(
                                    id="date-range-filter",
                                    start_date_placeholder_text="من",
                                    end_date_placeholder_text="إلى",
                                    display_format="YYYY-MM-DD",
                                    className="date-picker",
                                ),
                                html.Button("تحديث البيانات", id="refresh-data-button", className="refresh-button"),
                            ],
                            className="sidebar-panel",
                        ),
                        html.Div(
                            [
                                html.Div("مصدر البيانات", className="sidebar-section-title"),
                                html.Div("منصة بيانات تشغيلية موحدة", className="sidebar-note-title"),
                                html.P(
                                    "تعتمد المنصة على طبقة بيانات تشغيلية موحدة قابلة للتحديث الدوري، بما يدعم العروض التنفيذية والتحليلات القطاعية دون إظهار تفاصيل تقنية للمستخدم النهائي.",
                                    className="sidebar-note-text",
                                ),
                            ],
                            className="sidebar-panel sidebar-note-panel",
                        ),
                    ],
                    className="sidebar",
                ),
                html.Main(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("منصة تحليلية عربية", className="hero-eyebrow"),
                                        html.H2("لوحة تنفيذية لمؤشرات نبض المجتمع", className="hero-title"),
                                        html.P(
                                            "منصة عربية تفاعلية توحد المؤشرات الصحية والاجتماعية، والتحليلات المكانية، والاتجاهات الزمنية، والتنبؤات التشغيلية لدعم القرار داخل المملكة العربية السعودية.",
                                            className="hero-subtitle",
                                        ),
                                    ],
                                    className="hero-copy",
                                ),
                                html.Div(
                                    [
                                        html.Div(id="hero-source-pill", className="hero-pill"),
                                        html.Div(id="connection-status", className="hero-status"),
                                    ],
                                    className="hero-meta",
                                ),
                            ],
                            className="hero-card",
                        ),
                        html.Div(page_container, className="page-content"),
                        html.Footer(
                            "منصة تحليلية تنفيذية تدعم القرار الصحي عبر مؤشرات موحدة ورؤى مكانية واتجاهات مستقبلية",
                            className="footer-note",
                        ),
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
    Output("hero-source-pill", "children"),
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
        clear_environmental_cache()

    try:
        datasets = load_dashboard_datasets()
        cleaned = prepare_dashboard_data(datasets)
        options = get_filter_options(cleaned)
    except GoogleSheetsConnectionError as exc:
        today = datetime.utcnow().date().isoformat()
        fallback = [{"label": "الكل", "value": "الكل"}]
        return fallback, "الكل", fallback, "الكل", today, today, today, today, "المصدر غير متاح", str(exc)

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
    source_label = cleaned.get("source_label", "مصدر غير محدد")
    if "رسمي" in source_label:
        source_chip = "بيانات رسمية"
    elif "تجريبي" in source_label:
        source_chip = "بيانات تجريبية"
    elif "جوجل شيت" in source_label:
        source_chip = "ربط تشغيلي مباشر"
    else:
        source_chip = "مصدر تشغيلي"
    status = f"آخر تحديث ناجح: {loaded_at} بتوقيت غرينتش"

    return (
        province_options,
        selected_province,
        gender_options,
        selected_gender,
        min_date,
        max_date,
        selected_start,
        selected_end,
        source_chip,
        status,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
