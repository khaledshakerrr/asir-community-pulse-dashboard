from __future__ import annotations

import pandas as pd
import plotly.express as px

from src.charts import apply_dashboard_theme, build_empty_figure
from src.config import COLORS


def build_regions_map(filtered_data: dict):
    regions = filtered_data["tables"].get("clean_regions_master", pd.DataFrame())
    survey = filtered_data["tables"].get("survey_responses_simulated", pd.DataFrame())

    if regions.empty or not {"region_id", "province_name_ar", "latitude", "longitude"}.issubset(regions.columns):
        return build_empty_figure("بيانات الإحداثيات غير مكتملة لعرض الخريطة.")

    map_frame = regions.copy()

    if not survey.empty and {"region_id", "community_pulse_index", "response_id"}.issubset(survey.columns):
        survey_summary = (
            survey.groupby("region_id", dropna=True)
            .agg(
                avg_pulse=("community_pulse_index", "mean"),
                responses=("response_id", "nunique"),
            )
            .reset_index()
        )
        map_frame = map_frame.merge(survey_summary, on="region_id", how="left")
    else:
        map_frame["avg_pulse"] = None
        map_frame["responses"] = None

    figure_kwargs = {
        "data_frame": map_frame,
        "lat": "latitude",
        "lon": "longitude",
        "hover_name": "province_name_ar",
        "hover_data": {
            "region_id": True,
            "avg_pulse": ":.1f",
            "responses": True,
            "latitude": False,
            "longitude": False,
        },
        "zoom": 6,
        "height": 460,
    }
    if map_frame["responses"].notna().any():
        figure_kwargs["size"] = "responses"
    if map_frame["avg_pulse"].notna().any():
        figure_kwargs["color"] = "avg_pulse"
        figure_kwargs["color_continuous_scale"] = [COLORS["teal"], COLORS["navy_soft"]]

    fig = px.scatter_mapbox(**figure_kwargs)
    fig.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox_center={"lat": map_frame["latitude"].mean(), "lon": map_frame["longitude"].mean()},
        coloraxis_showscale=False,
    )
    return apply_dashboard_theme(fig, "الخريطة التفاعلية للمناطق والمحافظات")
