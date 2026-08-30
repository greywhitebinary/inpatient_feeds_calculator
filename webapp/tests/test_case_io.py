from io import BytesIO
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from case_io import export_case_record_workbook, import_case_record_workbook
from data import load_master_formulas, load_master_modulars


class CaseRecordTests(unittest.TestCase):
    def test_default_website_metadata_is_safe_and_not_hyperlinked(self):
        payload = export_case_record_workbook({}, load_master_formulas().head(0), load_master_modulars().head(0))
        workbook = load_workbook(BytesIO(payload))
        sheet = workbook["Case record"]

        self.assertEqual(sheet["A2"].value, "Calculator website")
        self.assertEqual(sheet["B2"].value, "To be added after deployment")
        self.assertIsNone(sheet["B2"].hyperlink)
        self.assertIn("does not retain case records", sheet["A4"].value)
        self.assertIn("hosted session processes entered values", sheet["A4"].value)

    def test_live_configured_website_is_hyperlinked(self):
        with patch.dict(os.environ, {"CALCULATOR_WEBSITE_URL": "https://feeds.example.org/calculator"}):
            payload = export_case_record_workbook({}, load_master_formulas().head(0), load_master_modulars().head(0))
        sheet = load_workbook(BytesIO(payload))["Case record"]

        self.assertEqual(sheet["B2"].value, "https://feeds.example.org/calculator")
        self.assertEqual(sheet["B2"].hyperlink.target, "https://feeds.example.org/calculator")

    def test_localhost_configuration_is_not_written_to_workbook(self):
        with patch.dict(os.environ, {"CALCULATOR_WEBSITE_URL": "http://localhost:8501"}):
            payload = export_case_record_workbook({}, load_master_formulas().head(0), load_master_modulars().head(0))
        sheet = load_workbook(BytesIO(payload))["Case record"]

        self.assertEqual(sheet["B2"].value, "To be added after deployment")
        self.assertIsNone(sheet["B2"].hyperlink)

    def test_import_accepts_workbook_without_new_website_field(self):
        formulas = load_master_formulas().head(0)
        modulars = load_master_modulars().head(0)
        payload = export_case_record_workbook({"case_record_label": "Older record"}, formulas, modulars)
        workbook = load_workbook(BytesIO(payload))
        workbook["Case record"].delete_rows(2, 1)
        legacy = BytesIO()
        workbook.save(legacy)

        restored, _, _ = import_case_record_workbook(BytesIO(legacy.getvalue()))

        self.assertEqual(restored["case_record_label"], "Older record")

    def test_import_accepts_legacy_plan_goal_mirrors(self):
        payload = export_case_record_workbook(
            {"case_record_label": "Older goal record"},
            load_master_formulas().head(0),
            load_master_modulars().head(0),
        )
        workbook = load_workbook(BytesIO(payload))
        inputs = workbook["Case inputs"]
        inputs.append(["icu_total_energy_target", "1750.0"])
        legacy = BytesIO()
        workbook.save(legacy)

        restored, _, _ = import_case_record_workbook(BytesIO(legacy.getvalue()))

        self.assertEqual(restored["icu_total_energy_target"], 1750.0)

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
            "en_hydration_schedule_format": "qXh",
            "en_hydration_interval_hours": 4,
            f"modular_units_{modulars.iloc[0]['id']}": 2.0,
        }

        payload = export_case_record_workbook(state, formulas, modulars)
        restored, restored_formulas, restored_modulars = import_case_record_workbook(BytesIO(payload))

        self.assertEqual(restored["assessment_age"], 67.0)
        self.assertEqual(restored["feed_candidates"], [formulas.iloc[0]["name"]])
        self.assertEqual(restored["en_hydration_schedule_format"], "qXh")
        self.assertEqual(restored["en_hydration_interval_hours"], 4)
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

    def test_import_rejects_an_invalid_numeric_widget_value(self):
        payload = export_case_record_workbook(
            {"assessment_age": 67},
            load_master_formulas().head(0),
            load_master_modulars().head(0),
        )
        workbook = load_workbook(BytesIO(payload))
        inputs = workbook["Case inputs"]
        inputs["B2"] = '"sixty-seven"'
        edited = BytesIO()
        workbook.save(edited)

        with self.assertRaisesRegex(ValueError, "non-numeric.*assessment_age"):
            import_case_record_workbook(BytesIO(edited.getvalue()))

    def test_import_rejects_an_invalid_scenario_schedule(self):
        payload = export_case_record_workbook(
            {"scenario_standard_schedule_type": "Continuous / cyclic"},
            load_master_formulas().head(0),
            load_master_modulars().head(0),
        )
        workbook = load_workbook(BytesIO(payload))
        inputs = workbook["Case inputs"]
        inputs["B2"] = '"Unsupported schedule"'
        edited = BytesIO()
        workbook.save(edited)

        with self.assertRaisesRegex(ValueError, "unsupported schedule"):
            import_case_record_workbook(BytesIO(edited.getvalue()))

    def test_import_rejects_duplicate_case_fields(self):
        payload = export_case_record_workbook(
            {"assessment_age": 67},
            load_master_formulas().head(0),
            load_master_modulars().head(0),
        )
        workbook = load_workbook(BytesIO(payload))
        workbook["Case inputs"].append(["assessment_age", "68"])
        edited = BytesIO()
        workbook.save(edited)

        with self.assertRaisesRegex(ValueError, "duplicate field keys"):
            import_case_record_workbook(BytesIO(edited.getvalue()))

    def test_round_trip_preserves_both_en_scenarios(self):
        formulas = load_master_formulas().head(1)
        modulars = load_master_modulars().head(1)
        product_id = modulars.iloc[0]["id"]
        state = {
            "en_total_energy_target": 1800.0,
            "en_has_alternate_plan": True,
            "scenario_primary_include_propofol": False,
            "scenario_primary_propofol_rate": 0.0,
            "scenario_primary_selected_formula": formulas.iloc[0]["name"],
            f"scenario_primary_modular_doses_{product_id}": 2.0,
            "scenario_alternate_include_propofol": True,
            "scenario_alternate_propofol_rate": 20.0,
            "scenario_alternate_selected_formula": formulas.iloc[0]["name"],
            f"scenario_alternate_modular_doses_{product_id}": 4.0,
        }

        payload = export_case_record_workbook(state, formulas, modulars)
        restored, _, _ = import_case_record_workbook(BytesIO(payload))

        self.assertFalse(restored["scenario_primary_include_propofol"])
        self.assertEqual(restored[f"scenario_primary_modular_doses_{product_id}"], 2.0)
        self.assertTrue(restored["scenario_alternate_include_propofol"])
        self.assertEqual(restored["scenario_alternate_propofol_rate"], 20.0)
        self.assertEqual(restored[f"scenario_alternate_modular_doses_{product_id}"], 4.0)

    def test_round_trip_preserves_independent_standard_and_icu_workflows(self):
        formulas = load_master_formulas().head(1)
        modulars = load_master_modulars().head(1)
        state = {
            "assessment_energy_target": 1800.0,
            "assessment_protein_target": 100.0,
            "assessment_water_target": 2000.0,
            "en_total_energy_target": 1800.0,
            "feed_candidates": [formulas.iloc[0]["name"]],
            "scenario_standard_feeding_hours": 18.0,
            "scenario_standard_ordered_rate_ml_hr": 55.0,
            "scenario_standard_ordered_formula_name": formulas.iloc[0]["name"],
            "scenario_standard_order_user_edited": True,
            "scenario_standard_order_reset_requested": True,
            "scenario_standard_hydration_schedule_format": "qXh",
            "scenario_standard_hydration_interval_hours": 4,
            "icu_total_energy_target": 1750.0,
            "icu_protein_target": 100.0,
            "icu_water_target": 2000.0,
            "icu_feed_candidates": [formulas.iloc[0]["name"]],
            "icu_planned_daily_intake_scenario": "higher",
            "scenario_lower_propofol_rate": 8.0,
            "scenario_lower_propofol_hours": 12.0,
            "scenario_lower_ordered_rate_ml_hr": 50.0,
            "scenario_higher_propofol_rate": 22.0,
            "scenario_higher_propofol_hours": 18.0,
            "scenario_higher_ordered_rate_ml_hr": 35.0,
            "assessment_activity_factor": 1.1,
            "assessment_stress_factor": 1.2,
        }

        payload = export_case_record_workbook(state, formulas, modulars)
        restored, _, _ = import_case_record_workbook(BytesIO(payload))

        self.assertEqual(restored["scenario_standard_feeding_hours"], 18.0)
        self.assertEqual(restored["scenario_standard_ordered_rate_ml_hr"], 55.0)
        self.assertTrue(restored["scenario_standard_order_user_edited"])
        self.assertNotIn("scenario_standard_order_reset_requested", restored)
        self.assertEqual(restored["scenario_standard_hydration_schedule_format"], "qXh")
        self.assertEqual(restored["scenario_standard_hydration_interval_hours"], 4)
        self.assertEqual(restored["assessment_energy_target"], 1800.0)
        self.assertEqual(restored["assessment_protein_target"], 100.0)
        self.assertEqual(restored["assessment_water_target"], 2000.0)
        self.assertNotIn("en_total_energy_target", restored)
        self.assertNotIn("icu_total_energy_target", restored)
        self.assertEqual(restored["icu_planned_daily_intake_scenario"], "higher")
        self.assertEqual(restored["scenario_lower_propofol_rate"], 8.0)
        self.assertEqual(restored["scenario_lower_propofol_hours"], 12.0)
        self.assertEqual(restored["scenario_lower_ordered_rate_ml_hr"], 50.0)
        self.assertEqual(restored["scenario_higher_propofol_rate"], 22.0)
        self.assertEqual(restored["scenario_higher_propofol_hours"], 18.0)
        self.assertEqual(restored["scenario_higher_ordered_rate_ml_hr"], 35.0)
        self.assertEqual(restored["assessment_activity_factor"], 1.1)
        self.assertEqual(restored["assessment_stress_factor"], 1.2)

    def test_old_height_fields_migrate_to_centimetres_on_import(self):
        formulas = load_master_formulas().head(0)
        modulars = load_master_modulars().head(0)
        payload = export_case_record_workbook(
            {
                "assessment_height_unit": "m",
                "assessment_height_m": 1.65,
            },
            formulas,
            modulars,
        )

        restored, _, _ = import_case_record_workbook(BytesIO(payload))

        self.assertEqual(restored["assessment_height_cm"], 165.0)
        self.assertNotIn("assessment_height_unit", restored)
        self.assertNotIn("assessment_height_m", restored)
