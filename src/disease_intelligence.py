from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.charts import apply_dashboard_theme, apply_horizontal_bar_layout, build_empty_figure
from src.config import COLORS
from src.environmental_models import build_environmental_current_frame, build_environmental_forecast_frame, classify_risk_level


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DISEASE_DIR = PROJECT_ROOT / "data" / "official_curated" / "diseases"

DISEASE_FILES = {
    "disease_catalog_ar": "disease_catalog_ar.csv",
    "communicable_diseases_by_region_ar": "communicable_diseases_by_region_ar.csv",
    "communicable_diseases_by_month_ar": "communicable_diseases_by_month_ar.csv",
    "communicable_diseases_by_age_ar": "communicable_diseases_by_age_ar.csv",
    "communicable_diseases_by_gender_nationality_ar": "communicable_diseases_by_gender_nationality_ar.csv",
    "communicable_diseases_5_year_trend_ar": "communicable_diseases_5_year_trend_ar.csv",
    "tuberculosis_ar": "tuberculosis_ar.csv",
    "malaria_ar": "malaria_ar.csv",
    "bilharzia_ar": "bilharzia_ar.csv",
    "leishmaniasis_ar": "leishmaniasis_ar.csv",
    "foodborne_outbreaks_ar": "foodborne_outbreaks_ar.csv",
    "intoxication_ar": "intoxication_ar.csv",
    "environmental_health_diseases_ar": "environmental_health_diseases_ar.csv",
    "immunization_gap_ar": "immunization_gap_ar.csv",
}

SUPPORT_FILES = {
    "official_region_summary": [
        PROJECT_ROOT / "data" / "official_curated" / "official_region_summary_2024.csv",
        PROJECT_ROOT / "data" / "official_google_sheet_tabs" / "official_region_summary.csv",
    ],
    "workforce_regional": [
        PROJECT_ROOT / "data" / "official_curated" / "asir_qassim_workforce_2024.csv",
        PROJECT_ROOT / "data" / "official_google_sheet_tabs" / "workforce_regional.csv",
    ],
    "asir_clusters": [
        PROJECT_ROOT / "data" / "official_curated" / "asir_cluster_detail_2024.csv",
        PROJECT_ROOT / "data" / "official_google_sheet_tabs" / "asir_clusters.csv",
    ],
    "qassim_governorates": [
        PROJECT_ROOT / "data" / "official_curated" / "qassim_governorate_population_detail.csv",
        PROJECT_ROOT / "data" / "official_google_sheet_tabs" / "qassim_governorates.csv",
    ],
}

REGION_ORDER = [
    "السعودية",
    "الرياض",
    "مكة المكرمة",
    "المدينة المنورة",
    "القصيم",
    "الشرقية",
    "عسير",
    "بيشة",
    "تبوك",
    "حائل",
    "الحدود الشمالية",
    "جازان",
    "نجران",
    "الباحة",
    "الجوف",
]

MONTH_AR_ORDER = ["يناير", "فبراير", "مارس", "ابريل", "مايو", "يونيه", "يوليو", "أغسطس", "سبتمبر", "اكتوبر", "نوفمبر", "ديسمبر"]
MONTH_TO_NUM = {name: index + 1 for index, name in enumerate(MONTH_AR_ORDER)}


def _read_first_existing_csv(candidates: list[Path]) -> pd.DataFrame:
    for path in candidates:
        if path.is_file():
            return pd.read_csv(path)
    return pd.DataFrame()


def _ensure_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _normalize_table_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame.copy()
    for column in frame.columns:
        if frame[column].dtype == object:
            frame[column] = frame[column].fillna("").astype(str).str.strip()
    return frame


def _available_disease_names(tables: dict[str, pd.DataFrame]) -> list[str]:
    disease_names: set[str] = set()
    for table_name in [
        "communicable_diseases_by_region_ar",
        "communicable_diseases_by_month_ar",
        "communicable_diseases_by_age_ar",
        "communicable_diseases_by_gender_nationality_ar",
        "communicable_diseases_5_year_trend_ar",
    ]:
        frame = tables.get(table_name, pd.DataFrame())
        if frame.empty or "disease_name_ar" not in frame.columns:
            continue
        values = frame["disease_name_ar"].dropna().astype(str).str.strip()
        disease_names.update({value for value in values if value and not value.startswith(".") and "تشمل الحالات" not in value})
    return sorted(disease_names)


@lru_cache(maxsize=1)
def load_disease_curated_tables() -> dict:
    tables: dict[str, pd.DataFrame] = {}
    for key, filename in DISEASE_FILES.items():
        path = DISEASE_DIR / filename
        tables[key] = pd.read_csv(path) if path.is_file() else pd.DataFrame()
        tables[key] = _normalize_table_columns(tables[key])

    support = {key: _normalize_table_columns(_read_first_existing_csv(paths)) for key, paths in SUPPORT_FILES.items()}

    for table_name in [
        "communicable_diseases_by_region_ar",
        "communicable_diseases_by_month_ar",
        "communicable_diseases_by_age_ar",
        "communicable_diseases_by_gender_nationality_ar",
        "communicable_diseases_5_year_trend_ar",
        "tuberculosis_ar",
        "malaria_ar",
        "bilharzia_ar",
        "leishmaniasis_ar",
        "foodborne_outbreaks_ar",
        "intoxication_ar",
        "environmental_health_diseases_ar",
        "immunization_gap_ar",
    ]:
        numeric_columns = [column for column in tables[table_name].columns if column not in {"disease_name_ar", "health_region_ar", "month_ar", "age_group_ar", "gender_ar", "nationality_ar", "source_sheet", "tb_type_ar", "parasite_type_ar", "leishmaniasis_type_ar", "source_type_ar"}]
        tables[table_name] = _ensure_numeric(tables[table_name], numeric_columns)

    support["official_region_summary"] = _ensure_numeric(
        support["official_region_summary"],
        [
            "population_total",
            "hospitals_total",
            "beds_total",
            "hospitals_per_100k",
            "beds_per_1000",
            "avg_waiting_time_minutes",
        ],
    )
    support["workforce_regional"] = _ensure_numeric(
        support["workforce_regional"],
        [
            "physicians_total_all_sectors",
            "nurses_and_midwives_total_all_sectors",
            "pharmacists_total_all_sectors",
        ],
    )

    return {"tables": tables, "support": support}


def normalize_arabic_disease_names(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    normalized = frame.copy()
    for column in ["disease_name_ar", "tb_type_ar", "leishmaniasis_type_ar"]:
        if column in normalized.columns:
            normalized[column] = normalized[column].astype(str).str.replace("*", "", regex=False).str.strip()
    return normalized


def _apply_filter(frame: pd.DataFrame, column: str, selected_value: str | None) -> pd.DataFrame:
    if frame.empty or column not in frame.columns or not selected_value or selected_value == "الكل":
        return frame
    return frame[frame[column].astype(str) == str(selected_value)].copy()


def _filtered_tables(bundle: dict, filters: dict[str, str | None]) -> dict[str, pd.DataFrame]:
    tables = {name: normalize_arabic_disease_names(frame) for name, frame in bundle["tables"].items()}
    disease_name = filters.get("disease_name_ar")
    health_region = filters.get("health_region_ar")
    month_ar = filters.get("month_ar")
    age_group = filters.get("age_group_ar")
    gender = filters.get("gender_ar")
    nationality = filters.get("nationality_ar")

    tables["communicable_diseases_by_region_ar"] = _apply_filter(tables["communicable_diseases_by_region_ar"], "disease_name_ar", disease_name)
    tables["communicable_diseases_by_region_ar"] = _apply_filter(tables["communicable_diseases_by_region_ar"], "health_region_ar", health_region)

    tables["communicable_diseases_by_month_ar"] = _apply_filter(tables["communicable_diseases_by_month_ar"], "disease_name_ar", disease_name)
    tables["communicable_diseases_by_month_ar"] = _apply_filter(tables["communicable_diseases_by_month_ar"], "month_ar", month_ar)

    tables["communicable_diseases_by_age_ar"] = _apply_filter(tables["communicable_diseases_by_age_ar"], "disease_name_ar", disease_name)
    tables["communicable_diseases_by_age_ar"] = _apply_filter(tables["communicable_diseases_by_age_ar"], "age_group_ar", age_group)

    tables["communicable_diseases_by_gender_nationality_ar"] = _apply_filter(tables["communicable_diseases_by_gender_nationality_ar"], "disease_name_ar", disease_name)
    tables["communicable_diseases_by_gender_nationality_ar"] = _apply_filter(tables["communicable_diseases_by_gender_nationality_ar"], "gender_ar", gender)
    tables["communicable_diseases_by_gender_nationality_ar"] = _apply_filter(tables["communicable_diseases_by_gender_nationality_ar"], "nationality_ar", nationality)

    tables["communicable_diseases_5_year_trend_ar"] = _apply_filter(tables["communicable_diseases_5_year_trend_ar"], "disease_name_ar", disease_name)
    tables["tuberculosis_ar"] = _apply_filter(tables["tuberculosis_ar"], "health_region_ar", health_region)
    tables["malaria_ar"] = _apply_filter(tables["malaria_ar"], "health_region_ar", health_region)
    tables["foodborne_outbreaks_ar"] = _apply_filter(tables["foodborne_outbreaks_ar"], "health_region_ar", health_region)
    tables["intoxication_ar"] = _apply_filter(tables["intoxication_ar"], "health_region_ar", health_region)
    return tables


def _region_population_frame(bundle: dict) -> pd.DataFrame:
    region_summary = bundle["support"].get("official_region_summary", pd.DataFrame()).copy()
    if region_summary.empty:
        return pd.DataFrame(columns=["health_region_ar", "population_total", "hospitals_total", "beds_total", "hospitals_per_100k", "beds_per_1000", "avg_waiting_time_minutes"])

    source_column = "province_name_ar" if "province_name_ar" in region_summary.columns else "region_name_ar"
    frame = region_summary[
        [source_column, "population_total", "hospitals_total", "beds_total", "hospitals_per_100k", "beds_per_1000", "avg_waiting_time_minutes"]
    ].copy()
    frame = frame.rename(columns={source_column: "health_region_ar"})
    saudi = {
        "health_region_ar": "السعودية",
        "population_total": frame["population_total"].sum(),
        "hospitals_total": frame["hospitals_total"].sum(),
        "beds_total": frame["beds_total"].sum(),
        "hospitals_per_100k": np.average(frame["hospitals_per_100k"].fillna(0), weights=frame["population_total"].fillna(0)),
        "beds_per_1000": np.average(frame["beds_per_1000"].fillna(0), weights=frame["population_total"].fillna(0)),
        "avg_waiting_time_minutes": np.average(frame["avg_waiting_time_minutes"].fillna(0), weights=frame["population_total"].fillna(0)),
    }
    return pd.concat([pd.DataFrame([saudi]), frame], ignore_index=True)


def _workforce_frame(bundle: dict) -> pd.DataFrame:
    workforce = bundle["support"].get("workforce_regional", pd.DataFrame()).copy()
    if workforce.empty:
        return pd.DataFrame(columns=["health_region_ar", "doctors_total", "nurses_total"])

    frame = workforce.rename(
        columns={
            "region_name_ar": "health_region_ar",
            "physicians_total_all_sectors": "doctors_total",
            "nurses_and_midwives_total_all_sectors": "nurses_total",
        }
    )[["health_region_ar", "doctors_total", "nurses_total"]].copy()
    saudi = {
        "health_region_ar": "السعودية",
        "doctors_total": frame["doctors_total"].sum(),
        "nurses_total": frame["nurses_total"].sum(),
    }
    return pd.concat([pd.DataFrame([saudi]), frame], ignore_index=True)


def calculate_cases_per_100k(cases: float | int | None, population: float | int | None) -> float | None:
    if cases is None or population in (None, 0) or pd.isna(cases) or pd.isna(population):
        return None
    return float(cases) / float(population) * 100000


def _safe_normalize(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.dropna().empty:
        return pd.Series([0.0] * len(series), index=series.index)
    min_value = numeric.min()
    max_value = numeric.max()
    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        return pd.Series([50.0] * len(series), index=series.index)
    return ((numeric - min_value) / (max_value - min_value) * 100).fillna(0)


def calculate_intervention_priority_score(region_frame: pd.DataFrame) -> pd.DataFrame:
    if region_frame.empty:
        return region_frame
    frame = region_frame.copy()
    frame["cases_norm"] = _safe_normalize(frame["cases_per_100k"])
    frame["waiting_norm"] = _safe_normalize(frame["avg_waiting_time_minutes"])
    frame["hospitals_inverse_norm"] = 100 - _safe_normalize(frame["hospitals_per_100k"])
    frame["beds_inverse_norm"] = 100 - _safe_normalize(frame["beds_per_1000"])
    frame["doctors_inverse_norm"] = 100 - _safe_normalize(frame["doctors_per_100k"])
    frame["disease_capacity_risk"] = (
        0.40 * frame["cases_norm"]
        + 0.20 * frame["waiting_norm"]
        + 0.15 * frame["hospitals_inverse_norm"]
        + 0.15 * frame["beds_inverse_norm"]
        + 0.10 * frame["doctors_inverse_norm"]
    ).round(1)
    frame["priority_level_ar"] = frame["disease_capacity_risk"].apply(classify_risk_level)
    return frame


def _build_region_burden_frame(bundle: dict, disease_name_ar: str | None = None) -> pd.DataFrame:
    region_table = bundle["tables"].get("communicable_diseases_by_region_ar", pd.DataFrame()).copy()
    if region_table.empty:
        return pd.DataFrame()
    if disease_name_ar and disease_name_ar != "الكل":
        region_table = _apply_filter(region_table, "disease_name_ar", disease_name_ar)
    burden = region_table.groupby("health_region_ar", as_index=False)["cases"].sum()
    merged = burden.merge(_region_population_frame(bundle), on="health_region_ar", how="left").merge(_workforce_frame(bundle), on="health_region_ar", how="left")
    merged["cases_per_100k"] = merged.apply(lambda row: calculate_cases_per_100k(row["cases"], row["population_total"]), axis=1)
    merged["doctors_per_100k"] = merged.apply(lambda row: calculate_cases_per_100k(row["doctors_total"], row["population_total"]), axis=1)
    merged["cases_per_doctor"] = merged["cases"] / merged["doctors_total"].replace({0: np.nan})
    merged["cases_per_nurse"] = merged["cases"] / merged["nurses_total"].replace({0: np.nan})
    merged["cases_per_hospital"] = merged["cases"] / merged["hospitals_total"].replace({0: np.nan})
    merged = calculate_intervention_priority_score(merged)
    merged["health_region_ar"] = pd.Categorical(merged["health_region_ar"], categories=REGION_ORDER, ordered=True)
    return merged.sort_values(["health_region_ar", "cases"], ascending=[True, False]).reset_index(drop=True)


def _pick_total_cases(bundle: dict, disease_name_ar: str | None = None) -> float | None:
    region_frame = bundle["tables"].get("communicable_diseases_by_region_ar", pd.DataFrame())
    month_frame = bundle["tables"].get("communicable_diseases_by_month_ar", pd.DataFrame())
    age_frame = bundle["tables"].get("communicable_diseases_by_age_ar", pd.DataFrame())
    trend_frame = bundle["tables"].get("communicable_diseases_5_year_trend_ar", pd.DataFrame())

    for frame in [region_frame, month_frame, age_frame]:
        if frame.empty:
            continue
        if disease_name_ar and disease_name_ar != "الكل":
            frame = _apply_filter(frame, "disease_name_ar", disease_name_ar)
        total = pd.to_numeric(frame.get("cases"), errors="coerce").sum()
        if total > 0:
            return float(total)

    if not trend_frame.empty:
        if disease_name_ar and disease_name_ar != "الكل":
            trend_frame = _apply_filter(trend_frame, "disease_name_ar", disease_name_ar)
        trend_frame = trend_frame.sort_values("year")
        if not trend_frame.empty:
            return float(pd.to_numeric(trend_frame.iloc[-1].get("cases"), errors="coerce"))
    return None


def _choose_focus_disease(bundle: dict, filters: dict[str, str | None]) -> str | None:
    disease_name = filters.get("disease_name_ar")
    if disease_name and disease_name != "الكل":
        return disease_name
    region_frame = bundle["tables"].get("communicable_diseases_by_region_ar", pd.DataFrame())
    if region_frame.empty:
        return None
    summary = region_frame.groupby("disease_name_ar", as_index=False)["cases"].sum().sort_values("cases", ascending=False)
    return None if summary.empty else str(summary.iloc[0]["disease_name_ar"])


def build_disease_filter_options(bundle: dict) -> dict[str, list[str]]:
    tables = bundle["tables"]
    options = {
        "diseases": _available_disease_names(tables),
        "regions": sorted(set(tables["communicable_diseases_by_region_ar"].get("health_region_ar", pd.Series(dtype="object")).dropna().astype(str)), key=lambda value: REGION_ORDER.index(value) if value in REGION_ORDER else 999),
        "months": sorted(set(tables["communicable_diseases_by_month_ar"].get("month_ar", pd.Series(dtype="object")).dropna().astype(str)), key=lambda value: MONTH_TO_NUM.get(value, 99)),
        "ages": sorted(set(tables["communicable_diseases_by_age_ar"].get("age_group_ar", pd.Series(dtype="object")).dropna().astype(str))),
        "genders": sorted(set(tables["communicable_diseases_by_gender_nationality_ar"].get("gender_ar", pd.Series(dtype="object")).dropna().astype(str))),
        "nationalities": sorted(set(tables["communicable_diseases_by_gender_nationality_ar"].get("nationality_ar", pd.Series(dtype="object")).dropna().astype(str))),
    }
    return options


def build_disease_kpis(bundle: dict, filters: dict[str, str | None]) -> list[dict[str, str]]:
    tables = _filtered_tables(bundle, filters)
    focus_disease = _choose_focus_disease({"tables": tables, "support": bundle["support"]}, filters)
    region_burden = _build_region_burden_frame(bundle, focus_disease)
    filtered_burden = region_burden.copy()
    if filters.get("health_region_ar") and filters["health_region_ar"] != "الكل":
        filtered_burden = filtered_burden[filtered_burden["health_region_ar"].astype(str) == filters["health_region_ar"]]

    total_cases = _pick_total_cases({"tables": tables, "support": bundle["support"]}, focus_disease)
    disease_count = len(_available_disease_names(tables))

    region_table = tables.get("communicable_diseases_by_region_ar", pd.DataFrame())
    top_disease = "غير متاح"
    if not region_table.empty:
        summary = region_table.groupby("disease_name_ar", as_index=False)["cases"].sum().sort_values("cases", ascending=False)
        if not summary.empty:
            top_disease = str(summary.iloc[0]["disease_name_ar"])

    top_region = "غير متاح"
    if not filtered_burden.empty:
        top_region = str(filtered_burden.sort_values("cases", ascending=False).iloc[0]["health_region_ar"])

    age_table = tables.get("communicable_diseases_by_age_ar", pd.DataFrame())
    top_age = "غير متاح"
    if not age_table.empty:
        summary = age_table.groupby("age_group_ar", as_index=False)["cases"].sum().sort_values("cases", ascending=False)
        if not summary.empty:
            top_age = str(summary.iloc[0]["age_group_ar"])

    month_table = tables.get("communicable_diseases_by_month_ar", pd.DataFrame())
    top_month = "غير متاح"
    if not month_table.empty:
        summary = month_table.groupby(["month_ar", "month_number"], as_index=False)["cases"].sum().sort_values(["cases", "month_number"], ascending=[False, True])
        if not summary.empty:
            top_month = str(summary.iloc[0]["month_ar"])

    cases_per_100k = None
    priority_label = "غير متاح"
    if not filtered_burden.empty:
        focus_row = filtered_burden.sort_values("cases", ascending=False).iloc[0]
        cases_per_100k = focus_row.get("cases_per_100k")
        priority_label = str(focus_row.get("priority_level_ar", "غير متاح"))

    return [
        {"label": "إجمالي الحالات المبلغة", "value": f"{int(total_cases):,}" if total_cases is not None else "غير متاح", "hint": "أعلى مصدر متاح للحالات بعد تطبيق المرشحات"},
        {"label": "عدد الأمراض المرصودة", "value": f"{disease_count:,}", "hint": "عدد الأمراض المتاحة في طبقة الاستخراج الحالية"},
        {"label": "أعلى مرض من حيث الحالات", "value": top_disease, "hint": "استنادًا إلى جداول الحالات الموزعة حسب المنطقة"},
        {"label": "أعلى منطقة صحية", "value": top_region, "hint": "المنطقة ذات العبء الأعلى ضمن المرشح الحالي"},
        {"label": "أعلى فئة عمرية تأثرًا", "value": top_age, "hint": "استنادًا إلى الجدول العمري الوطني المتاح"},
        {"label": "أعلى شهر من حيث الحالات", "value": top_month, "hint": "استنادًا إلى السلسلة الشهرية الوطنية المتاحة"},
        {"label": "معدل الحالات لكل 100 ألف", "value": f"{cases_per_100k:.1f}" if cases_per_100k is not None and not pd.isna(cases_per_100k) else "غير متاح", "hint": "يُحسب عند توفر عبء الحالات والسكان للمنطقة المختارة"},
        {"label": "مستوى أولوية التدخل", "value": priority_label, "hint": "مشتق من عبء المرض والطاقة الصحية ووقت الانتظار"},
    ]


def build_top_diseases_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["communicable_diseases_by_region_ar"]
    if frame.empty:
        return build_empty_figure("لا توجد بيانات كافية لبناء ترتيب الأمراض.")
    summary = frame.groupby("disease_name_ar", as_index=False)["cases"].sum().sort_values("cases", ascending=False).head(10)
    fig = px.bar(
        summary.sort_values("cases", ascending=True),
        x="cases",
        y="disease_name_ar",
        orientation="h",
        text_auto=True,
        color="cases",
        color_continuous_scale=[COLORS["accent_cyan"], COLORS["accent_teal"]],
        labels={"cases": "عدد الحالات", "disease_name_ar": "المرض"},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(hovertemplate="المرض: %{y}<br>الحالات: %{x:,.0f}<extra></extra>")
    fig = apply_dashboard_theme(fig)
    return apply_horizontal_bar_layout(fig, left_margin=210)


def build_disease_region_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["communicable_diseases_by_region_ar"]
    if frame.empty:
        return build_empty_figure("لا توجد بيانات كافية لعرض الحالات حسب المنطقة الصحية.")
    summary = frame.groupby("health_region_ar", as_index=False)["cases"].sum().sort_values("cases", ascending=True)
    fig = px.bar(
        summary,
        x="cases",
        y="health_region_ar",
        orientation="h",
        text_auto=True,
        color="cases",
        color_continuous_scale=[COLORS["warning"], COLORS["danger"]],
        labels={"cases": "عدد الحالات", "health_region_ar": "المنطقة الصحية"},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(hovertemplate="المنطقة: %{y}<br>الحالات: %{x:,.0f}<extra></extra>")
    fig = apply_dashboard_theme(fig)
    return apply_horizontal_bar_layout(fig, left_margin=170)


def build_disease_region_heatmap(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["communicable_diseases_by_region_ar"]
    if frame.empty:
        return build_empty_figure("لا توجد بيانات كافية لبناء الخريطة الحرارية للأمراض والمناطق.")
    disease_order = (
        frame.groupby("disease_name_ar", as_index=False)["cases"].sum().sort_values("cases", ascending=False).head(12)["disease_name_ar"].tolist()
    )
    pivot = (
        frame[frame["disease_name_ar"].isin(disease_order)]
        .pivot_table(index="health_region_ar", columns="disease_name_ar", values="cases", aggfunc="sum", fill_value=0)
    )
    if pivot.empty:
        return build_empty_figure("لا توجد بيانات كافية لبناء الخريطة الحرارية للأمراض والمناطق.")
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[[0.0, "#DFF7F3"], [0.55, COLORS["warning"]], [1.0, COLORS["danger"]]],
            hovertemplate="المنطقة: %{y}<br>المرض: %{x}<br>الحالات: %{z:,.0f}<extra></extra>",
        )
    )
    fig.update_xaxes(title="المرض", tickangle=-25)
    fig.update_yaxes(title="المنطقة الصحية")
    return apply_dashboard_theme(fig)


def build_disease_month_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["communicable_diseases_by_month_ar"]
    if frame.empty:
        return build_empty_figure("لا تتوفر سلسلة شهرية صالحة ضمن المرشح الحالي.")
    summary = frame.groupby(["month_ar", "month_number"], as_index=False)["cases"].sum().sort_values("month_number")
    fig = px.line(
        summary,
        x="month_ar",
        y="cases",
        markers=True,
        labels={"month_ar": "الشهر", "cases": "عدد الحالات"},
    )
    fig.update_traces(
        line={"color": COLORS["accent_teal"], "width": 4},
        marker={"size": 8, "color": COLORS["accent_cyan"]},
        hovertemplate="الشهر: %{x}<br>الحالات: %{y:,.0f}<extra></extra>",
    )
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_disease_age_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["communicable_diseases_by_age_ar"]
    if frame.empty:
        return build_empty_figure("لا تتوفر بيانات عمرية صالحة ضمن المرشح الحالي.")
    summary = frame.groupby("age_group_ar", as_index=False)["cases"].sum()
    fig = px.bar(
        summary,
        x="age_group_ar",
        y="cases",
        text_auto=True,
        color="cases",
        color_continuous_scale=[COLORS["accent_cyan"], COLORS["accent_teal"]],
        labels={"age_group_ar": "الفئة العمرية", "cases": "عدد الحالات"},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(hovertemplate="الفئة العمرية: %{x}<br>الحالات: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_disease_gender_nationality_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["communicable_diseases_by_gender_nationality_ar"]
    if frame.empty:
        return build_empty_figure("لا تتوفر بيانات الجنس والجنسية ضمن المرشح الحالي.")
    summary = frame.groupby(["nationality_ar", "gender_ar"], as_index=False)["cases"].sum()
    summary["category_ar"] = summary["nationality_ar"] + " - " + summary["gender_ar"]
    fig = px.bar(
        summary,
        x="category_ar",
        y="cases",
        text_auto=True,
        color="nationality_ar",
        color_discrete_sequence=[COLORS["accent_teal"], COLORS["warning"]],
        labels={"category_ar": "الجنسية والجنس", "cases": "عدد الحالات", "nationality_ar": "الجنسية"},
    )
    fig.update_traces(hovertemplate="التصنيف: %{x}<br>الحالات: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_tb_comparison_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["tuberculosis_ar"]
    if frame.empty:
        return build_empty_figure("لا تتوفر بيانات الدرن ضمن النسخة الحالية.")
    summary = frame.groupby(["health_region_ar", "tb_type_ar"], as_index=False)["cases"].sum()
    if filters.get("health_region_ar") in {None, "", "الكل"}:
        top_regions = summary.groupby("health_region_ar", as_index=False)["cases"].sum().sort_values("cases", ascending=False).head(8)["health_region_ar"]
        summary = summary[summary["health_region_ar"].isin(top_regions)]
    fig = px.bar(
        summary,
        x="health_region_ar",
        y="cases",
        color="tb_type_ar",
        barmode="group",
        text_auto=True,
        color_discrete_sequence=[COLORS["danger"], COLORS["warning"]],
        labels={"health_region_ar": "المنطقة الصحية", "cases": "عدد الحالات", "tb_type_ar": "نوع الدرن"},
    )
    fig.update_traces(hovertemplate="المنطقة: %{x}<br>%{fullData.name}: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_malaria_parasite_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["malaria_ar"]
    frame = frame[
        frame["parasite_type_ar"].notna()
        & frame["parasite_type_ar"].astype(str).str.strip().ne("")
        & frame["month_ar"].astype(str).str.strip().eq("")
    ].copy()
    if frame.empty:
        return build_empty_figure("لا تتوفر بيانات كافية لعرض الملاريا حسب نوع الطفيل.")
    summary = frame.groupby("parasite_type_ar", as_index=False)["cases"].sum().sort_values("cases", ascending=False)
    fig = px.bar(
        summary,
        x="parasite_type_ar",
        y="cases",
        text_auto=True,
        color="cases",
        color_continuous_scale=[COLORS["warning"], COLORS["danger"]],
        labels={"parasite_type_ar": "نوع الطفيل أو التصنيف", "cases": "عدد الحالات"},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(hovertemplate="الفئة: %{x}<br>الحالات: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_malaria_month_region_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["malaria_ar"]
    frame = frame[frame["month_ar"].astype(str).str.strip().ne("")].copy()
    if frame.empty:
        return build_empty_figure("لا تتوفر بيانات شهرية ومكانية كافية للملاريا.")
    summary = (
        frame.groupby(["health_region_ar", "month_ar", "month_number"], as_index=False)["cases"]
        .sum()
        .sort_values(["health_region_ar", "month_number"])
    )
    pivot = summary.pivot_table(index="health_region_ar", columns="month_ar", values="cases", aggfunc="sum", fill_value=0)
    month_order = [month for month in MONTH_AR_ORDER if month in pivot.columns]
    pivot = pivot.reindex(columns=month_order)
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[[0.0, "#E8FFFB"], [0.55, COLORS["warning"]], [1.0, COLORS["danger"]]],
            hovertemplate="المنطقة: %{y}<br>الشهر: %{x}<br>الحالات: %{z:,.0f}<extra></extra>",
        )
    )
    fig.update_xaxes(title="الشهر")
    fig.update_yaxes(title="المنطقة الصحية")
    return apply_dashboard_theme(fig)


def build_foodborne_outbreak_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["foodborne_outbreaks_ar"]
    if frame.empty:
        return build_empty_figure("لا تتوفر بيانات صالحة لفاشيات الأمراض المنقولة بالغذاء.")
    summary = frame[frame["source_type_ar"].isin(["مصدر عام", "منزلي"])].groupby(["health_region_ar", "source_type_ar"], as_index=False)[["cases", "outbreak_count"]].sum()
    fig = px.bar(
        summary,
        x="health_region_ar",
        y="cases",
        color="source_type_ar",
        barmode="group",
        text_auto=True,
        color_discrete_sequence=[COLORS["accent_teal"], COLORS["warning"]],
        labels={"health_region_ar": "المنطقة الصحية", "cases": "عدد الحالات", "source_type_ar": "مصدر الفاشية"},
    )
    fig.update_traces(hovertemplate="المنطقة: %{x}<br>%{fullData.name}: %{y:,.0f} حالة<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_intoxication_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["intoxication_ar"]
    if frame.empty:
        return build_empty_figure("لا تتوفر بيانات التسمم الكيميائي والدوائي ضمن النسخة الحالية.")
    long_frame = pd.DataFrame(
        [
            {"health_region_ar": row["health_region_ar"], "category_ar": "تسمم دوائي", "cases": row["drug_intoxication_cases"]}
            for _, row in frame.iterrows()
        ]
        + [
            {"health_region_ar": row["health_region_ar"], "category_ar": "تسمم كيميائي", "cases": row["chemical_intoxication_cases"]}
            for _, row in frame.iterrows()
        ]
        + [
            {"health_region_ar": row["health_region_ar"], "category_ar": "غير محدد", "cases": row["unknown_intoxication_cases"]}
            for _, row in frame.iterrows()
        ]
    )
    fig = px.bar(
        long_frame,
        x="health_region_ar",
        y="cases",
        color="category_ar",
        barmode="stack",
        text_auto=True,
        color_discrete_sequence=[COLORS["danger"], COLORS["warning"], COLORS["accent_cyan"]],
        labels={"health_region_ar": "المنطقة الصحية", "cases": "عدد الحالات", "category_ar": "نوع التسمم"},
    )
    fig.update_traces(hovertemplate="المنطقة: %{x}<br>%{fullData.name}: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_disease_trend_chart(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    frame = _filtered_tables(bundle, filters)["communicable_diseases_5_year_trend_ar"]
    if frame.empty:
        return build_empty_figure("لا يتوفر اتجاه زمني لخمس سنوات ضمن المرشح الحالي.")
    focus_disease = _choose_focus_disease({"tables": _filtered_tables(bundle, filters), "support": bundle["support"]}, filters)
    if focus_disease:
        frame = frame[frame["disease_name_ar"].astype(str) == focus_disease]
    summary = frame.groupby(["year", "disease_name_ar"], as_index=False)["cases"].sum(min_count=1)
    fig = px.line(
        summary,
        x="year",
        y="cases",
        color="disease_name_ar",
        markers=True,
        labels={"year": "السنة", "cases": "عدد الحالات", "disease_name_ar": "المرض"},
        color_discrete_sequence=[COLORS["accent_teal"], COLORS["danger"], COLORS["warning"], COLORS["accent_cyan"]],
    )
    fig.update_traces(hovertemplate="%{fullData.name}<br>%{x}: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return apply_dashboard_theme(fig)


def build_disease_region_map(bundle: dict, filters: dict[str, str | None]) -> go.Figure:
    region_burden = _build_region_burden_frame(bundle, _choose_focus_disease(bundle, filters))
    if filters.get("health_region_ar") and filters["health_region_ar"] != "الكل":
        region_burden = region_burden[region_burden["health_region_ar"].astype(str) == filters["health_region_ar"]]
    region_summary = bundle["support"].get("official_region_summary", pd.DataFrame()).copy()
    if region_burden.empty or region_summary.empty:
        return build_empty_figure("لا تتوفر إحداثيات كافية لبناء خريطة عبء المرض.")
    map_frame = region_burden.merge(region_summary[["province_name_ar", "latitude", "longitude"]], left_on="health_region_ar", right_on="province_name_ar", how="left")
    map_frame = map_frame.dropna(subset=["latitude", "longitude"])
    if map_frame.empty:
        return build_empty_figure("لا تتوفر إحداثيات كافية لبناء خريطة عبء المرض.")
    fig = px.scatter_mapbox(
        map_frame,
        lat="latitude",
        lon="longitude",
        color="priority_level_ar",
        size="cases",
        size_max=30,
        zoom=4.3,
        center={"lat": 23.8, "lon": 45.0},
        color_discrete_map={"منخفض": COLORS["success"], "متوسط": COLORS["warning"], "مرتفع": COLORS["danger"]},
        custom_data=["health_region_ar", "cases", "cases_per_100k", "priority_level_ar"],
        opacity=0.92,
    )
    fig.update_traces(
        hovertemplate="المنطقة: %{customdata[0]}<br>الحالات: %{customdata[1]:,.0f}<br>المعدل لكل 100 ألف: %{customdata[2]:.1f}<br>مستوى الأولوية: %{customdata[3]}<extra></extra>"
    )
    fig.update_layout(mapbox_style="carto-positron", legend_title_text="الأولوية")
    return apply_dashboard_theme(fig)


def build_disease_drilldown_summary(bundle: dict, filters: dict[str, str | None]) -> dict[str, object]:
    focus_disease = _choose_focus_disease(bundle, filters)
    if not focus_disease:
        return {"disease_name_ar": None, "summary_rows": [], "interpretation_ar": "لا توجد بيانات كافية لبناء الشرح التنفيذي.", "recommendations_ar": []}

    region_frame = bundle["tables"].get("communicable_diseases_by_region_ar", pd.DataFrame())
    month_frame = bundle["tables"].get("communicable_diseases_by_month_ar", pd.DataFrame())
    age_frame = bundle["tables"].get("communicable_diseases_by_age_ar", pd.DataFrame())
    gender_frame = bundle["tables"].get("communicable_diseases_by_gender_nationality_ar", pd.DataFrame())
    trend_frame = bundle["tables"].get("communicable_diseases_5_year_trend_ar", pd.DataFrame())

    region_frame = _apply_filter(region_frame, "disease_name_ar", focus_disease)
    month_frame = _apply_filter(month_frame, "disease_name_ar", focus_disease)
    age_frame = _apply_filter(age_frame, "disease_name_ar", focus_disease)
    gender_frame = _apply_filter(gender_frame, "disease_name_ar", focus_disease)
    trend_frame = _apply_filter(trend_frame, "disease_name_ar", focus_disease)

    total_cases = _pick_total_cases(bundle, focus_disease)
    top_region = "غير متاح"
    top_month = "غير متاح"
    top_age = "غير متاح"
    distribution_text = "غير متاح"

    if not region_frame.empty:
        top_region = str(region_frame.groupby("health_region_ar", as_index=False)["cases"].sum().sort_values("cases", ascending=False).iloc[0]["health_region_ar"])
    if not month_frame.empty:
        top_month = str(month_frame.groupby(["month_ar", "month_number"], as_index=False)["cases"].sum().sort_values(["cases", "month_number"], ascending=[False, True]).iloc[0]["month_ar"])
    if not age_frame.empty:
        top_age = str(age_frame.groupby("age_group_ar", as_index=False)["cases"].sum().sort_values("cases", ascending=False).iloc[0]["age_group_ar"])
    if not gender_frame.empty:
        distribution = gender_frame.groupby(["nationality_ar", "gender_ar"], as_index=False)["cases"].sum().sort_values("cases", ascending=False)
        top_two = distribution.head(2)
        distribution_text = " | ".join([f"{row['nationality_ar']} - {row['gender_ar']}: {int(row['cases']):,}" for _, row in top_two.iterrows()])

    burden = _build_region_burden_frame(bundle, focus_disease)
    burden = burden.sort_values("disease_capacity_risk", ascending=False)
    focus_row = burden.iloc[0] if not burden.empty else None
    interpretation = f"يظهر مرض {focus_disease} بعبء أوضح في {top_region}، بينما يتركز النشاط الزمني في {top_month}، وتبرز الفئة {top_age} كأكثر الفئات تأثرًا ضمن الجداول المتاحة."
    if focus_row is not None:
        interpretation += f" كما أن أعلى ضغط تشغيلي نسبي مرتبط به يظهر في {focus_row['health_region_ar']} بمؤشر {focus_row['disease_capacity_risk']:.1f} من 100."

    return {
        "disease_name_ar": focus_disease,
        "summary_rows": [
            {"label": "إجمالي الحالات", "value": f"{int(total_cases):,}" if total_cases is not None else "غير متاح", "tone": "neutral"},
            {"label": "أعلى منطقة", "value": top_region, "tone": "warning"},
            {"label": "أعلى شهر", "value": top_month, "tone": "warning"},
            {"label": "أعلى فئة عمرية", "value": top_age, "tone": "warning"},
            {"label": "توزيع الجنس والجنسية", "value": distribution_text, "tone": "neutral"},
            {"label": "اتجاه زمني", "value": "متاح" if not trend_frame.empty else "غير متاح", "tone": "success" if not trend_frame.empty else "warning"},
        ],
        "interpretation_ar": interpretation,
        "recommendations_ar": build_disease_recommendations_ar(focus_disease, top_region, str(focus_row["priority_level_ar"]) if focus_row is not None else "غير متاح"),
    }


def build_disease_recommendations_ar(disease_name_ar: str | None, health_region_ar: str | None, priority_level_ar: str | None) -> list[str]:
    if not disease_name_ar:
        return ["لا تتوفر توصيات تشغيلية لأن المرض لم يُحدد بعد."]
    recommendations = [
        f"تعزيز الرصد الوبائي والتبليغ المبكر لمرض {disease_name_ar} داخل {health_region_ar or 'المنطقة ذات الأولوية'}.",
        "مراجعة جاهزية المختبرات ومسارات الإحالة والفرز لضمان سرعة اكتشاف الحالات والاستجابة لها.",
    ]
    if any(keyword in disease_name_ar for keyword in ["ملاريا", "ضنك", "ليشمانيا", "بلهارسيا"]):
        recommendations.append("تكثيف أعمال مكافحة النواقل والرش البيئي وتتبع البؤر المكانية الموسمية.")
    if any(keyword in disease_name_ar for keyword in ["حصبة", "نكاف", "جديري", "دفتيريا", "سعال", "شلل", "كزاز"]):
        recommendations.append("مراجعة تغطية التحصين والفئات المتأخرة واستهداف المناطق أو الفئات الأقل تغطية بحملات وقائية.")
    if any(keyword in disease_name_ar for keyword in ["كوليرا", "سالمونيلا", "تيفوئيد", "زحار", "فاشيات"]):
        recommendations.append("تشديد الرقابة على المياه وسلامة الغذاء ورفع وتيرة التفتيش في المواقع الأعلى تعرضًا.")
    if "درن" in disease_name_ar:
        recommendations.append("توسيع تتبع المخالطين واستكمال مسارات الفحص والعلاج والمتابعة العلاجية المنتظمة.")
    if "التهاب الكبد" in disease_name_ar:
        recommendations.append("تعزيز بروتوكولات مكافحة العدوى والفحص الموجه للفئات الأكثر تعرضًا ورفع الوعي المجتمعي.")
    if priority_level_ar == "مرتفع":
        recommendations.append("يوصى برفع هذا الملف إلى أولوية تنفيذية عالية مع متابعة أسبوعية للمؤشرات والقدرة الصحية.")
    return recommendations


def build_environmental_context_cards(filtered_data: dict, province: str | None) -> list[dict[str, str]]:
    try:
        current_frame = build_environmental_current_frame(filtered_data, province)
    except Exception:
        current_frame = pd.DataFrame()

    if current_frame.empty:
        return [
            {"label": "درجة الحرارة", "value": "غير متاح", "hint": "لا تتوفر بيانات حية للنطاق الحالي"},
            {"label": "الرطوبة", "value": "غير متاح", "hint": "لا تتوفر بيانات حية للنطاق الحالي"},
            {"label": "سرعة الرياح", "value": "غير متاح", "hint": "لا تتوفر بيانات حية للنطاق الحالي"},
            {"label": "PM2.5", "value": "غير متاح", "hint": "لا تتوفر بيانات حية للنطاق الحالي"},
            {"label": "PM10", "value": "غير متاح", "hint": "لا تتوفر بيانات حية للنطاق الحالي"},
            {"label": "مؤشر جودة الهواء", "value": "غير متاح", "hint": "لا تتوفر بيانات حية للنطاق الحالي"},
            {"label": "آخر تحديث", "value": "غير متاح", "hint": "لا تتوفر بيانات حية للنطاق الحالي"},
        ]

    focus_row = current_frame.sort_values(["respiratory_risk_index", "population_total"], ascending=[False, False]).iloc[0]
    city_hint = f"المدينة المرجعية: {focus_row['city_ar']}"
    updated_value = str(pd.to_datetime(focus_row["observed_at"], errors="coerce")).replace("T", " ")[:16] if "observed_at" in focus_row else "غير متاح"
    return [
        {"label": "درجة الحرارة", "value": f"{focus_row['temperature_c']:.1f}°" if pd.notna(focus_row.get("temperature_c")) else "غير متاح", "hint": city_hint},
        {"label": "الرطوبة", "value": f"{focus_row['humidity_pct']:.0f}%" if pd.notna(focus_row.get("humidity_pct")) else "غير متاح", "hint": city_hint},
        {"label": "سرعة الرياح", "value": f"{focus_row['wind_speed_kmh']:.1f} كم/س" if pd.notna(focus_row.get("wind_speed_kmh")) else "غير متاح", "hint": city_hint},
        {"label": "PM2.5", "value": f"{focus_row['pm25']:.1f}" if pd.notna(focus_row.get("pm25")) else "غير متاح", "hint": city_hint},
        {"label": "PM10", "value": f"{focus_row['pm10']:.1f}" if pd.notna(focus_row.get("pm10")) else "غير متاح", "hint": city_hint},
        {"label": "مؤشر جودة الهواء", "value": f"{focus_row['aqi']:.0f}" if pd.notna(focus_row.get("aqi")) else "غير متاح", "hint": city_hint},
        {"label": "آخر تحديث", "value": updated_value, "hint": "تحديث حي من مزود الرصد البيئي"},
    ]


def build_focus_comparison_rows(bundle: dict, disease_name_ar: str | None) -> list[dict[str, object]]:
    burden = _build_region_burden_frame(bundle, disease_name_ar)
    if burden.empty:
        return []
    focus = burden[burden["health_region_ar"].astype(str).isin(["السعودية", "عسير", "القصيم"])]
    rows = []
    for _, row in focus.iterrows():
        rows.append(
            {
                "region_ar": str(row["health_region_ar"]),
                "population_total": f"{int(row['population_total']):,}" if pd.notna(row.get("population_total")) else "غير متاح",
                "cases": f"{int(row['cases']):,}" if pd.notna(row.get("cases")) else "غير متاح",
                "cases_per_100k": f"{row['cases_per_100k']:.1f}" if pd.notna(row.get("cases_per_100k")) else "غير متاح",
                "hospitals_total": f"{int(row['hospitals_total']):,}" if pd.notna(row.get("hospitals_total")) else "غير متاح",
                "beds_total": f"{int(row['beds_total']):,}" if pd.notna(row.get("beds_total")) else "غير متاح",
                "doctors_total": f"{int(row['doctors_total']):,}" if pd.notna(row.get("doctors_total")) else "غير متاح",
                "nurses_total": f"{int(row['nurses_total']):,}" if pd.notna(row.get("nurses_total")) else "غير متاح",
                "pressure_score": f"{row['disease_capacity_risk']:.1f} - {row['priority_level_ar']}" if pd.notna(row.get("disease_capacity_risk")) else "غير متاح",
            }
        )
    return rows


def build_disease_forecast_frame(bundle: dict, disease_name_ar: str | None) -> pd.DataFrame:
    trend = bundle["tables"].get("communicable_diseases_5_year_trend_ar", pd.DataFrame()).copy()
    if trend.empty:
        return pd.DataFrame()
    if disease_name_ar and disease_name_ar != "الكل":
        trend = trend[trend["disease_name_ar"].astype(str) == disease_name_ar]
    trend = trend.groupby(["disease_name_ar", "year"], as_index=False)["cases"].sum(min_count=1)
    if trend.empty:
        return pd.DataFrame()

    records = []
    for disease, frame in trend.groupby("disease_name_ar"):
        frame = frame.dropna(subset=["cases"]).sort_values("year")
        if len(frame) < 3:
            continue
        x = frame["year"].astype(float).to_numpy()
        y = frame["cases"].astype(float).to_numpy()
        slope, intercept = np.polyfit(x, y, 1)
        for _, row in frame.iterrows():
            records.append({"disease_name_ar": disease, "year": int(row["year"]), "actual": float(row["cases"]), "forecast": np.nan})
        last_year = int(frame["year"].max())
        rolling_mean = frame["cases"].tail(min(3, len(frame))).mean()
        for step in range(1, 4):
            next_year = last_year + step
            linear_value = intercept + slope * next_year
            forecast_value = max((0.65 * linear_value) + (0.35 * rolling_mean), 0)
            records.append({"disease_name_ar": disease, "year": next_year, "actual": np.nan, "forecast": float(forecast_value)})
    return pd.DataFrame.from_records(records)


def build_disease_forecast_figure(bundle: dict, disease_name_ar: str | None) -> go.Figure:
    frame = build_disease_forecast_frame(bundle, disease_name_ar)
    if frame.empty:
        return build_empty_figure("لا توجد سلسلة زمنية كافية لبناء توقع مرضي واضح.")
    disease = disease_name_ar if disease_name_ar and disease_name_ar != "الكل" else frame["disease_name_ar"].iloc[0]
    frame = frame[frame["disease_name_ar"].astype(str) == disease].copy()
    fig = go.Figure()
    actual = frame.dropna(subset=["actual"])
    forecast = frame.dropna(subset=["forecast"])
    fig.add_trace(go.Scatter(x=actual["year"], y=actual["actual"], mode="lines+markers", name="القيم الفعلية", line={"color": COLORS["navy_soft"], "width": 3}))
    fig.add_trace(go.Scatter(x=forecast["year"], y=forecast["forecast"], mode="lines+markers", name="التوقع", line={"color": COLORS["accent_teal"], "width": 3, "dash": "dot"}))
    fig.update_xaxes(title="السنة")
    fig.update_yaxes(title="عدد الحالات", showgrid=True, gridcolor=COLORS["grid"])
    fig.update_traces(hovertemplate="%{x}: %{y:,.0f}<extra></extra>")
    return apply_dashboard_theme(fig)


def build_malaria_seasonal_forecast_frame(bundle: dict, health_region_ar: str | None = None) -> pd.DataFrame:
    frame = bundle["tables"].get("malaria_ar", pd.DataFrame()).copy()
    frame = frame[frame["month_ar"].astype(str).str.strip().ne("")].copy()
    if health_region_ar and health_region_ar != "الكل":
        frame = frame[frame["health_region_ar"].astype(str) == health_region_ar]
    if frame.empty:
        return pd.DataFrame()
    summary = frame.groupby(["month_ar", "month_number"], as_index=False)["cases"].sum().sort_values("month_number")
    if summary.empty:
        return pd.DataFrame()
    rolling = summary["cases"].rolling(window=3, min_periods=1).mean()
    last_month = int(summary["month_number"].max())
    forecasts = []
    for step in range(1, 4):
        month_number = ((last_month + step - 1) % 12) + 1
        month_name = MONTH_AR_ORDER[month_number - 1]
        seasonal_reference = summary.loc[summary["month_number"] == month_number, "cases"]
        seasonal_value = float(seasonal_reference.mean()) if not seasonal_reference.empty else float(summary["cases"].tail(3).mean())
        forecasts.append({"month_ar": month_name, "month_number": month_number, "cases": np.nan, "forecast": seasonal_value})
    summary["forecast"] = np.nan
    return pd.concat([summary, pd.DataFrame(forecasts)], ignore_index=True)


def build_malaria_seasonal_forecast_figure(bundle: dict, health_region_ar: str | None = None) -> go.Figure:
    frame = build_malaria_seasonal_forecast_frame(bundle, health_region_ar)
    if frame.empty:
        return build_empty_figure("لا توجد سلسلة موسمية كافية للملاريا ضمن المرشح الحالي.")
    fig = go.Figure()
    actual = frame.dropna(subset=["cases"])
    forecast = frame.dropna(subset=["forecast"])
    fig.add_trace(go.Bar(x=actual["month_ar"], y=actual["cases"], name="النمط الشهري الفعلي", marker_color=COLORS["warning"]))
    fig.add_trace(go.Scatter(x=forecast["month_ar"], y=forecast["forecast"], mode="lines+markers", name="الخطر المتوقع للأشهر الثلاثة القادمة", line={"color": COLORS["danger"], "width": 3}))
    fig.update_xaxes(title="الشهر")
    fig.update_yaxes(title="عدد الحالات أو مستوى الخطر", showgrid=True, gridcolor=COLORS["grid"])
    fig.update_traces(hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>")
    return apply_dashboard_theme(fig)


def build_operational_recommendations_rows(bundle: dict, disease_name_ar: str | None, health_region_ar: str | None) -> list[dict[str, str]]:
    burden = _build_region_burden_frame(bundle, disease_name_ar)
    if health_region_ar and health_region_ar != "الكل":
        burden = burden[burden["health_region_ar"].astype(str) == health_region_ar]
    rows = []
    for _, row in burden.sort_values("disease_capacity_risk", ascending=False).head(6).iterrows():
        disease_label = disease_name_ar or "الأمراض المعدية"
        recommendation = build_disease_recommendations_ar(disease_label, str(row["health_region_ar"]), str(row["priority_level_ar"]))[0]
        rows.append(
            {
                "disease_name_ar": disease_label,
                "health_region_ar": str(row["health_region_ar"]),
                "risk_level_ar": str(row["priority_level_ar"]),
                "recommendation_ar": recommendation,
            }
        )
    return rows
