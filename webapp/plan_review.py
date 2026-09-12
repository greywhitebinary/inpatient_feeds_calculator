"""Regimen review controls and goal comparisons, without owning order state."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

import pandas as pd
import streamlit as st
from constants import (
    PLAN_CHECK_DECIMALS,
)
from plan_order import FeedOrder
from plan_sources import IntakeResult, IntakeSources, calculate_intake
from session_state import (
    scenario_key,
    show_partial_formula_delivery,
)
from ui_common import (
    number,
    render_report_table,
)


def _named_contributions(parts: list[tuple[float, str]]) -> str | None:
    """Name every source that actually contributed, with its amount.

    A zero contributor is not listed: "0 kcal from modulars" on a plan with no
    modulars is noise, and it read inconsistently beside the protein row, which
    already omitted its zeros. An empty result is None rather than a word, so
    the table prints the em dash it uses everywhere else for nothing to report.
    """
    named = [f"{amount:,.0f} {label}" for amount, label in parts if amount]
    return "; ".join(named) or None


def _listed_or_none(parts: list[str]) -> str | None:
    """Join already-worded contributions, or None when there are none."""
    return "; ".join(parts) or None


@dataclass(frozen=True)
class PlanTargets:
    energy: float | None
    protein: float | None
    water: float | None
    assessed_energy: float | None
    prescription_percent: float
    water_chart_only: bool


@dataclass(frozen=True)
class DeliveryReview:
    delivery: dict[str, float]
    percentage: int
    intake: IntakeResult


def render_delivery_review(
    scenario_id: str,
    *,
    formula: dict[str, object],
    feed_order: FeedOrder,
    final_planned_delivery: dict[str, float],
    schedule_description: str,
    sources: IntakeSources,
    targets: PlanTargets,
    modular_protein_sources: list[str],
) -> DeliveryReview:
    """Render full/partial controls and comparisons from one intake result."""
    total_energy_target, protein_target, water_target = (
        targets.energy,
        targets.protein,
        targets.water,
    )
    energy_requirement = targets.assessed_energy
    prescription_target_pct = targets.prescription_percent
    chart_water_only = targets.water_chart_only
    modular_totals, ons_totals = sources.modular_totals, sources.ons_totals
    propofol, iv_fluids = sources.propofol, sources.iv_fluids
    modular_preparation_water = modular_totals["preparation_water_ml"]
    other_water_flushes = sources.other_water_flushes
    achieved_key = scenario_key(scenario_id, "achieved_delivery_pct")
    delivery_view_key = scenario_key(scenario_id, "delivery_view")
    saved_achieved = int(number(st.session_state.get(achieved_key, 100)))
    saved_view = st.session_state.get(delivery_view_key, "Full planned EN")
    partial_active = saved_achieved < 100 and saved_view == "Achieved delivery"
    with st.expander("EN regimen check", expanded=partial_active):
        order_summary, partial_action = st.columns([3, 1], vertical_alignment="center")
        # The daily volume is stated rather than left to be multiplied out. It
        # is the quickest check that the figures below are pulling correctly.
        order_summary.markdown(
            '<p class="summary-line">Full planned formula order (100%): '
            f'{escape(str(formula["name"]))} at '
            f"{escape(schedule_description)} "
            f"&nbsp;|&nbsp; <strong>"
            f'{final_planned_delivery["planned_volume_ml"]:,.0f} mL/day</strong>.</p>',
            unsafe_allow_html=True,
        )
        popover_label = (
            f"Partial delivery: {saved_achieved}%"
            if partial_active
            else "Review partial delivery"
        )
        with partial_action.popover(popover_label, width="stretch"):
            achieved = int(
                st.number_input(
                    "Formula delivered (% of planned)",
                    min_value=0,
                    max_value=100,
                    step=1,
                    key=achieved_key,
                    on_change=show_partial_formula_delivery,
                    args=(scenario_id,),
                )
            )
            if achieved == 100:
                view_percent = 100
            else:
                view_choice = st.selectbox(
                    "Show intake for",
                    ["Full planned EN", "Achieved delivery"],
                    key=delivery_view_key,
                    format_func=lambda option: (
                        "Full planned formula (100%)"
                        if option == "Full planned EN"
                        else f"{achieved}% of planned formula"
                    ),
                )
                view_percent = 100 if view_choice == "Full planned EN" else achieved

        final_achieved_delivery = feed_order.delivery(formula, achieved)
        displayed_delivery = (
            final_planned_delivery if view_percent == 100 else final_achieved_delivery
        )
        intake = calculate_intake(final_planned_delivery, displayed_delivery, sources)
        final_protein = intake.goal_comparison_total["Protein (g)"]
        final_energy = intake.goal_comparison_total["Energy (kcal)"]
        if view_percent < 100:
            st.markdown(
                '<p class="summary-line">Showing estimated intake at '
                f"<strong>{view_percent}% formula delivery</strong>. Modulars and "
                "flushes remain unchanged.</p>",
                unsafe_allow_html=True,
            )
        other_protein_sources = list(modular_protein_sources)
        if ons_totals["protein_g"]:
            other_protein_sources.append(f"{ons_totals['protein_g']:.0f} g from ONS")
        other_protein_text = _listed_or_none(other_protein_sources)
        displayed_total_water = intake.goal_comparison_total["Water (mL)"]
        water_difference = (
            None if water_target is None else displayed_total_water - water_target
        )
        protein_difference = (
            None if protein_target is None else final_protein - protein_target
        )
        energy_difference = (
            None if total_energy_target is None else final_energy - total_energy_target
        )
        water_source_parts = []
        if modular_totals["free_water_ml"]:
            water_source_parts.append(
                f"{modular_totals['free_water_ml']:.0f} mL from modulars"
            )
        if ons_totals["free_water_ml"]:
            water_source_parts.append(f"{ons_totals['free_water_ml']:.0f} mL from ONS")
        if modular_preparation_water:
            water_source_parts.append(
                f"{modular_preparation_water:.0f} mL from modular preparation water"
            )
        if other_water_flushes:
            water_source_parts.append(
                f"{other_water_flushes:.0f} mL from water flushes"
            )
        water_sources_text = _listed_or_none(water_source_parts)

        def signed_difference(value: float | None) -> str | None:
            if value is None:
                return None
            if value > 0:
                return f"+{value:.0f}"
            if value < 0:
                return f"−{abs(value):.0f}"
            return "0"

        total_column = "Planned total" if view_percent == 100 else "Estimated total"
        difference_column = (
            "Difference (planned − goal)"
            if view_percent == 100
            else "Difference (estimated − goal)"
        )
        check_rows = [
            {
                "Component": "Energy (kcal/day)",
                "Goal": total_energy_target,
                "From feed": displayed_delivery["energy_kcal"],
                "From other sources": _named_contributions(
                    [
                        (modular_totals["energy_kcal"], "kcal from modulars"),
                        (propofol["kcal"], "kcal from propofol"),
                        (iv_fluids["energy_kcal"], "kcal from IV fluids"),
                        (ons_totals["energy_kcal"], "kcal from ONS"),
                    ]
                ),
                total_column: final_energy,
                difference_column: signed_difference(energy_difference),
            },
            {
                "Component": "Protein (g/day)",
                "Goal": protein_target,
                "From feed": displayed_delivery["protein_g"],
                "From other sources": other_protein_text,
                total_column: final_protein,
                difference_column: signed_difference(protein_difference),
            },
        ]
        # Without a water goal there is nothing to check against, so the row is
        # omitted rather than shown with an empty goal and a meaningless
        # difference. Free water still appears in the daily intake table.
        if water_target is not None:
            check_rows.append(
                {
                    "Component": "Water (mL/day)",
                    "Goal": water_target,
                    "From feed": displayed_delivery["free_water_ml"],
                    "From other sources": water_sources_text,
                    total_column: displayed_total_water,
                    # When the requirement is charted rather than filled enterally,
                    # enteral falls short by design, so a difference here would read
                    # as a miss rather than as the plan working as intended.
                    difference_column: (
                        None
                        if chart_water_only
                        else signed_difference(water_difference)
                    ),
                }
            )
        final_checks = pd.DataFrame(check_rows)
        # Reviewing a running feed without any goal entered leaves both of
        # these columns empty in every row, so they are dropped and the table
        # reports what the regimen delivers. Unlike water, the energy and
        # protein rows stay: their remaining columns are the intake itself.
        if (
            total_energy_target is None
            and protein_target is None
            and water_target is None
        ):
            final_checks = final_checks.drop(columns=["Goal", difference_column])
            st.caption(
                "No energy or protein goal is entered, so the table reports "
                "what the regimen delivers without comparing it to one."
            )
        render_report_table(final_checks, decimals=PLAN_CHECK_DECIMALS)
        # Below 100% the energy goal in the table is the share the feed is
        # meant to meet, not what the patient was assessed as needing. Those
        # are different numbers and the column cannot say which it is holding,
        # so it is stated here rather than left to be inferred.
        if prescription_target_pct != 100:
            st.caption(
                f"The energy goal above is {prescription_target_pct:g}% of the "
                f"assessed requirement of {energy_requirement:,.0f} kcal/day. "
                "Protein and water are compared against the full assessed "
                "requirement."
            )

    return DeliveryReview(displayed_delivery, view_percent, intake)
