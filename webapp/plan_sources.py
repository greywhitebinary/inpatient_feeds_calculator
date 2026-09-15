"""Build daily intake rows from explicit nutrition and fluid sources.

The displayed table may describe partial formula delivery, while the chart note
reports the full planned order. Both use the same source builder; auxiliary
sources retain their entered amounts in either view.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from calculations import (
    combined_intake,
    mg_to_mmol,
    mmol_from_delivery,
    mmol_if_disclosed,
)


@dataclass(frozen=True)
class IntakeSources:
    """Inputs shared by the planned and displayed intake calculations."""

    formula_name: str
    modular_totals: Mapping[str, object]
    ons_totals: Mapping[str, object]
    iv_fluids: Mapping[str, object]
    propofol: Mapping[str, object]
    include_modulars: bool
    include_ons: bool
    other_water_flushes: float


@dataclass(frozen=True)
class IntakeResult:
    """Source rows and numerical totals for the table and the chart note."""

    displayed_rows: list[dict[str, object]]
    displayed_total: dict[str, float]
    planned_rows: list[dict[str, object]]
    planned_total: dict[str, float]
    goal_comparison_total: dict[str, float]


def build_intake_rows(
    delivery: Mapping[str, object], sources: IntakeSources
) -> list[dict[str, object]]:
    """Describe one formula delivery alongside the entered auxiliary sources.

    IV fluids and propofol contribute volume but no water, because the water
    goal is entered net of IV fluids. Preparation water belongs to the modular
    row, and other_water_flushes must therefore exclude that preparation water.
    """
    modular_totals = sources.modular_totals
    modular_preparation_water = modular_totals["preparation_water_ml"]
    ons_totals = sources.ons_totals
    iv_fluids = sources.iv_fluids
    propofol = sources.propofol
    other_water_flushes = sources.other_water_flushes
    rows = [
        {
            "Source": sources.formula_name,
            "Volume (mL)": delivery["delivered_volume_ml"],
            "Energy (kcal)": delivery["energy_kcal"],
            "Protein (g)": delivery["protein_g"],
            "Carbohydrate (g)": delivery["carbohydrate_g"],
            "Fat (g)": delivery["fat_g"],
            "Water (mL)": delivery["free_water_ml"],
            "Na (mmol)": mmol_from_delivery(delivery, "sodium"),
            "K (mmol)": mmol_from_delivery(delivery, "potassium"),
            "Ca (mmol)": mmol_from_delivery(delivery, "calcium"),
            "P (mmol)": mmol_from_delivery(delivery, "phosphorus"),
            "Mg (mmol)": mmol_from_delivery(delivery, "magnesium"),
            "Fibre (g)": delivery.get("fibre_g", 0),
        },
        {
            # A row of zeros is not information. Modulars appear only when
            # some were ordered, matching how ONS, intravenous fluids and
            # propofol already behave.
            "Source": "Modulars",
            "Volume (mL)": modular_preparation_water,
            "Energy (kcal)": modular_totals["energy_kcal"],
            "Protein (g)": modular_totals["protein_g"],
            "Carbohydrate (g)": modular_totals["carbohydrate_g"],
            "Fat (g)": modular_totals["fat_g"],
            "Water (mL)": modular_totals["free_water_ml"] + modular_preparation_water,
            "Na (mmol)": mmol_if_disclosed(modular_totals, "sodium"),
            "K (mmol)": mmol_if_disclosed(modular_totals, "potassium"),
            "Ca (mmol)": mmol_if_disclosed(modular_totals, "calcium"),
            "P (mmol)": mmol_if_disclosed(modular_totals, "phosphorus"),
            "Mg (mmol)": mmol_if_disclosed(modular_totals, "magnesium"),
            "Fibre (g)": modular_totals.get("fibre_g", 0),
        },
        {
            "Source": "Water flushes",
            "Volume (mL)": other_water_flushes,
            "Energy (kcal)": 0,
            "Protein (g)": 0,
            "Carbohydrate (g)": 0,
            "Fat (g)": 0,
            "Water (mL)": other_water_flushes,
            "Na (mmol)": 0,
            "K (mmol)": 0,
            "Ca (mmol)": 0,
            "P (mmol)": 0,
            "Mg (mmol)": 0,
            "Fibre (g)": 0,
        },
    ]
    if sources.include_ons:
        rows.insert(
            2,
            {
                "Source": "ONS",
                "Volume (mL)": ons_totals["daily_volume_ml"],
                "Energy (kcal)": ons_totals["energy_kcal"],
                "Protein (g)": ons_totals["protein_g"],
                "Carbohydrate (g)": ons_totals["carbohydrate_g"],
                "Fat (g)": ons_totals["fat_g"],
                "Water (mL)": ons_totals["free_water_ml"],
                "Na (mmol)": mg_to_mmol("sodium", ons_totals["sodium_mg"]),
                "K (mmol)": mg_to_mmol("potassium", ons_totals["potassium_mg"]),
                "Ca (mmol)": mg_to_mmol("calcium", ons_totals["calcium_mg"]),
                "P (mmol)": mg_to_mmol("phosphorus", ons_totals["phosphorus_mg"]),
                "Mg (mmol)": mg_to_mmol("magnesium", ons_totals["magnesium_mg"]),
                "Fibre (g)": ons_totals.get("fibre_g", 0),
            },
        )
    if iv_fluids["energy_kcal"] > 0 or iv_fluids["volume_ml"] > 0:
        rows.insert(
            2,
            {
                "Source": "IV fluids",
                "Volume (mL)": iv_fluids["volume_ml"],
                "Energy (kcal)": iv_fluids["energy_kcal"],
                "Protein (g)": 0,
                "Carbohydrate (g)": iv_fluids["carbohydrate_g"],
                "Fat (g)": 0,
                # Volume above, but deliberately no water: the goals are entered
                # net of intravenous fluid, and the footnote says so.
                "Water (mL)": 0,
                "Na (mmol)": mg_to_mmol("sodium", iv_fluids["sodium_mg"]),
                "K (mmol)": mg_to_mmol("potassium", iv_fluids["potassium_mg"]),
                "Ca (mmol)": mg_to_mmol("calcium", iv_fluids["calcium_mg"]),
                "P (mmol)": 0,
                "Mg (mmol)": mg_to_mmol("magnesium", iv_fluids["magnesium_mg"]),
                "Fibre (g)": 0,
            },
        )
    if propofol["kcal"] > 0:
        rows.insert(
            2,
            {
                "Source": "Propofol",
                "Volume (mL)": propofol["volume_ml"],
                "Energy (kcal)": propofol["kcal"],
                "Protein (g)": 0,
                "Carbohydrate (g)": 0,
                "Fat (g)": propofol["fat_g"],
                "Water (mL)": 0,
                "Na (mmol)": 0,
                "K (mmol)": 0,
                "Ca (mmol)": 0,
                "P (mmol)": 0,
                "Mg (mmol)": 0,
                "Fibre (g)": 0,
            },
        )
    if not sources.include_modulars:
        rows = [row for row in rows if row["Source"] != "Modulars"]
    return rows


def calculate_intake(
    planned_delivery: Mapping[str, object],
    displayed_delivery: Mapping[str, object],
    sources: IntakeSources,
) -> IntakeResult:
    """Calculate both views without changing the supplied deliveries or sources."""
    displayed_rows = build_intake_rows(displayed_delivery, sources)
    planned_rows = build_intake_rows(planned_delivery, sources)
    return IntakeResult(
        displayed_rows=displayed_rows,
        displayed_total=combined_intake(displayed_rows),
        planned_rows=planned_rows,
        planned_total=combined_intake(planned_rows),
        goal_comparison_total=_goal_comparison_total(displayed_delivery, sources),
    )


def _goal_comparison_total(
    delivery: Mapping[str, object], sources: IntakeSources
) -> dict[str, float]:
    """Preserve the regimen check's established arithmetic and rounding.

    That check adds each water contribution in the order below, whereas intake
    rows group product water with preparation water. Regrouping floating-point
    additions can change a displayed integer at a half-mL boundary. Keep this
    calculation explicit rather than changing visible results during cleanup.
    It also remains independent of the display names used to filter rows.
    """
    modular, ons = sources.modular_totals, sources.ons_totals
    return {
        "Energy (kcal)": (
            delivery["energy_kcal"]
            + modular["energy_kcal"]
            + sources.propofol["kcal"]
            + sources.iv_fluids["energy_kcal"]
            + ons["energy_kcal"]
        ),
        "Protein (g)": delivery["protein_g"] + modular["protein_g"] + ons["protein_g"],
        "Water (mL)": (
            delivery["free_water_ml"]
            + modular["free_water_ml"]
            + ons["free_water_ml"]
            + modular["preparation_water_ml"]
            + sources.other_water_flushes
        ),
    }
