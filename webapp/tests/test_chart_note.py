import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chart_note import build_chart_note_html


def result_fixture():
    return {
        "label": "EN plan",
        "formula": {"name": "Isosource 1.5"},
        "delivery": {
            "energy_kcal": 1725,
            "protein_g": 78,
            "carbohydrate_g": 202,
            "fat_g": 69,
            "free_water_ml": 880,
        },
        "modular_totals": {"free_water_ml": 0},
        "propofol": {"kcal": 0, "fat_g": 0},
        "hydration": {
            "hydration_flush_each_ml": 130,
            "hydration_flush_total_ml": 780,
        },
        "chart_modulars": [{
            "name": "Beneprotein",
            "order": "1 packet BID",
            "energy_kcal": 50,
            "protein_g": 12,
            "fat_g": 0,
            "preparation_water_ml": 120,
            "preparation_water_per_dose_ml": 60,
        }],
        "schedule_description": "50 mL/hour for 23 hours daily",
        "hydration_chart_schedule_text": "q4h",
        "medication_flushes_ml": 120,
        "patency_flushes_ml": 0,
        "propofol_rate": 0,
        "propofol_hours": 24,
        "chart_total": {
            "Energy (kcal)": 1775,
            "Protein (g)": 90,
            "Carbohydrate (g)": 202,
            "Fat (g)": 69,
            "Free water (mL)": 880,
            "Water flushes (mL)": 1020,
        },
    }


class ChartNoteTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "assessment_sex": "Female",
            "assessment_age": 67,
            "assessment_height_cm": 165,
            "assessment_current_weight": 64,
            "assessment_usual_weight": 68,
            "assessment_weight_choice": "Current body weight",
            "assessment_energy_low_kcal_kg": 25,
            "assessment_energy_high_kcal_kg": 30,
            "assessment_activity_factor": 1,
            "assessment_stress_factor": 1,
            "assessment_protein_low_gkg": 1.2,
            "assessment_protein_high_gkg": 1.5,
            "assessment_water_low_mlkg": 25,
            "assessment_water_high_mlkg": 30,
        }

    def test_note_uses_spelled_out_adime_headings_and_water_sources(self):
        note = build_chart_note_html(self.state, [result_fixture()])
        for heading in (
            "Assessment",
            "Nutrition Diagnosis",
            "Nutrition Intervention(s)",
            "Monitoring, Evaluation, and Follow-Up Plan",
        ):
            self.assertIn(f"<strong>{heading}</strong>", note)
        self.assertIn("Modulars: Beneprotein 1 packet BID", note)
        self.assertIn(
            "At goal, the complete regimen provides energy 1,775 kcal ", note
        )
        self.assertIn("protein 90 g (Formula 78 g + Beneprotein 12 g)", note)
        self.assertIn("CHO 202 g, and fat 69 g.", note)
        self.assertIn("Total water provided is 1,900 mL/day", note)
        self.assertIn("Free water 880 mL", note)
        self.assertIn("Beneprotein flushes 120 mL", note)
        self.assertIn("Hydration flushes 130 mL q4h", note)
        self.assertNotIn("free water from water flushes", note)
        self.assertNotIn("nutrition dosing weight", note.lower())
        self.assertIn("Height: 1.65 m", note)
        self.assertIn("Current body weight: 64.0 kg", note)
        self.assertIn("UBW: 68.0 kg", note)
        self.assertNotIn("Usual weight:", note)
        self.assertIn("(CBW 64.0 kg × 1.2–1.5 g/kg)", note)

    def test_penn_equations_require_both_temperature_and_minute_ventilation(self):
        self.state["assessment_temperature"] = 38.2
        without_ventilation = build_chart_note_html(self.state, [result_fixture()])
        self.assertNotIn("Penn State", without_ventilation)

        self.state["assessment_minute_ventilation"] = 9.5
        complete = build_chart_note_html(self.state, [result_fixture()])
        self.assertIn("Penn State 2003b", complete)
        self.assertIn("Modified Penn State 2010", complete)
        self.assertIn("Tmax 38.2 °C, Ve 9.5 L/min", complete)

    def test_propofol_scenarios_state_when_each_plan_applies(self):
        lower = result_fixture()
        higher = result_fixture()
        higher["propofol_rate"] = 20
        higher["propofol_hours"] = 24
        note = build_chart_note_html(self.state, [lower, higher])
        self.assertIn("When Propofol is not running, use this EN plan:", note)
        self.assertIn(
            "When Propofol is running at 20 mL/hr for 24 hours/day, "
            "use this EN plan:",
            note,
        )

    def test_rd_selected_weight_is_named_in_weight_based_equations(self):
        self.state["assessment_estimated_weight"] = 62
        self.state["assessment_weight_choice"] = (
            "Estimated dry / clinician-selected weight"
        )
        note = build_chart_note_html(self.state, [result_fixture()])
        self.assertIn("(RD-selected weight 62.0 kg × 25–30 kcal/kg)", note)
        self.assertIn("(RD-selected weight 62.0 kg × 1.2–1.5 g/kg)", note)

    def test_rounded_energy_equations_are_marked_as_approximate(self):
        note = build_chart_note_html(self.state, [result_fixture()])
        self.assertIn("kcal/day ≈", note)
        self.assertNotIn("kcal/day =", note)


if __name__ == "__main__":
    unittest.main()
