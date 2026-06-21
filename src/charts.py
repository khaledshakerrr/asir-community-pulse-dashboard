
from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import COLORS


def build_empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        font={"size": 18, "color": COLORS["muted"]},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return apply_dashboard_theme(fig)


def apply_dashboard_theme(fig: go.Figure, title: str | None = None) -> go.Figure:
    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "'Tajawal', 'Noto Kufi Arabic', sans-serif", "color": COLORS["ink"]},
        title_font={"size": 22, "color": COLORS["ink"]},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 1, "xanchor": "right"},
        margin={"l": 20, "r": 20, "t": 56, "b": 20},
        hoverlabel={"bgcolor": COLORS["white"], "font_color": COLORS["ink"]},
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(17,37,51,0.08)", zeroline=False)
    return fig


def build_pulse_by_province_bar(filtered_data: dict) -> go.Figure:
    survey = filtered_data["tables"].get("survey_responses_simulated", pd.DataFrame())
    if survey.empty or "province_ar" not in survey.columns or "community_pulse_index" not in survey.columns:
        return build_empty_figure("لا توجد بيانات كافية لرسم مؤشر نبض المجتمع حسب المحافظة.")

    summary = (
        survey.groupby("province_ar", dropna=True)["community_pulse_index"]
        .mean()
        .reset_index()
        .sort_values("community_pulse_index", ascending=False)
    )

    fig = px.bar(
        summary,
        x="province_ar",
        y="community_pulse_index",
        text_auto=".1f",
        color="community_pulse_index",
        color_continuous_scale=[COLORS["teal"], COLORS["navy_soft"]],
        labels={"province_ar": "المحافظة", "community_pulse_index": "مؤشر نبض المجتمع"},
    )
    fig.update_traces(marker_line_width=0, hovertemplate="%{x}<br>%{y:.1f}<extra></extra>")
    fig.update_coloraxes(showscale=False)
    return apply_dashboard_theme(fig, "مؤشر نبض المجتمع حسب المحافظة")


def build_monthly_pulse_trend(filtered_data: dict) -> go.Figure:
    monthly = filtered_data["tables"].get("monthly_kpi_summary", pd.DataFrame())
    survey = filtered_data["tables"].get("survey_responses_simulated", pd.DataFrame())

    if not monthly.empty and {"period_month", "community_pulse_index"}.issubset(monthly.columns):
        trend = (
            monthly.groupby("period_month", dropna=True)["community_pulse_index"]
            .mean()
            .reset_index()
            .sort_values("period_month")
        )
    elif not survey.empty and {"response_date", "community_pulse_index"}.issubset(survey.columns):
        survey_copy = survey.copy()
        survey_copy["period_month"] = survey_copy["response_date"].dt.to_period("M").dt.to_timestamp()
        trend = (
            survey_copy.groupby("period_month", dropna=True)["community_pulse_index"]
            .mean()
            .reset_index()
            .sort_values("period_month")
        )
    else:
        return build_empty_figure("لا توجد بيانات زمنية كافية لرسم الاتجاه الشهري.")

    fig = px.line(
        trend,
        x="period_month",
        y="community_pulse_index",
        markers=True,
        labels={"period_month": "الشهر", "community_pulse_index": "المؤشر"},
    )
    fig.update_traces(line={"color": COLORS["teal"], "width": 4}, marker={"size": 8})
    return apply_dashboard_theme(fig, "الاتجاه الشهري لمؤشر نبض المجتمع")


def build_satisfaction_by_gender(filtered_data: dict) -> go.Figure:
    survey = filtered_data["tables"].get("survey_responses_simulated", pd.DataFrame())
    if survey.empty or not {"gender", "satisfaction_score"}.issubset(survey.columns):
        return build_empty_figure("لا توجد بيانات كافية لتحليل الرضا حسب الجنس.")

    summary = (
        survey.groupby("gender", dropna=True)["satisfaction_score"]
        .mean()
        .mul(20)
        .reset_index(name="satisfaction_rate")
    )

    fig = px.bar(
        summary,
        x="gender",
        y="satisfaction_rate",
        text_auto=".1f",
        color="gender",
        color_discrete_sequence=[COLORS["teal"], COLORS["navy_soft"], COLORS["cyan"]],
        labels={"gender": "الجنس", "satisfaction_rate": "معدل الرضا %"},
    )
    fig.update_layout(showlegend=False)
    return apply_dashboard_theme(fig, "معدل الرضا حسب الجنس")


def build_risk_by_age_group(filtered_data: dict) -> go.Figure:
    survey = filtered_data["tables"].get("survey_responses_simulated", pd.DataFrame())
    if survey.empty or not {"age_group", "risk_prediction_score"}.issubset(survey.columns):
        return build_empty_figure("لا توجد بيانات كافية لتحليل المخاطر حسب الفئة العمرية.")

    summary = (
        survey.groupby("age_group", dropna=True)["risk_prediction_score"]
        .mean()
        .reset_index()
        .sort_values("risk_prediction_score", ascending=False)
    )

    fig = px.bar(
        summary,
        x="age_group",
        y="risk_prediction_score",
        text_auto=".1f",
        color="risk_prediction_score",
        color_continuous_scale=[COLORS["warning"], COLORS["danger"]],
        labels={"age_group": "الفئة العمرية", "risk_prediction_score": "متوسط مؤشر المخاطر"},
    )
    fig.update_coloraxes(showscale=False)
    return apply_dashboard_theme(fig, "متوسط مؤشر المخاطر حسب الفئة العمرية")


def build_complaints_status_chart(filtered_data: dict) -> go.Figure:
    complaints = filtered_data["tables"].get("complaints_feedback", pd.DataFrame())
    if complaints.empty or "status" not in complaints.columns:
        return build_empty_figure("لا توجد بيانات كافية لحالات الشكاوى.")

    summary = complaints["status"].fillna("غير محدد").value_counts().reset_index()
    summary.columns = ["status", "count"]

    fig = px.pie(
        summary,
        names="status",
        values="count",
        hole=0.55,
        color_discrete_sequence=[COLORS["teal"], COLORS["navy_soft"], COLORS["cyan"], COLORS["warning"]],
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return apply_dashboard_theme(fig, "توزيع حالات الشكاوى")


def build_complaints_trend_chart(filtered_data: dict) -> go.Figure:
    complaints = filtered_data["tables"].get("complaints_feedback", pd.DataFrame())
    if complaints.empty or "date" not in complaints.columns:
        return build_empty_figure("لا توجد بيانات زمنية للشكاوى.")

    frame = complaints.copy()
    frame["period_month"] = frame["date"].dt.to_period("M").dt.to_timestamp()
    summary = frame["period_month"].value_counts().sort_index().reset_index()
    summary.columns = ["period_month", "count"]

    fig = px.bar(
        summary,
        x="period_month",
        y="count",
        text_auto=True,
        color_discrete_sequence=[COLORS["navy_soft"]],
        labels={"period_month": "الشهر", "count": "عدد الحالات"},
    )
    fig.update_layout(showlegend=False)
    return apply_dashboard_theme(fig, "الاتجاه الشهري للشكاوى والملاحظات")


def build_initiatives_progress_chart(filtered_data: dict) -> go.Figure:
    initiatives = filtered_data["tables"].get("initiatives_programs", pd.DataFrame())
    if initiatives.empty or not {
        "initiative_name_ar",
        "actual_beneficiaries_count",
        "target_beneficiaries_count",
    }.issubset(initiatives.columns):
        return build_empty_figure("لا توجد بيانات كافية لمتابعة المبادرات.")

    summary = initiatives.copy()
    summary["progress_pct"] = (
        summary["actual_beneficiaries_count"] / summary["target_beneficiaries_count"].replace({0: pd.NA})
    ) * 100
    summary = summary.sort_values("progress_pct", ascending=False).head(8)

    fig = px.bar(
        summary,
        x="progress_pct",
        y="initiative_name_ar",
        orientation="h",
        text_auto=".0f",
        color="progress_pct",
        color_continuous_scale=[COLORS["teal"], COLORS["navy_soft"]],
        labels={"progress_pct": "نسبة الإنجاز %", "initiative_name_ar": "المبادرة"},
    )
    fig.update_coloraxes(showscale=False)
    return apply_dashboard_theme(fig, "تقدم المبادرات والبرامج")


def build_initiatives_status_chart(filtered_data: dict) -> go.Figure:
    initiatives = filtered_data["tables"].get("initiatives_programs", pd.DataFrame())
    if initiatives.empty or "initiative_status" not in initiatives.columns:
        return build_empty_figure("لا توجد بيانات كافية لحالة المبادرات.")

    summary = initiatives["initiative_status"].fillna("غير محدد").value_counts().reset_index()
    summary.columns = ["initiative_status", "count"]

    fig = px.bar(
        summary,
        x="initiative_status",
        y="count",
        text_auto=True,
        color="initiative_status",
        color_discrete_sequence=[COLORS["teal"], COLORS["navy_soft"], COLORS["cyan"], COLORS["warning"]],
        labels={"initiative_status": "الحالة", "count": "عدد المبادرات"},
    )
    fig.update_layout(showlegend=False)
    return apply_dashboard_theme(fig, "توزيع حالات المبادرات")
