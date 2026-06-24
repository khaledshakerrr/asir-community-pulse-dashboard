from __future__ import annotations

import dash
from dash import Input, Output, callback, html

from src.charts import build_empty_figure
from src.data_cleaning import apply_filters, prepare_dashboard_data
from src.google_sheets import GoogleSheetsConnectionError, load_dashboard_datasets
from src.maps import build_map_dataset, build_regions_map
from src.ui_components import chart_card, metric_list_card, page_header, warning_card

dash.register_page(__name__, path="/map", name="الخريطة التفاعلية", order=1)


def _risk_tone(label: str) -> str:
    return {"عالي": "danger", "مرتفع": "danger", "متوسط": "warning", "منخفض": "success"}.get(label, "neutral")


def _build_map_side_cards(map_frame):
    if getattr(map_frame, "empty", True):
        return [
            metric_list_card(
                "ملخص جغرافي",
                "ستظهر هنا أهم أولويات المناطق فور توفر طبقة الجغرافيا الرسمية.",
                [],
            )
        ]

    priority_rows = [
        {
            "label": row["province_name_ar"],
            "value": row["risk_level"],
            "tone": _risk_tone(str(row["risk_level"])),
        }
        for _, row in map_frame.sort_values(
            ["risk_prediction_score", "community_pulse_index"],
            ascending=[False, True],
        ).head(5).iterrows()
    ]

    snapshot_rows = [
        {"label": "عدد المناطق المعروضة", "value": f"{len(map_frame):,}", "tone": "neutral"},
        {
            "label": "متوسط الجاهزية المركبة",
            "value": f"{map_frame['community_pulse_index'].dropna().mean():.1f}" if map_frame["community_pulse_index"].notna().any() else "غير متاح",
            "tone": "success",
        },
        {
            "label": "رضا وقت الطبيب",
            "value": f"{map_frame['doctor_time_satisfaction_pct'].dropna().mean():.1f}%" if map_frame["doctor_time_satisfaction_pct"].notna().any() else "غير متاح",
            "tone": "success",
        },
        {
            "label": "عدد المستشفيات",
            "value": f"{int(map_frame['hospitals_total'].fillna(0).sum()):,}",
            "tone": "neutral",
        },
        {
            "label": "متوسط الانتظار",
            "value": f"{map_frame['avg_waiting_time_minutes'].dropna().mean():.1f} دقيقة" if map_frame["avg_waiting_time_minutes"].notna().any() else "غير متاح",
            "tone": "warning",
        },
    ]

    return [
        metric_list_card(
            "أعلى المناطق أولوية",
            "ترتيب تنفيذي للمناطق التي يظهر فيها ضغط أعلى بحسب المؤشر المركب والمخاطر التشغيلية الرسمية.",
            priority_rows,
        ),
        metric_list_card(
            "لقطة سريعة للمشهد",
            "ملخص كمي سريع للطاقة والرضا والانتظار في النطاق الجغرافي الحالي.",
            snapshot_rows,
        ),
    ]


def layout():
    return html.Div(
        [
            page_header(
                "الخريطة التفاعلية",
                "قراءة مكانية تنفيذية تعتمد على نقاط تمركز المناطق الرسمية وتبرز الفروقات بين الجاهزية والرضا والطاقة الاستيعابية عبر المملكة مع دعم التركيز على عسير والقصيم.",
                eyebrow="Interactive Map",
            ),
            html.Div(id="map-alert", className="message-stack"),
            html.Div(
                [
                    chart_card(
                        "regions-map-full",
                        "الخريطة التنفيذية للمؤشرات الصحية",
                        "استخدم المرشحات للانتقال من المشهد الوطني إلى قراءة أكثر تركيزاً لعسير أو القصيم، مع تلميحات مختصرة جاهزة للعرض أمام العميل.",
                        graph_height="580px",
                        graph_config={"displayModeBar": True, "scrollZoom": True, "responsive": True},
                    ),
                    html.Div(id="map-side-cards", className="side-stack"),
                ],
                className="dashboard-two-col dashboard-two-col--wide",
            ),
        ],
        className="page-stack",
    )


@callback(
    Output("map-alert", "children"),
    Output("regions-map-full", "figure"),
    Output("map-side-cards", "children"),
    Input("province-filter", "value"),
    Input("gender-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("data-refresh-interval", "n_intervals"),
)
def refresh_map_page(province, gender, start_date, end_date, _):
    try:
        datasets = load_dashboard_datasets()
        filtered_data = apply_filters(prepare_dashboard_data(datasets), province, gender, start_date, end_date)
        map_frame = build_map_dataset(filtered_data)
    except GoogleSheetsConnectionError as exc:
        return [warning_card(str(exc), title="تعذر تحميل الخريطة", tone="danger")], build_empty_figure(
            "تعذر تحميل بيانات الخريطة."
        ), _build_map_side_cards(None)

    return [], build_regions_map(filtered_data), _build_map_side_cards(map_frame)
