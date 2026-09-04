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
    "Volume (mL)": 0,
    "Energy (kcal)": 0,
    "Protein (g)": 0,
    "Carbohydrate (g)": 0,
    "Fat (g)": 0,
    "Water (mL)": 0,
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
    "Chart water requirement range and use the water goal to calculate "
    "required hydration flushes"
)
WATER_MODE_CHART_ONLY = (
    "IV fluids running — chart water requirement range only"
)
WATER_MODES = (WATER_MODE_FLUSHES, WATER_MODE_CHART_ONLY)


# Which direction the plan is being worked in. Starting a feed runs from the
# assessed goal to a suggested rate. A patient already on a feed runs the other
# way: the running order is the fact, and the suggestion is only a comparison,
# so nothing may overwrite what the clinician entered.
# How the order is written down, which is a question about entry rather than
# about the feed. Each form collects a different pair of numbers and reduces to
# the same three facts: a daily volume, the feeding hours, and the feeds per
# day. Only the sentence describing the order back to the clinician reads this,
# so no calculation ever learns that forms exist.
ORDER_FORM_RATE_AND_HOURS = "A rate in mL/hour"
ORDER_FORM_VOLUME_PER_FEED = "A volume in mL per feed"
ORDER_FORM_RATE_PER_FEED = "A rate in mL/hour, run for a set time each feed"
ORDER_FORM_DAILY_TOTAL = "A total volume in mL per day"
CONTINUOUS_ORDER_FORMS = (ORDER_FORM_RATE_AND_HOURS, ORDER_FORM_DAILY_TOTAL)
INTERMITTENT_ORDER_FORMS = (
    ORDER_FORM_VOLUME_PER_FEED,
    ORDER_FORM_RATE_PER_FEED,
    ORDER_FORM_DAILY_TOTAL,
)
ORDER_FORMS = (
    ORDER_FORM_RATE_AND_HOURS,
    ORDER_FORM_VOLUME_PER_FEED,
    ORDER_FORM_RATE_PER_FEED,
    ORDER_FORM_DAILY_TOTAL,
)


# Transcribing an order that already exists asks one question rather than a
# schedule and then a form nested inside it. These three cover every way an
# order is written, and each decides both facts at once.
RUNNING_CONTINUOUS = "Continuous, at a rate over so many hours"
RUNNING_RATE_PER_FEED = "Intermittent, each feed run at a rate for a set time"
RUNNING_VOLUME_PER_FEED = "Intermittent, each feed a set volume"
RUNNING_SHAPES = (
    RUNNING_CONTINUOUS, RUNNING_RATE_PER_FEED, RUNNING_VOLUME_PER_FEED,
)
RUNNING_SHAPE_MEANINGS = {
    RUNNING_CONTINUOUS: ("Continuous / cyclic", ORDER_FORM_RATE_AND_HOURS),
    RUNNING_RATE_PER_FEED: ("Intermittent", ORDER_FORM_RATE_PER_FEED),
    RUNNING_VOLUME_PER_FEED: ("Intermittent", ORDER_FORM_VOLUME_PER_FEED),
}


REGIMEN_SOURCE_NEW = "Starting a new feed"
REGIMEN_SOURCE_EXISTING = "Reviewing a feed already running"
REGIMEN_SOURCES = (REGIMEN_SOURCE_NEW, REGIMEN_SOURCE_EXISTING)


# How the hydration flush volume is arrived at. The calculated mode divides a
# goal-driven remainder across a frequency. The ordered mode records flushes
# that are already running, which no goal can be back-solved from.
HYDRATION_ENTRY_CALCULATED = "Calculate flushes from the water goal"
HYDRATION_ENTRY_ORDERED = "Enter flushes as ordered"
HYDRATION_ENTRY_MODES = (HYDRATION_ENTRY_CALCULATED, HYDRATION_ENTRY_ORDERED)


# A peri-feed flush is written against each feed rather than against the clock,
# so its daily count follows the number of feeds instead of a frequency.
PERI_FEED_FLUSH_NONE = "No peri-feed flushes"
PERI_FEED_FLUSH_BEFORE = "Before each feed"
PERI_FEED_FLUSH_AFTER = "After each feed"
PERI_FEED_FLUSH_BOTH = "Before and after each feed"
PERI_FEED_FLUSH_PATTERNS = (
    PERI_FEED_FLUSH_NONE,
    PERI_FEED_FLUSH_BEFORE,
    PERI_FEED_FLUSH_AFTER,
    PERI_FEED_FLUSH_BOTH,
)
PERI_FEED_FLUSHES_PER_FEED = {
    PERI_FEED_FLUSH_NONE: 0,
    PERI_FEED_FLUSH_BEFORE: 1,
    PERI_FEED_FLUSH_AFTER: 1,
    PERI_FEED_FLUSH_BOTH: 2,
}


# The short form of each selectable weight, matching what the chart note emits.
# Used where a figure names the weight that produced it and the full label would
# crowd the line.
WEIGHT_ACRONYMS = {
    "Current body weight": "CBW",
    "Ideal body weight (Hamwi — SI units)": "IBW",
    "Adjusted body weight (Hamwi IBW)": "AdjBW",
    "Estimated dry / clinician-selected weight": "clinician-selected weight",
}
