from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import COLORS, FONT_FAMILY


def build_empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        align="center",
        font={"size": 18, "color": COLORS["muted"], "family": FONT_FAMILY},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return apply_dashboard_theme(fig)


def apply_dashboard_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": FONT_FAMILY, "color": COLORS["text_dark"]},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "x": 1,
            "xanchor": "right",
            "font": {"size": 12},
        },
        margin={"l": 34, "r": 24, "t": 16, "b": 30},
        hoverlabel={
            "bgcolor": COLORS["card_bg"],
            "font_color": COLORS["text_dark"],
            "font_family": FONT_FAMILY,
        },
        separators=".,",
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        automargin=True,
        title_standoff=14,
        tickfont={"size": 12, "color": COLORS["text_muted"]},
    )
    fig.update_yaxes(
        gridcolor=COLORS["grid"],
        zeroline=False,
        showline=False,
        automargin=True,
        title_standoff=14,
        tickfont={"size": 12, "color": COLORS["text_muted"]},
    )
    return fig


def apply_horizontal_bar_layout(fig: go.Figure, left_margin: int = 135) -> go.Figure:
    current_margin = fig.layout.margin.to_plotly_json() if fig.layout.margin else {}
    current_margin.update(
        {
            "l": max(left_margin, current_margin.get("l", 0)),
            "r": max(28, current_margin.get("r", 0)),
            "b": max(40, current_margin.get("b", 0)),
        }
    )
    fig.update_layout(margin=current_margin)
    fig.update_yaxes(automargin=True, title=None, tickfont={"size": 13, "color": COLORS["text_dark"]})
    fig.update_xaxes(automargin=True)
    return fig


def build_pulse_by_province_bar(filtered_data: dict) -> go.Figure:
    survey = filtered_data["tables"].get("survey_responses_simulated", pd.DataFrame())
    if survey.empty or "province_ar" not in survey.columns or "community_pulse_index" not in survey.columns:
        return build_empty_figure("لا توجد بيانات كافية لعرض مؤشر نبض المجتمع حسب المحافظة.")

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
        color_continuous_scale=[COLORS["accent_cyan"], COLORS["accent_teal"]],
        labels={"province_ar": "المحافظة", "community_pulse_index": "المؤشر"},
    )
    fig.update_traces(
        marker_line_width=0,
        hovertemplate="المحافظة: %{x}<br>المؤشر: %{y:.1f}<extra></extra>",
        textfont={"size": 12},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


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
        return build_empty_figure("لا توجد بيانات زمنية كافية لعرض الاتجاه الشهري.")

    fig = px.line(
        trend,
        x="period_month",
        y="community_pulse_index",
        markers=True,
        labels={"period_month": "الشهر", "community_pulse_index": "المؤشر"},
    )
    fig.update_traces(
        line={"color": COLORS["accent_teal"], "width": 4},
        marker={"size": 8, "color": COLORS["accent_cyan"], "line": {"width": 2, "color": COLORS["accent_teal"]}},
        hovertemplate="الشهر: %{x|%Y-%m}<br>المؤشر: %{y:.1f}<extra></extra>",
    )
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


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
        color_discrete_sequence=[COLORS["accent_teal"], COLORS["accent_cyan"], COLORS["warning"]],
        labels={"gender": "الجنس", "satisfaction_rate": "معدل الرضا %"},
    )
    fig.update_layout(showlegend=False)
    fig.update_traces(hovertemplate="الجنس: %{x}<br>الرضا: %{y:.1f}%<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


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
        labels={"age_group": "الفئة العمرية", "risk_prediction_score": "مؤشر المخاطر"},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(hovertemplate="الفئة العمرية: %{x}<br>متوسط المخاطر: %{y:.1f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_complaints_status_chart(filtered_data: dict) -> go.Figure:
    complaints = filtered_data["tables"].get("complaints_feedback", pd.DataFrame())
    if complaints.empty or "status" not in complaints.columns:
        return build_empty_figure("لا توجد بيانات كافية لحالات الشكاوى والتغذية الراجعة.")

    summary = complaints["status"].fillna("غير محدد").value_counts().reset_index()
    summary.columns = ["status", "count"]

    fig = px.pie(
        summary,
        names="status",
        values="count",
        hole=0.62,
        color="status",
        color_discrete_sequence=[COLORS["accent_teal"], COLORS["accent_cyan"], COLORS["warning"], COLORS["danger"]],
    )
    fig.update_traces(textposition="inside", textinfo="percent+label", hovertemplate="%{label}: %{value}<extra></extra>")
    return apply_dashboard_theme(fig)


def build_complaints_trend_chart(filtered_data: dict) -> go.Figure:
    complaints = filtered_data["tables"].get("complaints_feedback", pd.DataFrame())
    if complaints.empty or "date" not in complaints.columns:
        return build_empty_figure("لا توجد بيانات زمنية كافية لرصد تطور الشكاوى.")

    frame = complaints.copy()
    frame["period_month"] = frame["date"].dt.to_period("M").dt.to_timestamp()
    summary = frame["period_month"].value_counts().sort_index().reset_index()
    summary.columns = ["period_month", "count"]

    fig = px.bar(
        summary,
        x="period_month",
        y="count",
        text_auto=True,
        color_discrete_sequence=[COLORS["accent_teal"]],
        labels={"period_month": "الشهر", "count": "عدد الحالات"},
    )
    fig.update_layout(showlegend=False)
    fig.update_traces(hovertemplate="الشهر: %{x|%Y-%m}<br>الحالات: %{y}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_initiatives_progress_chart(filtered_data: dict) -> go.Figure:
    initiatives = filtered_data["tables"].get("initiatives_programs", pd.DataFrame())
    required = {"initiative_name_ar", "actual_beneficiaries_count", "target_beneficiaries_count"}
    if initiatives.empty or not required.issubset(initiatives.columns):
        return build_empty_figure("لا توجد بيانات كافية لقياس تقدم المبادرات.")

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
        color_continuous_scale=[COLORS["accent_cyan"], COLORS["accent_teal"]],
        labels={"progress_pct": "نسبة الإنجاز %", "initiative_name_ar": "المبادرة"},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(hovertemplate="المبادرة: %{y}<br>نسبة الإنجاز: %{x:.0f}%<extra></extra>")
    return apply_horizontal_bar_layout(apply_dashboard_theme(fig), left_margin=165)


def build_initiatives_status_chart(filtered_data: dict) -> go.Figure:
    initiatives = filtered_data["tables"].get("initiatives_programs", pd.DataFrame())
    if initiatives.empty or "initiative_status" not in initiatives.columns:
        return build_empty_figure("لا توجد بيانات كافية لتوزيع حالات المبادرات.")

    summary = initiatives["initiative_status"].fillna("غير محدد").value_counts().reset_index()
    summary.columns = ["initiative_status", "count"]

    fig = px.bar(
        summary,
        x="initiative_status",
        y="count",
        text_auto=True,
        color="initiative_status",
        color_discrete_sequence=[COLORS["accent_teal"], COLORS["accent_cyan"], COLORS["warning"], COLORS["danger"]],
        labels={"initiative_status": "الحالة", "count": "عدد المبادرات"},
    )
    fig.update_layout(showlegend=False)
    fig.update_traces(hovertemplate="الحالة: %{x}<br>العدد: %{y}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_chronic_disease_distribution(filtered_data: dict) -> go.Figure:
    survey = filtered_data["tables"].get("survey_responses_simulated", pd.DataFrame())
    if survey.empty or "predicted_disease_ar" not in survey.columns:
        return build_empty_figure("لا توجد بيانات كافية لتوزيع الأمراض المزمنة المتوقعة.")

    summary = survey["predicted_disease_ar"].fillna("غير محدد").value_counts().reset_index()
    summary.columns = ["predicted_disease_ar", "count"]
    fig = px.bar(
        summary,
        x="predicted_disease_ar",
        y="count",
        text_auto=True,
        color="predicted_disease_ar",
        color_discrete_sequence=[
            COLORS["danger"],
            COLORS["warning"],
            COLORS["accent_teal"],
            COLORS["accent_cyan"],
        ],
        labels={"predicted_disease_ar": "المرض المتوقع", "count": "عدد الحالات"},
    )
    fig.update_layout(showlegend=False)
    fig.update_traces(hovertemplate="المرض المتوقع: %{x}<br>عدد الحالات: %{y}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_chronic_risk_gauge(filtered_data: dict) -> go.Figure:
    survey = filtered_data["tables"].get("survey_responses_simulated", pd.DataFrame())
    if survey.empty or "risk_prediction_score" not in survey.columns:
        return build_empty_figure("لا توجد بيانات كافية لبناء مؤشر المخاطر المزمنة.")

    avg_risk = pd.to_numeric(survey["risk_prediction_score"], errors="coerce").mean()
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=avg_risk,
            number={"suffix": "", "font": {"size": 44, "color": COLORS["text_dark"]}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 0},
                "bar": {"color": COLORS["accent_teal"], "thickness": 0.34},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0, 40], "color": "rgba(0,168,143,0.18)"},
                    {"range": [40, 70], "color": "rgba(242,184,75,0.20)"},
                    {"range": [70, 100], "color": "rgba(231,76,60,0.18)"},
                ],
            },
        )
    )
    fig.update_layout(margin={"l": 20, "r": 20, "t": 20, "b": 0})
    return apply_dashboard_theme(fig)


def build_chronic_risk_trend(filtered_data: dict) -> go.Figure:
    survey = filtered_data["tables"].get("survey_responses_simulated", pd.DataFrame())
    if survey.empty or not {"response_date", "risk_prediction_score"}.issubset(survey.columns):
        return build_empty_figure("لا توجد بيانات كافية لعرض الاتجاه الزمني للمخاطر المزمنة.")

    frame = survey.copy()
    frame["period_month"] = frame["response_date"].dt.to_period("M").dt.to_timestamp()
    summary = (
        frame.groupby("period_month", dropna=True)["risk_prediction_score"]
        .mean()
        .reset_index()
        .sort_values("period_month")
    )
    fig = px.line(
        summary,
        x="period_month",
        y="risk_prediction_score",
        markers=True,
        labels={"period_month": "الشهر", "risk_prediction_score": "متوسط المخاطر"},
    )
    fig.update_traces(
        line={"color": COLORS["danger"], "width": 4},
        marker={"size": 7, "color": COLORS["warning"], "line": {"color": COLORS["danger"], "width": 1.5}},
        hovertemplate="الشهر: %{x|%Y-%m}<br>متوسط المخاطر: %{y:.1f}<extra></extra>",
    )
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_high_risk_regions_chart(filtered_data: dict) -> go.Figure:
    survey = filtered_data["tables"].get("survey_responses_simulated", pd.DataFrame())
    if survey.empty or not {"province_ar", "risk_prediction_score"}.issubset(survey.columns):
        return build_empty_figure("لا توجد بيانات كافية لتحديد المناطق الأعلى خطورة.")

    summary = (
        survey.groupby("province_ar", dropna=True)["risk_prediction_score"]
        .mean()
        .reset_index()
        .sort_values("risk_prediction_score", ascending=False)
        .head(8)
    )
    fig = px.bar(
        summary,
        x="risk_prediction_score",
        y="province_ar",
        orientation="h",
        text_auto=".1f",
        color="risk_prediction_score",
        color_continuous_scale=[COLORS["warning"], COLORS["danger"]],
        labels={"province_ar": "المنطقة", "risk_prediction_score": "متوسط المخاطر"},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(hovertemplate="المنطقة: %{y}<br>متوسط المخاطر: %{x:.1f}<extra></extra>")
    return apply_horizontal_bar_layout(apply_dashboard_theme(fig), left_margin=170)
