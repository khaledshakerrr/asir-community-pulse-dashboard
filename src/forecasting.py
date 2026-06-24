from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.charts import apply_dashboard_theme, build_empty_figure
from src.config import COLORS


def build_forecast_frame(filtered_data: dict) -> pd.DataFrame:
    forecasting = filtered_data["tables"].get("forecasting_data", pd.DataFrame())
    monthly = filtered_data["tables"].get("monthly_kpi_summary", pd.DataFrame())

    if not forecasting.empty and {"indicator", "month", "actual", "forecast"}.issubset(forecasting.columns):
        return forecasting.sort_values(["indicator", "month"]).copy()

    if monthly.empty or not {"period_month", "community_pulse_index"}.issubset(monthly.columns):
        return pd.DataFrame()

    history = (
        monthly.groupby("period_month", dropna=True)["community_pulse_index"]
        .mean()
        .reset_index()
        .sort_values("period_month")
    )
    if history.empty:
        return pd.DataFrame()

    recent_mean = history["community_pulse_index"].tail(min(3, len(history))).mean()
    last_month = history["period_month"].max()
    future_rows = []
    for step in range(1, 4):
        next_month = (last_month + pd.offsets.MonthBegin(step)).normalize()
        future_rows.append(
            {
                "indicator": "توقع الطلب الصحي التشغيلي",
                "month": next_month,
                "actual": None,
                "forecast": recent_mean,
                "lower_bound": recent_mean * 0.94,
                "upper_bound": recent_mean * 1.06,
            }
        )

    history = history.rename(columns={"period_month": "month", "community_pulse_index": "actual"})
    history["indicator"] = "توقع الطلب الصحي التشغيلي"
    history["forecast"] = None
    history["lower_bound"] = None
    history["upper_bound"] = None

    return pd.concat([history, pd.DataFrame(future_rows)], ignore_index=True)


def build_forecast_figure(filtered_data: dict) -> go.Figure:
    frame = build_forecast_frame(filtered_data)
    if frame.empty:
        return build_empty_figure("لا توجد بيانات زمنية كافية لبناء توقع تشغيلي موثوق.")

    indicator = frame["indicator"].dropna().astype(str).iloc[0]
    fig = go.Figure()

    actual_frame = frame.dropna(subset=["actual"])
    if not actual_frame.empty:
        fig.add_trace(
            go.Scatter(
                x=actual_frame["month"],
                y=actual_frame["actual"],
                mode="lines+markers",
                name="القيمة الفعلية",
                line={"color": COLORS["navy_soft"], "width": 3},
                marker={"size": 7, "color": COLORS["navy_soft"]},
            )
        )

    forecast_frame = frame.dropna(subset=["forecast"]).sort_values("month")
    if not forecast_frame.empty:
        if {"lower_bound", "upper_bound"}.issubset(forecast_frame.columns):
            fig.add_trace(
                go.Scatter(
                    x=list(forecast_frame["month"]) + list(forecast_frame["month"])[::-1],
                    y=list(forecast_frame["upper_bound"]) + list(forecast_frame["lower_bound"])[::-1],
                    fill="toself",
                    fillcolor="rgba(40,214,196,0.18)",
                    line={"color": "rgba(0,0,0,0)"},
                    hoverinfo="skip",
                    name="نطاق الثقة",
                )
            )

        fig.add_trace(
            go.Scatter(
                x=forecast_frame["month"],
                y=forecast_frame["forecast"],
                mode="lines+markers",
                name="التنبؤ",
                line={"color": COLORS["accent_teal"], "width": 3, "dash": "dot"},
                marker={"size": 7, "color": COLORS["accent_cyan"]},
            )
        )

    fig.update_xaxes(title="الفترة الزمنية")
    fig.update_yaxes(title="حجم الطلب الصحي", showgrid=True, gridcolor=COLORS["grid"])
    fig.update_layout(legend={"orientation": "h", "x": 1, "xanchor": "right", "y": 1.05})
    fig = apply_dashboard_theme(fig)
    fig.update_layout(hovermode="x unified")
    fig.update_traces(hovertemplate=None)
    return fig
