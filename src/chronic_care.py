"""Published chronic-care snapshots, independent of operational dashboard filters.

Visits are encounters at MoH hospital diabetes clinics. Capacity counts MoH
facilities. 2022/2023 health regions and 2024 health clusters are distinct source
geographies, so these records must not imply a continuous comparable trend.
National rehabilitation encounters and dialysis patients retain their own units
and are independent of regional controls.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "official_curated" / "chronic_care"
ENTITY_ORDER = ("saudi_arabia", "asir", "bisha", "qassim", "asir_cluster_total")
FACILITY_ORDER = ("cardiology", "oncology", "diabetes_endocrinology", "dialysis")
COUNT_COLUMNS = {
    "diabetes_visits": ("saudi_male", "saudi_female", "non_saudi_male", "non_saudi_female", "visits_total"),
    "chronic_care_capacity": ("value",),
    "diabetes_rehabilitation_visits": ("saudi_male", "saudi_female", "non_saudi_male", "non_saudi_female", "visits_total"),
    "dialysis_patients_2024": ("patients",),
}
EXTRA_COLUMNS = {
    "chronic_care_capacity": ("facility_type", "facility_label_ar", "source_value_cell"),
    "dialysis_patients_2024": ("treatment_key", "treatment_label_ar", "sector_key", "sector_label_ar", "aggregation_role", "source_value_cell"),
}
COMMON_COLUMNS = (
    "year", "entity_key", "entity_label_ar", "geography_type", "geography_type_ar", "row_role",
    "source_geography_ar", "source_geography_en", "source_file", "source_sheet", "source_table",
    "source_range", "source_title_ar", "source_title_en", "source_url", "comparability_note_ar",
    "geography_note_ar", "unit", "unit_ar", "service_scope", "service_scope_ar", "definition_note_ar",
)


def load_chronic_care_data() -> dict[str, pd.DataFrame]:
    """Load curated source rows as fresh frames; retain unavailable counts as NA.

    Returns ``diabetes_visits`` (2023/2024, visits_total plus sex/nationality
    counts) and ``chronic_care_capacity`` (2022/2023/2024, one value per facility
    type), ``diabetes_rehabilitation_visits`` (national, 2023/2024) and
    ``dialysis_patients_2024`` (national, by treatment and sector). Each observation carries source geography, scope, unit and workbook
    row references. A missing CSV returns a typed empty frame for that dataset.

    ``asir`` excludes Bisha. The separate ``asir_cluster_total`` is a published
    2024 subtotal, includes both rows, and must not be summed with its children.
    The national rows are official published totals, not sums of focus regions.
    """
    datasets: dict[str, pd.DataFrame] = {}
    for name, count_columns in COUNT_COLUMNS.items():
        extra_columns = EXTRA_COLUMNS.get(name, ())
        path = DATA_DIR / f"{name}.csv"
        columns = list(dict.fromkeys((*COMMON_COLUMNS, *extra_columns, *count_columns)))
        if path.is_file():
            frame = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
            missing = set(columns) - set(frame.columns)
            if missing:
                raise ValueError(f"Missing chronic-care data columns in {path.name}: {', '.join(sorted(missing))}")
        else:
            frame = pd.DataFrame(columns=columns)
        for column in ("year", *count_columns):
            frame[column] = pd.to_numeric(frame[column].replace("", pd.NA), errors="raise").astype("Int64")
        frame["_entity_order"] = frame["entity_key"].map({key: index for index, key in enumerate(ENTITY_ORDER)})
        sort_columns = ["year", "_entity_order"]
        if name == "chronic_care_capacity":
            frame["_facility_order"] = frame["facility_type"].map({key: index for index, key in enumerate(FACILITY_ORDER)})
            sort_columns.append("_facility_order")
        elif name == "dialysis_patients_2024":
            sort_columns.extend(["treatment_key", "sector_key"])
        frame = frame.sort_values(sort_columns).drop(columns=[column for column in sort_columns if column.startswith("_")])
        datasets[name] = frame.reset_index(drop=True)
    return datasets
