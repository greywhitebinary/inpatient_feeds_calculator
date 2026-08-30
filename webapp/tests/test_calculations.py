import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculations import (
    adjusted_body_weight_kg,
    devine_ibw_kg,
    feed_delivery,
    height_to_cm,
    hydration_flushes_per_day,
    mifflin_st_jeor_kcal,
    modular_delivery,
    ordered_feed_delivery,
    penn_state_2003b_kcal,
    penn_state_2010_kcal,
    practical_feed_delivery,
    propofol_intake,
    water_plan,
)


class CalculationTests(unittest.TestCase):
    def test_height_conversion(self):
        self.assertAlmostEqual(height_to_cm("ft_in", feet=5, inches=10), 177.8)

    def test_adjusted_weight(self):
        self.assertEqual(adjusted_body_weight_kg(100, 70), 77.5)

    def test_devine_medication_dosing_reference_weight(self):
        self.assertAlmostEqual(devine_ibw_kg("Female", 165), 56.91, places=2)
        self.assertAlmostEqual(devine_ibw_kg("Male", 180), 74.99, places=2)

    def test_mifflin_male(self):
        self.assertAlmostEqual(mifflin_st_jeor_kcal("Male", 70, 175, 40), 1598.75)

    def test_both_penn_state_equations(self):
        self.assertAlmostEqual(penn_state_2003b_kcal(1500, 37, 8), 1655)
        self.assertAlmostEqual(penn_state_2010_kcal(1500, 37, 8), 1637)

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

    def test_practical_continuous_delivery_rounds_the_pump_rate_to_five_ml(self):
        formula = {"kcal_per_mL": 1.5, "protein_per_mL": 0.07, "free_water_per_mL": 0.766}
        result = practical_feed_delivery(formula, 1900, 20)
        self.assertEqual(result["ordered_rate_ml_hr"], 65)
        self.assertEqual(result["planned_volume_ml"], 1300)
        self.assertEqual(result["energy_kcal"], 1950)

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


if __name__ == "__main__":
    unittest.main()
