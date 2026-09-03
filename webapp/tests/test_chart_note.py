import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculations import iv_fluid_delivery
from constants import IV_FLUIDS
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
        "estimated_energy_requirement": 1800,
        "prescription_target_pct": 100,
        "prescription_interruption_note": False,
        "chart_total": {
            "Energy (kcal)": 1775,
            "Protein (g)": 90,
            "Carbohydrate (g)": 202,
            "Fat (g)": 69,
            "Water (mL)": 1900,
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
        self.assertIn("CBW: 64.0 kg", note)
        self.assertIn("UBW: 68.0 kg", note)
        self.assertNotIn("Usual weight:", note)
        self.assertIn("(CBW 64.0 kg × 1.2–1.5 g/kg)", note)

    def test_mixed_flush_volumes_still_produce_a_hydration_line(self):
        # An order of 200 mL three times and 100 mL twice has a real total and
        # no shared per-flush volume. Gating the sentence on the per-flush
        # amount dropped hydration from the note entirely, without warning.
        result = result_fixture()
        result["hydration"] = {
            "hydration_flush_each_ml": 0,
            "hydration_flush_total_ml": 800,
        }
        result["hydration_chart_schedule_text"] = (
            "200 mL before and after each feed and 100 mL twice overnight"
        )
        note = build_chart_note_html(self.state, [result])
        self.assertIn("Hydration: Provide", note)
        self.assertIn("200 mL before and after each feed", note)
        self.assertIn("totalling 800 mL daily", note)

    def test_mixed_flush_volumes_never_quote_a_per_flush_amount(self):
        result = result_fixture()
        result["hydration"] = {
            "hydration_flush_each_ml": 0,
            "hydration_flush_total_ml": 800,
        }
        note = build_chart_note_html(self.state, [result])
        self.assertNotIn("Hydration flushes 0 mL", note)
        self.assertIn("Hydration flushes 800 mL daily", note)

    def test_no_hydration_order_still_omits_the_hydration_line(self):
        result = result_fixture()
        result["hydration"] = {
            "hydration_flush_each_ml": 0,
            "hydration_flush_total_ml": 0,
        }
        note = build_chart_note_html(self.state, [result])
        self.assertNotIn("Hydration:", note)

    def test_ons_order_has_separate_en_and_ons_macro_subtotals(self):
        result = result_fixture()
        result["chart_ons"] = [{
            "name": "BOOST Plus Calories — Vanilla",
            "package_unit": "carton",
            "containers_each_time": 1,
            "times_per_day": 2,
        }]
        result["ons_totals"] = {
            "energy_kcal": 720,
            "protein_g": 28,
            "carbohydrate_g": 90,
            "fat_g": 28,
            "free_water_ml": 366,
        }
        result["chart_total"].update({
            "Energy (kcal)": 2495,
            "Protein (g)": 118,
            "Carbohydrate (g)": 292,
            "Fat (g)": 97,
            "Water (mL)": 2266,
        })

        note = build_chart_note_html(self.state, [result])

        self.assertIn(
            "ONS: BOOST Plus Calories — Vanilla, 1 carton BID.", note
        )
        self.assertIn(
            "At goal, EN and ONS orders provide energy 2,495 kcal "
            "(EN 1,775 kcal + ONS 720 kcal)",
            note,
        )
        self.assertIn(
            "protein 118 g (EN 90 g + ONS 28 g)", note
        )
        self.assertIn("CHO 292 g (EN 202 g + ONS 90 g)", note)
        self.assertIn("fat 97 g (EN 69 g + ONS 28 g)", note)
        self.assertIn("Total water provided is 2,266 mL/day", note)
        self.assertIn("ONS water 366 mL", note)

    def test_serving_based_ons_uses_serving_wording_in_order(self):
        result = result_fixture()
        result["chart_ons"] = [{
            "name": "BOOST Pudding — Vanilla",
            "calculation_basis": "serving",
            "quantity_each_time": 1,
            "quantity_unit": "cup",
            "times_per_day": 2,
        }]
        result["ons_totals"] = {
            "energy_kcal": 460,
            "protein_g": 14,
            "carbohydrate_g": 64,
            "fat_g": 16,
            "free_water_ml": 186,
        }
        note = build_chart_note_html(self.state, [result])
        self.assertIn("ONS: BOOST Pudding — Vanilla, 1 cup BID.", note)

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

    def test_conditional_propofol_note_uses_one_plan_and_two_linked_rates(self):
        result = result_fixture()
        result["propofol_method"] = "Changing Propofol rates"
        result["prescription_target_pct"] = 110
        result["prescription_interruption_note"] = True
        result["delivery"]["planned_volume_ml"] = 1064
        result["feeding_hours"] = 23
        result["propofol_conditions"] = [
            {"rate_ml_hr": 0, "hours": 18},
            {"rate_ml_hr": 20, "hours": 6},
        ]
        result["conditional_orders"] = [
            {"propofol_rate_ml_hr": 0, "formula_rate_ml_hr": 50},
            {"propofol_rate_ml_hr": 20, "formula_rate_ml_hr": 35},
        ]

        note = build_chart_note_html(self.state, [result])

        self.assertIn(
            "EN prescription target: 110% of estimated energy requirement "
            "(1,980 kcal/day) to account for anticipated interruptions.",
            note,
        )
        self.assertEqual(note.count("Enteral nutrition plan: Isosource 1.5."), 1)
        self.assertIn(
            "When Propofol is not running, provide feed at 50 mL/hr.", note
        )
        self.assertIn(
            "When Propofol is at 20 mL/hr, provide feed at 35 mL/hr.", note
        )
        self.assertIn(
            "Projected Propofol exposure: 20 mL/hr for 6 hours/day.",
            note,
        )
        self.assertNotIn("0 mL/hr for 18 hours/day", note)
        self.assertIn(
            "Projected formula delivery is 1,064 mL/day over 23 feeding hours.",
            note,
        )

    def test_modified_prescription_target_does_not_invent_a_reason(self):
        result = result_fixture()
        result["prescription_target_pct"] = 80

        note = build_chart_note_html(self.state, [result])

        self.assertIn(
            "EN prescription target: 80% of estimated energy requirement "
            "(1,440 kcal/day).",
            note,
        )
        self.assertNotIn("anticipated interruptions", note)

    def test_selected_trickle_description_changes_intervention_wording(self):
        result = result_fixture()
        result["describe_as_trickle"] = True
        result["schedule_description"] = "20 mL/hour for 23 hours daily"

        note = build_chart_note_html(self.state, [result])

        self.assertIn(
            "Initiate trickle EN with Isosource 1.5 at 20 mL/hour for "
            "23 hours daily.",
            note,
        )
        self.assertNotIn("Enteral nutrition plan: Isosource 1.5", note)

    def test_clinician_selected_weight_is_named_in_weight_based_equations(self):
        self.state["assessment_estimated_weight"] = 62
        self.state["assessment_weight_choice"] = (
            "Estimated dry / clinician-selected weight"
        )
        note = build_chart_note_html(self.state, [result_fixture()])
        self.assertIn("(clinician-selected weight 62.0 kg × 25–30 kcal/kg)", note)
        self.assertIn("(clinician-selected weight 62.0 kg × 1.2–1.5 g/kg)", note)

    def test_protein_can_use_a_different_weight_than_energy_and_water(self):
        """Energy on CBW with protein on IBW is routine practice."""
        self.state["assessment_protein_weight_choice"] = (
            "Ideal body weight (Hamwi — SI units)"
        )
        note = build_chart_note_html(self.state, [result_fixture()])
        self.assertIn("(CBW 64.0 kg × 25–30 kcal/kg)", note)
        self.assertIn("(IBW 56.4 kg × 1.2–1.5 g/kg)", note)
        # Water deliberately has no selector and follows the energy weight.
        self.assertIn("(CBW 64.0 kg × 25–30 mL/kg)", note)

    def test_protein_weight_falls_back_to_the_energy_weight(self):
        """A case saved before protein had its own basis must read unchanged."""
        self.assertNotIn("assessment_protein_weight_choice", self.state)
        note = build_chart_note_html(self.state, [result_fixture()])
        self.assertIn("(CBW 64.0 kg × 1.2–1.5 g/kg)", note)

    def test_rounded_energy_equations_are_marked_as_approximate(self):
        note = build_chart_note_html(self.state, [result_fixture()])
        self.assertIn("kcal/day ≈", note)
        self.assertNotIn("kcal/day =", note)



class IVChartNoteTests(unittest.TestCase):
    """The note has to say what is running, not only what it supplies."""

    def _note(self, orders):
        result = result_fixture()
        result["iv_orders"] = orders
        return build_chart_note_html(self.state, [result])

    def setUp(self):
        super().setUp()
        if not hasattr(self, "state"):
            self.state = {}

    def test_fluid_is_named_with_its_rate_and_daily_totals(self):
        order = [{
            "name": "D5 1/2 NS", "rate_ml_hr": 85.0,
            "delivery": iv_fluid_delivery(IV_FLUIDS["D5 1/2 NS"], 85),
        }]
        note = self._note(order)
        self.assertIn("D5 1/2 NS at 85 mL/hour", note)
        self.assertIn("2,040 mL/day", note)
        self.assertIn("347 kcal/day", note)

    def test_tkvo_names_the_fluid_without_inventing_a_rate(self):
        order = [{
            "name": "D5W", "rate_ml_hr": 0.0, "tkvo": True,
            "delivery": iv_fluid_delivery(IV_FLUIDS["D5W"], 0),
        }]
        note = self._note(order)
        self.assertIn("IV: D5W, TKVO.", note)
        # A line kept open supplies nothing, so no providing clause follows.
        self.assertNotIn("providing", note.split("TKVO")[1][:40])

    def test_no_iv_produces_no_line(self):
        self.assertNotIn("IV:", self._note([]))


if __name__ == "__main__":
    unittest.main()
