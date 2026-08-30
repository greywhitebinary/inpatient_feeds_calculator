from pathlib import Path
import sys
import unittest

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from case_io import export_case_record_workbook
from calculations import modular_delivery, practical_feed_delivery, propofol_intake
from data import load_master_formulas, load_master_modulars


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class AssessmentRenderTests(unittest.TestCase):
    def test_saved_record_opens_without_mutating_an_instantiated_widget(self):
        formulas = load_master_formulas().iloc[[0]].copy()
        modulars = load_master_modulars().iloc[[0]].copy()
        workbook = export_case_record_workbook(
            {
                "case_record_label": "Imported test record",
                "assessment_age": 45,
                "assessment_energy_target": 1750,
                "assessment_protein_target": 90,
                "assessment_water_target": 2100,
                "scenario_standard_ordered_rate_ml_hr": 55,
            },
            formulas,
            modulars,
        )

        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)
        uploader = next(
            item for item in app.file_uploader if item.key == "case_record_upload"
        )
        uploader.upload(
            "saved-record.xlsx",
            workbook,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ).run(timeout=30)
        next(item for item in app.button if item.key == "load_case_record").click().run(
            timeout=30
        )

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["case_record_label"], "Imported test record")
        self.assertEqual(app.session_state["assessment_age"], 45)
        self.assertEqual(
            app.session_state["scenario_standard_ordered_rate_ml_hr"], 55
        )

    def test_invalid_saved_record_shows_an_error_without_crashing(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        uploader = next(
            item for item in app.file_uploader if item.key == "case_record_upload"
        )
        uploader.upload(
            "not-a-workbook.xlsx",
            b"This is not an Excel workbook.",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ).run(timeout=30)
        next(item for item in app.button if item.key == "load_case_record").click().run(
            timeout=30
        )

        self.assertFalse(app.exception)
        self.assertTrue(app.error)

    def test_sex_can_be_selected_before_height(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        sex = next(item for item in app.selectbox if item.key == "assessment_sex")
        sex.select("Female").run(timeout=30)
        self.assertFalse(app.exception)
        height = next(
            item for item in app.number_input
            if item.key == "assessment_height_cm_entry"
        )
        self.assertIsNone(height.value)

        sex = next(item for item in app.selectbox if item.key == "assessment_sex")
        sex.select("Male").run(timeout=30)
        self.assertFalse(app.exception)

    def test_one_entered_protein_bound_shows_a_worked_value(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        lower = next(item for item in app.number_input if item.key == "assessment_protein_low_gkg")
        upper = next(item for item in app.number_input if item.key == "assessment_protein_high_gkg")
        upper.set_value(None).run(timeout=30)
        lower = next(item for item in app.number_input if item.key == "assessment_protein_low_gkg")
        lower.set_value(1.2).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(any(
            "Calculated protein range" in item.value and "77 g/day" in item.value
            for item in app.markdown
        ))

    def test_activity_and_stress_factors_adjust_non_ventilator_equations(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        activity = next(
            item for item in app.number_input if item.key == "assessment_activity_factor"
        )
        stress = next(
            item for item in app.number_input if item.key == "assessment_stress_factor"
        )
        activity.set_value(1.10)
        stress.set_value(1.20).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn(
            "Activity/stress-adjusted<small>energy (kcal/day)</small>", rendered_html
        )
        self.assertIn(">1551<", rendered_html)

    def test_energy_table_includes_weight_based_and_measured_values(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        lower = next(
            item for item in app.number_input
            if item.key == "assessment_energy_low_kcal_kg"
        )
        lower.set_value(25).run(timeout=30)
        upper = next(
            item for item in app.number_input
            if item.key == "assessment_energy_high_kcal_kg"
        )
        upper.set_value(30).run(timeout=30)
        measured = next(
            item for item in app.number_input
            if item.key == "assessment_indirect_calorimetry"
        )
        measured.set_value(1650).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Energy calculations", rendered_html)
        self.assertIn("Weight-based range", rendered_html)
        self.assertIn("64.0 kg × 25–30 kcal/kg", rendered_html)
        self.assertIn("1600–1920", rendered_html)
        self.assertIn("Indirect calorimetry", rendered_html)
        self.assertIn("Measured value", rendered_html)
        self.assertNotIn(
            "Applied to Mifflin–St Jeor and Harris–Benedict only.",
            [item.value for item in app.caption],
        )

    def test_adjusted_weight_factor_is_identified_in_the_weight_table(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertNotIn("<th>Adjusted body-weight factor</th>", rendered_html)
        self.assertIn(
            '× <strong class="report-inline-emphasis">0.25</strong>', rendered_html
        )
        self.assertIn("Ideal body weight (Hamwi — SI units)", rendered_html)
        self.assertIn(
            "Ideal body weight (Devine — medication-dosing reference)", rendered_html
        )
        self.assertIn("Adjusted body weight (Hamwi IBW)", rendered_html)
        captions = [item.value for item in app.caption]
        self.assertNotIn(
            "Devine is shown as a medication-dosing reference only and is not available "
            "as an EN calculation weight.",
            captions,
        )

    def test_height_can_be_entered_in_feet_and_inches(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        unit = next(item for item in app.selectbox if item.key == "assessment_height_unit")
        unit.select("ft/in").run(timeout=30)
        feet = next(item for item in app.number_input if item.key == "assessment_height_feet")
        inches = next(item for item in app.number_input if item.key == "assessment_height_inches")
        feet.set_value(5)
        inches.set_value(6).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertAlmostEqual(app.session_state["assessment_height_cm"], 167.64)

    def test_height_does_not_revert_when_units_are_changed_twice(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        unit = next(
            item for item in app.selectbox if item.key == "assessment_height_unit"
        )
        unit.select("ft/in").run(timeout=30)
        next(
            item for item in app.number_input
            if item.key == "assessment_height_feet"
        ).set_value(5)
        next(
            item for item in app.number_input
            if item.key == "assessment_height_inches"
        ).set_value(6).run(timeout=30)

        next(
            item for item in app.selectbox if item.key == "assessment_height_unit"
        ).select("cm").run(timeout=30)
        next(
            item for item in app.number_input
            if item.key == "assessment_height_cm_entry"
        ).set_value(180).run(timeout=30)
        next(
            item for item in app.selectbox if item.key == "assessment_height_unit"
        ).select("ft/in").run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["assessment_height_feet"], 5)
        self.assertAlmostEqual(app.session_state["assessment_height_inches"], 10.9)
        self.assertEqual(app.session_state["assessment_height_cm"], 180)

    def test_weights_can_be_entered_in_pounds(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        unit = next(item for item in app.selectbox if item.key == "assessment_weight_unit")
        unit.select("lb").run(timeout=30)
        current = next(item for item in app.number_input if item.key == "assessment_current_weight_lb")
        usual = next(item for item in app.number_input if item.key == "assessment_usual_weight_lb")
        current.set_value(150.0)
        usual.set_value(160.0).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertAlmostEqual(app.session_state["assessment_current_weight"], 68.0388555)
        self.assertAlmostEqual(app.session_state["assessment_usual_weight"], 72.5747792)

    def test_weight_does_not_revert_when_units_are_changed_twice(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.selectbox if item.key == "assessment_weight_unit"
        ).select("lb").run(timeout=30)
        next(
            item for item in app.number_input
            if item.key == "assessment_current_weight_lb"
        ).set_value(150).run(timeout=30)

        next(
            item for item in app.selectbox if item.key == "assessment_weight_unit"
        ).select("kg").run(timeout=30)
        next(
            item for item in app.number_input
            if item.key == "assessment_current_weight_kg_entry"
        ).set_value(80).run(timeout=30)
        next(
            item for item in app.selectbox if item.key == "assessment_weight_unit"
        ).select("lb").run(timeout=30)

        self.assertFalse(app.exception)
        self.assertAlmostEqual(
            app.session_state["assessment_current_weight_lb"],
            80 / 0.45359237,
        )
        self.assertEqual(app.session_state["assessment_current_weight"], 80)

    def test_adjusting_a_plan_goal_updates_assessment_and_both_workflows(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        energy = next(
            item for item in app.number_input
            if item.key == "en_assessment_energy_goal_editor"
        )
        energy.set_value(1900).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["assessment_energy_target"], 1900)
        self.assertEqual(app.session_state["en_total_energy_target"], 1900)
        self.assertEqual(app.session_state["icu_total_energy_target"], 1900)
        self.assertEqual(
            app.session_state["icu_assessment_energy_goal_editor"], 1900
        )
        assessment_energy = next(
            item for item in app.number_input
            if item.key == "assessment_energy_target"
        )
        assessment_energy.set_value(1850).run(timeout=30)
        self.assertEqual(app.session_state["assessment_energy_target"], 1850)
        self.assertEqual(app.session_state["en_total_energy_target"], 1850)
        self.assertEqual(app.session_state["icu_total_energy_target"], 1850)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Goals from Assessment", rendered_html)

    def test_standard_and_icu_propofol_workflows_are_independent(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        tab_labels = [item.label for item in app.tabs]
        self.assertIn("EN plan", tab_labels)
        self.assertIn("Propofol", tab_labels)
        self.assertIn("Lower/no propofol", tab_labels)
        self.assertIn("Higher propofol", tab_labels)
        self.assertNotIn("Primary plan", tab_labels)
        self.assertNotIn("Alternate plan", tab_labels)
        self.assertIn("scenario_standard_schedule_type", {item.key for item in app.radio})
        self.assertEqual(app.session_state["scenario_standard_propofol_rate"], 0.0)
        self.assertEqual(app.session_state["icu_total_energy_target"], 1800.0)

        standard_hours = next(
            item for item in app.number_input if item.key == "scenario_standard_feeding_hours"
        )
        standard_hours.set_value(16).run(timeout=30)
        self.assertEqual(app.session_state["scenario_standard_feeding_hours"], 16)
        self.assertEqual(app.session_state["scenario_lower_feeding_hours"], 23.0)

        lower_schedule = next(
            item for item in app.radio if item.key == "scenario_lower_schedule_type"
        )
        lower_schedule.set_value("Intermittent").run(timeout=30)

        self.assertFalse(app.exception)
        number_input_keys = {item.key for item in app.number_input}
        self.assertIn("scenario_lower_feeds_per_day", number_input_keys)
        self.assertNotIn("scenario_lower_feeding_hours", number_input_keys)

    def test_copy_to_higher_propofol_keeps_the_higher_rate(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        lower_hours = next(
            item for item in app.number_input if item.key == "scenario_lower_feeding_hours"
        )
        lower_hours.set_value(18).run(timeout=30)
        lower_propofol_hours = next(
            item for item in app.number_input if item.key == "scenario_lower_propofol_hours"
        )
        higher_propofol_hours = next(
            item for item in app.number_input if item.key == "scenario_higher_propofol_hours"
        )
        lower_propofol_hours.set_value(12)
        higher_propofol_hours.set_value(18).run(timeout=30)
        copy_button = next(
            item for item in app.button
            if item.label == "Copy lower-propofol EN plan"
        )
        copy_button.click().run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_higher_feeding_hours"], 18)
        self.assertEqual(app.session_state["scenario_higher_propofol_rate"], 20.0)
        self.assertEqual(app.session_state["scenario_higher_propofol_hours"], 18)

    def test_higher_propofol_rate_stays_in_its_tab_and_drives_its_plan(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        higher_rate = next(
            item for item in app.number_input if item.key == "scenario_higher_propofol_rate"
        )
        higher_rate.set_value(None).run(timeout=30)

        number_input_keys = {item.key for item in app.number_input}
        self.assertIn("scenario_higher_propofol_rate", number_input_keys)
        self.assertIn("scenario_higher_propofol_hours", number_input_keys)
        self.assertNotIn("scenario_higher_feeding_hours", number_input_keys)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Energy from propofol", rendered_html)
        self.assertIn("Fat from propofol", rendered_html)
        self.assertIn(
            "Enter a higher propofol rate to calculate this plan.",
            [item.value for item in app.caption],
        )

        higher_rate = next(
            item for item in app.number_input if item.key == "scenario_higher_propofol_rate"
        )
        higher_rate.set_value(15.0).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertIn(
            "scenario_higher_feeding_hours", {item.key for item in app.number_input}
        )

    def test_propofol_plan_comparison_uses_full_orders_during_partial_review(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        achieved = next(
            item for item in app.number_input
            if item.key == "scenario_lower_achieved_delivery_pct"
        )
        achieved.set_value(50).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Estimated daily intake at 50% formula delivery", rendered_html)
        self.assertIn(
            '<th scope="row" class="">Total energy (kcal/day)</th>'
            '<td class="report-number">1775</td>'
            '<td class="report-number">1786</td>',
            rendered_html,
        )

    def test_formula_comparison_includes_the_full_electrolyte_profile(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        rendered_html = "\n".join(item.value for item in app.markdown)
        for heading in (
            "Na (mmol/day)",
            "K (mmol/day)",
            "Ca (mmol/day)",
            "P (mmol/day)",
            "Mg (mmol/day)",
        ):
            self.assertIn(heading, rendered_html)

    def test_planned_daily_intake_includes_electrolytes_and_structured_checks(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        rendered_html = "\n".join(item.value for item in app.markdown)
        for heading in (
            "Na (mmol)",
            "K (mmol)",
            "Ca (mmol)",
            "P (mmol)",
            "Mg (mmol)",
        ):
            self.assertIn(heading, rendered_html)
        plan_checks = [item for item in app.expander if item.label == "EN plan check"]
        self.assertTrue(plan_checks)
        self.assertTrue(all(not item.proto.expanded for item in plan_checks))
        self.assertNotIn("Final plan checks", rendered_html)
        self.assertIn("From feed", rendered_html)
        self.assertIn("From other sources", rendered_html)
        self.assertIn("Difference (planned − goal)", rendered_html)
        self.assertRegex(rendered_html, r">[+−]\d+<")
        self.assertNotIn("above goal", rendered_html)
        self.assertNotIn("below goal", rendered_html)
        self.assertIn("Recommended hydration flush schedule:", rendered_html)
        self.assertIn("Water from formula and modulars:", rendered_html)
        self.assertIn("Remaining before flushes:", rendered_html)
        self.assertIn('class="protein-gap protein-shortfall"', rendered_html)
        self.assertNotIn("Final EN order", rendered_html)
        self.assertNotIn("Review final rounded EN order", rendered_html)
        number_input_keys = {item.key for item in app.number_input}
        slider_keys = {item.key for item in app.slider}
        self.assertIn("scenario_standard_achieved_delivery_pct", number_input_keys)
        self.assertNotIn("scenario_standard_achieved_delivery_pct", slider_keys)
        self.assertNotIn(
            "Review or adjust the suggested EN rate",
            {item.label for item in app.expander},
        )

    def test_formulary_removal_controls_are_compact_popovers(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        self.assertFalse(app.exception)
        multiselect_keys = {item.key for item in app.multiselect}
        self.assertIn("remove_feeds", multiselect_keys)
        self.assertIn("remove_modulars", multiselect_keys)
        button_keys = {item.key for item in app.button}
        self.assertIn("remove_selected_feeds", button_keys)
        self.assertIn("remove_selected_modulars", button_keys)

    def test_clinical_tables_use_unit_appropriate_precision(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn(">1150<", rendered_html)
        self.assertIn(">1800<", rendered_html)
        self.assertIn(">881<", rendered_html)
        self.assertIn(">66.3<", rendered_html)
        self.assertNotIn(">1200.0<", rendered_html)
        self.assertNotIn(">1800.0<", rendered_html)
        self.assertNotIn(">880.9<", rendered_html)

    def test_q4h_hydration_is_independent_of_feeding_hours_and_charted_as_q4h(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(item for item in app.button if item.label == "📋 Load example record").click().run(timeout=30)

        feeding_hours = next(
            item for item in app.number_input
            if item.key == "scenario_standard_feeding_hours"
        )
        feeding_hours.set_value(12).run(timeout=30)
        frequency = next(
            item for item in app.selectbox
            if item.key == "scenario_standard_hydration_schedule_format"
        )
        frequency.select("qXh").run(timeout=30)
        interval = next(
            item for item in app.selectbox
            if item.key == "scenario_standard_hydration_interval_hours"
        )
        interval.select(4).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_feeding_hours"], 12)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Recommended hydration flush schedule:", rendered_html)
        self.assertRegex(rendered_html, r"<strong>\d+ mL q4h\.</strong>")
        chart_notes = "\n".join(item.value for item in app.code)
        self.assertRegex(chart_notes, r"Hydration flushes: \d+ mL q4h\.")

    def test_adding_formulary_products_preserves_the_existing_en_plan(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(item for item in app.button if item.label == "📋 Load example record").click().run(timeout=30)

        ordered_rate = next(
            item for item in app.number_input
            if item.key == "scenario_standard_ordered_rate_ml_hr"
        )
        ordered_rate.set_value(55).run(timeout=30)
        expected_state = {
            "energy": app.session_state["en_total_energy_target"],
            "protein": app.session_state["en_protein_target"],
            "water": app.session_state["en_water_target"],
            "candidates": list(app.session_state["feed_candidates"]),
            "formula": app.session_state["scenario_standard_selected_formula"],
            "schedule": app.session_state["scenario_standard_schedule_type"],
            "hours": app.session_state["scenario_standard_feeding_hours"],
            "rate": app.session_state["scenario_standard_ordered_rate_ml_hr"],
            "modulars": list(app.session_state["scenario_standard_chosen_modulars"]),
            "beneprotein_doses": app.session_state[
                "scenario_standard_modular_doses_nestle-beneprotein"
            ],
        }

        next(item for item in app.button if item.key == "add_feed_Nepro").click().run(timeout=30)
        next(item for item in app.button if item.key == "add_modular_MCT Oil").click().run(timeout=30)

        self.assertFalse(app.exception)
        self.assertIn("Nepro", app.session_state.my_formulas["name"].tolist())
        self.assertIn("MCT Oil", app.session_state.my_modulars["name"].tolist())
        self.assertEqual(app.session_state["en_total_energy_target"], expected_state["energy"])
        self.assertEqual(app.session_state["en_protein_target"], expected_state["protein"])
        self.assertEqual(app.session_state["en_water_target"], expected_state["water"])
        self.assertEqual(list(app.session_state["feed_candidates"]), expected_state["candidates"])
        self.assertEqual(app.session_state["scenario_standard_selected_formula"], expected_state["formula"])
        self.assertEqual(app.session_state["scenario_standard_schedule_type"], expected_state["schedule"])
        self.assertEqual(app.session_state["scenario_standard_feeding_hours"], expected_state["hours"])
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], expected_state["rate"])
        self.assertEqual(
            list(app.session_state["scenario_standard_chosen_modulars"]),
            expected_state["modulars"],
        )
        self.assertEqual(
            app.session_state["scenario_standard_modular_doses_nestle-beneprotein"],
            expected_state["beneprotein_doses"],
        )

    def test_entered_standard_rate_drives_the_planned_intake(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        ordered_rate = next(
            item for item in app.number_input
            if item.key == "scenario_standard_ordered_rate_ml_hr"
        )
        ordered_rate.set_value(55).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 55)
        self.assertTrue(app.session_state["scenario_standard_order_user_edited"])
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Energy (kcal/day)", rendered_html)
        self.assertIn(">1898<", rendered_html)
        self.assertIn("Difference (planned − goal)", rendered_html)
        self.assertIn("<strong>1265 mL</strong> formula/day", rendered_html)
        self.assertIn("<strong>1948 kcal/day</strong> total", rendered_html)
        self.assertIn(
            "Selected EN feed: <strong>89 g/day</strong>", rendered_html
        )

        reset = next(
            item for item in app.button
            if item.key == "scenario_standard_use_suggested_order"
        )
        reset.click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 50)
        self.assertFalse(app.session_state["scenario_standard_order_user_edited"])

    def test_unedited_order_follows_a_recalculated_suggestion(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        target = next(
            item for item in app.number_input
            if item.key == "en_assessment_energy_goal_editor"
        )
        target.set_value(1600).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 45)
        self.assertFalse(app.session_state["scenario_standard_order_user_edited"])

    def test_modular_energy_does_not_silently_reduce_the_standard_rate(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(item for item in app.button if item.label == "📋 Load example record").click().run(timeout=30)

        doses = next(
            item for item in app.number_input
            if item.key == "scenario_standard_modular_doses_nestle-beneprotein"
        )
        doses.set_value(4).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 50)
        self.assertFalse(app.session_state["scenario_standard_order_user_edited"])

    def test_modular_energy_does_not_silently_reduce_a_propofol_rate(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(item for item in app.button if item.label == "📋 Load example record").click().run(timeout=30)

        doses = next(
            item for item in app.number_input
            if item.key == "scenario_higher_modular_doses_nestle-beneprotein"
        )
        doses.set_value(6).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_higher_ordered_rate_ml_hr"], 35)
        self.assertFalse(app.session_state["scenario_higher_order_user_edited"])

    def test_reduced_delivery_review_keeps_the_order_and_explains_the_view(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(item for item in app.button if item.label == "📋 Load example record").click().run(timeout=30)

        achieved = next(
            item for item in app.number_input
            if item.key == "scenario_standard_achieved_delivery_pct"
        )
        achieved.set_value(50).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 50)
        self.assertEqual(
            app.session_state["scenario_standard_delivery_view"], "Achieved delivery"
        )
        rendered_html = "\n".join(item.value for item in app.markdown)
        planned_order = (
            "Full planned formula order (100%): Isosource Fibre 1.5 at "
            "50 mL/hour for 23 hours daily."
        )
        partial_notice = (
            "Showing estimated intake at <strong>50% formula delivery</strong>. "
            "Modulars and flushes remain unchanged."
        )
        self.assertIn(planned_order, rendered_html)
        self.assertIn(
            partial_notice,
            rendered_html,
        )
        self.assertLess(
            rendered_html.index(planned_order), rendered_html.index(partial_notice)
        )
        plan_checks = [item for item in app.expander if item.label == "EN plan check"]
        self.assertTrue(plan_checks)
        self.assertTrue(any(item.proto.expanded for item in plan_checks))
        self.assertIn("Estimated total", rendered_html)
        self.assertIn("Difference (estimated − goal)", rendered_html)
        self.assertIn("Estimated daily intake at 50% formula delivery", rendered_html)
        self.assertIn(">1460<", rendered_html)

    def test_modular_preparation_water_is_included_in_the_water_summary(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(item for item in app.button if item.label == "📋 Load example record").click().run(timeout=30)

        preparation_water = next(
            item for item in app.number_input
            if item.key == "scenario_standard_modular_water_nestle-beneprotein"
        )
        preparation_water.set_value(60).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn(
            "Water from formula and modulars: <strong>1001 mL/day</strong>",
            rendered_html,
        )
        self.assertIn(
            "Recommended hydration flush schedule: <strong>100 mL 6 times daily.</strong>",
            rendered_html,
        )
        self.assertIn(
            "120 mL from modular preparation water; 900 mL from water flushes",
            rendered_html,
        )

    def test_liquid_modular_water_is_not_reported_as_feed_water(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(item for item in app.button if item.label == "📋 Load example record").click().run(timeout=30)
        next(
            item for item in app.button
            if item.key == "add_modular_LiquiProtein"
        ).click().run(timeout=30)

        modulars = next(
            item for item in app.multiselect
            if item.key == "scenario_standard_chosen_modulars"
        )
        modulars.set_value(["Beneprotein", "LiquiProtein"]).run(timeout=30)
        self.assertIsNone(
            app.session_state["scenario_standard_modular_units_abbott-liquiprotein"]
        )
        self.assertIsNone(
            app.session_state["scenario_standard_modular_doses_abbott-liquiprotein"]
        )
        rendered_html = "\n".join(item.value for item in app.markdown)
        chart_notes = "\n".join(item.value for item in app.code)
        self.assertNotIn("5 mL from modulars", rendered_html)
        self.assertNotIn("LiquiProtein", chart_notes)

        liquid_modular_amount = next(
            item for item in app.number_input
            if item.key == "scenario_standard_modular_units_abbott-liquiprotein"
        )
        liquid_modular_amount.set_value(6).run(timeout=30)
        rendered_html = "\n".join(item.value for item in app.markdown)
        chart_notes = "\n".join(item.value for item in app.code)
        self.assertNotIn("5 mL from modulars", rendered_html)
        self.assertNotIn("LiquiProtein", chart_notes)

        liquid_modular_frequency = next(
            item for item in app.number_input
            if item.key == "scenario_standard_modular_doses_abbott-liquiprotein"
        )
        liquid_modular_frequency.set_value(1).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("5 mL from modulars", rendered_html)
        self.assertIn(">881<", rendered_html)

    def test_example_rates_and_modular_totals_use_the_regular_calculations(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        formula = load_master_formulas().loc[
            lambda frame: frame["name"] == "Isosource Fibre 1.5"
        ].iloc[0].to_dict()
        modular = load_master_modulars().loc[
            lambda frame: frame["id"] == "nestle-beneprotein"
        ].iloc[0].to_dict()
        standard = practical_feed_delivery(
            formula,
            app.session_state["en_total_energy_target"],
            app.session_state["scenario_standard_feeding_hours"],
        )
        propofol = propofol_intake(
            app.session_state["scenario_higher_propofol_rate"],
            app.session_state["scenario_higher_propofol_hours"],
        )
        higher = practical_feed_delivery(
            formula,
            app.session_state["icu_total_energy_target"] - propofol["kcal"],
            app.session_state["scenario_higher_feeding_hours"],
        )
        modular_totals = modular_delivery(modular, 1, 2, 60)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_feeding_hours"], 23)
        self.assertEqual(
            app.session_state["scenario_standard_ordered_rate_ml_hr"],
            standard["ordered_rate_ml_hr"],
        )
        self.assertEqual(
            app.session_state["scenario_lower_ordered_rate_ml_hr"],
            standard["ordered_rate_ml_hr"],
        )
        self.assertEqual(
            app.session_state["scenario_higher_ordered_rate_ml_hr"],
            higher["ordered_rate_ml_hr"],
        )
        self.assertFalse(app.session_state["scenario_standard_order_user_edited"])
        self.assertFalse(app.session_state["scenario_lower_order_user_edited"])
        self.assertFalse(app.session_state["scenario_higher_order_user_edited"])
        self.assertEqual(modular_totals["energy_kcal"], 50)
        self.assertEqual(modular_totals["protein_g"], 12)
        self.assertEqual(modular_totals["preparation_water_ml"], 120)

    def test_chart_note_uses_per_administration_modular_frequency(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(item for item in app.button if item.label == "📋 Load example record").click().run(timeout=30)

        self.assertFalse(app.exception)
        chart_notes = "\n".join(item.value for item in app.code)
        self.assertIn("Modulars: Beneprotein 1 packet BID.", chart_notes)
        self.assertNotIn("Modulars: Beneprotein:", chart_notes)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("2 packets daily", rendered_html)


if __name__ == "__main__":
    unittest.main()
