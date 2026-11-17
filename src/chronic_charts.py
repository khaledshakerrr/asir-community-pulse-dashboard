"""Annual published chronic-care snapshots; never interpolate across geographies."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.charts import apply_dashboard_theme, apply_horizontal_bar_layout, build_empty_figure
from src.chronic_care import FACILITY_ORDER
from src.config import COLORS


ENTITY_COLORS = {
    "عسير": COLORS["accent_teal"],
    "بيشة": COLORS["warning"],
    "القصيم": COLORS["accent_cyan"],
    "السعودية": COLORS["navy_soft"],
    "إجمالي تجمع عسير (عسير وبيشة)": COLORS["accent_teal"],
}


def select_snapshot(frame: pd.DataFrame, year: int, scope: str = "focus") -> pd.DataFrame:
    """Select published rows without aggregating national/subtotal/detail records."""
    selected = frame.loc[frame["year"].eq(year)].copy()
    if scope == "focus":
        return selected.loc[selected["row_role"].eq("detail")].copy()
    return selected.loc[selected["entity_key"].eq(scope)].copy()


def build_diabetes_snapshot_chart(frame: pd.DataFrame, year: int, scope: str = "focus") -> go.Figure:
    selected = select_snapshot(frame, year, scope)
    if selected.empty or selected["visits_total"].isna().all():
        return build_empty_figure("لا توجد قيمة منشورة لهذا النطاق في هذه السنة.")
    selected = selected.dropna(subset=["visits_total"])
    selected["visits_total"] = selected["visits_total"].astype(int)
    fig = px.bar(
        selected,
        x="visits_total",
        y="entity_label_ar",
        color="entity_label_ar",
        orientation="h",
        text="visits_total",
        color_discrete_map=ENTITY_COLORS,
        custom_data=["source_geography_ar", "source_table", "year"],
        labels={"visits_total": "عدد الزيارات", "entity_label_ar": "النطاق"},
    )
    fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{customdata[0]}<br>السنة: %{customdata[2]}<br>الزيارات: %{x:,.0f}<br>جدول %{customdata[1]}<extra></extra>",
    )
    apply_horizontal_bar_layout(apply_dashboard_theme(fig), left_margin=90)
    fig.update_layout(showlegend=False, margin={"r": 62})
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(rangemode="tozero", tickformat=",.0f", nticks=3, tickangle=0, title=None)
    return fig


def build_chronic_capacity_chart(frame: pd.DataFrame, year: int, scope: str = "focus") -> go.Figure:
    selected = select_snapshot(frame, year, scope)
    if selected.empty or selected["value"].isna().all():
        return build_empty_figure("لا توجد بيانات مرافق منشورة لهذا النطاق في هذه السنة.")
    selected = selected.dropna(subset=["value"])
    selected["value"] = selected["value"].astype(int)
    short_labels = {
        "cardiology": "مراكز القلب",
        "oncology": "مراكز الأورام",
        "diabetes_endocrinology": "السكري والغدد",
        "dialysis": "الغسيل الكلوي",
    }
    selected["facility_display"] = selected["facility_type"].map(short_labels)
    fig = px.bar(
        selected,
        x="value",
        y="facility_display",
        color="entity_label_ar",
        orientation="h",
        barmode="group",
        text="value",
        color_discrete_map=ENTITY_COLORS,
        category_orders={"facility_display": [short_labels[key] for key in FACILITY_ORDER]},
        custom_data=["facility_label_ar", "source_geography_ar", "source_table"],
        labels={"value": "عدد المرافق", "facility_display": "", "entity_label_ar": "النطاق"},
    )
    fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{customdata[1]}<br>%{customdata[0]}: %{x:,.0f}<br>جدول %{customdata[2]}<extra></extra>",
    )
    apply_horizontal_bar_layout(apply_dashboard_theme(fig), left_margin=125)
    fig.update_layout(margin={"r": 50, "t": 42}, legend={"y": 1.04})
    fig.update_xaxes(rangemode="tozero", dtick=1 if selected["value"].max() < 10 else None, tickformat=",.0f", title=None)
    return fig


def build_diabetes_rehabilitation_chart(frame: pd.DataFrame) -> go.Figure:
    selected = frame.loc[frame["entity_key"].eq("saudi_arabia") & frame["geography_type"].eq("national")].copy()
    selected = selected.dropna(subset=["visits_total"]).sort_values("year")
    if selected.empty:
        return build_empty_figure("لا توجد بيانات وطنية منشورة لزيارات التأهيل.")
    selected["visits_total"] = selected["visits_total"].astype(int)
    selected["year_label"] = selected["year"].astype(str)
    fig = px.bar(
        selected,
        x="year_label",
        y="visits_total",
        color="year_label",
        text="visits_total",
        color_discrete_map={"2023": COLORS["accent_cyan"], "2024": COLORS["accent_teal"]},
        labels={"year_label": "السنة", "visits_total": "عدد زيارات التأهيل"},
    )
    fig.update_traces(
        texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False,
        hovertemplate="السعودية — %{x}<br>زيارات التأهيل المرتبطة بالسكري بعد البتر: %{y:,.0f}<extra></extra>",
    )
    apply_dashboard_theme(fig)
    fig.update_layout(showlegend=False, margin={"t": 36})
    fig.update_xaxes(title=None, type="category")
    fig.update_yaxes(title=None, rangemode="tozero", tickformat=",.0f")
    return fig


def get_national_dialysis_total(frame: pd.DataFrame) -> int | None:
    """Sum only the two published treatment totals, never their sector detail."""
    totals = frame.loc[frame["year"].eq(2024) & frame["entity_key"].eq("saudi_arabia") & frame["sector_key"].eq("all_sectors")]
    if len(totals) != 2 or set(totals["treatment_key"]) != {"haemodialysis", "peritoneal"} or totals["patients"].isna().any():
        return None
    return int(totals["patients"].sum())


def build_dialysis_patients_chart(frame: pd.DataFrame) -> go.Figure:
    selected = frame.loc[
        frame["year"].eq(2024)
        & frame["entity_key"].eq("saudi_arabia")
        & frame["geography_type"].eq("national")
        & frame["aggregation_role"].eq("detail")
    ].copy()
    if selected.empty or selected["patients"].isna().any():
        return build_empty_figure("لا تتوفر بيانات مكتملة لمرضى الغسيل الكلوي حسب القطاع.")
    selected["patients"] = selected["patients"].astype(int)
    fig = px.bar(
        selected,
        x="patients",
        y="treatment_label_ar",
        color="sector_label_ar",
        orientation="h",
        barmode="stack",
        text="patients",
        category_orders={
            "treatment_label_ar": ["التنقية الدموية", "التنقية البريتونية"],
            "sector_label_ar": ["وزارة الصحة", "جهات حكومية أخرى", "القطاع الخاص"],
        },
        color_discrete_map={
            "وزارة الصحة": COLORS["accent_teal"],
            "جهات حكومية أخرى": COLORS["accent_cyan"],
            "القطاع الخاص": COLORS["warning"],
        },
        labels={"patients": "عدد المرضى", "treatment_label_ar": "نوع التنقية", "sector_label_ar": "القطاع الصحي"},
    )
    fig.update_traces(
        texttemplate="%{text:,.0f}", textposition="inside", insidetextanchor="middle",
        hovertemplate="%{fullData.name}<br>%{y}: %{x:,.0f} مريض<br>السعودية — 2024<extra></extra>",
    )
    apply_horizontal_bar_layout(apply_dashboard_theme(fig), left_margin=120)
    fig.update_layout(
        margin={"t": 72, "r": 20},
        uniformtext={"minsize": 11, "mode": "hide"},
        legend={"title": None, "font": {"size": 11}},
    )
    fig.update_xaxes(title=None, rangemode="tozero", nticks=3, tickangle=0, tickformat=",.0f")
    return fig
