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
    def test_modular_library_lists_all_products_without_a_manufacturer_filter(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        self.assertNotIn(
            "modular_reference_brand_filter",
            {item.key for item in app.radio},
        )
        modular_button_keys = {
            item.key for item in app.button
            if str(item.key).startswith(("add_modular_", "saved_modular_"))
        }
        self.assertEqual(len(modular_button_keys), 7)
        self.assertIn(
            "Scroll to view more feeds.",
            {item.value for item in app.caption},
        )
        ons_button_keys = {
            item.key for item in app.button
            if str(item.key).startswith(("add_ons_", "saved_ons_"))
        }
        self.assertEqual(len(ons_button_keys), 54)
        ons_filter = next(
            item for item in app.radio
            if item.key == "ons_reference_brand_filter"
        )
        self.assertEqual(
            ons_filter.options,
            ["All products", "Nestlé ONS", "Abbott ONS"],
        )
        product_filter = next(
            item for item in app.selectbox
            if item.key == "feed_reference_product_filter"
        )
        self.assertEqual(
            product_filter.options,
            [
                "All products",
                "Nestlé EN formulas",
                "Abbott EN formulas",
                "Nestlé ONS",
                "Abbott ONS",
            ],
        )
        subheadings = [item.value for item in app.subheader]
        self.assertLess(
            subheadings.index("My Formulary"), subheadings.index("My Modulars")
        )
        self.assertLess(
            subheadings.index("My Modulars"), subheadings.index("My ONS")
        )

    def test_modular_plan_card_uses_compact_parallel_labels(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        multiselect_labels = {item.label for item in app.multiselect}
        captions = {item.value for item in app.caption}
        self.assertIn("Modulars", multiselect_labels)
        self.assertNotIn("Modular orders (up to 6)", multiselect_labels)
        self.assertNotIn(
            "Enter the modular order. This calculator does not recommend doses.",
            captions,
        )
        self.assertIn(
            "Missing a modular? Add it to My Modulars on the Formulary tab.",
            captions,
        )
        self.assertIn(
            "Missing a feed? Add it to My Formulary on the Formulary tab.",
            captions,
        )
        self.assertNotIn("How ONS calculations work", {
            item.label for item in app.expander
        })
        # These two sit in a caption, and AppTest reports caption text as the
        # markdown source rather than rendered HTML.
        ons_guidance = "\n".join(captions)
        self.assertIn("**For tube feeding, use My Formulary.**", ons_guidance)
        self.assertIn("**For oral intake, use My ONS.**", ons_guidance)

    def test_assessment_footer_navigation_controls_the_active_tab(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        next(
            item for item in app.button
            if item.key == "workspace_nav_assessment_en_plan"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "EN plan")

        next(
            item for item in app.button
            if item.key == "workspace_nav_assessment_propofol"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "Propofol")

        next(
            item for item in app.button
            if item.key == "workspace_nav_assessment_formulary"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "Formulary")

    def test_formulary_footer_navigation_controls_the_active_tab(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        next(
            item for item in app.button
            if item.key == "workspace_nav_formulary_assessment"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "Assessment")

        next(
            item for item in app.button
            if item.key == "workspace_nav_formulary_en_plan"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "EN plan")

        next(
            item for item in app.button
            if item.key == "workspace_nav_formulary_propofol"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "Propofol")

    def test_plan_and_propofol_have_footer_navigation(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        next(
            item for item in app.button
            if item.key == "workspace_nav_en_plan_propofol"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "Propofol")

        next(
            item for item in app.button
            if item.key == "workspace_nav_propofol_en_plan"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "EN plan")

    def test_header_uses_a_text_link_and_separates_identity_from_workflow(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        self.assertFalse(app.exception)
        captions = "\n".join(item.value for item in app.caption)
        self.assertIn(
            "Adult Inpatient Enteral Nutrition Calculator, a [Feed. Form. Flow.]",
            captions,
        )
        self.assertIn(
            "Uses Canadian formula, modular, and ONS product information.", captions
        )
        self.assertIn("Work left to right: set up My Formulary", captions)
        self.assertNotIn("First time here?", captions)
        self.assertNotIn("substack logo", captions.lower())

    def test_footer_includes_platform_neutral_browser_zoom_guidance(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        self.assertFalse(app.exception)
        footer_text = "\n".join(item.value for item in app.caption)
        expander_labels = {item.label for item in app.expander}
        self.assertIn("About this calculator", expander_labels)
        self.assertIn("Review calculations before clinical use.", footer_text)
        self.assertIn(
            "[BTFCalc](https://btfcalc.feedformflow.ca) — blenderized tube feeding calculator.",
            footer_text,
        )
        self.assertNotIn("Under development", footer_text)
        self.assertIn(
            "Formula, modular, and ONS values come from manufacturers’ Canadian product information.",
            footer_text,
        )
        self.assertIn("Display tip:", footer_text)
        self.assertIn("Ctrl +/−", footer_text)
        self.assertIn("⌘ +/−", footer_text)
        self.assertIn("pinch on touchscreens and trackpads", footer_text)

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
            "Calculated protein requirement range" in item.value and "77 g/day" in item.value
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
        self.assertIn("Energy requirement calculations", rendered_html)
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
        # Only the Hamwi row carries the IBW acronym: it is the ideal weight the
        # calculator actually uses, and Devine is shown for medication dosing.
        self.assertIn("Ideal body weight (IBW) — Hamwi, SI units", rendered_html)
        self.assertIn(
            "Ideal body weight — Devine, medication-dosing reference", rendered_html
        )
        self.assertIn("Current body weight (CBW)", rendered_html)
        self.assertIn("Adjusted body weight (AdjBW) — from Hamwi IBW", rendered_html)
        self.assertIn("Adjusted body weight (AdjBW) — from Hamwi IBW", rendered_html)
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
        self.assertNotIn("Lower/no propofol", tab_labels)
        self.assertNotIn("Higher propofol", tab_labels)
        self.assertIn("scenario_standard_schedule_type", {item.key for item in app.radio})
        self.assertIn("scenario_propofol_schedule_type", {item.key for item in app.radio})
        self.assertEqual(app.session_state["scenario_standard_propofol_rate"], 0.0)
        self.assertEqual(app.session_state["icu_total_energy_target"], 1800.0)

        standard_hours = next(
            item for item in app.number_input if item.key == "scenario_standard_feeding_hours"
        )
        standard_hours.set_value(16).run(timeout=30)
        self.assertEqual(app.session_state["scenario_standard_feeding_hours"], 16)
        self.assertEqual(app.session_state["scenario_propofol_feeding_hours"], 23.0)

        propofol_schedule = next(
            item for item in app.radio if item.key == "scenario_propofol_schedule_type"
        )
        propofol_schedule.set_value("Intermittent").run(timeout=30)

        self.assertFalse(app.exception)
        number_input_keys = {item.key for item in app.number_input}
        self.assertIn("scenario_propofol_feeds_per_day", number_input_keys)
        self.assertNotIn("scenario_propofol_feeding_hours", number_input_keys)

    def test_propofol_help_copy_explains_each_method_concisely(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn(
            "subtracts projected Propofol energy from the EN energy target",
            rendered_html,
        )
        self.assertIn(
            "The calculator provides two suggested EN rates. It uses the expected "
            "durations to calculate planned daily formula volume and protein provision.",
            rendered_html,
        )
        self.assertIn(
            "If feeding time is less than 24 hours/day, it is distributed "
            "proportionally according to the expected hours at each Propofol rate.",
            rendered_html,
        )
        self.assertNotIn("for each condition", rendered_html)
        self.assertNotIn(
            "shortens the time assigned to both conditions",
            rendered_html,
        )

    def test_conditional_propofol_mode_uses_one_shared_en_plan(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        method = next(
            item for item in app.radio
            if item.key == "scenario_propofol_propofol_method"
        )
        method.set_value("Changing Propofol rates").run(timeout=30)

        self.assertFalse(app.exception)
        number_input_keys = {item.key for item in app.number_input}
        self.assertIn(
            "_propofol_widget_scenario_propofol_lower_propofol_rate",
            number_input_keys,
        )
        self.assertIn(
            "_propofol_widget_scenario_propofol_higher_propofol_rate",
            number_input_keys,
        )
        self.assertIn(
            "_propofol_widget_scenario_propofol_conditional_lower_rate_ml_hr",
            number_input_keys,
        )
        self.assertIn(
            "_propofol_widget_scenario_propofol_conditional_higher_rate_ml_hr",
            number_input_keys,
        )
        self.assertEqual(app.session_state["scenario_propofol_conditional_lower_rate_ml_hr"], 50)
        self.assertEqual(app.session_state["scenario_propofol_conditional_higher_rate_ml_hr"], 35)
        self.assertEqual(
            [item.key for item in app.selectbox].count("scenario_propofol_selected_formula"), 1
        )
        chart_note = app.session_state["_chart_note_generated_propofol"]
        self.assertIn(
            "When Propofol is not running, provide feed at 50 mL/hr.", chart_note
        )
        self.assertIn(
            "When Propofol is at 20 mL/hr, provide feed at 35 mL/hr.", chart_note
        )
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn(
            "Suggested EN rate with lower/no Propofol (mL/hour)", rendered_html
        )
        self.assertIn(
            "Suggested EN rate with higher Propofol (mL/hour)", rendered_html
        )
        self.assertIn(
            "Projected formula delivery: (50 mL/hour × 17.25 hours) + "
            "(35 mL/hour × 5.75 hours) = <strong>1,064 mL/day</strong>.",
            rendered_html,
        )

    def test_propofol_prescription_target_is_applied_before_propofol_energy(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        target = next(
            item for item in app.number_input
            if item.key == "scenario_propofol_prescription_target_pct"
        )
        target.set_value(110).run(timeout=30)

        self.assertFalse(app.exception)
        # 1800 × 110% = 1980 kcal; after 528 kcal from Propofol, a 1.5-kcal/mL
        # formula over 23 hours rounds to 40 mL/hour.
        self.assertEqual(app.session_state["scenario_propofol_ordered_rate_ml_hr"], 40)
        self.assertIn(
            "EN prescription target: 110% of estimated energy requirement "
            "(1,980 kcal/day).",
            app.session_state["_chart_note_generated_propofol"],
        )
        rationale = next(
            item for item in app.checkbox
            if item.key == "scenario_propofol_prescription_interruption_note"
        )
        self.assertFalse(rationale.value)
        self.assertEqual(
            rationale.label,
            'Include “to account for anticipated interruptions” in the '
            '**Chart note below**',
        )
        rationale.set_value(True).run(timeout=30)
        self.assertIn(
            "EN prescription target: 110% of estimated energy requirement "
            "(1,980 kcal/day) to account for anticipated interruptions.",
            app.session_state["_chart_note_generated_propofol"],
        )

    def test_standard_en_plan_has_an_independent_prescription_target(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        target = next(
            item for item in app.number_input
            if item.key == "scenario_standard_prescription_target_pct"
        )
        target.set_value(110).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 55)
        self.assertEqual(
            app.session_state["scenario_propofol_prescription_target_pct"], 100
        )
        rationale = next(
            item for item in app.checkbox
            if item.key == "scenario_standard_prescription_interruption_note"
        )
        self.assertFalse(rationale.value)
        self.assertIn(
            "EN prescription target: 110% of estimated energy requirement "
            "(1,980 kcal/day).",
            app.session_state["_chart_note_generated_en_plan"],
        )

    def test_projected_propofol_rate_and_hours_drive_the_shared_plan(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(item for item in app.button if item.label == "📋 Load example record")
        example.click().run(timeout=30)

        rate = next(
            item for item in app.number_input
            if item.label == "Propofol rate (mL/hour)"
        )
        hours = next(
            item for item in app.number_input if item.label == "Expected hours"
        )
        rate.set_value(15.0)
        hours.set_value(12.0).run(timeout=30)
        self.assertFalse(app.exception)
        chart_note = app.session_state["_chart_note_generated_propofol"]
        self.assertIn(
            "With projected Propofol at 15 mL/hr for 12 hours/day:",
            chart_note,
        )
        self.assertIn("Propofol 198 kcal", chart_note)
        self.assertNotIn("Propofol 528 kcal", chart_note)

    def test_propofol_values_remain_visible_when_switching_methods(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        method = next(
            item for item in app.radio
            if item.key == "scenario_propofol_propofol_method"
        )
        method.set_value("Changing Propofol rates").run(timeout=30)
        higher_rate = next(
            item for item in app.number_input
            if item.key == "_propofol_widget_scenario_propofol_higher_propofol_rate"
        )
        higher_hours = next(
            item for item in app.number_input
            if item.label == "Expected duration (hours/day)"
        )
        self.assertEqual(higher_rate.value, 20)
        self.assertEqual(higher_hours.value, 6)

        method = next(
            item for item in app.radio
            if item.key == "scenario_propofol_propofol_method"
        )
        method.set_value("Single Propofol rate").run(timeout=30)
        daily_rate = next(
            item for item in app.number_input
            if item.label == "Propofol rate (mL/hour)"
        )
        daily_hours = next(
            item for item in app.number_input if item.label == "Expected hours"
        )
        self.assertEqual(daily_rate.value, 20)
        self.assertEqual(daily_hours.value, 24)

    def test_propofol_partial_delivery_review_uses_the_shared_plan(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        achieved = next(
            item for item in app.number_input
            if item.key == "scenario_propofol_achieved_delivery_pct"
        )
        achieved.set_value(50).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Estimated daily intake at 50% formula delivery", rendered_html)

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
        self.assertIn("Calculated hydration flush schedule:", rendered_html)
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
        self.assertIn(">880<", rendered_html)
        self.assertIn(">65.0<", rendered_html)
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
        self.assertIn("Calculated hydration flush schedule:", rendered_html)
        self.assertRegex(rendered_html, r"<strong>\d+ mL q4h\.</strong>")
        chart_note = app.session_state["_chart_note_generated_en_plan"]
        self.assertRegex(
            chart_note,
            r"Hydration: Provide \d+ mL water flushes q4h\.",
        )

    def test_patency_flush_change_updates_generated_chart_note(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        before = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn("Hydration flushes 130 mL q4h", before)
        self.assertNotIn("Patency flushes", before)

        patency = next(
            item for item in app.number_input
            if item.key == "scenario_standard_patency_flushes"
        )
        patency.set_value(120).run(timeout=30)

        self.assertFalse(app.exception)
        after = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn("Patency flushes 120 mL", after)
        self.assertIn("Hydration flushes 110 mL q4h", after)
        self.assertNotIn("Hydration flushes 130 mL q4h", after)

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
        self.assertIn(
            "Selected EN feed: <strong>86 g/day</strong>", rendered_html
        )

        reset = next(
            item for item in app.button
            if item.key == "scenario_standard_use_suggested_order"
        )
        reset.click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 50)
        self.assertFalse(app.session_state["scenario_standard_order_user_edited"])
        self.assertFalse(app.session_state["scenario_standard_order_user_edited"])

    def test_low_continuous_rate_can_be_described_as_trickle_in_chart_note(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        ordered_rate = next(
            item for item in app.number_input
            if item.key == "scenario_standard_ordered_rate_ml_hr"
        )
        ordered_rate.set_value(20).run(timeout=30)

        trickle = next(
            item for item in app.checkbox
            if item.key == "scenario_standard_describe_as_trickle"
        )
        trickle.check().run(timeout=30)

        self.assertFalse(app.exception)
        self.assertIn(
            "Initiate trickle EN with Isosource 1.5 at 20 mL/hour for "
            "23 hours daily.",
            app.session_state["_chart_note_generated_en_plan"],
        )

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
        chart_note = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn(
            "Enteral nutrition plan: Isosource 1.5 at 45 mL/hour for "
            "23 hours daily.",
            chart_note,
        )
        self.assertNotIn(
            "Enteral nutrition plan: Isosource 1.5 at 50 mL/hour for "
            "23 hours daily.",
            chart_note,
        )

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

    def test_ons_order_does_not_change_the_suggested_en_rate(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        suggested_rate = app.session_state[
            "scenario_standard_ordered_rate_ml_hr"
        ]
        ons = next(
            item for item in app.multiselect
            if item.key == "scenario_standard_chosen_ons"
        )
        ons.set_value(["BOOST Plus Calories — Vanilla"]).run(timeout=30)
        next(
            item for item in app.number_input
            if item.key == (
                "scenario_standard_ons_containers_"
                "nestle-boost-plus-calories-vanilla"
            )
        ).set_value(1).run(timeout=30)
        next(
            item for item in app.number_input
            if item.key == (
                "scenario_standard_ons_times_"
                "nestle-boost-plus-calories-vanilla"
            )
        ).set_value(2).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(
            app.session_state["scenario_standard_ordered_rate_ml_hr"],
            suggested_rate,
        )
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Planned EN and ONS provision", rendered_html)
        self.assertIn("Combined EN + ONS", rendered_html)
        self.assertIn(
            "Free water from ONS is included in daily totals but excluded "
            "from water-flush calculations.",
            {item.value for item in app.caption},
        )
        chart_note = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn(
            "ONS: BOOST Plus Calories — Vanilla, 1 carton BID.", chart_note
        )
        self.assertIn("At goal, EN and ONS orders provide", chart_note)
        self.assertIn("(EN 1,775 kcal + ONS 720 kcal)", chart_note)
        self.assertIn("Total water provided is 2,266 mL/day", chart_note)
        self.assertIn("ONS water 366 mL", chart_note)
        self.assertIn(
            "Hydration: Provide 130 mL water flushes q4h.", chart_note
        )
        self.assertFalse(app.session_state["scenario_standard_order_user_edited"])

    def test_ons_selected_as_formula_is_treated_as_en(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        candidates = next(
            item for item in app.multiselect if item.key == "feed_candidates"
        )
        self.assertNotIn("BOOST Plus Calories — Vanilla", candidates.options)
        self.assertNotIn("BOOST Pudding — Vanilla", candidates.options)
        next(
            item for item in app.button
            if item.key == "add_feed_BOOST Plus Calories — Vanilla"
        ).click().run(timeout=30)
        candidates = next(
            item for item in app.multiselect if item.key == "feed_candidates"
        )
        self.assertIn("BOOST Plus Calories — Vanilla", candidates.options)
        candidates.set_value(["BOOST Plus Calories — Vanilla"]).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(
            app.session_state["scenario_standard_selected_formula"],
            "BOOST Plus Calories — Vanilla",
        )
        chart_note = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn(
            "Enteral nutrition plan: BOOST Plus Calories — Vanilla", chart_note
        )
        self.assertNotIn("ONS: BOOST Plus Calories — Vanilla", chart_note)
        self.assertNotIn("EN and ONS orders provide", chart_note)

    def test_modular_energy_does_not_silently_reduce_a_propofol_rate(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(item for item in app.button if item.label == "📋 Load example record").click().run(timeout=30)

        doses = next(
            item for item in app.number_input
            if item.key == "scenario_propofol_modular_doses_nestle-beneprotein"
        )
        doses.set_value(6).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_propofol_ordered_rate_ml_hr"], 35)
        self.assertFalse(app.session_state["scenario_propofol_order_user_edited"])

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
            "Full planned formula order (100%): Isosource 1.5 at "
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
            "Water from formula and modulars: <strong>1000 mL/day</strong>",
            rendered_html,
        )
        self.assertIn(
            "Calculated hydration flush schedule: <strong>130 mL q4h.</strong>",
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
        chart_notes = app.session_state["_chart_note_generated_en_plan"]
        self.assertNotIn("5 mL from modulars", rendered_html)
        self.assertNotIn("LiquiProtein", chart_notes)

        liquid_modular_amount = next(
            item for item in app.number_input
            if item.key == "scenario_standard_modular_units_abbott-liquiprotein"
        )
        liquid_modular_amount.set_value(6).run(timeout=30)
        rendered_html = "\n".join(item.value for item in app.markdown)
        chart_notes = app.session_state["_chart_note_generated_en_plan"]
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
        self.assertIn(">885<", rendered_html)

    def test_example_rates_and_modular_totals_use_the_regular_calculations(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        standard_formula = load_master_formulas().loc[
            lambda frame: frame["name"] == "Isosource 1.5"
        ].iloc[0].to_dict()
        propofol_formula = load_master_formulas().loc[
            lambda frame: frame["name"] == "Peptamen 1.5"
        ].iloc[0].to_dict()
        modular = load_master_modulars().loc[
            lambda frame: frame["id"] == "nestle-beneprotein"
        ].iloc[0].to_dict()
        standard = practical_feed_delivery(
            standard_formula,
            app.session_state["en_total_energy_target"],
            app.session_state["scenario_standard_feeding_hours"],
        )
        propofol = propofol_intake(
            app.session_state["scenario_propofol_propofol_rate"],
            app.session_state["scenario_propofol_propofol_hours"],
        )
        higher = practical_feed_delivery(
            propofol_formula,
            app.session_state["icu_total_energy_target"] - propofol["kcal"],
            app.session_state["scenario_propofol_feeding_hours"],
        )
        modular_totals = modular_delivery(modular, 1, 2, 60)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_feeding_hours"], 23)
        self.assertEqual(
            app.session_state["scenario_standard_ordered_rate_ml_hr"],
            standard["ordered_rate_ml_hr"],
        )
        self.assertEqual(
            app.session_state["scenario_propofol_ordered_rate_ml_hr"],
            higher["ordered_rate_ml_hr"],
        )
        self.assertFalse(app.session_state["scenario_standard_order_user_edited"])
        self.assertFalse(app.session_state["scenario_propofol_order_user_edited"])
        self.assertEqual(modular_totals["energy_kcal"], 50)
        self.assertEqual(modular_totals["protein_g"], 12)
        self.assertEqual(modular_totals["preparation_water_ml"], 120)

    def test_example_chart_notes_match_independent_hand_calculations(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        standard_note = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn(
            "energy 1,775 kcal (Formula 1,725 kcal + Beneprotein 50 kcal)",
            standard_note,
        )
        self.assertIn(
            "protein 90 g (Formula 78 g + Beneprotein 12 g), CHO 202 g, and fat 69 g",
            standard_note,
        )
        self.assertIn(
            "Total water provided is 1,900 mL/day (Free water 880 mL + "
            "Beneprotein flushes 120 mL + Med flushes 120 mL + "
            "Hydration flushes 130 mL q4h)",
            standard_note,
        )

        propofol_note = app.session_state["_chart_note_generated_propofol"]
        self.assertIn(
            "With projected Propofol at 20 mL/hr for 24 hours/day",
            propofol_note,
        )
        self.assertIn(
            "energy 1,786 kcal (Formula 1,208 kcal + Beneprotein 50 kcal + "
            "Propofol 528 kcal)",
            propofol_note,
        )
        self.assertIn(
            "protein 67 g (Formula 55 g + Beneprotein 12 g), CHO 151 g, and "
            "fat 93 g (Formula 45 g + Propofol 48 g)",
            propofol_note,
        )
        self.assertIn(
            "Total water provided is 1,910 mL/day (Free water 620 mL + "
            "Beneprotein flushes 120 mL + Med flushes 120 mL + "
            "Hydration flushes 175 mL q4h)",
            propofol_note,
        )

    def test_chart_note_uses_per_administration_modular_frequency(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(item for item in app.button if item.label == "📋 Load example record").click().run(timeout=30)

        self.assertFalse(app.exception)
        chart_notes = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn(
            "Modulars: Beneprotein 1 packet BID, administered with 60 mL water each time.",
            chart_notes,
        )
        self.assertNotIn("Modulars: Beneprotein:", chart_notes)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("2 packets daily", rendered_html)


if __name__ == "__main__":
    unittest.main()
