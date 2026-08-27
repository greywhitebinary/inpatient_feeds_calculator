import sys
from pathlib import Path
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import load_master_formulas, load_master_modulars, validate_import


class FormularyImportTests(unittest.TestCase):
    def setUp(self):
        self.formulas = load_master_formulas().iloc[[0]].copy()
        self.modulars = load_master_modulars().iloc[[0]].copy()

    def test_accepts_a_complete_product_profile(self):
        formulas, modulars = validate_import(self.formulas, self.modulars)
        self.assertEqual(formulas.iloc[0]["name"], "Isosource Fibre 1.5")
        self.assertEqual(modulars.iloc[0]["name"], "Beneprotein")

    def test_rejects_a_negative_core_nutrient_value(self):
        self.formulas.loc[self.formulas.index[0], "protein_per_mL"] = -0.01
        with self.assertRaisesRegex(ValueError, "negative"):
            validate_import(self.formulas, self.modulars)

    def test_rejects_missing_source_metadata(self):
        self.formulas.loc[self.formulas.index[0], "source"] = ""
        with self.assertRaisesRegex(ValueError, "blank source"):
            validate_import(self.formulas, self.modulars)

    def test_rejects_duplicate_product_names(self):
        duplicate = self.formulas.copy()
        formulas = pd.concat([self.formulas, duplicate], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicate product names"):
            validate_import(formulas, self.modulars)

    def test_abbott_profiles_use_the_reverified_ready_to_hang_values(self):
        formulas = load_master_formulas().set_index("name")
        expected = {
            "Jevity 1.2 Cal": (1.06667, 2.39, 0.807333),
            "Jevity 1.5 Cal": (1.33, 2.18, 0.76),
            "Osmolite 1.2 Cal": (1.06667, 2.27333, 0.82),
            "TwoCal HN": (0.844, 2.11, 0.7),
        }
        for name, (sodium, potassium, free_water) in expected.items():
            with self.subTest(name=name):
                row = formulas.loc[name]
                self.assertAlmostEqual(row["sodium_per_mL"], sodium, places=5)
                self.assertAlmostEqual(row["potassium_per_mL"], potassium, places=5)
                self.assertAlmostEqual(row["free_water_per_mL"], free_water, places=5)
                self.assertIn("ready-to-hang", row["source"])
                self.assertEqual(row["verified"], "2026-08-27")


if __name__ == "__main__":
    unittest.main()
