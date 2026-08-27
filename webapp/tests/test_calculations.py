import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculations import (
    adjusted_body_weight_kg,
    feed_delivery,
    height_to_cm,
    mifflin_st_jeor_kcal,
    water_plan,
)


class CalculationTests(unittest.TestCase):
    def test_height_conversion(self):
        self.assertAlmostEqual(height_to_cm("ft_in", feet=5, inches=10), 177.8)

    def test_adjusted_weight(self):
        self.assertEqual(adjusted_body_weight_kg(100, 70), 77.5)

    def test_mifflin_male(self):
        self.assertAlmostEqual(mifflin_st_jeor_kcal("Male", 70, 175, 40), 1598.75)

    def test_feed_delivery_uses_achieved_percentage(self):
        formula = {"kcal_per_mL": 1.5, "protein_per_mL": 0.07, "free_water_per_mL": 0.766}
        result = feed_delivery(formula, 1800, 20, 80)
        self.assertEqual(result["planned_volume_ml"], 1200)
        self.assertEqual(result["delivered_volume_ml"], 960)
        self.assertAlmostEqual(result["protein_g"], 67.2)

    def test_water_plan_rounds_hydration_flushes_to_five_ml(self):
        result = water_plan(2000, 1100, 0, 0, 100, 0, 6)
        self.assertEqual(result["hydration_flush_each_ml"], 135)
        self.assertEqual(result["total_water_ml"], 2010)


if __name__ == "__main__":
    unittest.main()
