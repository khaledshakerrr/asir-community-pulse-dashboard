from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.charts import apply_dashboard_theme, build_empty_figure
from src.config import COLORS
from src.official_analytics import (
    build_utilization_long,
    get_asir_clusters,
    get_focus_comparison,
    get_qassim_governorates,
    get_region_summary,
    get_workforce_regional,
)


FOCUS_COLORS = {
    "السعودية": COLORS["navy_soft"],
    "عسير": COLORS["accent_teal"],
    "القصيم": COLORS["accent_cyan"],
    "بيشة": COLORS["warning"],
}


def build_focus_capacity_chart(filtered_data: dict) -> go.Figure:
    focus = get_focus_comparison(filtered_data)
    if focus.empty:
        return build_empty_figure("لا توجد بيانات رسمية كافية لبناء المقارنة الإقليمية.")

    frame = focus.melt(
        id_vars=["display_name"],
        value_vars=["hospitals_per_100k", "beds_per_1000", "phc_per_10k"],
        var_name="metric",
        value_name="value",
    )
    metric_labels = {
        "hospitals_per_100k": "المستشفيات لكل 100 ألف",
        "beds_per_1000": "الأسرة لكل 1000",
        "phc_per_10k": "الرعاية الأولية لكل 10 آلاف",
    }
    frame["metric"] = frame["metric"].map(metric_labels)
    fig = px.bar(
        frame,
        x="metric",
        y="value",
        color="display_name",
        barmode="group",
        text_auto=".2f",
        color_discrete_map=FOCUS_COLORS,
        labels={"display_name": "النطاق", "metric": "", "value": "القيمة"},
    )
    fig.update_traces(marker_line_width=0, hovertemplate="%{fullData.name}<br>%{x}: %{y:.2f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    fig.update_yaxes(title=None)
    return apply_dashboard_theme(fig)


def build_focus_access_chart(filtered_data: dict) -> go.Figure:
    focus = get_focus_comparison(filtered_data)
    if focus.empty:
        return build_empty_figure("لا توجد بيانات رسمية كافية لتحليل الوصول الرقمي والرضا.")

    frame = focus.melt(
        id_vars=["display_name"],
        value_vars=["doctor_time_satisfaction_pct", "teleconsultation_pct", "emr_access_pct"],
        var_name="metric",
        value_name="value",
    )
    metric_labels = {
        "doctor_time_satisfaction_pct": "رضا وقت الطبيب",
        "teleconsultation_pct": "الاستشارات عن بعد",
        "emr_access_pct": "الوصول للسجل الطبي",
    }
    frame["metric"] = frame["metric"].map(metric_labels)
    fig = px.bar(
        frame,
        x="metric",
        y="value",
        color="display_name",
        barmode="group",
        text_auto=".1f",
        color_discrete_map=FOCUS_COLORS,
        labels={"display_name": "النطاق", "metric": "", "value": "النسبة %"},
    )
    fig.update_traces(marker_line_width=0, hovertemplate="%{fullData.name}<br>%{x}: %{y:.1f}%<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    fig.update_yaxes(title=None)
    return apply_dashboard_theme(fig)


def build_qassim_population_chart(filtered_data: dict) -> go.Figure:
    frame = get_qassim_governorates(filtered_data)
    if frame.empty:
        return build_empty_figure("تفصيل محافظات القصيم غير متاح ضمن النطاق الحالي.")

    frame = frame.sort_values("population_total", ascending=True)
    fig = px.bar(
        frame,
        x="population_total",
        y="governorate_ar",
        orientation="h",
        text_auto=True,
        color_discrete_sequence=[COLORS["accent_teal"]],
        labels={"population_total": "عدد السكان", "governorate_ar": "المحافظة"},
    )
    fig.update_layout(showlegend=False)
    fig.update_yaxes(title=None)
    fig.update_traces(hovertemplate="المحافظة: %{y}<br>السكان: %{x:,.0f}<extra></extra>")
    return apply_dashboard_theme(fig)


def build_asir_cluster_capacity_chart(filtered_data: dict) -> go.Figure:
    frame = get_asir_clusters(filtered_data)
    if frame.empty:
        return build_empty_figure("تفصيل تجمعات عسير غير متاح ضمن النطاق الحالي.")

    long_frame = frame.melt(
        id_vars=["cluster_name_ar"],
        value_vars=["beds_total", "icu_beds", "diabetic_clinic_visits_2024"],
        var_name="metric",
        value_name="value",
    )
    long_frame["metric"] = long_frame["metric"].map(
        {
            "beds_total": "إجمالي الأسرة",
            "icu_beds": "أسرة العناية المركزة",
            "diabetic_clinic_visits_2024": "زيارات عيادات السكري",
        }
    )
    fig = px.bar(
        long_frame,
        x="metric",
        y="value",
        color="cluster_name_ar",
        barmode="group",
        text_auto=True,
        color_discrete_sequence=[COLORS["accent_teal"], COLORS["warning"]],
        labels={"cluster_name_ar": "التجمع", "metric": "", "value": "القيمة"},
    )
    fig.update_traces(hovertemplate="%{fullData.name}<br>%{x}: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_workforce_totals_chart(filtered_data: dict) -> go.Figure:
    frame = get_workforce_regional(filtered_data)
    if frame.empty:
        return build_empty_figure("لا توجد بيانات رسمية كافية للقوى العاملة ضمن النطاق الحالي.")

    long_frame = frame.melt(
        id_vars=["region_name_ar"],
        value_vars=[
            "physicians_total_all_sectors",
            "nurses_and_midwives_total_all_sectors",
            "pharmacists_total_all_sectors",
        ],
        var_name="metric",
        value_name="value",
    )
    long_frame["metric"] = long_frame["metric"].map(
        {
            "physicians_total_all_sectors": "الأطباء",
            "nurses_and_midwives_total_all_sectors": "التمريض والقبالة",
            "pharmacists_total_all_sectors": "الصيادلة",
        }
    )
    fig = px.bar(
        long_frame,
        x="metric",
        y="value",
        color="region_name_ar",
        barmode="group",
        text_auto=True,
        color_discrete_map=FOCUS_COLORS,
        labels={"region_name_ar": "المنطقة", "metric": "", "value": "عدد الكوادر"},
    )
    fig.update_traces(hovertemplate="%{fullData.name}<br>%{x}: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_workforce_share_chart(filtered_data: dict) -> go.Figure:
    frame = get_workforce_regional(filtered_data)
    if frame.empty:
        return build_empty_figure("لا توجد بيانات كافية لحساب مساهمة وزارة الصحة ضمن القوى العاملة.")

    share = frame.copy()
    share["moh_share_pct"] = (
        pd.to_numeric(share["physicians_total_moh"], errors="coerce")
        / pd.to_numeric(share["physicians_total_all_sectors"], errors="coerce").replace({0: pd.NA})
        * 100
    )
    fig = px.bar(
        share,
        x="region_name_ar",
        y="moh_share_pct",
        text_auto=".1f",
        color="region_name_ar",
        color_discrete_map=FOCUS_COLORS,
        labels={"region_name_ar": "المنطقة", "moh_share_pct": "حصة وزارة الصحة من الأطباء %"},
    )
    fig.update_layout(showlegend=False)
    fig.update_traces(hovertemplate="المنطقة: %{x}<br>حصة وزارة الصحة: %{y:.1f}%<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_utilization_focus_chart(filtered_data: dict) -> go.Figure:
    region_summary = get_region_summary(filtered_data)
    frame = build_utilization_long(region_summary)
    if frame.empty:
        return build_empty_figure("لا توجد سلسلة رسمية كافية لتحليل الطلب الصحي التاريخي.")

    frame = frame[frame["service_type"] == "إجمالي الطلب الصحي"].copy()
    fig = px.line(
        frame,
        x="year",
        y="value",
        color="entity",
        markers=True,
        color_discrete_map=FOCUS_COLORS,
        labels={"entity": "النطاق", "year": "السنة", "value": "إجمالي الطلب الصحي"},
    )
    fig.update_traces(line={"width": 4}, marker={"size": 8}, hovertemplate="%{fullData.name}<br>%{x}: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_regional_ranking_chart(filtered_data: dict) -> go.Figure:
    frame = get_region_summary(filtered_data)
    if frame.empty:
        return build_empty_figure("لا توجد بيانات إقليمية كافية لبناء ترتيب المقارنة.")

    frame = frame.sort_values("community_pulse_index", ascending=True)
    fig = px.bar(
        frame,
        x="community_pulse_index",
        y="province_name_ar",
        orientation="h",
        text_auto=".1f",
        color="risk_prediction_score",
        color_continuous_scale=[COLORS["success"], COLORS["warning"], COLORS["danger"]],
        labels={"community_pulse_index": "مؤشر الجاهزية المركب", "province_name_ar": "المنطقة"},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_yaxes(title=None)
    fig.update_traces(
        hovertemplate="المنطقة: %{y}<br>المؤشر المركب: %{x:.1f}<br>ضغط المخاطر: %{marker.color:.1f}<extra></extra>"
    )
    return apply_dashboard_theme(fig)


def build_service_mix_chart(filtered_data: dict) -> go.Figure:
    focus = get_focus_comparison(filtered_data)
    if focus.empty:
        return build_empty_figure("لا توجد بيانات رسمية كافية لتحليل مزيج الخدمات.")

    frame = focus[focus["display_name"] != "السعودية"].copy()
    if frame.empty:
        return build_empty_figure("اختر عسير أو القصيم لعرض مزيج الخدمات.")

    long_frame = frame.melt(
        id_vars=["display_name"],
        value_vars=["hospitals_total", "phc_total", "private_pharmacies"],
        var_name="metric",
        value_name="value",
    )
    long_frame["metric"] = long_frame["metric"].map(
        {
            "hospitals_total": "المستشفيات",
            "phc_total": "مراكز الرعاية",
            "private_pharmacies": "الصيدليات الخاصة",
        }
    )
    fig = px.bar(
        long_frame,
        x="display_name",
        y="value",
        color="metric",
        barmode="stack",
        text_auto=True,
        color_discrete_sequence=[COLORS["navy_soft"], COLORS["accent_teal"], COLORS["accent_cyan"]],
        labels={"display_name": "المنطقة", "value": "عدد المواقع/الخدمات", "metric": "نوع الخدمة"},
    )
    fig.update_traces(hovertemplate="%{x}<br>%{fullData.name}: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)
