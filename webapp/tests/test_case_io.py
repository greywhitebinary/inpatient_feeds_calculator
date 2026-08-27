from io import BytesIO
import unittest

from case_io import export_case_record_workbook, import_case_record_workbook
from data import load_master_formulas, load_master_modulars


class CaseRecordTests(unittest.TestCase):
    def test_round_trip_includes_inputs_and_formulary_snapshot(self):
        formulas = load_master_formulas().head(1)
        modulars = load_master_modulars().head(1)
        state = {
            "case_record_label": "Ward nutrition review",
            "assessment_age": 67.0,
            "assessment_sex": "Female",
            "assessment_energy_target": 1750.0,
            "feed_candidates": [formulas.iloc[0]["name"]],
            "chosen_modulars": [modulars.iloc[0]["name"]],
            f"modular_units_{modulars.iloc[0]['id']}": 2.0,
        }

        payload = export_case_record_workbook(state, formulas, modulars)
        restored, restored_formulas, restored_modulars = import_case_record_workbook(BytesIO(payload))

        self.assertEqual(restored["assessment_age"], 67.0)
        self.assertEqual(restored["feed_candidates"], [formulas.iloc[0]["name"]])
        self.assertEqual(restored_formulas["name"].tolist(), formulas["name"].tolist())
        self.assertEqual(restored_modulars["id"].tolist(), modulars["id"].tolist())

    def test_round_trip_preserves_an_unentered_value(self):
        formulas = load_master_formulas().head(0)
        modulars = load_master_modulars().head(0)
        payload = export_case_record_workbook(
            {"case_record_label": "Blank example", "assessment_energy_target": None},
            formulas,
            modulars,
        )

        restored, _, _ = import_case_record_workbook(BytesIO(payload))

        self.assertIn("assessment_energy_target", restored)
        self.assertIsNone(restored["assessment_energy_target"])
