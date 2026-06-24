from __future__ import annotations

import pandas as pd
import plotly.express as px

from src.charts import apply_dashboard_theme, build_empty_figure
from src.config import COLORS
from src.official_analytics import get_region_summary

SAUDI_CENTER = {"lat": 23.8859, "lon": 45.0792}
ASIR_CENTER = {"lat": 18.2164, "lon": 42.5053}
QASSIM_CENTER = {"lat": 26.3303, "lon": 43.9743}
RISK_COLOR_MAP = {
    "عالي": COLORS["danger"],
    "مرتفع": COLORS["danger"],
    "متوسط": COLORS["warning"],
    "منخفض": COLORS["success"],
}


def build_map_dataset(filtered_data: dict) -> pd.DataFrame:
    summary = get_region_summary(filtered_data)
    if summary.empty:
        return pd.DataFrame()

    frame = summary.copy()
    frame["province_name_ar"] = frame["province_name_ar"].fillna(frame["region_name_ar"])
    frame["city_name_ar"] = frame["city_name_ar"].fillna(frame["province_name_ar"])
    frame["risk_level"] = frame["risk_level"].fillna(frame["priority_level"]).fillna("منخفض")
    frame["marker_size"] = (
        pd.to_numeric(frame["population_total"], errors="coerce").fillna(0).pow(0.4) * 0.9
    ).clip(lower=14, upper=32)
    return frame


def _resolve_map_view(map_frame: pd.DataFrame) -> tuple[dict[str, float], float]:
    if map_frame.empty:
        return SAUDI_CENTER, 4.0

    provinces = set(map_frame.get("province_name_ar", pd.Series(dtype="object")).dropna().astype(str))
    if provinces == {"عسير"}:
        return ASIR_CENTER, 6.0
    if provinces == {"القصيم"}:
        return QASSIM_CENTER, 6.0
    if len(map_frame) <= 3:
        return {
            "lat": pd.to_numeric(map_frame["latitude"], errors="coerce").mean(),
            "lon": pd.to_numeric(map_frame["longitude"], errors="coerce").mean(),
        }, 5.0
    return SAUDI_CENTER, 4.2


def build_regions_map(filtered_data: dict):
    map_frame = build_map_dataset(filtered_data)
    if map_frame.empty:
        return build_empty_figure("بيانات الخريطة الرسمية غير متاحة حالياً.")

    center, zoom = _resolve_map_view(map_frame)
    fig = px.scatter_mapbox(
        map_frame,
        lat="latitude",
        lon="longitude",
        color="risk_level",
        size="marker_size",
        size_max=28,
        color_discrete_map=RISK_COLOR_MAP,
        hover_name="province_name_ar",
        custom_data=[
            "province_name_ar",
            "city_name_ar",
            "community_pulse_index",
            "doctor_time_satisfaction_pct",
            "hospitals_total",
            "risk_level",
        ],
        zoom=zoom,
        center=center,
        opacity=0.92,
    )
    fig.update_traces(
        marker={"opacity": 0.94},
        hovertemplate=(
            "المحافظة: %{customdata[0]}<br>"
            "المدينة: %{customdata[1]}<br>"
            "مؤشر الجاهزية المركب: %{customdata[2]:.1f}<br>"
            "رضا وقت الطبيب: %{customdata[3]:.1f}%<br>"
            "عدد المستشفيات: %{customdata[4]:,.0f}<br>"
            "مستوى الأولوية: %{customdata[5]}<extra></extra>"
        ),
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_center=center,
        mapbox_zoom=zoom,
        legend_title_text="مستوى الأولوية",
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
    )
    return apply_dashboard_theme(fig)
