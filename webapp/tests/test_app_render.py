import re
import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculations import modular_delivery, practical_feed_delivery, propofol_intake
from case_io import export_case_record_workbook
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
            item.key
            for item in app.button
            if str(item.key).startswith(("add_modular_", "saved_modular_"))
        }
        self.assertEqual(len(modular_button_keys), 7)
        self.assertIn(
            "Scroll to view more feeds.",
            {item.value for item in app.caption},
        )
        ons_button_keys = {
            item.key
            for item in app.button
            if str(item.key).startswith(("add_ons_", "saved_ons_"))
        }
        self.assertEqual(len(ons_button_keys), 54)
        ons_filter = next(
            item for item in app.radio if item.key == "ons_reference_brand_filter"
        )
        self.assertEqual(
            ons_filter.options,
            ["All products", "Nestlé ONS", "Abbott ONS"],
        )
        product_filter = next(
            item
            for item in app.selectbox
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
        self.assertLess(subheadings.index("My Modulars"), subheadings.index("My ONS"))

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
        self.assertNotIn(
            "How ONS calculations work", {item.label for item in app.expander}
        )
        # These two sit in a caption, and AppTest reports caption text as the
        # markdown source rather than rendered HTML.
        ons_guidance = "\n".join(captions)
        self.assertIn("**For tube feeding, use My Formulary.**", ons_guidance)
        self.assertIn("**For oral intake, use My ONS.**", ons_guidance)

    def test_assessment_footer_navigation_controls_the_active_tab(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        next(
            item
            for item in app.button
            if item.key == "workspace_nav_assessment_en_plan"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "EN plan")

        next(
            item
            for item in app.button
            if item.key == "workspace_nav_assessment_propofol"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "Propofol")

        next(
            item
            for item in app.button
            if item.key == "workspace_nav_assessment_formulary"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "Formulary")

    def test_formulary_footer_navigation_controls_the_active_tab(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        next(
            item
            for item in app.button
            if item.key == "workspace_nav_formulary_assessment"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "Assessment")

        next(
            item for item in app.button if item.key == "workspace_nav_formulary_en_plan"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "EN plan")

        next(
            item
            for item in app.button
            if item.key == "workspace_nav_formulary_propofol"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "Propofol")

    def test_plan_and_propofol_have_footer_navigation(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        next(
            item for item in app.button if item.key == "workspace_nav_en_plan_propofol"
        ).click().run(timeout=30)
        self.assertEqual(app.session_state["workspace_tab"], "Propofol")

        next(
            item for item in app.button if item.key == "workspace_nav_propofol_en_plan"
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
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 55)

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
        # Alerts are the project's own markup, not Streamlit's, so they arrive
        # as markdown rather than in app.error.
        self.assertIn(
            "app-alert--error", "\n".join(item.value for item in app.markdown)
        )

    def test_sex_can_be_selected_before_height(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        sex = next(item for item in app.selectbox if item.key == "assessment_sex")
        sex.select("Female").run(timeout=30)
        self.assertFalse(app.exception)
        height = next(
            item
            for item in app.number_input
            if item.key == "assessment_height_cm_entry"
        )
        self.assertIsNone(height.value)

        sex = next(item for item in app.selectbox if item.key == "assessment_sex")
        sex.select("Male").run(timeout=30)
        self.assertFalse(app.exception)

    def test_one_entered_protein_bound_shows_a_worked_value(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
        example.click().run(timeout=30)

        lower = next(
            item
            for item in app.number_input
            if item.key == "assessment_protein_low_gkg"
        )
        upper = next(
            item
            for item in app.number_input
            if item.key == "assessment_protein_high_gkg"
        )
        upper.set_value(None).run(timeout=30)
        lower = next(
            item
            for item in app.number_input
            if item.key == "assessment_protein_low_gkg"
        )
        lower.set_value(1.2).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                "Calculated protein requirement range" in item.value
                and "77 g/day" in item.value
                for item in app.markdown
            )
        )

    def test_activity_and_stress_factors_adjust_non_ventilator_equations(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
        example.click().run(timeout=30)

        activity = next(
            item
            for item in app.number_input
            if item.key == "assessment_activity_factor"
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
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
        example.click().run(timeout=30)

        lower = next(
            item
            for item in app.number_input
            if item.key == "assessment_energy_low_kcal_kg"
        )
        lower.set_value(25).run(timeout=30)
        upper = next(
            item
            for item in app.number_input
            if item.key == "assessment_energy_high_kcal_kg"
        )
        upper.set_value(30).run(timeout=30)
        measured = next(
            item
            for item in app.number_input
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
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
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

        unit = next(
            item for item in app.selectbox if item.key == "assessment_height_unit"
        )
        unit.select("ft/in").run(timeout=30)
        feet = next(
            item for item in app.number_input if item.key == "assessment_height_feet"
        )
        inches = next(
            item for item in app.number_input if item.key == "assessment_height_inches"
        )
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
            item for item in app.number_input if item.key == "assessment_height_feet"
        ).set_value(5)
        next(
            item for item in app.number_input if item.key == "assessment_height_inches"
        ).set_value(6).run(timeout=30)

        next(
            item for item in app.selectbox if item.key == "assessment_height_unit"
        ).select("cm").run(timeout=30)
        next(
            item
            for item in app.number_input
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

        unit = next(
            item for item in app.selectbox if item.key == "assessment_weight_unit"
        )
        unit.select("lb").run(timeout=30)
        current = next(
            item
            for item in app.number_input
            if item.key == "assessment_current_weight_lb"
        )
        usual = next(
            item
            for item in app.number_input
            if item.key == "assessment_usual_weight_lb"
        )
        current.set_value(150.0)
        usual.set_value(160.0).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertAlmostEqual(
            app.session_state["assessment_current_weight"], 68.0388555
        )
        self.assertAlmostEqual(app.session_state["assessment_usual_weight"], 72.5747792)

    def test_weight_does_not_revert_when_units_are_changed_twice(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.selectbox if item.key == "assessment_weight_unit"
        ).select("lb").run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "assessment_current_weight_lb"
        ).set_value(150).run(timeout=30)

        next(
            item for item in app.selectbox if item.key == "assessment_weight_unit"
        ).select("kg").run(timeout=30)
        next(
            item
            for item in app.number_input
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
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
        example.click().run(timeout=30)

        energy = next(
            item
            for item in app.number_input
            if item.key == "en_assessment_energy_goal_editor"
        )
        energy.set_value(1900).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["assessment_energy_target"], 1900)
        self.assertEqual(app.session_state["en_total_energy_target"], 1900)
        self.assertEqual(app.session_state["icu_total_energy_target"], 1900)
        self.assertEqual(app.session_state["icu_assessment_energy_goal_editor"], 1900)
        assessment_energy = next(
            item for item in app.number_input if item.key == "assessment_energy_target"
        )
        assessment_energy.set_value(1850).run(timeout=30)
        self.assertEqual(app.session_state["assessment_energy_target"], 1850)
        self.assertEqual(app.session_state["en_total_energy_target"], 1850)
        self.assertEqual(app.session_state["icu_total_energy_target"], 1850)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Goals from Assessment", rendered_html)

    def test_standard_and_icu_propofol_workflows_are_independent(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
        example.click().run(timeout=30)

        tab_labels = [item.label for item in app.tabs]
        self.assertIn("EN plan", tab_labels)
        self.assertIn("Propofol", tab_labels)
        self.assertNotIn("Lower/no propofol", tab_labels)
        self.assertNotIn("Higher propofol", tab_labels)
        radio_keys = {item.key for item in app.radio}
        self.assertIn("scenario_standard_running_shape", radio_keys)
        self.assertIn("scenario_propofol_running_shape", radio_keys)
        self.assertEqual(app.session_state["scenario_standard_propofol_rate"], 0.0)
        self.assertEqual(app.session_state["icu_total_energy_target"], 1800.0)

        standard_hours = next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_feeding_hours"
        )
        standard_hours.set_value(16).run(timeout=30)
        self.assertEqual(app.session_state["scenario_standard_feeding_hours"], 16)
        self.assertEqual(app.session_state["scenario_propofol_feeding_hours"], 23.0)

        next(
            item for item in app.radio if item.key == "scenario_propofol_running_shape"
        ).set_value("Intermittent, each feed a set volume").run(timeout=30)

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
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
        example.click().run(timeout=30)

        method = next(
            item
            for item in app.radio
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
        self.assertEqual(
            app.session_state["scenario_propofol_conditional_lower_rate_ml_hr"], 50
        )
        self.assertEqual(
            app.session_state["scenario_propofol_conditional_higher_rate_ml_hr"], 35
        )
        self.assertEqual(
            [item.key for item in app.selectbox].count(
                "scenario_propofol_selected_formula"
            ),
            1,
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
        self.assertIn("Suggested EN rate with higher Propofol (mL/hour)", rendered_html)
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
            item
            for item in app.number_input
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
            item
            for item in app.checkbox
            if item.key == "scenario_propofol_prescription_interruption_note"
        )
        self.assertFalse(rationale.value)
        self.assertEqual(
            rationale.label,
            "Include “to account for anticipated interruptions” in the "
            "**Chart note below**",
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
            item
            for item in app.number_input
            if item.key == "scenario_standard_prescription_target_pct"
        )
        target.set_value(110).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 55)
        self.assertEqual(
            app.session_state["scenario_propofol_prescription_target_pct"], 100
        )
        rationale = next(
            item
            for item in app.checkbox
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
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
        example.click().run(timeout=30)

        rate = next(
            item for item in app.number_input if item.label == "Propofol rate (mL/hour)"
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
            item
            for item in app.radio
            if item.key == "scenario_propofol_propofol_method"
        )
        method.set_value("Changing Propofol rates").run(timeout=30)
        higher_rate = next(
            item
            for item in app.number_input
            if item.key == "_propofol_widget_scenario_propofol_higher_propofol_rate"
        )
        higher_hours = next(
            item
            for item in app.number_input
            if item.label == "Expected duration (hours/day)"
        )
        self.assertEqual(higher_rate.value, 20)
        self.assertEqual(higher_hours.value, 6)

        method = next(
            item
            for item in app.radio
            if item.key == "scenario_propofol_propofol_method"
        )
        method.set_value("Single Propofol rate").run(timeout=30)
        daily_rate = next(
            item for item in app.number_input if item.label == "Propofol rate (mL/hour)"
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
            item
            for item in app.number_input
            if item.key == "scenario_propofol_achieved_delivery_pct"
        )
        achieved.set_value(50).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Estimated daily intake at 50% formula delivery", rendered_html)

    def test_formula_comparison_includes_the_full_electrolyte_profile(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
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
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
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
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        feeding_hours = next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_feeding_hours"
        )
        feeding_hours.set_value(12).run(timeout=30)
        frequency = next(
            item
            for item in app.selectbox
            if item.key == "scenario_standard_hydration_schedule_format"
        )
        frequency.select("qXh").run(timeout=30)
        interval = next(
            item
            for item in app.selectbox
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

    def _volume_per_feed_from_summary(self, app):
        # Every intermittent form names the volume per feed, whichever pair of
        # numbers was typed, so it is the invariant to compare across them.
        rendered_html = "\n".join(item.value for item in app.markdown)
        match = re.search(r"<strong>([\d,]+) mL per feed</strong>", rendered_html)
        self.assertIsNotNone(match, "no order summary rendered")
        return int(match.group(1).replace(",", ""))

    def _daily_volume_from_summary(self, app):
        rendered_html = "\n".join(item.value for item in app.markdown)
        match = re.search(r"<strong>([\d,]+) mL</strong> formula/day", rendered_html)
        self.assertIsNotNone(match, "no order summary rendered")
        return int(match.group(1).replace(",", ""))

    def test_every_entry_form_for_the_same_order_agrees_on_the_daily_volume(self):
        # The central guarantee of the entry forms. 180 mL/hour for 2 hours
        # three times daily, 360 mL per feed three times daily, and 1080 mL a
        # day across three feeds are the same order written three ways.
        volumes = {}

        for form, setup in (
            (
                "Intermittent, each feed a set volume",
                {"scenario_standard_ordered_volume_per_feed_ml": 360},
            ),
            (
                "Intermittent, each feed run at a rate for a set time",
                {"scenario_standard_ordered_rate_ml_hr": 180},
            ),
        ):
            app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
            next(
                item for item in app.button if item.label == "📋 Load example record"
            ).click().run(timeout=30)
            next(
                item
                for item in app.radio
                if item.key == "scenario_standard_running_shape"
            ).set_value(form).run(timeout=30)
            next(
                item
                for item in app.number_input
                if item.key == "scenario_standard_feeds_per_day"
            ).set_value(3).run(timeout=30)
            if form == "A rate in mL/hour, run for a set time each feed":
                next(
                    item
                    for item in app.number_input
                    if item.key == "scenario_standard_hours_per_feed"
                ).set_value(2.0).run(timeout=30)
            for key, value in setup.items():
                next(item for item in app.number_input if item.key == key).set_value(
                    value
                ).run(timeout=30)

            self.assertFalse(app.exception, f"{form} raised")
            volumes[form] = self._volume_per_feed_from_summary(app)

        self.assertEqual(set(volumes.values()), {360}, volumes)

    def test_the_presenting_case_charts_correctly_end_to_end(self):
        # Isosource Fibre 1.5 at 180 mL/hour for 2 hours three times daily,
        # with 150 mL flushes before and after each feed plus 150 mL overnight.
        # Entered exactly as the chart writes it, with the assessment untouched.
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)
        next(item for item in app.text_input if item.key == "feed_search").set_value(
            "Isosource Fibre 1.5"
        ).run(timeout=30)
        next(
            item for item in app.button if str(item.key).startswith("add_feed_")
        ).click().run(timeout=30)
        next(
            item for item in app.multiselect if item.key == "feed_candidates"
        ).set_value(["Isosource Fibre 1.5"]).run(timeout=30)

        for key, value in (
            ("scenario_standard_regimen_source", "Reviewing a feed already running"),
            (
                "scenario_standard_running_shape",
                "Intermittent, each feed run at a rate for a set time",
            ),
            ("scenario_standard_hydration_entry_mode", "Enter flushes as ordered"),
        ):
            next(item for item in app.radio if item.key == key).set_value(value).run(
                timeout=30
            )
        next(
            item
            for item in app.selectbox
            if item.key == "scenario_standard_peri_feed_flush_pattern"
        ).select("Before and after each feed").run(timeout=30)
        for key, value in (
            ("scenario_standard_hours_per_feed", 2.0),
            ("scenario_standard_feeds_per_day", 3),
            ("scenario_standard_ordered_rate_ml_hr", 180),
            ("scenario_standard_peri_feed_flush_volume_ml", 150),
            ("scenario_standard_ordered_flush_times_per_day", 1),
            ("scenario_standard_ordered_flush_volume_ml", 150),
            ("scenario_standard_medication_flushes", 0),
        ):
            next(item for item in app.number_input if item.key == key).set_value(
                value
            ).run(timeout=30)
        next(
            item
            for item in app.multiselect
            if item.key == "scenario_standard_chosen_modulars"
        ).set_value([]).run(timeout=30)

        self.assertFalse(app.exception)
        note = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn(
            "Continue enteral nutrition: Isosource Fibre 1.5 at 180 mL/hour "
            "over 2 hours per feed, 3 feeds daily (360 mL per feed).",
            note,
        )
        self.assertIn(
            "Hydration: Provide 150 mL before and after each feed and 150 mL "
            "once daily, totalling 1,050 mL daily.",
            note,
        )
        self.assertIn("energy 1,620 kcal", note)
        self.assertIn("Total water provided is 1,877 mL/day", note)
        # The volume must never be said twice, which the first wording did.
        self.assertNotIn("150 mL water flushes 150 mL", note)

    def test_rate_and_time_per_feed_is_charted_the_way_it_was_entered(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        next(
            item for item in app.radio if item.key == "scenario_standard_running_shape"
        ).set_value("Intermittent, each feed run at a rate for a set time").run(
            timeout=30
        )
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_feeds_per_day"
        ).set_value(3).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_hours_per_feed"
        ).set_value(2.0).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_rate_ml_hr"
        ).set_value(180).run(timeout=30)

        self.assertFalse(app.exception)
        chart_note = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn("180 mL/hour over 2 hours per feed, 3 feeds daily", chart_note)

    def test_feeding_hours_beyond_a_day_warn_without_changing_the_arithmetic(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        next(
            item for item in app.radio if item.key == "scenario_standard_running_shape"
        ).set_value("Intermittent, each feed run at a rate for a set time").run(
            timeout=30
        )
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_feeds_per_day"
        ).set_value(6).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_hours_per_feed"
        ).set_value(5.0).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_rate_ml_hr"
        ).set_value(100).run(timeout=30)

        # 5 hours across 6 feeds is 30 hours. The tool warns rather than
        # refusing, and still reports what was entered.
        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("app-alert--warning", rendered_html)
        self.assertIn("more than a day", rendered_html)
        self.assertEqual(self._daily_volume_from_summary(app), 3000)

    def _propofol_conditional(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)
        next(
            item for item in app.button if item.key == "workspace_nav_en_plan_propofol"
        ).click().run(timeout=30)
        next(
            item
            for item in app.radio
            if item.key == "scenario_propofol_propofol_method"
        ).set_value("Changing Propofol rates").run(timeout=30)
        return app

    def test_reviewing_on_conditional_propofol_rates_still_renders(self):
        # The prescription box dropped the schedule when reviewing, while the
        # caller only rebuilt it outside conditional mode, so this combination
        # raised before anything drew.
        app = self._propofol_conditional()
        next(
            item for item in app.radio if item.key == "scenario_propofol_regimen_source"
        ).set_value("Reviewing a feed already running").run(timeout=30)

        self.assertFalse(app.exception)
        # Conditional rates keep the prescription layout, not the review one.
        headings = "\n".join(item.value for item in app.markdown)
        self.assertNotIn("The order that is running", headings)
        self.assertIn(
            "scenario_propofol_feeding_hours",
            {i.key for i in app.number_input},
        )

    def test_reviewing_protects_conditional_rates_from_the_suggestion(self):
        # The "don't overwrite what was typed" rule has to reach the per-
        # condition rates too. It was disabled there, because the flag that
        # carried it also carried the layout decision.
        app = self._propofol_conditional()
        next(
            item for item in app.radio if item.key == "scenario_propofol_regimen_source"
        ).set_value("Reviewing a feed already running").run(timeout=30)

        rate_key = "_propofol_widget_scenario_propofol_conditional_lower_rate_ml_hr"
        next(item for item in app.number_input if item.key == rate_key).set_value(
            20
        ).run(timeout=30)
        # An unrelated change elsewhere reruns the page.
        next(
            item
            for item in app.number_input
            if item.key == "scenario_propofol_medication_flushes"
        ).set_value(40).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(
            app.session_state["scenario_propofol_conditional_lower_rate_ml_hr"], 20
        )

    def test_conditional_propofol_mode_offers_no_entry_form_picker(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)
        next(
            item for item in app.button if item.key == "workspace_nav_en_plan_propofol"
        ).click().run(timeout=30)
        next(
            item
            for item in app.radio
            if item.key == "scenario_propofol_propofol_method"
        ).set_value("Changing Propofol rates").run(timeout=30)

        self.assertFalse(app.exception)
        # Feeding hours are split across the sedation conditions, so a per-feed
        # form has nothing to mean and the picker is withheld.
        self.assertNotIn(
            "scenario_propofol_order_entry_form",
            {item.key for item in app.radio},
        )

    def test_intake_table_keeps_one_water_column_with_iv_fluids_running(self):
        # The IV row was left on the old two-column shape, which gave the table
        # stray columns and left that row with no water value at all. Nothing
        # exercised the intake table with a line running, so it passed.
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)
        next(
            item for item in app.selectbox if item.key == "assessment_iv_fluid_0"
        ).select("D5W").run(timeout=30)
        next(
            item for item in app.number_input if item.key == "assessment_iv_rate_0"
        ).set_value(100).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Water (mL)", rendered_html)
        self.assertNotIn("Free water (mL)<", rendered_html)
        self.assertNotIn("Water flushes (mL)<", rendered_html)
        # The fluid's volume is reported even though it is not counted as water.
        self.assertIn("IV fluids", rendered_html)
        self.assertIn(">2400<", rendered_html)

    def _every_source_plan(self):
        """Load a plan carrying a feed, modulars, an IV, ONS and flushes."""
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)
        next(
            item for item in app.selectbox if item.key == "assessment_iv_fluid_0"
        ).select("D5 1/2 NS").run(timeout=30)
        next(
            item for item in app.number_input if item.key == "assessment_iv_rate_0"
        ).set_value(85).run(timeout=30)
        next(
            item
            for item in app.multiselect
            if item.key == "scenario_standard_chosen_ons"
        ).set_value(["BOOST Plus Calories — Vanilla"]).run(timeout=30)
        product = "nestle-boost-plus-calories-vanilla"
        next(
            item
            for item in app.number_input
            if item.key == f"scenario_standard_ons_containers_{product}"
        ).set_value(1).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == f"scenario_standard_ons_times_{product}"
        ).set_value(2).run(timeout=30)
        self.assertFalse(app.exception)
        return app

    def _intake_rows(self, app):
        rendered_html = "\n".join(item.value for item in app.markdown)
        table = re.search(r"Planned daily intake.*?</table>", rendered_html, re.DOTALL)
        self.assertIsNotNone(table, "no daily intake table rendered")
        rows = {}
        for row in re.findall(r"<tr>(.*?)</tr>", table.group(0), re.DOTALL):
            cells = [
                re.sub("<[^>]+>", "", cell).strip()
                for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL)
            ]
            if cells:
                rows[cells[0]] = cells[1:]
        return rows

    def test_daily_intake_totals_are_unchanged(self):
        """Today's figures, pinned before the summing moves to the engine.

        The totals are added up inside the page, where no unit test reaches
        them, and they have been edited repeatedly. Recording them here first
        is what makes moving that arithmetic provable rather than hopeful.
        """
        rows = self._intake_rows(self._every_source_plan())

        self.assertEqual(
            rows["Source"][:6],
            [
                "Volume (mL)",
                "Energy (kcal)",
                "Protein (g)",
                "Carbohydrate (g)",
                "Fat (g)",
                "Water (mL)",
            ],
        )
        self.assertEqual(
            rows["Isosource 1.5"][:6], ["920", "1380", "63", "162", "55", "704"]
        )
        self.assertEqual(rows["Modulars"][:6], ["120", "50", "12", "0", "0", "120"])
        self.assertEqual(rows["IV fluids"][:6], ["2040", "347", "0", "102", "0", "0"])
        self.assertEqual(rows["ONS"][:6], ["474", "720", "28", "90", "28", "366"])
        self.assertEqual(
            rows["Water flushes"][:6], ["1080", "0", "0", "0", "0", "1080"]
        )
        self.assertEqual(
            rows["Total"][:6], ["4634", "2497", "103", "354", "83", "2270"]
        )

    def test_chart_note_totals_match_the_intake_table(self):
        # The note and the table are summed by separate code today. They must
        # agree, and must go on agreeing once that summing is shared.
        app = self._every_source_plan()
        note = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn("energy 2,497 kcal", note)
        self.assertIn("protein 103 g", note)
        self.assertIn("CHO 354 g", note)
        self.assertIn("Total water provided is 2,270 mL/day", note)

    def test_a_partial_target_says_which_figure_the_goal_column_holds(self):
        # At anything but 100% the energy goal in the table is the share the
        # feed is meant to meet, not the assessed requirement, and the column
        # header cannot say which of the two it is showing.
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)
        captions = "\n".join(str(item.value) for item in app.caption)
        self.assertNotIn("of the assessed requirement", captions)

        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_prescription_target_pct"
        ).set_value(50).run(timeout=30)

        self.assertFalse(app.exception)
        captions = "\n".join(str(item.value) for item in app.caption)
        self.assertIn(
            "The energy goal above is 50% of the assessed requirement of "
            "1,800 kcal/day.",
            captions,
        )
        self.assertIn("Protein and water are compared against the full", captions)

    def test_ordered_flushes_count_while_iv_fluids_are_running(self):
        # The intensive care case. With a line running, fluid needs are charted
        # rather than filled enterally, which used to zero the flushes out of
        # the totals even when they were genuinely ordered.
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        water_mode = next(
            item for item in app.radio if item.key == "assessment_water_mode"
        )
        chart_only = next(
            option for option in water_mode.options if "IV fluids running" in option
        )
        water_mode.set_value(chart_only).run(timeout=30)

        next(
            item
            for item in app.radio
            if item.key == "scenario_standard_hydration_entry_mode"
        ).set_value("Enter flushes as ordered").run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_flush_times_per_day"
        ).set_value(6).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_flush_volume_ml"
        ).set_value(100).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("600 mL/day", rendered_html)
        chart_note = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn("Hydration", chart_note)

    def test_chart_note_says_continue_for_a_regimen_already_running(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        before = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn("Enteral nutrition plan:", before)

        next(
            item for item in app.radio if item.key == "scenario_standard_regimen_source"
        ).set_value("Reviewing a feed already running").run(timeout=30)

        self.assertFalse(app.exception)
        after = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn("Continue enteral nutrition:", after)
        self.assertNotIn("Enteral nutrition plan:", after)

    def test_starting_a_feed_shows_the_comparison_and_reviewing_does_not(self):
        # The two jobs get different screens. Choosing a feed is a browsing job
        # and the comparison is the point of it. Reviewing a running order is a
        # transcription job, where suggested rates for feeds nobody asked about
        # are noise, so the whole order sits in one box instead.
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        # Both plan tabs render on every run, so count rather than search: the
        # Propofol tab keeps its own comparison while the EN plan loses one.
        def counts(app):
            headings = "\n".join(item.value for item in app.markdown)
            # Both plan boxes are titled "EN prescription", so the heading
            # that tells the layouts apart is the comparison, which reviewing
            # drops. "Select formula" no longer exists on either: choosing and
            # setting the amount happen inside the comparison box.
            return headings.count("Formula comparison")

        self.assertEqual(counts(app), 2)

        next(
            item for item in app.radio if item.key == "scenario_standard_regimen_source"
        ).set_value("Reviewing a feed already running").run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(counts(app), 1)
        # One question replaces the schedule radio and the form radio nested
        # inside it, because transcribing an order does not need both.
        review_radios = {item.key for item in app.radio}
        self.assertIn("scenario_standard_running_shape", review_radios)
        self.assertNotIn("scenario_standard_schedule_type", review_radios)
        self.assertNotIn("scenario_standard_order_entry_form", review_radios)
        # No prescription target either: the goal is the assessed requirement.
        self.assertNotIn(
            "scenario_standard_prescription_target_pct",
            {item.key for item in app.number_input},
        )
        self.assertIn(
            "scenario_standard_selected_formula",
            {item.key for item in app.selectbox},
        )

    def test_existing_regimen_rate_is_not_overwritten_by_the_suggestion(self):
        # The running order is the fact. Entering it must survive a rerun that
        # the clinician did not cause, which is what the suggestion used to win.
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        next(
            item for item in app.radio if item.key == "scenario_standard_regimen_source"
        ).set_value("Reviewing a feed already running").run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_rate_ml_hr"
        ).set_value(180).run(timeout=30)

        # An unrelated change elsewhere reruns the whole page.
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_medication_flushes"
        ).set_value(60).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 180)

    def test_existing_regimen_entry_survives_a_formula_change(self):
        # Comparing an alternative feed is not abandoning the order. The rate
        # keeps its units, so it stays and drives the comparison.
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        next(
            item for item in app.multiselect if item.key == "feed_candidates"
        ).set_value(["Isosource 1.5", "Peptamen 1.5"]).run(timeout=30)
        next(
            item for item in app.radio if item.key == "scenario_standard_regimen_source"
        ).set_value("Reviewing a feed already running").run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_rate_ml_hr"
        ).set_value(180).run(timeout=30)

        next(
            item
            for item in app.selectbox
            if item.key == "scenario_standard_selected_formula"
        ).select("Peptamen 1.5").run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(
            app.session_state["scenario_standard_selected_formula"], "Peptamen 1.5"
        )
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 180)

    def test_starting_a_new_feed_still_discards_a_rate_on_a_formula_change(self):
        # The contrasting half of the test above. The default direction of work
        # must keep its existing behaviour, where a manually entered rate is
        # dropped and the suggestion returns once the feed changes.
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        self.assertEqual(
            app.session_state["scenario_standard_regimen_source"],
            "Starting a new feed",
        )
        next(
            item for item in app.multiselect if item.key == "feed_candidates"
        ).set_value(["Isosource 1.5", "Peptamen 1.5"]).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_rate_ml_hr"
        ).set_value(180).run(timeout=30)
        self.assertEqual(app.session_state["scenario_standard_ordered_rate_ml_hr"], 180)

        next(
            item
            for item in app.selectbox
            if item.key == "scenario_standard_selected_formula"
        ).select("Peptamen 1.5").run(timeout=30)

        self.assertFalse(app.exception)
        self.assertNotEqual(
            app.session_state["scenario_standard_ordered_rate_ml_hr"], 180
        )

    def test_ordered_flushes_are_totalled_as_written_and_leave_the_goal_alone(self):
        # The presenting case: a patient already running 150 mL flushes before
        # and after each of three feeds, plus 150 mL overnight, which totals
        # 1050 mL. None of that is derivable from a water goal.
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        water_goal_before = app.session_state["assessment_water_target"]

        next(
            item for item in app.radio if item.key == "scenario_standard_running_shape"
        ).set_value("Intermittent, each feed a set volume").run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_feeds_per_day"
        ).set_value(3).run(timeout=30)
        next(
            item
            for item in app.radio
            if item.key == "scenario_standard_hydration_entry_mode"
        ).set_value("Enter flushes as ordered").run(timeout=30)
        next(
            item
            for item in app.selectbox
            if item.key == "scenario_standard_peri_feed_flush_pattern"
        ).select("Before and after each feed").run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_peri_feed_flush_volume_ml"
        ).set_value(150).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_flush_times_per_day"
        ).set_value(1).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_flush_volume_ml"
        ).set_value(150).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Ordered hydration flushes:", rendered_html)
        self.assertIn("1,050 mL/day", rendered_html)
        # The assessed requirement must survive untouched, which is the whole
        # point of entering the order rather than back-solving the goal.
        self.assertEqual(
            app.session_state["assessment_water_target"], water_goal_before
        )

    def test_ordered_flush_entry_does_not_round_away_the_entered_volume(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        next(
            item
            for item in app.radio
            if item.key == "scenario_standard_hydration_entry_mode"
        ).set_value("Enter flushes as ordered").run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_flush_times_per_day"
        ).set_value(7).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_flush_volume_ml"
        ).set_value(149).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        # 149 x 7 = 1043, which the goal-driven path would have rounded.
        self.assertIn("1,043 mL/day", rendered_html)

    def test_switching_hydration_entry_mode_keeps_the_calculated_schedule_usable(self):
        # The two modes hold their counts in separate keys, because the ordered
        # mode allows zero and the calculated one does not.
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        mode = next(
            item
            for item in app.radio
            if item.key == "scenario_standard_hydration_entry_mode"
        )
        mode.set_value("Enter flushes as ordered").run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_flush_times_per_day"
        ).set_value(0).run(timeout=30)
        self.assertFalse(app.exception)

        next(
            item
            for item in app.radio
            if item.key == "scenario_standard_hydration_entry_mode"
        ).set_value("Calculate flushes from the water goal").run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("Calculated hydration flush schedule:", rendered_html)

    def test_patency_flush_change_updates_generated_chart_note(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        before = app.session_state["_chart_note_generated_en_plan"]
        self.assertIn("Hydration flushes 130 mL q4h", before)
        self.assertNotIn("Patency flushes", before)

        patency = next(
            item
            for item in app.number_input
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
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        ordered_rate = next(
            item
            for item in app.number_input
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

        next(item for item in app.button if item.key == "add_feed_Nepro").click().run(
            timeout=30
        )
        next(
            item for item in app.button if item.key == "add_modular_MCT Oil"
        ).click().run(timeout=30)

        self.assertFalse(app.exception)
        self.assertIn("Nepro", app.session_state.my_formulas["name"].tolist())
        self.assertIn("MCT Oil", app.session_state.my_modulars["name"].tolist())
        self.assertEqual(
            app.session_state["en_total_energy_target"], expected_state["energy"]
        )
        self.assertEqual(
            app.session_state["en_protein_target"], expected_state["protein"]
        )
        self.assertEqual(app.session_state["en_water_target"], expected_state["water"])
        self.assertEqual(
            list(app.session_state["feed_candidates"]), expected_state["candidates"]
        )
        self.assertEqual(
            app.session_state["scenario_standard_selected_formula"],
            expected_state["formula"],
        )
        self.assertEqual(
            app.session_state["scenario_standard_schedule_type"],
            expected_state["schedule"],
        )
        self.assertEqual(
            app.session_state["scenario_standard_feeding_hours"],
            expected_state["hours"],
        )
        self.assertEqual(
            app.session_state["scenario_standard_ordered_rate_ml_hr"],
            expected_state["rate"],
        )
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
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
        example.click().run(timeout=30)

        ordered_rate = next(
            item
            for item in app.number_input
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
        self.assertIn("Selected EN feed: <strong>86 g/day</strong>", rendered_html)

        reset = next(
            item
            for item in app.button
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
            item
            for item in app.number_input
            if item.key == "scenario_standard_ordered_rate_ml_hr"
        )
        ordered_rate.set_value(20).run(timeout=30)

        trickle = next(
            item
            for item in app.checkbox
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
        example = next(
            item for item in app.button if item.label == "📋 Load example record"
        )
        example.click().run(timeout=30)

        target = next(
            item
            for item in app.number_input
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
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        doses = next(
            item
            for item in app.number_input
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

        suggested_rate = app.session_state["scenario_standard_ordered_rate_ml_hr"]
        ons = next(
            item
            for item in app.multiselect
            if item.key == "scenario_standard_chosen_ons"
        )
        ons.set_value(["BOOST Plus Calories — Vanilla"]).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key
            == ("scenario_standard_ons_containers_nestle-boost-plus-calories-vanilla")
        ).set_value(1).run(timeout=30)
        next(
            item
            for item in app.number_input
            if item.key
            == ("scenario_standard_ons_times_nestle-boost-plus-calories-vanilla")
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
        self.assertIn("ONS: BOOST Plus Calories — Vanilla, 1 carton BID.", chart_note)
        self.assertIn("At goal, EN and ONS orders provide", chart_note)
        self.assertIn("(EN 1,775 kcal + ONS 720 kcal)", chart_note)
        self.assertIn("Total water provided is 2,266 mL/day", chart_note)
        self.assertIn("ONS water 366 mL", chart_note)
        self.assertIn("Hydration: Provide 130 mL water flushes q4h.", chart_note)
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
            item
            for item in app.button
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
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        doses = next(
            item
            for item in app.number_input
            if item.key == "scenario_propofol_modular_doses_nestle-beneprotein"
        )
        doses.set_value(6).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["scenario_propofol_ordered_rate_ml_hr"], 35)
        self.assertFalse(app.session_state["scenario_propofol_order_user_edited"])

    def test_reduced_delivery_review_keeps_the_order_and_explains_the_view(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        achieved = next(
            item
            for item in app.number_input
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
            "50 mL/hour for 23 hours daily "
            "&nbsp;|&nbsp; <strong>1,150 mL/day</strong>."
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
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        preparation_water = next(
            item
            for item in app.number_input
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
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)
        next(
            item for item in app.button if item.key == "add_modular_LiquiProtein"
        ).click().run(timeout=30)

        modulars = next(
            item
            for item in app.multiselect
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
            item
            for item in app.number_input
            if item.key == "scenario_standard_modular_units_abbott-liquiprotein"
        )
        liquid_modular_amount.set_value(6).run(timeout=30)
        rendered_html = "\n".join(item.value for item in app.markdown)
        chart_notes = app.session_state["_chart_note_generated_en_plan"]
        self.assertNotIn("5 mL from modulars", rendered_html)
        self.assertNotIn("LiquiProtein", chart_notes)

        liquid_modular_frequency = next(
            item
            for item in app.number_input
            if item.key == "scenario_standard_modular_doses_abbott-liquiprotein"
        )
        liquid_modular_frequency.set_value(1).run(timeout=30)

        self.assertFalse(app.exception)
        rendered_html = "\n".join(item.value for item in app.markdown)
        self.assertIn("5 mL from modulars", rendered_html)
        # The feed row keeps its own 880 mL. The liquid modular's 5 mL lands on
        # the Modulars row instead, alongside 120 mL of preparation water.
        self.assertIn(">880<", rendered_html)
        self.assertIn(">125<", rendered_html)
        self.assertNotIn(">885<", rendered_html)

    def test_example_rates_and_modular_totals_use_the_regular_calculations(self):
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

        standard_formula = (
            load_master_formulas()
            .loc[lambda frame: frame["name"] == "Isosource 1.5"]
            .iloc[0]
            .to_dict()
        )
        propofol_formula = (
            load_master_formulas()
            .loc[lambda frame: frame["name"] == "Peptamen 1.5"]
            .iloc[0]
            .to_dict()
        )
        modular = (
            load_master_modulars()
            .loc[lambda frame: frame["id"] == "nestle-beneprotein"]
            .iloc[0]
            .to_dict()
        )
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
        next(
            item for item in app.button if item.label == "📋 Load example record"
        ).click().run(timeout=30)

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
