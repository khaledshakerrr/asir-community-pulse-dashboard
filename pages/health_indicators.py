from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

from src.charts import build_empty_figure
from src.chronic_care import load_chronic_care_data
from src.chronic_charts import (
    build_chronic_capacity_chart,
    build_diabetes_rehabilitation_chart,
    build_diabetes_snapshot_chart,
    build_dialysis_patients_chart,
    get_national_dialysis_total,
)
from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.official_charts import (
    build_asir_cluster_capacity_chart,
    build_focus_access_chart,
    build_focus_capacity_chart,
    build_qassim_population_chart,
)
from src.ui_components import chart_card, page_header, warning_card

dash.register_page(__name__, path="/health-indicators", name="المقارنة الإقليمية", order=2)


def _chronic_care_section():
    return html.Section(
        [
            page_header(
                "خدمات رعاية السكري",
                "زيارات عيادات السكري بمستشفيات وزارة الصحة كما نُشرت في عامي 2023 و2024. تساعد هذه اللقطات في فهم حجم الخدمة، ولا تمثل عدد المرضى أو انتشار المرض.",
                eyebrow="بيانات رسمية عن رعاية الأمراض المزمنة",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("نطاق بيانات الرعاية المزمنة", htmlFor="chronic-scope-filter", className="filter-label filter-label--dark"),
                                    dcc.Dropdown(
                                        id="chronic-scope-filter",
                                        options=[
                                            {"label": "مقارنة عسير وبيشة والقصيم", "value": "focus"},
                                            {"label": "السعودية — الإجمالي الرسمي", "value": "saudi_arabia"},
                                            {"label": "عسير — دون بيشة", "value": "asir"},
                                            {"label": "بيشة", "value": "bisha"},
                                            {"label": "القصيم", "value": "qassim"},
                                            {"label": "إجمالي تجمع عسير — يشمل بيشة (2024)", "value": "asir_cluster_total"},
                                        ],
                                        value="focus",
                                        clearable=False,
                                        className="filter-dropdown",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label("سنة بيانات المرافق المتخصصة", htmlFor="chronic-capacity-year", className="filter-label filter-label--dark"),
                                    dcc.Dropdown(
                                        id="chronic-capacity-year",
                                        options=[{"label": str(year), "value": year} for year in (2024, 2023, 2022)],
                                        value=2024,
                                        clearable=False,
                                        className="filter-dropdown",
                                    ),
                                ]
                            ),
                        ],
                        className="page-filter-grid page-filter-grid--two",
                    ),
                    html.P("مرشحات هذا القسم مستقلة عن مرشحات الشريط الجانبي. البيانات سنوية وتشمل كلا الجنسين.", className="chart-card-subtitle"),
                ],
                className="chart-card page-filter-card",
            ),
            warning_card(
                "يعرض مصدر 2023 مناطق صحية، ويعرض مصدر 2024 تجمعات صحية؛ لذلك تُعرض كل سنة كلقطة مستقلة دون حساب نمو بينهما. صف عسير منفصل عن بيشة، والإجمالي المنشور الذي يجمعهما متاح لعام 2024 فقط.",
                title="نطاق المقارنة بين السنوات",
            ),
            html.Div(
                [
                    chart_card("chronic-visits-2023", "زيارات عيادات السكري — 2023", "مناطق صحية وفق الجدول الرسمي 4-13.", graph_height="300px"),
                    chart_card("chronic-visits-2024", "زيارات عيادات السكري — 2024", "تجمعات صحية وفق الجدول الرسمي 4-16.", graph_height="300px"),
                ],
                className="dashboard-two-col",
            ),
            page_header(
                "الطاقة المتخصصة لرعاية الأمراض المزمنة",
                "أعداد مرافق وزارة الصحة المتخصصة في القلب والأورام والسكري والغدد الصماء، ومراكز ووحدات الغسيل الكلوي. توضح توزيع الخدمات المتاحة ضمن النطاق والسنة المختارين.",
            ),
            chart_card("chronic-capacity-chart", "المرافق المتخصصة حسب نوع الخدمة", "أعداد مرافق وزارة الصحة وفق السنة المختارة؛ لا تشمل جميع القطاعات الصحية.", graph_height="460px"),
            html.Div(
                [
                    html.P(id="chronic-capacity-source", className="chart-card-subtitle"),
                    html.A(
                        "المصدر: وزارة الصحة — الكتب الإحصائية السنوية 2022 و2023 و2024",
                        href="https://www.moh.gov.sa/Ministry/Statistics/book/Pages/default.aspx",
                        target="_blank",
                        rel="noopener noreferrer",
                        className="source-link",
                    ),
                ],
                className="chart-card",
            ),
        ],
        className="page-stack",
        **{"aria-label": "بيانات الرعاية المزمنة الرسمية"},
    )


def _national_chronic_care_section():
    return html.Section(
        [
            page_header(
                "التأهيل المرتبط بالسكري والغسيل الكلوي",
                "بيانات رسمية على مستوى المملكة توضح استخدام خدمات التأهيل بعد البتر المرتبط بالسكري، وتوزيع مرضى الغسيل الكلوي بين القطاعات الصحية. لا تتغير هذه البيانات الوطنية بمرشحات المنطقة أو الجنس أو الفترة الزمنية في الصفحة.",
                eyebrow="مؤشرات وطنية للرعاية المزمنة",
            ),
            html.Div(
                [
                    chart_card(
                        "national-diabetes-rehabilitation-chart",
                        "زيارات التأهيل بعد البتر المرتبط بالسكري",
                        "مراكز وأقسام التأهيل الطبي بوزارة الصحة — 2023 و2024. القيم زيارات خدمة، وليست أعداد عمليات بتر أو مرضى فريدين أو معدل مضاعفات السكري.",
                        graph_height="360px",
                    ),
                    chart_card(
                        "national-dialysis-patients-chart",
                        "مرضى الغسيل الكلوي حسب القطاع — 2024",
                        "التنقية الدموية والبريتونية في وزارة الصحة والجهات الحكومية الأخرى والقطاع الخاص على مستوى المملكة.",
                        graph_height="360px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    html.P(id="national-dialysis-patients-total", className="chart-card-subtitle"),
                    html.P(
                        [
                            "مصدر التأهيل: عام 2023، جدول ", html.Bdi("4-37"),
                            "؛ عام 2024، جدول ", html.Bdi("4-45"),
                            ". مصدر مرضى الغسيل الكلوي: عام 2024، جدول ", html.Bdi("4-42"),
                            "، مع مطابقة الإجمالي بالجدول ", html.Bdi("4-43"), ".",
                        ],
                        className="chart-card-subtitle",
                    ),
                    html.A(
                        "وزارة الصحة — الكتب الإحصائية السنوية",
                        href="https://www.moh.gov.sa/Ministry/Statistics/book/Pages/default.aspx",
                        target="_blank", rel="noopener noreferrer", className="source-link",
                    ),
                ],
                className="chart-card",
            ),
        ],
        className="page-stack",
        **{"aria-label": "التأهيل والغسيل الكلوي على مستوى المملكة"},
    )


def layout():
    return html.Div(
        [
            page_header(
                "المقارنة الإقليمية",
                "تحليل مباشر يضع السعودية وعسير والقصيم في إطار واحد، ثم يهبط إلى تفصيل محافظات القصيم وتجمع عسير لإظهار الفروق التي تهم صانع القرار.",
                eyebrow="المقارنة الإقليمية",
            ),
            html.Div(id="regional-alert", className="message-stack"),
            html.Div(
                [
                    chart_card(
                        "regional-capacity-chart",
                        "مقارنة البنية الصحية المعيارية",
                        "ثلاثة مقاييس قياسية تقيس كثافة المستشفيات والأسرة والرعاية الأولية بين السعودية وعسير والقصيم.",
                        graph_height="360px",
                    ),
                    chart_card(
                        "regional-access-chart",
                        "الوصول الرقمي والرضا",
                        "قياس متكامل بين الرضا عن وقت الطبيب والاستفادة من الاستشارات عن بعد والوصول إلى السجل الطبي.",
                        graph_height="360px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    chart_card(
                        "regional-qassim-chart",
                        "تفصيل محافظات القصيم سكانياً",
                        "حجم المحافظات داخل القصيم يحدد أين يجب أن تتوزع الطاقة والخدمة عند بناء نماذج التدخل والاستهداف.",
                        graph_height="420px",
                    ),
                    chart_card(
                        "regional-asir-chart",
                        "تفصيل تجمع عسير الصحي",
                        "مقارنة داخلية بين تجمع عسير وتجمع بيشة على مستوى الأسرة والعناية المركزة وزيارات عيادات السكري.",
                        graph_height="420px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            _chronic_care_section(),
            _national_chronic_care_section(),
        ],
        className="page-stack",
    )


@callback(
    Output("regional-alert", "children"),
    Output("regional-capacity-chart", "figure"),
    Output("regional-access-chart", "figure"),
    Output("regional-qassim-chart", "figure"),
    Output("regional-asir-chart", "figure"),
    Input("province-filter", "value"),
    Input("gender-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_health_page(province, gender, start_date, end_date, _):
    try:
        datasets = load_dashboard_datasets()
        filtered_data = apply_filters(prepare_dashboard_data(datasets), province, gender, start_date, end_date)
    except GoogleSheetsConnectionError as exc:
        error_figure = build_empty_figure("تعذر تحميل بيانات المقارنة الإقليمية في الوقت الحالي.")
        return (
            [warning_card(str(exc), title="تعذر الاتصال بمصدر البيانات", tone="danger")],
            error_figure,
            error_figure,
            error_figure,
            error_figure,
        )

    return (
        [],
        build_focus_capacity_chart(filtered_data),
        build_focus_access_chart(filtered_data),
        build_qassim_population_chart(filtered_data),
        build_asir_cluster_capacity_chart(filtered_data),
    )


@callback(
    Output("chronic-visits-2023", "figure"),
    Output("chronic-visits-2024", "figure"),
    Output("chronic-capacity-chart", "figure"),
    Output("chronic-capacity-source", "children"),
    Input("chronic-scope-filter", "value"),
    Input("chronic-capacity-year", "value"),
)
def refresh_chronic_care(scope, capacity_year):
    scope = scope or "focus"
    year = int(capacity_year or 2024)
    datasets = load_chronic_care_data()
    geography = "تجمعات صحية" if year == 2024 else "مناطق صحية"
    table_number = {2022: "2-6", 2023: "2-11", 2024: "2-4"}[year]
    source_note = f"المرافق: عام {year}، {geography}، جدول {table_number}. الغسيل الكلوي يشمل المراكز والوحدات. القيم غير المنشورة لا تُعامل كصفر."
    return (
        build_diabetes_snapshot_chart(datasets["diabetes_visits"], 2023, scope),
        build_diabetes_snapshot_chart(datasets["diabetes_visits"], 2024, scope),
        build_chronic_capacity_chart(datasets["chronic_care_capacity"], year, scope),
        source_note,
    )


@callback(
    Output("national-diabetes-rehabilitation-chart", "figure"),
    Output("national-dialysis-patients-chart", "figure"),
    Output("national-dialysis-patients-total", "children"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_national_chronic_care(_):
    datasets = load_chronic_care_data()
    patients = datasets["dialysis_patients_2024"]
    total = get_national_dialysis_total(patients)
    treatment_totals = patients.loc[patients["sector_key"].eq("all_sectors")].set_index("treatment_key")["patients"].to_dict()
    summary = (
        f"السعودية — 2024: إجمالي مرضى الغسيل الكلوي {total:,.0f} مريض؛ التنقية الدموية {treatment_totals['haemodialysis']:,.0f}، والتنقية البريتونية {treatment_totals['peritoneal']:,.0f}. تشمل الأعداد جميع القطاعات الصحية."
        if total is not None else "إجمالي مرضى الغسيل الكلوي لعام 2024 غير متاح لعدم اكتمال القيم المنشورة."
    )
    return (
        build_diabetes_rehabilitation_chart(datasets["diabetes_rehabilitation_visits"]),
        build_dialysis_patients_chart(patients),
        summary,
    )
