"""Independent arithmetic examples for the planned and displayed intake views."""

import sys
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plan_sources import IntakeSources, build_intake_rows, calculate_intake


@pytest.fixture
def formula_delivery():
    # One litre, with 10/20/30/40/50 mmol of Na/K/Ca/P/Mg respectively.
    return {
        "delivered_volume_ml": 1000,
        "energy_kcal": 1500,
        "protein_g": 60,
        "carbohydrate_g": 180,
        "fat_g": 60,
        "free_water_ml": 750,
        "sodium_mg": 229.9,
        "potassium_mg": 782,
        "calcium_mg": 1202.34,
        "phosphorus_mg": 1238.96,
        "magnesium_mg": 1215.25,
    }


@pytest.fixture
def sources():
    return IntakeSources(
        formula_name="Example formula",
        modular_totals={
            "preparation_water_ml": 120,
            "energy_kcal": 100,
            "protein_g": 25,
            "carbohydrate_g": 0,
            "fat_g": 0,
            "free_water_ml": 20,
            "sodium_mg": 22.99,
            "potassium_mg": 78.2,
            "calcium_mg": 120.234,
            "phosphorus_mg": 123.896,
            "magnesium_mg": 121.525,
            "disclosed": {
                "sodium_mg": 1,
                "potassium_mg": 1,
                "calcium_mg": 1,
                "phosphorus_mg": 1,
                "magnesium_mg": 1,
            },
        },
        ons_totals={
            "daily_volume_ml": 240,
            "energy_kcal": 300,
            "protein_g": 15,
            "carbohydrate_g": 40,
            "fat_g": 10,
            "free_water_ml": 180,
            "sodium_mg": 45.98,
            "potassium_mg": 117.3,
            "calcium_mg": 160.312,
            "phosphorus_mg": 154.87,
            "magnesium_mg": 145.83,
        },
        iv_fluids={
            "volume_ml": 1000,
            "energy_kcal": 170,
            "carbohydrate_g": 50,
            "sodium_mg": 3540.46,
            "potassium_mg": 782,
            "calcium_mg": 60.117,
            "magnesium_mg": 48.61,
        },
        propofol={"volume_ml": 200, "kcal": 220, "fat_g": 20},
        include_modulars=True,
        include_ons=True,
        other_water_flushes=300,
    )


def test_full_and_partial_formula_have_independent_expected_totals(
    formula_delivery, sources
):
    half_formula = {key: value / 2 for key, value in formula_delivery.items()}
    result = calculate_intake(formula_delivery, half_formula, sources)

    assert result.planned_total == pytest.approx(
        {
            "Volume (mL)": 2860,
            "Energy (kcal)": 2290,
            "Protein (g)": 100,
            "Carbohydrate (g)": 270,
            "Fat (g)": 90,
            "Water (mL)": 1370,
            "Na (mmol)": 167,
            "K (mmol)": 45,
            "Ca (mmol)": 38.5,
            "P (mmol)": 49,
            "Mg (mmol)": 63,
            "Fibre (g)": 0,
        }
    )
    assert result.displayed_total == pytest.approx(
        {
            "Volume (mL)": 2360,
            "Energy (kcal)": 1540,
            "Protein (g)": 70,
            "Carbohydrate (g)": 180,
            "Fat (g)": 60,
            "Water (mL)": 995,
            "Na (mmol)": 162,
            "K (mmol)": 35,
            "Ca (mmol)": 23.5,
            "P (mmol)": 29,
            "Mg (mmol)": 38,
            "Fibre (g)": 0,
        }
    )
    assert result.displayed_rows[1:] == result.planned_rows[1:]
    assert [row["Source"] for row in result.planned_rows] == [
        "Example formula",
        "Modulars",
        "Propofol",
        "IV fluids",
        "ONS",
        "Water flushes",
    ]


def test_iv_electrolytes_count_but_iv_and_propofol_water_do_not(
    formula_delivery, sources
):
    rows = {row["Source"]: row for row in build_intake_rows(formula_delivery, sources)}
    iv = rows["IV fluids"]
    assert {
        key: value for key, value in iv.items() if key != "Source"
    } == pytest.approx(
        {
            "Volume (mL)": 1000,
            "Energy (kcal)": 170,
            "Protein (g)": 0,
            "Carbohydrate (g)": 50,
            "Fat (g)": 0,
            "Water (mL)": 0,
            "Na (mmol)": 154,
            "K (mmol)": 20,
            "Ca (mmol)": 1.5,
            "P (mmol)": 0,
            "Mg (mmol)": 2,
            "Fibre (g)": 0,
        }
    )
    assert rows["Propofol"]["Volume (mL)"] == 200
    assert rows["Propofol"]["Water (mL)"] == 0
    assert rows["Modulars"]["Volume (mL)"] == 120
    assert rows["Modulars"]["Water (mL)"] == 140
    assert rows["Water flushes"]["Water (mL)"] == 300


def test_undisclosed_modular_minerals_remain_distinct_from_disclosed_zero(
    formula_delivery, sources
):
    modulars = dict(sources.modular_totals)
    modulars["sodium_mg"] = 0
    modulars["disclosed"] = {"sodium_mg": 1}
    result = calculate_intake(
        formula_delivery,
        formula_delivery,
        replace(sources, modular_totals=modulars),
    )
    modular_row = result.displayed_rows[1]
    assert modular_row["Na (mmol)"] == 0
    for mineral in ("K (mmol)", "Ca (mmol)", "P (mmol)", "Mg (mmol)"):
        assert modular_row[mineral] is None
    # Unknown modular amounts are excluded from the sum; known sources remain.
    assert result.displayed_total["Na (mmol)"] == pytest.approx(166)
    assert result.displayed_total["K (mmol)"] == pytest.approx(43)
    assert result.displayed_total["Ca (mmol)"] == pytest.approx(35.5)
    assert result.displayed_total["P (mmol)"] == pytest.approx(45)
    assert result.displayed_total["Mg (mmol)"] == pytest.approx(58)


def test_unselected_optional_sources_are_absent_and_zero_flush_row_remains(
    formula_delivery, sources
):
    unused = replace(
        sources,
        include_modulars=False,
        include_ons=False,
        iv_fluids={**sources.iv_fluids, "volume_ml": 0, "energy_kcal": 0},
        propofol={**sources.propofol, "kcal": 0},
        other_water_flushes=0,
    )
    result = calculate_intake(formula_delivery, formula_delivery, unused)
    assert [row["Source"] for row in result.displayed_rows] == [
        "Example formula",
        "Water flushes",
    ]
    assert result.displayed_total["Energy (kcal)"] == 1500
    assert result.displayed_total["Volume (mL)"] == 1000
    assert result.displayed_total["Water (mL)"] == 750
    assert result.displayed_total == result.planned_total


@pytest.mark.parametrize("energy,volume", [(0, 1000), (170, 0)])
def test_iv_row_is_present_for_either_energy_or_volume(
    formula_delivery, sources, energy, volume
):
    iv = {**sources.iv_fluids, "energy_kcal": energy, "volume_ml": volume}
    rows = build_intake_rows(formula_delivery, replace(sources, iv_fluids=iv))
    assert "IV fluids" in [row["Source"] for row in rows]


def test_missing_formula_minerals_keep_existing_zero_fallback(
    formula_delivery, sources
):
    delivery = {
        key: value for key, value in formula_delivery.items() if not key.endswith("_mg")
    }
    formula = build_intake_rows(delivery, sources)[0]
    for mineral in ("Na (mmol)", "K (mmol)", "Ca (mmol)", "P (mmol)", "Mg (mmol)"):
        assert formula[mineral] == 0


def test_inputs_are_unchanged_and_result_rows_are_independent(
    formula_delivery, sources
):
    original_delivery = deepcopy(formula_delivery)
    original_sources = deepcopy(sources)
    result = calculate_intake(formula_delivery, formula_delivery, sources)
    result.displayed_rows[0]["Energy (kcal)"] = -1
    result.displayed_rows[1]["Energy (kcal)"] = -2
    assert formula_delivery == original_delivery
    assert sources == original_sources
    assert result.planned_rows[0]["Energy (kcal)"] == 1500
    assert result.planned_rows[1]["Energy (kcal)"] == 100
    with pytest.raises(FrozenInstanceError):
        sources.formula_name = "Replaced"


def test_goal_water_preserves_original_rounding_at_half_ml(formula_delivery, sources):
    formula_delivery["free_water_ml"] = 1243.9
    sources.modular_totals["free_water_ml"] = 80.7
    sources.modular_totals["preparation_water_ml"] = 38.4
    sources.ons_totals["free_water_ml"] = 171.9
    sources = replace(sources, other_water_flushes=399.6)
    result = calculate_intake(formula_delivery, formula_delivery, sources)
    assert format(result.goal_comparison_total["Water (mL)"], ".0f") == "1935"
    assert format(result.displayed_total["Water (mL)"], ".0f") == "1934"


def test_goal_comparison_does_not_depend_on_formula_display_name(
    formula_delivery, sources
):
    normal = calculate_intake(formula_delivery, formula_delivery, sources)
    renamed = replace(sources, formula_name="Modulars", include_modulars=False)
    result = calculate_intake(formula_delivery, formula_delivery, renamed)
    assert result.goal_comparison_total == normal.goal_comparison_total
