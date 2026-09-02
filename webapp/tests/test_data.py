import sys
from io import BytesIO
from pathlib import Path
import unittest

import pandas as pd
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import (
    MODULAR_PATH,
    export_formulary_workbook,
    import_formulary_workbook,
    load_master_formulas,
    load_master_modulars,
    load_master_ons,
    validate_import,
)


class FormularyImportTests(unittest.TestCase):
    def setUp(self):
        self.formulas = load_master_formulas().iloc[[0]].copy()
        self.modulars = load_master_modulars().iloc[[0]].copy()
        self.ons = load_master_ons().iloc[[0]].copy()

    def test_accepts_a_complete_product_profile(self):
        formulas, modulars, ons = validate_import(
            self.formulas, self.modulars, self.ons
        )
        self.assertEqual(formulas.iloc[0]["name"], "Isosource Fibre 1.5")
        self.assertEqual(modulars.iloc[0]["name"], "Beneprotein")
        self.assertEqual(ons.iloc[0]["name"], "Ensure Advance — Vanilla")

    def test_downloaded_formulary_reimports_without_changing_products(self):
        formulas = load_master_formulas()
        modulars = load_master_modulars()
        ons = load_master_ons()

        payload = export_formulary_workbook(formulas, modulars, ons)
        restored_formulas, restored_modulars, restored_ons = import_formulary_workbook(
            BytesIO(payload)
        )

        pd.testing.assert_frame_equal(
            restored_formulas.reset_index(drop=True), formulas.reset_index(drop=True),
            check_dtype=False,
        )
        pd.testing.assert_frame_equal(
            restored_modulars.reset_index(drop=True), modulars.reset_index(drop=True),
            check_dtype=False,
        )
        pd.testing.assert_frame_equal(
            restored_ons.reset_index(drop=True), ons.reset_index(drop=True),
            check_dtype=False,
        )

    def test_legacy_ons_sheet_without_serving_columns_remains_importable(self):
        legacy_ons = self.ons.drop(columns=[
            "calculation_basis", "serving_size_g", "serving_unit",
            "kcal_per_serving", "protein_g_per_serving", "fat_g_per_serving",
            "carbohydrate_g_per_serving", "fibre_g_per_serving",
            "sodium_mg_per_serving", "potassium_mg_per_serving",
            "calcium_mg_per_serving", "magnesium_mg_per_serving",
            "phosphorus_mg_per_serving", "free_water_ml_per_serving",
        ])
        _, _, restored_ons = validate_import(self.formulas, self.modulars, legacy_ons)
        self.assertEqual(restored_ons.iloc[0]["calculation_basis"], "container_ml")

    def test_legacy_two_sheet_formulary_opens_with_an_empty_ons_list(self):
        payload = export_formulary_workbook(self.formulas, self.modulars)
        workbook = load_workbook(BytesIO(payload))
        del workbook["My ONS"]
        legacy = BytesIO()
        workbook.save(legacy)
        formulas, modulars, ons = import_formulary_workbook(
            BytesIO(legacy.getvalue())
        )
        self.assertEqual(len(formulas), 1)
        self.assertEqual(len(modulars), 1)
        self.assertTrue(ons.empty)

    def test_ons_library_uses_separate_flavour_rows(self):
        ons = load_master_ons()
        self.assertEqual(len(ons), 54)
        boost = ons.loc[ons["product_name"] == "BOOST Plus Calories"]
        self.assertEqual(
            set(boost["flavour"]), {"Vanilla", "Chocolate", "Strawberry"}
        )
        for product in ("Ensure Regular", "Ensure Plus Calories"):
            flavours = set(
                ons.loc[ons["product_name"] == product, "flavour"]
            )
            self.assertIn("Butter Pecan", flavours)
        glucerna = ons.loc[ons["product_name"] == "Glucerna nutritional drink"]
        self.assertEqual(
            set(glucerna["flavour"]),
            {"Vanilla", "Chocolate", "Strawberry", "Mixed Berry"},
        )
        self.assertEqual(len(glucerna), 4)
        glucerna_vanilla = glucerna.loc[glucerna["flavour"] == "Vanilla"].iloc[0]
        self.assertAlmostEqual(
            glucerna_vanilla["kcal_per_mL"] * glucerna_vanilla["container_size_ml"],
            225,
            places=3,
        )
        self.assertAlmostEqual(
            glucerna_vanilla["protein_per_mL"] * glucerna_vanilla["container_size_ml"],
            11.3,
            places=3,
        )
        vanilla = boost.loc[boost["flavour"] == "Vanilla"].iloc[0]
        self.assertAlmostEqual(
            vanilla["kcal_per_mL"] * vanilla["container_size_ml"], 360,
            places=3,
        )
        self.assertAlmostEqual(
            vanilla["protein_per_mL"] * vanilla["container_size_ml"], 14,
            places=3,
        )
        pudding = ons.loc[ons["product_name"] == "BOOST Pudding"]
        self.assertEqual(set(pudding["flavour"]), {"Vanilla", "Chocolate"})
        self.assertTrue((pudding["calculation_basis"] == "serving").all())
        self.assertTrue((pudding["serving_size_g"] == 142).all())
        self.assertTrue((pudding["free_water_ml_per_serving"] == 93).all())

    def test_boost_just_protein_is_a_modular_protein_flush(self):
        modulars = load_master_modulars().set_index("id")
        row = modulars.loc["nestle-boost-just-protein"]
        self.assertEqual(row["name"], "BOOST Just Protein")
        self.assertEqual(row["dose_unit"], "scoop")
        self.assertEqual(row["basis_amount"], 3)
        self.assertEqual(row["protein_g_per_basis"], 18)
        self.assertIn("protein flush", row["administration_note"])

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

    def test_rejects_missing_modular_electrolyte_column(self):
        modulars = self.modulars.drop(columns=["sodium_mg_per_basis"])
        with self.assertRaisesRegex(ValueError, "sodium_mg_per_basis"):
            validate_import(self.formulas, modulars)

    def test_rejects_malformed_required_modular_value(self):
        modulars = self.modulars.astype({"basis_amount": "object"}).copy()
        modulars.loc[modulars.index[0], "basis_amount"] = "not-a-number"
        with self.assertRaisesRegex(ValueError, "basis_amount"):
            validate_import(self.formulas, modulars)

    def test_rejects_zero_formula_energy_density(self):
        self.formulas.loc[self.formulas.index[0], "kcal_per_mL"] = 0
        with self.assertRaisesRegex(ValueError, "greater than zero.*kcal_per_mL"):
            validate_import(self.formulas, self.modulars)

    def test_rejects_zero_modular_basis(self):
        self.modulars.loc[self.modulars.index[0], "basis_amount"] = 0
        with self.assertRaisesRegex(ValueError, "greater than zero.*basis_amount"):
            validate_import(self.formulas, self.modulars)

    def test_rejects_malformed_present_modular_electrolyte_value(self):
        modulars = self.modulars.astype({"sodium_mg_per_basis": "object"}).copy()
        modulars.loc[modulars.index[0], "sodium_mg_per_basis"] = "not-a-number"
        with self.assertRaisesRegex(ValueError, "sodium_mg_per_basis"):
            validate_import(self.formulas, modulars)

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

    def test_medtrition_profiles_use_the_canadian_product_sheets(self):
        modulars = load_master_modulars().set_index("id")
        expected = {
            "medtrition-prosource-nocarb": (60, 15, 0, "label_directed"),
            "medtrition-hifibre": (30, 0, 12, "rd_entered"),
            "medtrition-banatrall-gos": (40, 0, 2, "rd_entered"),
        }
        for product_id, (energy, protein, fibre, water_rule) in expected.items():
            with self.subTest(product_id=product_id):
                row = modulars.loc[product_id]
                self.assertEqual(row["kcal_per_basis"], energy)
                self.assertEqual(row["protein_g_per_basis"], protein)
                self.assertEqual(row["fibre_g_per_basis"], fibre)
                self.assertEqual(row["preparation_water_rule"], water_rule)
                self.assertEqual(row["verified"], "2026-08-31")

        raw = pd.read_csv(MODULAR_PATH).set_index("id")
        for product_id in expected:
            self.assertTrue(pd.isna(raw.loc[product_id, "free_water_ml_per_basis"]))

    def test_boost_just_protein_is_a_tube_compatible_modular(self):
        modulars = load_master_modulars().set_index("id")
        row = modulars.loc["nestle-boost-just-protein"]
        self.assertEqual(row["basis_amount"], 3)
        self.assertEqual(row["basis_description"], "3 scoops (21 g)")
        self.assertEqual(row["kcal_per_basis"], 80)
        self.assertEqual(row["protein_g_per_basis"], 18)
        self.assertEqual(row["preparation_water_rule"], "rd_entered")
        self.assertIn("2026_nestle-product-guide.pdf p.16", row["source"])


if __name__ == "__main__":
    unittest.main()
