from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.charts import apply_dashboard_theme, build_empty_figure, apply_horizontal_bar_layout
from src.config import COLORS


RISK_COLORS = {
    "منخفض": COLORS["success"],
    "متوسط": COLORS["warning"],
    "مرتفع": COLORS["danger"],
}


def build_environment_map(current_frame: pd.DataFrame, color_column: str, title_label: str) -> go.Figure:
    if current_frame.empty:
        return build_empty_figure("لا توجد بيانات بيئية حية متاحة لرسم الخريطة.")

    fig = px.scatter_mapbox(
        current_frame,
        lat="latitude",
        lon="longitude",
        color="risk_level",
        size=current_frame[color_column].clip(lower=10) if color_column in current_frame.columns else None,
        size_max=30,
        color_discrete_map=RISK_COLORS,
        zoom=5.2,
        center={"lat": 22.4, "lon": 43.1},
        custom_data=[
            "province_ar",
            "city_ar",
            "temperature_c",
            "humidity_pct",
            "aqi",
            color_column,
            "alert_text",
        ],
        opacity=0.92,
    )
    fig.update_traces(
        hovertemplate=(
            "المنطقة: %{customdata[0]}<br>"
            "المدينة: %{customdata[1]}<br>"
            "الحرارة: %{customdata[2]:.1f}°<br>"
            "الرطوبة: %{customdata[3]:.0f}%<br>"
            "AQI: %{customdata[4]:.0f}<br>"
            f"{title_label}: %{{customdata[5]:.1f}}<br>"
            "المحركات: %{customdata[6]}<extra></extra>"
        ),
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        legend_title_text="مستوى المخاطر",
    )
    return apply_dashboard_theme(fig)


def build_city_environment_bar(current_frame: pd.DataFrame, metric_column: str, x_title: str, color_column: str | None = None) -> go.Figure:
    if current_frame.empty or metric_column not in current_frame.columns:
        return build_empty_figure("لا توجد بيانات كافية لبناء الترتيب الحالي.")

    frame = current_frame.sort_values(metric_column, ascending=True)
    fig = px.bar(
        frame,
        x=metric_column,
        y="city_ar",
        orientation="h",
        text_auto=".1f",
        color=color_column if color_column and color_column in frame.columns else metric_column,
        color_continuous_scale=[COLORS["success"], COLORS["warning"], COLORS["danger"]],
        color_discrete_map=RISK_COLORS,
        labels={"city_ar": "المدينة", metric_column: x_title},
    )
    if color_column:
        fig.update_coloraxes(showscale=False)
    else:
        fig.update_layout(showlegend=False)
    fig.update_traces(hovertemplate="المدينة: %{y}<br>القيمة: %{x:.1f}<extra></extra>")
    fig.update_yaxes(title=None)
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["grid"])
    fig = apply_dashboard_theme(fig)
    return apply_horizontal_bar_layout(fig, left_margin=180)


def build_multi_metric_scatter(current_frame: pd.DataFrame) -> go.Figure:
    if current_frame.empty:
        return build_empty_figure("لا توجد بيانات كافية لبناء العلاقة بين الهواء والحرارة.")

    fig = px.scatter(
        current_frame,
        x="pm25",
        y="temperature_c",
        size="respiratory_risk_index",
        color="province_ar",
        hover_name="city_ar",
        color_discrete_sequence=[COLORS["accent_teal"], COLORS["accent_cyan"]],
        labels={"pm25": "PM2.5", "temperature_c": "الحرارة °م", "province_ar": "المنطقة"},
    )
    fig.update_traces(
        hovertemplate="المدينة: %{hovertext}<br>PM2.5: %{x:.1f}<br>الحرارة: %{y:.1f}°<br>الخطر التنفسي: %{marker.size:.1f}<extra></extra>"
    )
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_forecast_trend_chart(forecast_frame: pd.DataFrame, metric_column: str, title_label: str) -> go.Figure:
    if forecast_frame.empty or metric_column not in forecast_frame.columns:
        return build_empty_figure("لا توجد بيانات كافية لبناء التوقعات القصيرة المدى.")

    focus = (
        forecast_frame.groupby("city_ar", dropna=True)[metric_column]
        .mean()
        .sort_values(ascending=False)
        .head(4)
        .index.tolist()
    )
    frame = forecast_frame[forecast_frame["city_ar"].isin(focus)].copy()
    fig = px.line(
        frame,
        x="forecast_date",
        y=metric_column,
        color="city_ar",
        markers=True,
        labels={"forecast_date": "التاريخ", metric_column: title_label, "city_ar": "المدينة"},
        color_discrete_sequence=[COLORS["danger"], COLORS["warning"], COLORS["accent_teal"], COLORS["accent_cyan"]],
    )
    fig.update_traces(hovertemplate="%{fullData.name}<br>%{x|%Y-%m-%d}: %{y:.1f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_forecast_heatmap(forecast_frame: pd.DataFrame, metric_column: str, colorbar_title: str) -> go.Figure:
    if forecast_frame.empty or metric_column not in forecast_frame.columns:
        return build_empty_figure("لا توجد بيانات كافية لبناء الخريطة الحرارية للتوقعات.")

    pivot = forecast_frame.pivot_table(index="city_ar", columns="forecast_date", values=metric_column, aggfunc="mean")
    if pivot.empty:
        return build_empty_figure("لا توجد بيانات كافية لبناء الخريطة الحرارية للتوقعات.")

    fig = go.Figure(
        data=
        go.Heatmap(
            z=pivot.values,
            x=[pd.to_datetime(value).strftime("%Y-%m-%d") for value in pivot.columns],
            y=pivot.index.tolist(),
            colorscale=[
                [0.0, COLORS["success"]],
                [0.5, COLORS["warning"]],
                [1.0, COLORS["danger"]],
            ],
            colorbar={"title": colorbar_title},
            hovertemplate="المدينة: %{y}<br>التاريخ: %{x}<br>القيمة: %{z:.1f}<extra></extra>",
        )
    )
    fig.update_xaxes(title=None, showgrid=False)
    fig.update_yaxes(title=None, showgrid=False)
    return apply_dashboard_theme(fig)


def build_alert_distribution_chart(current_frame: pd.DataFrame) -> go.Figure:
    if current_frame.empty:
        return build_empty_figure("لا توجد بيانات كافية لتحليل توزيع مستويات الإنذار.")

    summary = current_frame["risk_level"].value_counts().reindex(["مرتفع", "متوسط", "منخفض"]).fillna(0).reset_index()
    summary.columns = ["risk_level", "count"]
    fig = px.bar(
        summary,
        x="risk_level",
        y="count",
        text_auto=True,
        color="risk_level",
        color_discrete_map=RISK_COLORS,
        labels={"risk_level": "مستوى الإنذار", "count": "عدد المدن"},
    )
    fig.update_layout(showlegend=False)
    fig.update_traces(hovertemplate="المستوى: %{x}<br>المدن: %{y}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)
