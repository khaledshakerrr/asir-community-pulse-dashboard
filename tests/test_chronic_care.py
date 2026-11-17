"""Check source snapshots, disjoint geography and missing-value presentation."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
import pandas as pd

from src.chronic_care import load_chronic_care_data
from src.chronic_charts import (
    build_chronic_capacity_chart,
    build_diabetes_rehabilitation_chart,
    build_diabetes_snapshot_chart,
    build_dialysis_patients_chart,
    get_national_dialysis_total,
    select_snapshot,
)
from scripts.build_chronic_care_data import _check_national_table


class ChronicCareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_chronic_care_data()

    def test_published_visit_values_and_demographic_totals(self):
        visits = self.data["diabetes_visits"]
        expected = {
            (2023, "saudi_arabia"): 617377,
            (2023, "asir"): 81356,
            (2023, "bisha"): 15131,
            (2023, "qassim"): 50902,
            (2024, "saudi_arabia"): 620742,
            (2024, "asir"): 87748,
            (2024, "bisha"): 19452,
            (2024, "qassim"): 56290,
            (2024, "asir_cluster_total"): 107200,
        }
        self.assertEqual(visits.set_index(["year", "entity_key"])["visits_total"].to_dict(), expected)
        self.assertTrue((visits[["saudi_male", "saudi_female", "non_saudi_male", "non_saudi_female"]].sum(axis=1) == visits["visits_total"]).all())

    def test_focus_never_double_counts_national_or_asir_subtotal(self):
        for name in ("diabetes_visits", "chronic_care_capacity"):
            frame = self.data[name]
            for year in frame["year"].unique():
                focus = select_snapshot(frame, int(year))
                self.assertEqual(set(focus["entity_key"]), {"asir", "bisha", "qassim"})
                self.assertEqual(set(focus["row_role"]), {"detail"})
            key = ["year", "entity_key"] + (["facility_type"] if name == "chronic_care_capacity" else [])
            self.assertFalse(frame.duplicated(key).any())

    def test_missing_historical_subtotal_is_unavailable_not_zero(self):
        for year in (2022, 2023):
            self.assertTrue(select_snapshot(self.data["chronic_care_capacity"], year, "asir_cluster_total").empty)
            chart = build_chronic_capacity_chart(self.data["chronic_care_capacity"], year, "asir_cluster_total")
            self.assertEqual(len(chart.data), 0)
            self.assertIn("لا توجد", chart.layout.annotations[0].text)
        self.assertEqual(len(build_diabetes_snapshot_chart(self.data["diabetes_visits"], 2023, "asir_cluster_total").data), 0)

    def test_facility_zero_and_published_asir_subtotals(self):
        capacity = self.data["chronic_care_capacity"]
        oncology = capacity.loc[(capacity["year"] == 2022) & (capacity["entity_key"] == "asir") & (capacity["facility_type"] == "oncology"), "value"].item()
        self.assertEqual(oncology, 0)
        current = capacity.loc[capacity["year"] == 2024].pivot(index="facility_type", columns="entity_key", values="value")
        self.assertTrue((current["asir"] + current["bisha"] == current["asir_cluster_total"]).all())
        self.assertEqual(current["asir_cluster_total"].to_dict(), {"cardiology": 1, "oncology": 1, "diabetes_endocrinology": 3, "dialysis": 25})

    def test_missing_value_does_not_become_zero_bar(self):
        capacity = self.data["chronic_care_capacity"].copy()
        capacity.loc[(capacity["year"] == 2024) & (capacity["entity_key"] == "asir"), "value"] = pd.NA
        self.assertEqual(len(build_chronic_capacity_chart(capacity, 2024, "asir").data), 0)

    def test_source_provenance_and_geography_are_preserved(self):
        for name, frame in self.data.items():
            for column in ("source_file", "source_sheet", "source_table", "source_range", "source_url", "definition_note_ar"):
                self.assertTrue(frame[column].str.len().gt(0).all())
            if name in ("diabetes_visits", "chronic_care_capacity"):
                self.assertEqual(set(frame.loc[(frame["year"] == 2023) & (frame["row_role"] == "detail"), "geography_type"]), {"health_region"})
                self.assertEqual(set(frame.loc[(frame["year"] == 2024) & (frame["row_role"] == "detail"), "geography_type"]), {"health_cluster"})
            else:
                self.assertEqual(set(frame["geography_type"]), {"national"})
                self.assertEqual(set(frame["entity_key"]), {"saudi_arabia"})

    def test_rehabilitation_uses_diabetes_encounters_and_reconciles(self):
        visits = self.data["diabetes_rehabilitation_visits"]
        self.assertEqual(visits.set_index("year")["visits_total"].to_dict(), {2023: 651, 2024: 1215})
        self.assertEqual(set(visits["unit"]), {"rehabilitation_encounters"})
        self.assertEqual(visits.set_index("year")["source_table"].to_dict(), {2023: "4-37", 2024: "4-45"})
        self.assertTrue((visits[["saudi_male", "saudi_female", "non_saudi_male", "non_saudi_female"]].sum(axis=1) == visits["visits_total"]).all())
        chart = build_diabetes_rehabilitation_chart(visits)
        self.assertEqual(sum(sum(trace.y) for trace in chart.data), 1866)

    def test_dialysis_uses_only_2024_and_does_not_double_count_sectors(self):
        patients = self.data["dialysis_patients_2024"]
        self.assertEqual(set(patients["year"]), {2024})
        self.assertEqual(set(patients["unit"]), {"patients"})
        self.assertFalse(patients.duplicated(["year", "treatment_key", "sector_key"]).any())
        totals = patients[patients["sector_key"].eq("all_sectors")].set_index("treatment_key")["patients"]
        details = patients[patients["aggregation_role"].eq("detail")].groupby("treatment_key")["patients"].sum()
        self.assertEqual(totals.to_dict(), {"haemodialysis": 17734, "peritoneal": 1208})
        self.assertEqual(totals.to_dict(), details.to_dict())
        self.assertEqual(get_national_dialysis_total(patients), 18942)
        chart = build_dialysis_patients_chart(patients)
        self.assertEqual(len(chart.data), 3)
        self.assertEqual(sum(sum(trace.x) for trace in chart.data), 18942)

    def test_incomplete_national_counts_are_unavailable(self):
        patients = self.data["dialysis_patients_2024"].copy()
        patients.loc[patients["sector_key"].eq("all_sectors"), "patients"] = pd.NA
        self.assertIsNone(get_national_dialysis_total(patients))
        patients.loc[patients["sector_key"].eq("private"), "patients"] = pd.NA
        self.assertEqual(len(build_dialysis_patients_chart(patients).data), 0)
        visits = self.data["diabetes_rehabilitation_visits"].copy()
        visits["visits_total"] = pd.NA
        self.assertEqual(len(build_diabetes_rehabilitation_chart(visits).data), 0)

    def test_source_title_year_takes_precedence_over_book_filename(self):
        cells = {
            "A1": SimpleNamespace(value="مراكز ومرضى الغسيل الكلوي حسب القطاعات الصحية عام 2021م."),
            "A3": SimpleNamespace(value="جدول 4-34"),
        }
        sheet = MagicMock()
        sheet.title = "34."
        sheet.__getitem__.side_effect = cells.__getitem__
        with self.assertRaisesRegex(ValueError, "title/year/table"):
            _check_national_table(sheet, 2023, "4-34", ("مرضى الغسيل الكلوي",))


if __name__ == "__main__":
    unittest.main()
