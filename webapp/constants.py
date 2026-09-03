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
    "Projected EN volume (mL/day)": 0,
    "Rate (mL/hour)": 0,
    "Suggested EN rate with lower/no Propofol (mL/hour)": 0,
    "Suggested EN rate with higher Propofol (mL/hour)": 0,
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


# Energy and protein are routinely set on different weights: practice commonly
# runs energy on current or adjusted body weight while protein is prescribed on
# ideal body weight. Assessment therefore offers protein its own weight
# selector, defaulting to this sentinel so an untouched case behaves exactly as
# it did when one weight drove all three figures. Water deliberately has no
# selector of its own and always follows the energy weight.
PROTEIN_WEIGHT_SAME_AS_ENERGY = "Same as energy weight"


# Standard maintenance intravenous fluids, per litre. Only the
# dextrose-containing fluids carry energy; the rest are listed because they
# still contribute volume, and because an RD whose fluid is missing cannot tell
# whether the tool ignored it or does not know it.
#
# Therapeutic fluids are deliberately absent. Hypertonic saline, added
# potassium and the like are given to correct a laboratory value rather than to
# maintain a patient, they run at rates and durations this section does not
# model, and they do not change how enteral nutrition is provided: where sodium
# or potassium is that critical, a site's single renal formula is already the
# answer. Adding them would invite a corrective order being entered as if it
# were a 24-hour maintenance infusion.
#
# Dextrose is supplied as the monohydrate at 3.4 kcal/g, so 5% (50 g/L) yields
# 170 kcal/L. Lactated Ringer's carries roughly 9 kcal/L from its 28 mmol/L of
# lactate; that is about 22 kcal/day at a typical rate, shown rather than
# rounded away because the column already exists.
#
# Electrolytes are held in mmol/L, which is how the bags are labelled. The
# delivery calculation converts to mg so an IV contributes to the daily intake
# table through the same path as every other source.
IV_FLUIDS: dict[str, dict[str, float]] = {
    "NS": {
        "kcal_per_l": 0.0, "dextrose_g_per_l": 0.0,
        "sodium_mmol_per_l": 154.0, "potassium_mmol_per_l": 0.0,
        "calcium_mmol_per_l": 0.0, "magnesium_mmol_per_l": 0.0,
    },
    "1/2 NS": {
        "kcal_per_l": 0.0, "dextrose_g_per_l": 0.0,
        "sodium_mmol_per_l": 77.0, "potassium_mmol_per_l": 0.0,
        "calcium_mmol_per_l": 0.0, "magnesium_mmol_per_l": 0.0,
    },
    "D5W": {
        "kcal_per_l": 170.0, "dextrose_g_per_l": 50.0,
        "sodium_mmol_per_l": 0.0, "potassium_mmol_per_l": 0.0,
        "calcium_mmol_per_l": 0.0, "magnesium_mmol_per_l": 0.0,
    },
    "D10W": {
        "kcal_per_l": 340.0, "dextrose_g_per_l": 100.0,
        "sodium_mmol_per_l": 0.0, "potassium_mmol_per_l": 0.0,
        "calcium_mmol_per_l": 0.0, "magnesium_mmol_per_l": 0.0,
    },
    "D5NS": {
        "kcal_per_l": 170.0, "dextrose_g_per_l": 50.0,
        "sodium_mmol_per_l": 154.0, "potassium_mmol_per_l": 0.0,
        "calcium_mmol_per_l": 0.0, "magnesium_mmol_per_l": 0.0,
    },
    "D5 1/2 NS": {
        "kcal_per_l": 170.0, "dextrose_g_per_l": 50.0,
        "sodium_mmol_per_l": 77.0, "potassium_mmol_per_l": 0.0,
        "calcium_mmol_per_l": 0.0, "magnesium_mmol_per_l": 0.0,
    },
    # A standard maintenance bag. The potassium here is routine maintenance,
    # not a corrective infusion for a low result, so it belongs with the other
    # maintenance fluids.
    "D5 1/2 NS + 20 mmol/L KCl": {
        "kcal_per_l": 170.0, "dextrose_g_per_l": 50.0,
        "sodium_mmol_per_l": 77.0, "potassium_mmol_per_l": 20.0,
        "calcium_mmol_per_l": 0.0, "magnesium_mmol_per_l": 0.0,
    },
    "LR": {
        "kcal_per_l": 9.0, "dextrose_g_per_l": 0.0,
        "sodium_mmol_per_l": 130.0, "potassium_mmol_per_l": 4.0,
        "calcium_mmol_per_l": 1.4, "magnesium_mmol_per_l": 0.0,
    },
    "D5LR": {
        "kcal_per_l": 179.0, "dextrose_g_per_l": 50.0,
        "sodium_mmol_per_l": 130.0, "potassium_mmol_per_l": 4.0,
        "calcium_mmol_per_l": 1.4, "magnesium_mmol_per_l": 0.0,
    },
}

# Most IV orders on a ward are a single maintenance line, but a patient on
# sedation commonly has a second. Three is more than has been needed in
# practice without turning the section into a table.
MAX_IV_FLUID_ORDERS = 3


# How water is being managed for this patient. Charting the requirement and
# prescribing flushes are separate decisions: with a line running an RD still
# charts the fluid need, as they do for protein, but does not work a flush
# schedule out of it. A blank water goal cannot express that, because it hides
# the requirement as well as the flushes.
WATER_MODE_FLUSHES = (
    "Chart water requirement range and use the water goal for EN plan "
    "to calculate hydration flushes"
)
WATER_MODE_CHART_ONLY = (
    "IV fluids running — chart water requirement range only"
)
WATER_MODES = (WATER_MODE_FLUSHES, WATER_MODE_CHART_ONLY)


# The short form of each selectable weight, matching what the chart note emits.
# Used where a figure names the weight that produced it and the full label would
# crowd the line.
WEIGHT_ACRONYMS = {
    "Current body weight": "CBW",
    "Ideal body weight (Hamwi — SI units)": "IBW",
    "Adjusted body weight (Hamwi IBW)": "AdjBW",
    "Estimated dry / clinician-selected weight": "clinician-selected weight",
}
