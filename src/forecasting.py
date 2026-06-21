
from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
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
                "indicator": "مؤشر نبض المجتمع",
                "month": next_month,
                "actual": None,
                "forecast": recent_mean,
                "lower_bound": recent_mean * 0.94,
                "upper_bound": recent_mean * 1.06,
            }
        )

    history = history.rename(columns={"period_month": "month", "community_pulse_index": "actual"})
    history["indicator"] = "مؤشر نبض المجتمع"
    history["forecast"] = None
    history["lower_bound"] = None
    history["upper_bound"] = None

    return pd.concat([history, pd.DataFrame(future_rows)], ignore_index=True)


def build_forecast_figure(filtered_data: dict) -> go.Figure:
    frame = build_forecast_frame(filtered_data)
    if frame.empty:
        return build_empty_figure("لا توجد بيانات كافية لبناء صفحة التنبؤات.")

    indicator = frame["indicator"].dropna().astype(str).iloc[0]
    fig = go.Figure()

    actual_frame = frame.dropna(subset=["actual"])
    if not actual_frame.empty:
        fig.add_trace(
            go.Scatter(
                x=actual_frame["month"],
                y=actual_frame["actual"],
                mode="lines+markers",
                name="الفعلي",
                line={"color": COLORS["navy_soft"], "width": 3},
            )
        )

    forecast_frame = frame.dropna(subset=["forecast"])
    if not forecast_frame.empty:
        fig.add_trace(
            go.Scatter(
                x=forecast_frame["month"],
                y=forecast_frame["forecast"],
                mode="lines+markers",
                name="التنبؤ",
                line={"color": COLORS["teal"], "width": 3, "dash": "dot"},
            )
        )

        if {"lower_bound", "upper_bound"}.issubset(forecast_frame.columns):
            fig.add_trace(
                go.Scatter(
                    x=list(forecast_frame["month"]) + list(forecast_frame["month"])[::-1],
                    y=list(forecast_frame["upper_bound"]) + list(forecast_frame["lower_bound"])[::-1],
                    fill="toself",
                    fillcolor="rgba(19,197,194,0.18)",
                    line={"color": "rgba(0,0,0,0)"},
                    name="نطاق الثقة",
                )
            )

    fig.update_yaxes(title="القيمة")
    fig.update_xaxes(title="الشهر")
    return apply_dashboard_theme(fig, f"التوقعات المستقبلية - {indicator}")
