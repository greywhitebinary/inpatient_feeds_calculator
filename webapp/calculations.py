"""Pure, inspectable calculations for the Adult Inpatient EN Calculator.

These functions organize arithmetic for clinician review; they do not select a
formula or prescribe a nutrition regimen.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Mapping


ATOMIC_WEIGHTS_MG_PER_MMOL = {
    "sodium": 22.99,
    "potassium": 39.10,
    "calcium": 40.078,
    "phosphorus": 30.974,
    "magnesium": 24.305,
}


def height_to_cm(unit: str, metres: float | None = None, feet: int | None = None,
                 inches: float | None = None) -> float:
    """Convert a height entry to centimetres."""
    if unit == "m":
        return (metres or 0) * 100
    return ((feet or 0) * 12 + (inches or 0)) * 2.54


def hamwi_ibw_kg(sex: str, height_cm: float) -> float:
    """Return Hamwi ideal body weight in kg for an adult height."""
    inches_over_five_feet = (height_cm / 2.54) - 60
    if sex == "Male":
        return 48.0 + (2.7 * inches_over_five_feet)
    return 45.5 + (2.2 * inches_over_five_feet)


def devine_ibw_kg(sex: str, height_cm: float) -> float:
    """Return the historical Devine medication-dosing reference weight."""
    inches_over_five_feet = (height_cm / 2.54) - 60
    return (50.0 if sex == "Male" else 45.5) + 2.3 * inches_over_five_feet


def adjusted_body_weight_kg(current_kg: float, ibw_kg: float,
                            correction_factor: float = 0.25) -> float:
    return ibw_kg + correction_factor * (current_kg - ibw_kg)


def mifflin_st_jeor_kcal(sex: str, weight_kg: float, height_cm: float,
                          age_years: float) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age_years
    return base + (5 if sex == "Male" else -161)


def harris_benedict_kcal(sex: str, weight_kg: float, height_cm: float,
                          age_years: float) -> float:
    if sex == "Male":
        return 88.362 + 13.397 * weight_kg + 4.799 * height_cm - 5.677 * age_years
    return 447.593 + 9.247 * weight_kg + 3.098 * height_cm - 4.330 * age_years


def penn_state_2003b_kcal(mifflin_kcal: float, temperature_c: float,
                           minute_ventilation_l_min: float) -> float:
    """Penn State 2003b estimate for ventilated adults.

    The interface displays this equation when temperature and minute
    ventilation are entered, and the clinician determines applicability.
    """
    return 0.96 * mifflin_kcal + 167 * temperature_c + 31 * minute_ventilation_l_min - 6212


def penn_state_2010_kcal(mifflin_kcal: float, temperature_c: float,
                         minute_ventilation_l_min: float) -> float:
    """Return modified Penn State 2010 for clinician review alongside 2003b."""
    return 0.71 * mifflin_kcal + 85 * temperature_c + 64 * minute_ventilation_l_min - 3085


def propofol_intake(rate_ml_hr: float, hours_per_day: float = 24) -> dict[str, float]:
    """Calculate intake using 1.1 kcal and 0.1 g fat per mL of propofol emulsion."""
    volume_ml = rate_ml_hr * hours_per_day
    return {"volume_ml": volume_ml, "kcal": volume_ml * 1.1, "fat_g": volume_ml * 0.1}


def total_propofol_intake(
    conditions: list[dict[str, float]],
) -> dict[str, float]:
    """Sum projected propofol exposure across rate-and-duration conditions."""
    totals = {"volume_ml": 0.0, "kcal": 0.0, "fat_g": 0.0}
    for condition in conditions:
        contribution = propofol_intake(
            max(float(condition.get("rate_ml_hr", 0)), 0),
            max(float(condition.get("hours", 0)), 0),
        )
        for key in totals:
            totals[key] += contribution[key]
    return totals


def suggested_conditional_formula_rate(
    formula: Mapping[str, object],
    energy_target_kcal: float,
    feeding_hours: float,
    propofol_rate_ml_hr: float,
) -> float:
    """Return a 5-mL-rounded EN rate for one propofol condition.

    Propofol exposure is projected over a 24-hour clock day. Formula-running
    hours are distributed proportionally across the conditions, so a 23-hour
    EN schedule does not require the clinician to enter a second set of hours.
    """
    safe_feeding_hours = max(float(feeding_hours), 0)
    kcal_per_ml = float(formula["kcal_per_mL"])
    if safe_feeding_hours == 0 or kcal_per_ml <= 0:
        return 0.0
    hourly_formula_kcal = (
        max(float(energy_target_kcal), 0) / safe_feeding_hours
        - max(float(propofol_rate_ml_hr), 0) * 1.1 * 24 / safe_feeding_hours
    )
    unrounded_rate = max(hourly_formula_kcal, 0) / kcal_per_ml
    return floor(unrounded_rate / 5 + 0.5) * 5


def conditional_feed_delivery(
    formula: Mapping[str, object],
    feeding_hours: float,
    conditions: list[dict[str, float]],
    formula_rates_ml_hr: list[float],
    achieved_percent: float = 100,
) -> dict[str, float]:
    """Aggregate formula delivery across conditional propofol-linked rates."""
    if len(conditions) != len(formula_rates_ml_hr):
        raise ValueError("Each propofol condition requires one formula rate.")
    total_condition_hours = sum(max(float(item.get("hours", 0)), 0) for item in conditions)
    safe_feeding_hours = max(float(feeding_hours), 0)
    if total_condition_hours <= 0 or safe_feeding_hours <= 0:
        return ordered_feed_delivery(formula, 0, safe_feeding_hours, achieved_percent)

    deliveries = []
    for condition, rate in zip(conditions, formula_rates_ml_hr):
        condition_hours = max(float(condition.get("hours", 0)), 0)
        allocated_feeding_hours = safe_feeding_hours * condition_hours / total_condition_hours
        deliveries.append(
            ordered_feed_delivery(
                formula,
                max(float(rate), 0),
                allocated_feeding_hours,
                achieved_percent,
            )
        )

    result: dict[str, float] = {}
    additive_keys = {
        "planned_volume_ml", "delivered_volume_ml", "energy_kcal", "protein_g",
        "carbohydrate_g", "fat_g", "fibre_g", "free_water_ml", "sodium_mg",
        "potassium_mg", "calcium_mg", "magnesium_mg", "phosphorus_mg",
    }
    for key in additive_keys:
        result[key] = sum(delivery.get(key, 0) for delivery in deliveries)
    result["rate_ml_hr"] = result["planned_volume_ml"] / safe_feeding_hours
    result["ordered_rate_ml_hr"] = result["rate_ml_hr"]
    result["ordered_volume_per_feed_ml"] = 0.0
    return result


def open_abdomen_protein_loss_g(exudate_ml_day: float, factor_g_l: float) -> float:
    return exudate_ml_day / 1000 * factor_g_l


def mg_to_mmol(element: str, milligrams: float) -> float:
    return milligrams / ATOMIC_WEIGHTS_MG_PER_MMOL[element]


def disclosed_value(raw: object) -> tuple[float, bool]:
    """Split a product cell into its value and whether the label declared it.

    A blank cell means the manufacturer did not disclose the figure, which is
    not the same as a declared zero. An undisclosed value contributes nothing to
    a total, but it is reported separately so the total can be shown as a lower
    bound rather than a measured amount. See
    formula_sources/DATA_CONVENTIONS.md section 1.
    """
    if raw is None:
        return 0.0, False
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return 0.0, False
        raw = text
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0, False
    if value != value:  # NaN, which is how pandas carries a blank cell
        return 0.0, False
    return value, True


def feed_delivery(formula: Mapping[str, object], en_energy_target_kcal: float,
                  hours_per_day: float, achieved_percent: float = 100) -> dict[str, float]:
    """Calculate formula volume, rate, and nutrient delivery for one day."""
    kcal_per_ml = float(formula["kcal_per_mL"])
    if kcal_per_ml <= 0:
        raise ValueError("Formula kcal_per_mL must be greater than zero.")
    planned_volume = en_energy_target_kcal / kcal_per_ml
    delivered_volume = planned_volume * achieved_percent / 100
    result = {
        "planned_volume_ml": planned_volume,
        "delivered_volume_ml": delivered_volume,
        "rate_ml_hr": planned_volume / hours_per_day if hours_per_day else 0,
        "energy_kcal": delivered_volume * kcal_per_ml,
    }
    for nutrient, column in {
        "protein_g": "protein_per_mL",
        "carbohydrate_g": "carbohydrate_per_mL",
        "fat_g": "fat_per_mL",
        "fibre_g": "fibre_per_mL",
        "free_water_ml": "free_water_per_mL",
        "sodium_mg": "sodium_per_mL",
        "potassium_mg": "potassium_per_mL",
        "calcium_mg": "calcium_per_mL",
        "magnesium_mg": "magnesium_per_mL",
        "phosphorus_mg": "phosphorus_per_mL",
    }.items():
        value = formula.get(column, 0)
        result[nutrient] = delivered_volume * float(value or 0)
    return result


def practical_feed_delivery(formula: Mapping[str, object], en_energy_target_kcal: float,
                            hours_per_day: float, achieved_percent: float = 100,
                            schedule_type: str = "Continuous / cyclic",
                            feeds_per_day: int = 1) -> dict[str, float]:
    """Calculate delivery from a pump- or feed-volume order rounded to 5 mL."""
    unrounded = feed_delivery(formula, en_energy_target_kcal, hours_per_day, 100)
    kcal_per_ml = float(formula["kcal_per_mL"])
    if schedule_type == "Continuous / cyclic":
        ordered_rate = floor(unrounded["rate_ml_hr"] / 5 + 0.5) * 5
        ordered_volume = ordered_rate * hours_per_day
        result = feed_delivery(formula, ordered_volume * kcal_per_ml, hours_per_day, achieved_percent)
        result["ordered_rate_ml_hr"] = ordered_rate
        result["ordered_volume_per_feed_ml"] = 0.0
        return result

    safe_feeds = max(int(feeds_per_day), 1)
    ordered_volume_per_feed = floor(unrounded["planned_volume_ml"] / safe_feeds / 5 + 0.5) * 5
    ordered_volume = ordered_volume_per_feed * safe_feeds
    result = feed_delivery(formula, ordered_volume * kcal_per_ml, hours_per_day, achieved_percent)
    result["ordered_rate_ml_hr"] = 0.0
    result["ordered_volume_per_feed_ml"] = ordered_volume_per_feed
    return result


def ordered_feed_delivery(formula: Mapping[str, object], ordered_amount_ml: float,
                          hours_per_day: float, achieved_percent: float = 100,
                          schedule_type: str = "Continuous / cyclic",
                          feeds_per_day: int = 1) -> dict[str, float]:
    """Calculate nutrients from an explicitly entered pump rate or volume per feed."""
    kcal_per_ml = float(formula["kcal_per_mL"])
    if schedule_type == "Continuous / cyclic":
        ordered_rate = max(float(ordered_amount_ml), 0)
        ordered_volume = ordered_rate * hours_per_day
        result = feed_delivery(
            formula, ordered_volume * kcal_per_ml, hours_per_day, achieved_percent
        )
        result["ordered_rate_ml_hr"] = ordered_rate
        result["ordered_volume_per_feed_ml"] = 0.0
        return result

    safe_feeds = max(int(feeds_per_day), 1)
    ordered_volume_per_feed = max(float(ordered_amount_ml), 0)
    ordered_volume = ordered_volume_per_feed * safe_feeds
    result = feed_delivery(
        formula, ordered_volume * kcal_per_ml, hours_per_day, achieved_percent
    )
    result["ordered_rate_ml_hr"] = 0.0
    result["ordered_volume_per_feed_ml"] = ordered_volume_per_feed
    return result


def modular_delivery(product: Mapping[str, object], units_per_dose: float,
                     doses_per_day: float, preparation_water_ml_per_dose: float = 0) -> dict[str, object]:
    """Calculate daily modular delivery from its labelled product basis."""
    basis = float(product.get("basis_amount", 0) or 0)
    if basis <= 0:
        raise ValueError("Modular basis_amount must be greater than zero.")
    multiplier = units_per_dose * doses_per_day / basis
    output = {"preparation_water_ml": preparation_water_ml_per_dose * doses_per_day}
    disclosed: dict[str, int] = {}
    for result_key, column in {
        "energy_kcal": "kcal_per_basis",
        "protein_g": "protein_g_per_basis",
        "carbohydrate_g": "carbohydrate_g_per_basis",
        "fat_g": "fat_g_per_basis",
        "fibre_g": "fibre_g_per_basis",
        "free_water_ml": "free_water_ml_per_basis",
        "sodium_mg": "sodium_mg_per_basis",
        "potassium_mg": "potassium_mg_per_basis",
        "calcium_mg": "calcium_mg_per_basis",
        "magnesium_mg": "magnesium_mg_per_basis",
        "phosphorus_mg": "phosphorus_mg_per_basis",
    }.items():
        value, known = disclosed_value(product.get(column))
        output[result_key] = multiplier * value
        disclosed[result_key] = int(known)
    # A product with no dose entered is not part of the plan, so it must not
    # affect the coverage denominator or be reported as an undisclosed source.
    ordered = units_per_dose > 0 and doses_per_day > 0
    output["disclosed"] = disclosed if ordered else dict.fromkeys(disclosed, 0)
    output["product_count"] = 1 if ordered else 0
    return output


def total_modular_delivery(orders: list[dict[str, object]]) -> dict[str, object]:
    keys = {
        "energy_kcal", "protein_g", "carbohydrate_g", "fat_g", "fibre_g",
        "free_water_ml", "preparation_water_ml", "sodium_mg", "potassium_mg",
        "calcium_mg", "magnesium_mg", "phosphorus_mg",
    }
    totals: dict[str, object] = {
        key: sum(order.get(key, 0) for order in orders) for key in keys
    }
    # Coverage travels with the totals so a table can say how many of the
    # ordered products actually declared each nutrient.
    totals["disclosed"] = {
        key: sum(order.get("disclosed", {}).get(key, 0) for order in orders)
        for key in keys - {"preparation_water_ml"}
    }
    totals["product_count"] = sum(order.get("product_count", 0) for order in orders)
    return totals


def ons_delivery(
    product: Mapping[str, object],
    containers_each_time: float,
    times_per_day: float,
) -> dict[str, float]:
    """Calculate planned daily ONS provision from its labelled basis.

    Liquid ONS products use the existing container-and-millilitre basis. Oral
    products such as pudding use a labelled serving basis, while retaining the
    same output keys so they can be included in the existing summary tables.
    """
    basis = str(product.get("calculation_basis", "container_ml")).strip().casefold()
    if basis == "serving":
        daily_servings = containers_each_time * times_per_day
        output = {
            "daily_containers": 0.0,
            "daily_servings": daily_servings,
            "daily_volume_ml": 0.0,
        }
        for result_key, column in {
            "energy_kcal": "kcal_per_serving",
            "protein_g": "protein_g_per_serving",
            "carbohydrate_g": "carbohydrate_g_per_serving",
            "fat_g": "fat_g_per_serving",
            "fibre_g": "fibre_g_per_serving",
            "free_water_ml": "free_water_ml_per_serving",
            "sodium_mg": "sodium_mg_per_serving",
            "potassium_mg": "potassium_mg_per_serving",
            "calcium_mg": "calcium_mg_per_serving",
            "magnesium_mg": "magnesium_mg_per_serving",
            "phosphorus_mg": "phosphorus_mg_per_serving",
        }.items():
            output[result_key] = daily_servings * float(product.get(column, 0) or 0)
        return output
    container_size_ml = float(product.get("container_size_ml", 0) or 0)
    if container_size_ml <= 0:
        raise ValueError("ONS container_size_ml must be greater than zero.")
    daily_containers = containers_each_time * times_per_day
    daily_volume_ml = daily_containers * container_size_ml
    output = {
        "daily_containers": daily_containers,
        "daily_servings": 0.0,
        "daily_volume_ml": daily_volume_ml,
    }
    for result_key, column in {
        "energy_kcal": "kcal_per_mL",
        "protein_g": "protein_per_mL",
        "carbohydrate_g": "carbohydrate_per_mL",
        "fat_g": "fat_per_mL",
        "fibre_g": "fibre_per_mL",
        "free_water_ml": "free_water_per_mL",
        "sodium_mg": "sodium_per_mL",
        "potassium_mg": "potassium_per_mL",
        "calcium_mg": "calcium_per_mL",
        "magnesium_mg": "magnesium_per_mL",
        "phosphorus_mg": "phosphorus_per_mL",
    }.items():
        output[result_key] = daily_volume_ml * float(product.get(column, 0) or 0)
    return output


def total_ons_delivery(orders: list[dict[str, float]]) -> dict[str, float]:
    keys = {
        "daily_containers", "daily_servings", "daily_volume_ml", "energy_kcal", "protein_g",
        "carbohydrate_g", "fat_g", "fibre_g", "free_water_ml", "sodium_mg",
        "potassium_mg", "calcium_mg", "magnesium_mg", "phosphorus_mg",
    }
    return {key: sum(order.get(key, 0) for order in orders) for key in keys}


def hydration_flushes_per_day(schedule_format: str, schedule_value: int) -> int:
    """Resolve a hydration-flush frequency over a full 24-hour day."""
    value = int(schedule_value)
    if value <= 0:
        raise ValueError("Hydration-flush frequency must be greater than zero.")
    if schedule_format == "qXh":
        if 24 % value:
            raise ValueError("A qXh interval must divide evenly into 24 hours.")
        return 24 // value
    return value


def water_plan(water_target_ml: float, formula_free_water_ml: float,
               modular_free_water_ml: float, modular_preparation_water_ml: float,
               medication_flush_ml: float, patency_flush_ml: float,
               hydration_flushes_per_day: int) -> dict[str, float]:
    """Calculate counted water and a practical, rounded hydration flush amount."""
    existing_water = (
        formula_free_water_ml + modular_free_water_ml + modular_preparation_water_ml
        + medication_flush_ml + patency_flush_ml
    )
    hydration_total = max(water_target_ml - existing_water, 0)
    each_hydration_flush = (hydration_total / hydration_flushes_per_day
                            if hydration_flushes_per_day else 0)
    # Match practical feed-volume rounding: exact half-way values round up,
    # rather than following Python's bankers-rounding rule.
    rounded_each = floor(each_hydration_flush / 5 + 0.5) * 5
    rounded_total = rounded_each * hydration_flushes_per_day
    return {
        "counted_before_hydration_ml": existing_water,
        "hydration_flush_total_ml": rounded_total,
        "hydration_flush_each_ml": rounded_each,
        "water_flushes_total_ml": modular_preparation_water_ml + medication_flush_ml
        + patency_flush_ml + rounded_total,
        "total_water_ml": formula_free_water_ml + modular_free_water_ml
        + modular_preparation_water_ml + medication_flush_ml + patency_flush_ml + rounded_total,
    }
