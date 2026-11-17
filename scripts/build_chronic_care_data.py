"""Extract published chronic-care service snapshots without altering source workbooks.

Run from any directory with ``python scripts/build_chronic_care_data.py``.
The application reads the generated CSV files; it never needs the notes workbooks.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "official_curated" / "chronic_care"
SOURCE_URL = "https://www.moh.gov.sa/Ministry/Statistics/book/Pages/default.aspx"
COMPARABILITY_NOTE = (
    "لقطات سنوية كما نشرها المصدر: مناطق صحية في 2022 و2023، وتجمعات صحية في 2024. "
    "لا يفترض تطابق الحدود الجغرافية بين السنوات."
)
VISITS_NOTE = (
    "زيارات لعيادات السكري بمستشفيات وزارة الصحة، وليست أعداد مرضى فريدين أو معدل انتشار السكري."
)
CAPACITY_NOTE = "أعداد مرافق وزارة الصحة المتخصصة، وليست أعداد المرضى أو جميع مرافق القطاعات الصحية."
REHABILITATION_NOTE = (
    "زيارات ما بعد البتر المرتبط بداء السكري لمراكز وأقسام التأهيل الطبي بوزارة الصحة على مستوى المملكة؛ "
    "وليست أعداد عمليات البتر أو المرضى الفريدين أو معدل مضاعفات السكري."
)
DIALYSIS_NOTE = "أعداد مرضى التنقية الدموية والبريتونية حسب القطاع الصحي على مستوى المملكة لعام 2024."


@dataclass(frozen=True)
class SourceSpec:
    year: int
    source_file: str
    capacity_sheet: str
    capacity_table: str
    visits_sheet: str | None = None
    visits_table: str | None = None


SOURCES = (
    SourceSpec(2022, "notes/2022-Chapter-II-Health-Resources (1).xlsx", "2-6", "2-6"),
    SourceSpec(2023, "notes/Statistical-Yearbook-2023.xlsx", "11.", "2-11", "13..", "4-13"),
    # Reuse the existing official 2024 workbook; the notes copy repeats these tables.
    SourceSpec(
        2024,
        "data/official_sources/moh_statistical_yearbook_2024.xlsx",
        "2-4",
        "2-4",
        "4-16",
        "4-16",
    ),
)
FACILITY_TYPES = (
    ("cardiology", "مراكز القلب", "D", "مركز قلب"),
    ("oncology", "مراكز الأورام", "E", "مركز أورام"),
    ("diabetes_endocrinology", "مراكز السكري والغدد الصماء", "F", "مراكز السكري والغدد الصماء"),
    ("dialysis", "مراكز ووحدات الغسيل الكلوي", "G", "مركز/وحدة غسيل كلوي"),
)
VISIT_COLUMNS = (
    ("saudi_male", "B"),
    ("saudi_female", "C"),
    ("non_saudi_male", "D"),
    ("non_saudi_female", "E"),
    ("visits_total", "F"),
)


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _count(value: object, location: str) -> int | None:
    """Retain missing inputs and real zeros, rejecting ambiguous count values."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or int(value) != value:
        raise ValueError(f"Expected a nonnegative integer or blank at {location}: {value!r}")
    return int(value)


def _row_specs(year: int) -> tuple[tuple[str, str, int, str], ...]:
    if year == 2024:
        return (
            ("saudi_arabia", "السعودية", 34, "national"),
            ("asir", "عسير", 22, "detail"),
            ("bisha", "بيشة", 23, "detail"),
            ("qassim", "القصيم", 18, "detail"),
            ("asir_cluster_total", "إجمالي تجمع عسير (عسير وبيشة)", 24, "subtotal"),
        )
    return (
        ("saudi_arabia", "السعودية", 26, "national"),
        ("asir", "عسير", 15, "detail"),
        ("bisha", "بيشة", 16, "detail"),
        ("qassim", "القصيم", 11, "detail"),
    )


def _check_table(ws: Worksheet, spec: SourceSpec, table: str, visits: bool) -> None:
    title = _text(ws["A1"].value)
    if str(spec.year) not in title or _text(ws["A3"].value) != f"جدول {table}":
        raise ValueError(f"Source title/table changed: {spec.source_file}, {ws.title}")
    if visits:
        if "زيارات" not in title or "السكرى" not in title or "مستشفيات وزارة الصحة" not in title:
            raise ValueError(f"Unexpected diabetes-visit definition in {ws.title}")
        expected = {"B4": "سعودي", "D4": "غير سعودي", "F4": "الإجمالي"}
        for cell, label in expected.items():
            if label not in _text(ws[cell].value):
                raise ValueError(f"Unexpected visit header at {ws.title}!{cell}")
        for cell, label in {"B5": "Male", "C5": "Female", "D5": "Male", "E5": "Female"}.items():
            if label not in _text(ws[cell].value):
                raise ValueError(f"Unexpected visit gender at {ws.title}!{cell}")
    else:
        if "المرافق الصحية بوزارة الصحة" not in title:
            raise ValueError(f"Unexpected facility definition in {ws.title}")
        for _, _, column, label in FACILITY_TYPES:
            if _text(ws[f"{column}4"].value) != label:
                raise ValueError(f"Unexpected facility header at {ws.title}!{column}4")
    expected_geography = "التجمع" if spec.year == 2024 else "المنطقة الصحية"
    if expected_geography not in _text(ws["A4"].value):
        raise ValueError(f"Unexpected geography definition in {ws.title}")


def _check_rows(ws: Worksheet, year: int, columns: tuple[str, ...]) -> None:
    """Reconcile disjoint source rows; never add published subtotals twice."""
    if year == 2024:
        detail_rows = (6, 7, 8, 10, 11, 13, 14, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32)
        total_row = 34
    else:
        detail_rows = tuple(range(6, 26))
        total_row = 26
    for column in columns:
        detail = [_count(ws[f"{column}{row}"].value, f"{ws.title}!{column}{row}") for row in detail_rows]
        total = _count(ws[f"{column}{total_row}"].value, f"{ws.title}!{column}{total_row}")
        if total is not None and all(value is not None for value in detail) and sum(detail) != total:
            raise ValueError(f"National total does not reconcile at {ws.title}!{column}{total_row}")
        if year == 2024:
            parts = [_count(ws[f"{column}{row}"].value, f"{ws.title}!{column}{row}") for row in (22, 23)]
            subtotal = _count(ws[f"{column}24"].value, f"{ws.title}!{column}24")
            if subtotal is not None and all(value is not None for value in parts) and sum(parts) != subtotal:
                raise ValueError(f"Asir/Bisha subtotal does not reconcile at {ws.title}!{column}24")


def _metadata(ws: Worksheet, spec: SourceSpec, table: str, row_spec: tuple, last_column: str) -> dict:
    key, label, row, role = row_spec
    source_label = _text(ws[f"A{row}"].value)
    expected_fragment = {"asir": "عسير", "bisha": "بيشة", "qassim": "القصيم"}.get(key)
    if expected_fragment and expected_fragment not in source_label:
        raise ValueError(f"Geographic row changed at {ws.title}!A{row}: {source_label}")
    if role in {"national", "subtotal"} and not any(fragment in source_label for fragment in ("جمال", "المجموع")):
        raise ValueError(f"Expected a labeled total at {ws.title}!A{row}")
    if role == "national":
        geography_type, geography_type_ar = "national", "إجمالي المملكة"
    elif role == "subtotal":
        geography_type, geography_type_ar = "health_cluster_subtotal", "إجمالي تجمع عسير (يشمل عسير وبيشة)"
    elif spec.year == 2024:
        geography_type, geography_type_ar = "health_cluster", "تجمع صحي وفق جدول 2024"
    else:
        geography_type, geography_type_ar = "health_region", "منطقة صحية وفق المصدر"
    return {
        "year": spec.year,
        "entity_key": key,
        "entity_label_ar": label,
        "geography_type": geography_type,
        "geography_type_ar": geography_type_ar,
        "row_role": role,
        "source_geography_ar": source_label,
        "source_geography_en": _text(ws[f"{'G' if last_column == 'G' else 'N'}{row}"].value),
        "source_file": spec.source_file,
        "source_sheet": ws.title,
        "source_table": table,
        "source_range": f"A{row}:{last_column}{row}",
        "source_title_ar": _text(ws["A1"].value),
        "source_title_en": _text(ws["A2"].value),
        "source_url": SOURCE_URL,
        "comparability_note_ar": COMPARABILITY_NOTE,
        "geography_note_ar": (
            "إجمالي منشور يشمل صفّي عسير وبيشة؛ لا يجمع معهما مرة أخرى."
            if role == "subtotal"
            else "صف عسير منفصل عن بيشة؛ لا يفترض أنه إجمالي المنطقة الإدارية."
            if key == "asir"
            else "النطاق الجغرافي كما ورد في الجدول الأصلي."
        ),
    }


def _national_metadata(ws: Worksheet, spec: SourceSpec, table: str, source_range: str) -> dict:
    return {
        "year": spec.year,
        "entity_key": "saudi_arabia",
        "entity_label_ar": "السعودية",
        "geography_type": "national",
        "geography_type_ar": "إجمالي المملكة",
        "row_role": "national",
        "source_geography_ar": "المملكة العربية السعودية",
        "source_geography_en": "Saudi Arabia",
        "source_file": spec.source_file,
        "source_sheet": ws.title,
        "source_table": table,
        "source_range": source_range,
        "source_title_ar": _text(ws["A1"].value),
        "source_title_en": _text(ws["A2"].value),
        "source_url": SOURCE_URL,
        "comparability_note_ar": "البيانات وطنية وفق السنة المذكورة في عنوان الجدول الأصلي.",
        "geography_note_ar": "لا يتوفر تفصيل إقليمي في هذا الجدول؛ لا تُنسب القيم إلى عسير أو بيشة أو القصيم.",
    }


def _check_national_table(ws: Worksheet, year: int, table: str, title_fragments: tuple[str, ...]) -> None:
    title = _text(ws["A1"].value)
    if str(year) not in title or _text(ws["A3"].value).split() != ["جدول", table]:
        raise ValueError(f"National source title/year/table changed: {ws.title}")
    if not all(fragment in title for fragment in title_fragments):
        raise ValueError(f"Unexpected national source definition: {ws.title}")


def _extract_rehabilitation(workbook, spec: SourceSpec) -> list[dict]:
    sheet, table = ("37.", "4-37") if spec.year == 2023 else ("4-45", "4-45")
    ws = workbook[sheet]
    _check_national_table(ws, spec.year, table, ("زيارات ما بعد البتر", "التأهيل الطبي بوزارة الصحة"))
    if _text(ws["A8"].value) != "داء السكري" or "Diabetes" not in _text(ws["G8"].value):
        raise ValueError(f"Diabetes rehabilitation row changed: {sheet}!A8:G8")
    for cell, label in {"B4": "Saudi", "D4": "Non-Saudi", "B5": "Male", "C5": "Female", "D5": "Male", "E5": "Female", "F5": "Total"}.items():
        if label not in _text(ws[cell].value):
            raise ValueError(f"Rehabilitation header changed: {sheet}!{cell}")
    counts = {name: _count(ws[f"{column}8"].value, f"{sheet}!{column}8") for name, column in VISIT_COLUMNS}
    if all(value is not None for value in counts.values()) and sum(counts[name] for name, _ in VISIT_COLUMNS if name != "visits_total") != counts["visits_total"]:
        raise ValueError(f"Rehabilitation demographic total does not reconcile: {sheet}!F8")
    return [{
        **_national_metadata(ws, spec, table, "A8:G8"),
        **counts,
        "unit": "rehabilitation_encounters",
        "unit_ar": "زيارة تأهيل",
        "service_scope": "Diabetes-related post-amputation encounters at MoH rehabilitation facilities",
        "service_scope_ar": "زيارات ما بعد البتر المرتبط بالسكري لمراكز وأقسام التأهيل الطبي بوزارة الصحة",
        "definition_note_ar": REHABILITATION_NOTE,
    }]


def _extract_dialysis(workbook, spec: SourceSpec) -> list[dict]:
    # Only the 2024 table is used; the 2023 book's dialysis tables are labeled 2021.
    ws = workbook["4-42"]
    _check_national_table(ws, 2024, "4-42", ("مرضى الغسيل الكلوي", "القطاعات الصحية"))
    sectors = (
        ("moh", "وزارة الصحة", "B", "وزارة الصحة"),
        ("other_government", "جهات حكومية أخرى", "C", "جهات حكومية أخرى"),
        ("private", "القطاع الخاص", "D", "قطاع خاص"),
        ("all_sectors", "جميع القطاعات", "E", "المجموع"),
    )
    for _, _, column, header in sectors:
        if _text(ws[f"{column}4"].value) != header:
            raise ValueError(f"Dialysis sector changed: 4-42!{column}4")
    records = []
    totals = []
    for key, label, row, source_fragment in (
        ("haemodialysis", "التنقية الدموية", 7, "التنقية الدموية"),
        ("peritoneal", "التنقية البريتونية", 8, "التنقية البريتونية"),
    ):
        if source_fragment not in _text(ws[f"A{row}"].value):
            raise ValueError(f"Dialysis treatment row changed: 4-42!A{row}")
        counts = [_count(ws[f"{column}{row}"].value, f"4-42!{column}{row}") for _, _, column, _ in sectors]
        if all(value is not None for value in counts) and sum(counts[:3]) != counts[3]:
            raise ValueError(f"Dialysis sector counts do not reconcile: 4-42!E{row}")
        totals.append(counts[3])
        for (sector_key, sector_label, column, _), count in zip(sectors, counts):
            records.append({
                **_national_metadata(ws, spec, "4-42", f"A{row}:F{row}"),
                "treatment_key": key,
                "treatment_label_ar": label,
                "sector_key": sector_key,
                "sector_label_ar": sector_label,
                "aggregation_role": "total" if sector_key == "all_sectors" else "detail",
                "patients": count,
                "unit": "patients",
                "unit_ar": "مريض",
                "service_scope": "Renal dialysis patients across all health sectors",
                "service_scope_ar": "مرضى الغسيل الكلوي في جميع القطاعات الصحية بالمملكة",
                "definition_note_ar": DIALYSIS_NOTE,
                "source_value_cell": f"{column}{row}",
            })
    summary = workbook["4-43"]
    _check_national_table(summary, 2024, "4-43", ("مرضى الغسيل الكلوي", "الجنس والجنسية"))
    published_total = _count(summary["A7"].value, "4-43!A7")
    if published_total is not None and all(value is not None for value in totals) and sum(totals) != published_total:
        raise ValueError("Dialysis treatment totals do not reconcile with published national total at 4-43!A7")
    return records


def extract_chronic_care_data() -> dict[str, list[dict]]:
    """Return source-level visit and facility records with row/cell provenance."""
    datasets: dict[str, list[dict]] = {
        "diabetes_visits": [], "chronic_care_capacity": [],
        "diabetes_rehabilitation_visits": [], "dialysis_patients_2024": [],
    }
    for spec in SOURCES:
        source_path = PROJECT_ROOT / spec.source_file
        if not source_path.is_file():
            raise FileNotFoundError(f"Required source workbook is missing: {source_path}")
        workbook = load_workbook(source_path, read_only=True, data_only=True)
        try:
            capacity = workbook[spec.capacity_sheet]
            _check_table(capacity, spec, spec.capacity_table, visits=False)
            _check_rows(capacity, spec.year, tuple(column for _, _, column, _ in FACILITY_TYPES))
            for row_spec in _row_specs(spec.year):
                metadata = _metadata(capacity, spec, spec.capacity_table, row_spec, "N")
                for facility_type, facility_label, column, _ in FACILITY_TYPES:
                    datasets["chronic_care_capacity"].append({
                        **metadata,
                        "facility_type": facility_type,
                        "facility_label_ar": facility_label,
                        "value": _count(capacity[f"{column}{row_spec[2]}"].value, f"{capacity.title}!{column}{row_spec[2]}"),
                        "unit": "facility_count",
                        "unit_ar": "مرفق",
                        "service_scope": "MoH facilities",
                        "service_scope_ar": "مرافق وزارة الصحة",
                        "definition_note_ar": CAPACITY_NOTE,
                        "source_value_cell": f"{column}{row_spec[2]}",
                    })
            if spec.visits_sheet:
                visits = workbook[spec.visits_sheet]
                _check_table(visits, spec, spec.visits_table, visits=True)
                _check_rows(visits, spec.year, tuple(column for _, column in VISIT_COLUMNS))
                for row_spec in _row_specs(spec.year):
                    counts = {
                        name: _count(visits[f"{column}{row_spec[2]}"].value, f"{visits.title}!{column}{row_spec[2]}")
                        for name, column in VISIT_COLUMNS
                    }
                    if all(value is not None for value in counts.values()) and sum(
                        counts[name] for name, _ in VISIT_COLUMNS if name != "visits_total"
                    ) != counts["visits_total"]:
                        raise ValueError(f"Visit sex/nationality totals do not reconcile at {visits.title}!F{row_spec[2]}")
                    datasets["diabetes_visits"].append({
                        **_metadata(visits, spec, spec.visits_table, row_spec, "G"),
                        **counts,
                        "unit": "clinic_encounters",
                        "unit_ar": "زيارة",
                        "service_scope": "Diabetes clinics in MoH hospitals",
                        "service_scope_ar": "عيادات السكري بمستشفيات وزارة الصحة",
                        "definition_note_ar": VISITS_NOTE,
                    })
            if spec.year in (2023, 2024):
                datasets["diabetes_rehabilitation_visits"].extend(_extract_rehabilitation(workbook, spec))
            if spec.year == 2024:
                datasets["dialysis_patients_2024"].extend(_extract_dialysis(workbook, spec))
        finally:
            workbook.close()
    for name, records in datasets.items():
        keys = [(row["year"], row["entity_key"], row.get("facility_type"), row.get("treatment_key"), row.get("sector_key")) for row in records]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Duplicate source observations in {name}")
    return datasets


def main() -> None:
    datasets = extract_chronic_care_data()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, records in datasets.items():
        path = OUTPUT_DIR / f"{name}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
        print(f"Wrote {len(records)} source observations: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
