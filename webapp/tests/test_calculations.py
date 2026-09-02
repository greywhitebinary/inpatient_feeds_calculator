import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculations import (
    adjusted_body_weight_kg,
    conditional_feed_delivery,
    devine_ibw_kg,
    feed_delivery,
    hamwi_ibw_kg,
    height_to_cm,
    harris_benedict_kcal,
    hydration_flushes_per_day,
    disclosed_value,
    mg_to_mmol,
    mifflin_st_jeor_kcal,
    modular_delivery,
    ons_delivery,
    open_abdomen_protein_loss_g,
    ordered_feed_delivery,
    penn_state_2003b_kcal,
    penn_state_2010_kcal,
    practical_feed_delivery,
    propofol_intake,
    suggested_conditional_formula_rate,
    total_modular_delivery,
    total_propofol_intake,
    total_ons_delivery,
    water_plan,
)


class CalculationTests(unittest.TestCase):
    """Reference-value tests whose expected results are calculated independently."""

    def test_height_conversion(self):
        self.assertAlmostEqual(height_to_cm("ft_in", feet=5, inches=10), 177.8)

    def test_metric_height_conversion(self):
        self.assertEqual(height_to_cm("m", metres=1.65), 165)

    def test_hamwi_si_reference_values(self):
        # At 65 inches: female 45.5 + 2.2(5); at 70 inches: male 48 + 2.7(10).
        self.assertAlmostEqual(hamwi_ibw_kg("Female", 165.1), 56.5)
        self.assertAlmostEqual(hamwi_ibw_kg("Male", 177.8), 75.0)

    def test_adjusted_weight(self):
        self.assertEqual(adjusted_body_weight_kg(100, 70), 77.5)

    def test_devine_medication_dosing_reference_weight(self):
        self.assertAlmostEqual(devine_ibw_kg("Female", 165), 56.91, places=2)
        self.assertAlmostEqual(devine_ibw_kg("Male", 180), 74.99, places=2)

    def test_mifflin_male(self):
        self.assertAlmostEqual(mifflin_st_jeor_kcal("Male", 70, 175, 40), 1598.75)

    def test_mifflin_female_reference_value(self):
        # 10(64) + 6.25(165) - 5(67) - 161.
        self.assertAlmostEqual(mifflin_st_jeor_kcal("Female", 64, 165, 67), 1175.25)

    def test_revised_harris_benedict_reference_values(self):
        # These literals independently exercise both published sex-specific equations.
        self.assertAlmostEqual(
            harris_benedict_kcal("Female", 64, 165, 67), 1260.461, places=3
        )
        self.assertAlmostEqual(
            harris_benedict_kcal("Male", 80, 180, 50), 1740.092, places=3
        )

    def test_both_penn_state_equations(self):
        self.assertAlmostEqual(penn_state_2003b_kcal(1500, 37, 8), 1655)
        self.assertAlmostEqual(penn_state_2010_kcal(1500, 37, 8), 1637)

    def test_penn_state_reference_values_retain_unrounded_mifflin_input(self):
        self.assertAlmostEqual(penn_state_2003b_kcal(975.25, 38.2, 9.7), 1404.34)
        self.assertAlmostEqual(penn_state_2010_kcal(975.25, 38.2, 9.7), 1475.2275)

    def test_open_abdomen_loss_converts_ml_to_litres(self):
        self.assertAlmostEqual(open_abdomen_protein_loss_g(850, 22), 18.7)

    def test_mg_to_mmol_uses_element_atomic_weight(self):
        self.assertAlmostEqual(mg_to_mmol("potassium", 3910), 100)
        self.assertAlmostEqual(mg_to_mmol("sodium", 2300), 100.043497, places=6)

    def test_feed_delivery_uses_achieved_percentage(self):
        formula = {"kcal_per_mL": 1.5, "protein_per_mL": 0.07, "free_water_per_mL": 0.766}
        result = feed_delivery(formula, 1800, 20, 80)
        self.assertEqual(result["planned_volume_ml"], 1200)
        self.assertEqual(result["delivered_volume_ml"], 960)
        self.assertAlmostEqual(result["protein_g"], 67.2)

    def test_feed_delivery_rejects_zero_energy_density(self):
        with self.assertRaisesRegex(ValueError, "kcal_per_mL"):
            feed_delivery({"kcal_per_mL": 0}, 1800, 20)

    def test_modular_delivery_rejects_zero_basis(self):
        with self.assertRaisesRegex(ValueError, "basis_amount"):
            modular_delivery(
                {"basis_amount": 0, "kcal_per_basis": 100},
                units_per_dose=2,
                doses_per_day=3,
            )

    def test_modular_delivery_scales_label_basis_and_preparation_water(self):
        product = {
            "basis_amount": 30,
            "kcal_per_basis": 60,
            "protein_g_per_basis": 15,
            "sodium_mg_per_basis": 180,
        }
        result = modular_delivery(
            product, units_per_dose=45, doses_per_day=2,
            preparation_water_ml_per_dose=30,
        )
        # 45 mL twice daily is three 30-mL label servings per day.
        self.assertEqual(result["energy_kcal"], 180)
        self.assertEqual(result["protein_g"], 45)
        self.assertEqual(result["sodium_mg"], 540)
        self.assertEqual(result["preparation_water_ml"], 60)

    def test_ons_delivery_scales_container_and_frequency(self):
        product = {
            "container_size_ml": 237,
            "kcal_per_mL": 360 / 237,
            "protein_per_mL": 14 / 237,
            "carbohydrate_per_mL": 45 / 237,
            "fat_per_mL": 14 / 237,
            "free_water_per_mL": 183 / 237,
        }
        order = ons_delivery(product, containers_each_time=1, times_per_day=2)
        totals = total_ons_delivery([order])
        self.assertEqual(totals["daily_containers"], 2)
        self.assertEqual(totals["daily_volume_ml"], 474)
        self.assertAlmostEqual(totals["energy_kcal"], 720)
        self.assertAlmostEqual(totals["protein_g"], 28)
        self.assertAlmostEqual(totals["carbohydrate_g"], 90)
        self.assertAlmostEqual(totals["fat_g"], 28)
        self.assertAlmostEqual(totals["free_water_ml"], 366)

    def test_ons_delivery_scales_serving_based_oral_product(self):
        product = {
            "calculation_basis": "serving",
            "serving_size_g": 142,
            "serving_unit": "cup",
            "kcal_per_serving": 230,
            "protein_g_per_serving": 7,
            "carbohydrate_g_per_serving": 32,
            "fat_g_per_serving": 8,
            "free_water_ml_per_serving": 93,
        }
        order = ons_delivery(product, containers_each_time=1, times_per_day=2)
        totals = total_ons_delivery([order])
        self.assertEqual(totals["daily_servings"], 2)
        self.assertEqual(totals["daily_volume_ml"], 0)
        self.assertEqual(totals["energy_kcal"], 460)
        self.assertEqual(totals["protein_g"], 14)
        self.assertEqual(totals["free_water_ml"], 186)

    def test_practical_continuous_delivery_rounds_the_pump_rate_to_five_ml(self):
        formula = {"kcal_per_mL": 1.5, "protein_per_mL": 0.07, "free_water_per_mL": 0.766}
        result = practical_feed_delivery(formula, 1900, 20)
        self.assertEqual(result["ordered_rate_ml_hr"], 65)
        self.assertEqual(result["planned_volume_ml"], 1300)
        self.assertEqual(result["energy_kcal"], 1950)

    def test_practical_continuous_delivery_uses_rounded_order_for_every_nutrient(self):
        formula = {
            "kcal_per_mL": 1.5,
            "protein_per_mL": 0.068,
            "carbohydrate_per_mL": 0.176,
            "fat_per_mL": 0.060,
            "free_water_per_mL": 0.765,
        }
        result = practical_feed_delivery(formula, 1800, 23)
        # 1800 / 1.5 / 23 = 52.17 mL/h, ordered as 50 mL/h for 1150 mL/day.
        self.assertEqual(result["ordered_rate_ml_hr"], 50)
        self.assertEqual(result["planned_volume_ml"], 1150)
        self.assertEqual(result["energy_kcal"], 1725)
        self.assertAlmostEqual(result["protein_g"], 78.2)
        self.assertAlmostEqual(result["carbohydrate_g"], 202.4)
        self.assertAlmostEqual(result["fat_g"], 69.0)
        self.assertAlmostEqual(result["free_water_ml"], 879.75)

    def test_entered_continuous_rate_drives_all_delivery_values(self):
        formula = {
            "kcal_per_mL": 1.5,
            "protein_per_mL": 0.07,
            "free_water_per_mL": 0.766,
            "sodium_per_mL": 1.2,
        }
        result = ordered_feed_delivery(formula, 55, 20, 100)
        self.assertEqual(result["ordered_rate_ml_hr"], 55)
        self.assertEqual(result["planned_volume_ml"], 1100)
        self.assertEqual(result["energy_kcal"], 1650)
        self.assertAlmostEqual(result["protein_g"], 77)
        self.assertAlmostEqual(result["free_water_ml"], 842.6)
        self.assertEqual(result["sodium_mg"], 1320)

    def test_entered_intermittent_volume_drives_daily_delivery(self):
        formula = {
            "kcal_per_mL": 1.2,
            "protein_per_mL": 0.05,
            "free_water_per_mL": 0.8,
        }
        result = ordered_feed_delivery(
            formula, 275, 24, 80,
            schedule_type="Intermittent", feeds_per_day=4,
        )
        self.assertEqual(result["ordered_volume_per_feed_ml"], 275)
        self.assertEqual(result["planned_volume_ml"], 1100)
        self.assertEqual(result["delivered_volume_ml"], 880)
        self.assertEqual(result["energy_kcal"], 1056)
        self.assertEqual(result["protein_g"], 44)

    def test_water_plan_rounds_hydration_flushes_to_five_ml(self):
        result = water_plan(2000, 1100, 0, 0, 100, 0, 6)
        self.assertEqual(result["hydration_flush_each_ml"], 135)
        self.assertEqual(result["total_water_ml"], 2010)

    def test_water_plan_rounds_halfway_hydration_flush_up(self):
        result = water_plan(775, 100, 0, 0, 0, 0, 6)
        self.assertEqual(result["hydration_flush_each_ml"], 115)
        self.assertEqual(result["hydration_flush_total_ml"], 690)

    def test_water_plan_totals_each_water_source_once(self):
        result = water_plan(1900, 879.75, 0, 60, 120, 0, 6)
        # (1900 - 879.75 - 60 - 120) / 6 = 140.04, rounded to 140 mL.
        self.assertEqual(result["hydration_flush_each_ml"], 140)
        self.assertEqual(result["hydration_flush_total_ml"], 840)
        self.assertAlmostEqual(result["total_water_ml"], 1899.75)

    def test_q4h_hydration_means_six_flushes_over_24_hours(self):
        self.assertEqual(hydration_flushes_per_day("qXh", 4), 6)

    def test_common_qxh_intervals_resolve_over_24_hours(self):
        expected = {1: 24, 2: 12, 3: 8, 4: 6, 6: 4, 8: 3, 12: 2, 24: 1}
        for interval, count in expected.items():
            with self.subTest(interval=interval):
                self.assertEqual(hydration_flushes_per_day("qXh", interval), count)

    def test_qxh_and_times_per_day_produce_the_same_water_plan(self):
        q4h_count = hydration_flushes_per_day("qXh", 4)
        six_daily_count = hydration_flushes_per_day("times/day", 6)
        self.assertEqual(
            water_plan(2000, 1100, 0, 0, 100, 0, q4h_count),
            water_plan(2000, 1100, 0, 0, 100, 0, six_daily_count),
        )

    def test_propofol_uses_the_entered_hours_instead_of_assuming_24_hours(self):
        result = propofol_intake(20, 12)
        self.assertEqual(result["volume_ml"], 240)
        self.assertEqual(result["kcal"], 264)
        self.assertEqual(result["fat_g"], 24)

    def test_propofol_conditions_sum_to_one_projected_daily_exposure(self):
        result = total_propofol_intake([
            {"rate_ml_hr": 0, "hours": 18},
            {"rate_ml_hr": 20, "hours": 6},
        ])
        self.assertEqual(result["volume_ml"], 120)
        self.assertEqual(result["kcal"], 132)
        self.assertEqual(result["fat_g"], 12)

    def test_conditional_rates_preserve_the_daily_target_with_23_feeding_hours(self):
        formula = {
            "kcal_per_mL": 1.5,
            "protein_per_mL": 0.07,
            "free_water_per_mL": 0.76,
        }
        conditions = [
            {"rate_ml_hr": 0, "hours": 18},
            {"rate_ml_hr": 20, "hours": 6},
        ]
        rates = [
            suggested_conditional_formula_rate(formula, 1800, 23, item["rate_ml_hr"])
            for item in conditions
        ]
        self.assertEqual(rates, [50, 35])
        delivery = conditional_feed_delivery(formula, 23, conditions, rates)
        combined_energy = delivery["energy_kcal"] + total_propofol_intake(conditions)["kcal"]
        # Bedside rates are rounded to 5 mL/hour, so the projected total is close
        # to, rather than mathematically identical to, the unrounded target.
        self.assertAlmostEqual(delivery["planned_volume_ml"], 1063.75)
        self.assertAlmostEqual(combined_energy, 1727.625)



class UndisclosedValueTests(unittest.TestCase):
    """A blank label figure must stay distinguishable from a declared zero."""

    def test_disclosed_value_reads_real_numbers(self):
        self.assertEqual(disclosed_value(40), (40.0, True))
        self.assertEqual(disclosed_value("40"), (40.0, True))
        self.assertEqual(disclosed_value(0), (0.0, True))

    def test_disclosed_value_treats_blanks_as_undisclosed(self):
        for blank in (None, "", "   ", float("nan")):
            value, known = disclosed_value(blank)
            self.assertEqual(value, 0.0)
            self.assertFalse(known, f"{blank!r} should be undisclosed")

    def test_modular_delivery_reports_undisclosed_columns(self):
        product = {
            "basis_amount": 30, "kcal_per_basis": 60, "protein_g_per_basis": 15,
            "carbohydrate_g_per_basis": 0, "fat_g_per_basis": 0,
            "fibre_g_per_basis": 0, "sodium_mg_per_basis": 40,
            "potassium_mg_per_basis": 10, "calcium_mg_per_basis": 0,
            "magnesium_mg_per_basis": None, "phosphorus_mg_per_basis": None,
            "free_water_ml_per_basis": None,
        }
        order = modular_delivery(product, 30, 3)
        self.assertEqual(order["sodium_mg"], 120)
        self.assertEqual(order["disclosed"]["sodium_mg"], 1)
        self.assertEqual(order["disclosed"]["calcium_mg"], 1, "a declared 0 is disclosed")
        self.assertEqual(order["disclosed"]["phosphorus_mg"], 0)
        self.assertEqual(order["phosphorus_mg"], 0, "undisclosed contributes nothing")
        self.assertEqual(order["product_count"], 1)

    def test_unordered_product_is_not_a_coverage_source(self):
        product = {
            "basis_amount": 30, "kcal_per_basis": 60, "protein_g_per_basis": 15,
            "carbohydrate_g_per_basis": 0, "fat_g_per_basis": 0,
            "fibre_g_per_basis": 0, "sodium_mg_per_basis": 40,
            "potassium_mg_per_basis": 10, "calcium_mg_per_basis": 0,
            "magnesium_mg_per_basis": None, "phosphorus_mg_per_basis": None,
            "free_water_ml_per_basis": None,
        }
        order = modular_delivery(product, 0, 0)
        self.assertEqual(order["product_count"], 0)
        self.assertEqual(order["disclosed"]["sodium_mg"], 0)

    def test_total_modular_delivery_accumulates_coverage(self):
        disclosed_order = {
            "sodium_mg": 100, "phosphorus_mg": 50,
            "disclosed": {"sodium_mg": 1, "phosphorus_mg": 1}, "product_count": 1,
        }
        partial_order = {
            "sodium_mg": 40, "phosphorus_mg": 0,
            "disclosed": {"sodium_mg": 1, "phosphorus_mg": 0}, "product_count": 1,
        }
        totals = total_modular_delivery([disclosed_order, partial_order])
        self.assertEqual(totals["product_count"], 2)
        self.assertEqual(totals["sodium_mg"], 140)
        self.assertEqual(totals["disclosed"]["sodium_mg"], 2)
        self.assertEqual(totals["disclosed"]["phosphorus_mg"], 1)



class OptionalWaterGoalTests(unittest.TestCase):
    """No water goal must not produce a hydration flush order."""

    def test_no_goal_prescribes_no_hydration_flush(self):
        plan = water_plan(None, 1150, 0, 0, 200, 0, 4)
        self.assertEqual(plan["hydration_flush_each_ml"], 0)
        self.assertEqual(plan["hydration_flush_total_ml"], 0)

    def test_no_goal_still_counts_ordered_flushes(self):
        # Medication and patency flushes are ordered independently of a goal,
        # so they stay in the water ledger.
        plan = water_plan(None, 1150, 50, 30, 200, 100, 4)
        self.assertEqual(plan["water_flushes_total_ml"], 330)
        self.assertEqual(plan["total_water_ml"], 1530)

    def test_zero_goal_and_no_goal_differ_from_a_real_goal(self):
        no_goal = water_plan(None, 1150, 0, 0, 0, 0, 4)
        real_goal = water_plan(2000, 1150, 0, 0, 0, 0, 4)
        self.assertEqual(no_goal["hydration_flush_each_ml"], 0)
        self.assertGreater(real_goal["hydration_flush_each_ml"], 0)


if __name__ == "__main__":
    unittest.main()
