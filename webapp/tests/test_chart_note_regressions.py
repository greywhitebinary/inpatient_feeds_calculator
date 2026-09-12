"""Keep charted orders and nutrient sources faithful to the entered plan."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chart_note import build_chart_note_html


def note_result():
    return {
        "formula": {"name": "Test formula"},
        "delivery": {
            "energy_kcal": 1000,
            "protein_g": 50,
            "carbohydrate_g": 150,
            "fat_g": 22,
            "free_water_ml": 800,
        },
        "modular_totals": {},
        "propofol": {},
        "hydration": {},
        "schedule_description": "20 mL/hour for 23 hours daily",
        "chart_total": {
            "Energy (kcal)": 1000,
            "Protein (g)": 50,
            "Carbohydrate (g)": 150,
            "Fat (g)": 22,
            "Water (mL)": 800,
        },
    }


def add_ons(result, quantity=1, unit="carton", times=2):
    result["chart_ons"] = [
        {
            "name": "Test ONS",
            "quantity_each_time": quantity,
            "quantity_unit": unit,
            "times_per_day": times,
        }
    ]
    result["ons_totals"] = {
        "energy_kcal": 720,
        "protein_g": 28,
        "carbohydrate_g": 90,
        "fat_g": 28,
        "free_water_ml": 366,
    }
    for column, amount in {
        "Energy (kcal)": 720,
        "Protein (g)": 28,
        "Carbohydrate (g)": 90,
        "Fat (g)": 28,
        "Water (mL)": 366,
    }.items():
        result["chart_total"][column] += amount


@pytest.mark.parametrize("quantity", [0.5, 1.5])
@pytest.mark.parametrize("unit", ["carton", "cup"])
def test_fractional_ons_quantity_is_preserved_in_chart_order(quantity, unit):
    result = note_result()
    add_ons(result, quantity=quantity, unit=unit)
    note = build_chart_note_html({}, [result])
    assert f"Test ONS, {quantity:g} {unit}s BID." in note


def test_fractional_ons_frequency_is_not_rounded_to_a_different_order():
    result = note_result()
    add_ons(result, times=0.5)
    note = build_chart_note_html({}, [result])
    assert "Test ONS, 1 carton 0.5 times/day." in note


@pytest.mark.parametrize("source", ["iv", "propofol", "both"])
def test_ons_breakdown_names_non_enteral_contributions(source):
    result = note_result()
    add_ons(result)
    if source in {"iv", "both"}:
        result["iv_fluids"] = {"energy_kcal": 408, "carbohydrate_g": 120}
        result["chart_total"]["Energy (kcal)"] += 408
        result["chart_total"]["Carbohydrate (g)"] += 120
    if source in {"propofol", "both"}:
        result["propofol"] = {"kcal": 264, "fat_g": 24}
        result["chart_total"]["Energy (kcal)"] += 264
        result["chart_total"]["Fat (g)"] += 24
    note = build_chart_note_html({}, [result])
    assert "Formula 1,000 kcal" in note
    assert "ONS 720 kcal" in note
    assert "Formula 50 g + ONS 28 g" in note
    assert "EN and ONS orders provide" not in note
    if source in {"iv", "both"}:
        assert "IV fluids 408 kcal" in note
        assert "IV fluids 120 g" in note
        assert "Formula 150 g" in note
        assert "ONS 90 g" in note
    if source in {"propofol", "both"}:
        assert "Propofol 264 kcal" in note
        assert "Propofol 24 g" in note
    expected_energy = {"iv": "2,128", "propofol": "1,984", "both": "2,392"}
    assert f"provides energy {expected_energy[source]} kcal" in note


def test_simple_en_and_ons_breakdown_keeps_existing_wording():
    result = note_result()
    add_ons(result)
    note = build_chart_note_html({}, [result])
    assert "At goal, EN and ONS orders provide energy 1,720 kcal" in note
    assert "EN 1,000 kcal + ONS 720 kcal" in note


@pytest.mark.parametrize("method", [None, "Changing Propofol rates"])
def test_running_trickle_feed_is_described_as_continuing(method):
    result = note_result()
    result.update(
        regimen_already_running=True,
        describe_as_trickle=True,
        propofol_method=method,
    )
    note = build_chart_note_html({}, [result])
    assert "Continue trickle EN with Test formula" in note
    assert "Initiate" not in note


@pytest.mark.parametrize("hours", [0, 0.5, 12, 24, None])
def test_iv_chart_duration_distinguishes_zero_and_preserves_fractional_hours(hours):
    state = {
        "assessment_iv_fluid_0": "D5W",
        "assessment_iv_rate_0": 100,
        "assessment_iv_hours_0": hours,
    }
    note = build_chart_note_html(state, [])
    description = "IV D5W at 100 mL/hour"
    if hours is not None and hours != 24:
        description += f" for {hours:g} hours"
    assert description + "<br>" in note
