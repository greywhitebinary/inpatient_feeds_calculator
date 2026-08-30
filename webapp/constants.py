"""Shared display and session-state constants for the EN calculator."""

from __future__ import annotations

KG_PER_LB = 0.45359237
MEASUREMENT_ENTRY_KEYS = {
    "assessment_height_cm_entry",
    "assessment_current_weight_kg_entry",
    "assessment_usual_weight_kg_entry",
}

PLAN_GOALS = (
    {
        "name": "energy",
        "label": "Energy",
        "assessment_key": "assessment_energy_target",
        "en_key": "en_total_energy_target",
        "icu_key": "icu_total_energy_target",
        "handoff_key": "energy_target",
        "unit": "kcal/day",
        "step": 25.0,
    },
    {
        "name": "protein",
        "label": "Protein",
        "assessment_key": "assessment_protein_target",
        "en_key": "en_protein_target",
        "icu_key": "icu_protein_target",
        "handoff_key": "protein_target",
        "unit": "g/day",
        "step": 1.0,
    },
    {
        "name": "water",
        "label": "Water",
        "assessment_key": "assessment_water_target",
        "en_key": "en_water_target",
        "icu_key": "icu_water_target",
        "handoff_key": "water_target",
        "unit": "mL/day",
        "step": 25.0,
    },
)

FORMULARY_TABLE_DECIMALS = {
    "Energy\nkcal/mL": 1,
    "Protein\ng/L": 1,
    "Free water\nmL/L": 0,
    "Na\nmmol/L": 1,
    "K\nmmol/L": 1,
    "Ca\nmmol/L": 1,
    "P\nmmol/L": 1,
    "Mg\nmmol/L": 1,
    "Fibre\ng/L": 1,
}

FORMULA_COMPARISON_DECIMALS = {
    "Volume (mL/day)": 0,
    "Rate (mL/hour)": 0,
    "Volume/feed (mL)": 0,
    "Energy (kcal/day)": 0,
    "Protein (g/day)": 0,
    "Free water (mL/day)": 0,
    "Na (mmol/day)": 1,
    "K (mmol/day)": 1,
    "Ca (mmol/day)": 1,
    "P (mmol/day)": 1,
    "Mg (mmol/day)": 1,
}

PLAN_CHECK_DECIMALS = {
    "Goal": 0,
    "From feed": 0,
    "Planned total": 0,
    "Estimated total": 0,
}

DAILY_INTAKE_DECIMALS = {
    "Energy (kcal)": 0,
    "Protein (g)": 0,
    "Carbohydrate (g)": 0,
    "Fat (g)": 0,
    "Free water (mL)": 0,
    "Water flushes (mL)": 0,
    "Na (mmol)": 1,
    "K (mmol)": 1,
    "Ca (mmol)": 1,
    "P (mmol)": 1,
    "Mg (mmol)": 1,
}

PROPOFOL_COMPARISON_ROW_DECIMALS = {
    "Propofol rate (mL/hour)": 1,
    "Hours at this rate": 1,
    "Propofol volume (mL/day)": 0,
    "Propofol energy (kcal/day)": 0,
    "Formula energy allocation (kcal/day)": 0,
    "Total energy (kcal/day)": 0,
    "Total protein (g/day)": 0,
    "Total fat (g/day)": 0,
}

PROPOFOL_SCENARIOS = (
    ("lower", "Lower/no propofol"),
    ("higher", "Higher propofol"),
)
