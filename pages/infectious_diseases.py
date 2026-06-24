from __future__ import annotations

from pathlib import Path

import dash
import pandas as pd
from pandas.errors import EmptyDataError
from dash import Input, Output, callback, dcc, html

from src.data_cleaning import prepare_dashboard_data
from src.disease_intelligence import (
    build_disease_drilldown_summary,
    build_disease_filter_options,
    build_disease_gender_nationality_chart,
    build_disease_kpis,
    build_disease_month_chart,
    build_disease_region_chart,
    build_disease_region_heatmap,
    build_disease_region_map,
    build_disease_trend_chart,
    build_disease_age_chart,
    build_disease_recommendations_ar,
    build_environmental_context_cards,
    build_focus_comparison_rows,
    build_foodborne_outbreak_chart,
    build_intoxication_chart,
    build_malaria_month_region_chart,
    build_malaria_parasite_chart,
    build_tb_comparison_chart,
    build_top_diseases_chart,
    load_disease_curated_tables,
)
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.ui_components import chart_card, data_table_card, kpi_card, metric_list_card, page_header, warning_card


dash.register_page(__name__, path="/infectious-diseases", name="الأمراض المعدية", order=2)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKIPPED_REPORT_PATH = PROJECT_ROOT / "data" / "official_curated" / "diseases" / "skipped_tables_report.csv"

COMPARISON_COLUMN_LABELS = {
    "region_ar": "النطاق",
    "population_total": "السكان",
    "cases": "الحالات المبلغة",
    "cases_per_100k": "المعدل لكل 100 ألف",
    "hospitals_total": "المستشفيات",
    "beds_total": "الأسرة",
    "doctors_total": "الأطباء",
    "nurses_total": "الممرضون",
    "pressure_score": "مؤشر الضغط الصحي",
}


def _dropdown_options(values: list[str]) -> list[dict[str, str]]:
    return [{"label": "الكل", "value": ""}] + [{"label": value, "value": value} for value in values]


def _build_filter_card() -> html.Div:
    bundle = load_disease_curated_tables()
    options = build_disease_filter_options(bundle)
    return html.Div(
        [
            html.Div("مرشحات لوحة الأمراض المعدية", className="chart-card-title"),
            html.P(
                "تعمل المرشحات التالية على طبقة الأمراض المعدية الرسمية المستخرجة، وتبقي جميع العناوين والرسوم والتوصيات بالعربية فقط.",
                className="chart-card-subtitle",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("المرض", className="filter-label filter-label--dark"),
                            dcc.Dropdown(
                                id="infectious-disease-filter",
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
                                id="infectious-region-filter",
                                options=_dropdown_options(options["regions"]),
                                value="",
                                clearable=False,
                                className="filter-dropdown",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("الشهر", className="filter-label filter-label--dark"),
                            dcc.Dropdown(
                                id="infectious-month-filter",
                                options=_dropdown_options(options["months"]),
                                value="",
                                clearable=False,
                                className="filter-dropdown",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("الفئة العمرية", className="filter-label filter-label--dark"),
                            dcc.Dropdown(
                                id="infectious-age-filter",
                                options=_dropdown_options(options["ages"]),
                                value="",
                                clearable=False,
                                className="filter-dropdown",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("الجنس", className="filter-label filter-label--dark"),
                            dcc.Dropdown(
                                id="infectious-gender-filter",
                                options=_dropdown_options(options["genders"]),
                                value="",
                                clearable=False,
                                className="filter-dropdown",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("الجنسية", className="filter-label filter-label--dark"),
                            dcc.Dropdown(
                                id="infectious-nationality-filter",
                                options=_dropdown_options(options["nationalities"]),
                                value="",
                                clearable=False,
                                className="filter-dropdown",
                            ),
                        ]
                    ),
                ],
                className="page-filter-grid",
            ),
        ],
        className="chart-card page-filter-card",
    )


def layout():
    return html.Div(
        [
            page_header(
                "لوحة الأمراض المعدية",
                "تحليل عربي تنفيذي للأمراض المعدية حسب المنطقة، الشهر، العمر، الجنس، والجنسية اعتمادًا على جداول الكتاب الإحصائي السنوي لوزارة الصحة والملفات الرسمية المتاحة.",
                eyebrow="الأمراض المعدية",
            ),
            html.Div(id="infectious-alerts", className="message-stack"),
            warning_card(
                "تعتمد هذه الصفحة على الجداول المستخرجة من الكتاب الإحصائي السنوي لوزارة الصحة والملفات الرسمية المتاحة. بعض الأمراض تتوفر حسب المنطقة، وبعضها حسب الشهر أو العمر أو الجنس، وليس كل مرض متاحًا بكل الأبعاد في نفس الوقت.",
                title="أمانة البيانات",
                tone="warning",
            ),
            _build_filter_card(),
            html.Div(id="infectious-kpis", className="kpi-grid"),
            html.Div(id="infectious-environment-cards", className="kpi-grid"),
            html.Div(
                [
                    chart_card(
                        "infectious-top-diseases-chart",
                        "أعلى 10 أمراض حسب الحالات",
                        "يرتب الأمراض المعدية الأعلى عبئًا داخل الجداول الرسمية المتاحة بعد تطبيق المرشحات الحالية.",
                        graph_height="420px",
                    ),
                    chart_card(
                        "infectious-region-chart",
                        "الحالات حسب المنطقة الصحية",
                        "يعرض تركز الحالات المبلغة حسب المناطق الصحية ويبرز أين يتصاعد الضغط التنفيذي نسبيًا.",
                        graph_height="420px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    chart_card(
                        "infectious-heatmap-chart",
                        "الخريطة الحرارية للمرض والمنطقة",
                        "توضح تداخل أعلى الأمراض مع المناطق الصحية الأكثر تسجيلًا للحالات ضمن طبقة الرصد الحالية.",
                        graph_height="440px",
                    ),
                    chart_card(
                        "infectious-map-chart",
                        "الخريطة الإقليمية لعبء المرض",
                        "كل نقطة تمثل منطقة صحية ويعكس لونها عبء الحالات المعدل على السكان والضغط النسبي على الطاقة الصحية.",
                        graph_height="440px",
                        graph_config={"displayModeBar": True, "scrollZoom": True, "responsive": True},
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    chart_card(
                        "infectious-month-chart",
                        "الحالات حسب الشهر",
                        "اتجاه شهري يوضح المواسم الأعلى نشاطًا داخل الجداول الرسمية التي تحتوي على بعد زمني شهري.",
                        graph_height="390px",
                    ),
                    chart_card(
                        "infectious-age-chart",
                        "الحالات حسب الفئة العمرية",
                        "يوضح أين يتركز العبء العمري للأمراض المختارة في الجداول الوطنية المتاحة.",
                        graph_height="390px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    chart_card(
                        "infectious-gender-chart",
                        "الحالات حسب الجنس والجنسية",
                        "يوضح توزيع الحالات بين الذكور والإناث والسعوديين وغير السعوديين عندما يتوفر هذا البعد في الجدول الرسمي.",
                        graph_height="410px",
                    ),
                    chart_card(
                        "infectious-tb-chart",
                        "مقارنة الدرن الرئوي وغير الرئوي",
                        "مقارنة مباشرة بين نمطي الدرن الأكثر حضورًا في المناطق الصحية الأعلى تسجيلًا.",
                        graph_height="410px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    chart_card(
                        "infectious-malaria-parasite-chart",
                        "الملاريا حسب نوع الطفيل",
                        "يبين أكثر أنواع الطفيليات أو التصنيفات المرتبطة بحالات الملاريا في الجداول الرسمية.",
                        graph_height="390px",
                    ),
                    chart_card(
                        "infectious-malaria-month-region-chart",
                        "الملاريا حسب الشهر والمنطقة",
                        "خريطة حرارية تجمع المناطق الصحية بالشهور لإظهار النمط الموسمي المكاني لحالات الملاريا.",
                        graph_height="390px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    chart_card(
                        "infectious-foodborne-chart",
                        "تفشيات الأمراض المنقولة بالغذاء حسب المصدر",
                        "يعرض توزيع الحالات والفاشيات بين المصادر العامة والمنزلية حيثما تتوفر البيانات الرسمية المباشرة.",
                        graph_height="390px",
                    ),
                    chart_card(
                        "infectious-intoxication-chart",
                        "التسمم الكيميائي والدوائي حسب المنطقة",
                        "يوضح عبء التسممات الدوائية والكيميائية وغير المحددة على مستوى المناطق الصحية.",
                        graph_height="390px",
                    ),
                ],
                className="dashboard-two-col",
            ),
            html.Div(
                [
                    chart_card(
                        "infectious-trend-chart",
                        "اتجاه خمس سنوات للأمراض المختارة",
                        "يعرض الاتجاه الرسمي للحالات عبر خمس سنوات للأمراض التي يتوفر لها سجل زمني مباشر.",
                        graph_height="420px",
                    ),
                    html.Div(
                        [
                            html.Div(id="infectious-drilldown-card"),
                            html.Div(id="infectious-recommendations-card"),
                        ],
                        className="side-stack",
                    ),
                ],
                className="dashboard-two-col dashboard-two-col--wide",
            ),
            html.Div(id="infectious-comparison-table"),
        ],
        className="page-stack",
    )


@callback(
    Output("infectious-alerts", "children"),
    Output("infectious-kpis", "children"),
    Output("infectious-environment-cards", "children"),
    Output("infectious-top-diseases-chart", "figure"),
    Output("infectious-region-chart", "figure"),
    Output("infectious-heatmap-chart", "figure"),
    Output("infectious-map-chart", "figure"),
    Output("infectious-month-chart", "figure"),
    Output("infectious-age-chart", "figure"),
    Output("infectious-gender-chart", "figure"),
    Output("infectious-tb-chart", "figure"),
    Output("infectious-malaria-parasite-chart", "figure"),
    Output("infectious-malaria-month-region-chart", "figure"),
    Output("infectious-foodborne-chart", "figure"),
    Output("infectious-intoxication-chart", "figure"),
    Output("infectious-trend-chart", "figure"),
    Output("infectious-drilldown-card", "children"),
    Output("infectious-recommendations-card", "children"),
    Output("infectious-comparison-table", "children"),
    Input("infectious-disease-filter", "value"),
    Input("infectious-region-filter", "value"),
    Input("infectious-month-filter", "value"),
    Input("infectious-age-filter", "value"),
    Input("infectious-gender-filter", "value"),
    Input("infectious-nationality-filter", "value"),
    Input("province-filter", "value"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_infectious_diseases_page(
    disease_name,
    health_region,
    month_ar,
    age_group,
    gender_ar,
    nationality_ar,
    province,
    _,
):
    bundle = load_disease_curated_tables()
    filters = {
        "disease_name_ar": disease_name or "",
        "health_region_ar": health_region or "",
        "month_ar": month_ar or "",
        "age_group_ar": age_group or "",
        "gender_ar": gender_ar or "",
        "nationality_ar": nationality_ar or "",
    }

    alerts: list = []
    if SKIPPED_REPORT_PATH.is_file() and SKIPPED_REPORT_PATH.stat().st_size > 0:
        try:
            skipped = pd.read_csv(SKIPPED_REPORT_PATH)
        except EmptyDataError:
            skipped = pd.DataFrame()
        if not skipped.empty:
            first_issue = skipped.iloc[0].to_dict()
            alerts.append(
                warning_card(
                    f"تعذر استخراج بعض الجداول المركبة بالكامل. أول ملاحظة: {first_issue.get('sheet_name', 'غير محدد')} - {first_issue.get('reason', 'سبب غير موضح')}",
                    title="تنبيه جودة الاستخراج الرسمي",
                    tone="warning",
                )
            )

    effective_region = health_region if health_region not in {None, '', 'الكل'} else province
    try:
        filtered_data = prepare_dashboard_data(load_dashboard_datasets())
        environment_metrics = build_environmental_context_cards(filtered_data, effective_region)
    except GoogleSheetsConnectionError as exc:
        environment_metrics = build_environmental_context_cards({}, effective_region)
        alerts.append(
            warning_card(
                f"تعذر تحميل طبقة الرصد البيئي الحي: {exc}",
                title="تعذر تحميل الرصد البيئي الحي",
                tone="warning",
            )
        )
    except Exception as exc:
        environment_metrics = build_environmental_context_cards({}, effective_region)
        alerts.append(
            warning_card(
                f"تعذر تحديث بطاقات البيئة والصحة الحية: {exc}",
                title="تنبيه رصد حي",
                tone="warning",
            )
        )

    kpi_cards = [
        kpi_card(metric["label"], metric["value"], metric["hint"], accent="teal" if index % 2 == 0 else "cyan")
        for index, metric in enumerate(build_disease_kpis(bundle, filters))
    ]
    environment_cards = [
        kpi_card(metric["label"], metric["value"], metric["hint"], accent="cyan" if index % 2 == 0 else "teal")
        for index, metric in enumerate(environment_metrics)
    ]

    drilldown = build_disease_drilldown_summary(bundle, filters)
    drilldown_card = metric_list_card(
        f"ملخص تنفيذي: {drilldown['disease_name_ar'] or 'المرض المختار'}",
        "قراءة مركزة توضح أين يتركز العبء وما الذي تعنيه المؤشرات الحالية تشغيليًا.",
        drilldown["summary_rows"],
    )
    recommendation_rows = [
        {"label": f"توصية {index}", "value": recommendation, "tone": "success" if index == 1 else "warning"}
        for index, recommendation in enumerate(drilldown["recommendations_ar"] or build_disease_recommendations_ar(drilldown["disease_name_ar"], None, None), start=1)
    ]
    recommendations_card = metric_list_card(
        "التفسير التنفيذي والتوصيات",
        drilldown["interpretation_ar"],
        recommendation_rows,
    )

    comparison_rows = build_focus_comparison_rows(bundle, drilldown["disease_name_ar"])
    comparison_table = data_table_card(
        "مقارنة السعودية وعسير والقصيم",
        "جدول مركّز يربط السكان والعبء المرضي والطاقة الصحية لمساندة العرض التنفيذي أمام الجهة المستهدفة.",
        ["region_ar", "population_total", "cases", "cases_per_100k", "hospitals_total", "beds_total", "doctors_total", "nurses_total", "pressure_score"],
        comparison_rows,
        column_labels=COMPARISON_COLUMN_LABELS,
    )

    return (
        alerts,
        kpi_cards,
        environment_cards,
        build_top_diseases_chart(bundle, filters),
        build_disease_region_chart(bundle, filters),
        build_disease_region_heatmap(bundle, filters),
        build_disease_region_map(bundle, filters),
        build_disease_month_chart(bundle, filters),
        build_disease_age_chart(bundle, filters),
        build_disease_gender_nationality_chart(bundle, filters),
        build_tb_comparison_chart(bundle, filters),
        build_malaria_parasite_chart(bundle, filters),
        build_malaria_month_region_chart(bundle, filters),
        build_foodborne_outbreak_chart(bundle, filters),
        build_intoxication_chart(bundle, filters),
        build_disease_trend_chart(bundle, filters),
        drilldown_card,
        recommendations_card,
        comparison_table,
    )
