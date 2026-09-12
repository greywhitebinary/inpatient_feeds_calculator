"""Shared enteral formula, modular, hydration, and plan-check workflow."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from assessment_ui import render_assessment_goals
from calculations import (
    micronutrient_delivery,
)
from case_record_ui import render_save_record
from chart_note import build_chart_note_html, render_chart_note_editor
from constants import (
    DAILY_INTAKE_DECIMALS,
    MICRONUTRIENT_ROW_DECIMALS,
    MICRONUTRIENT_ROW_LABELS,
    ORDER_FORM_RATE_PER_FEED,
)
from plan_feed_controls import render_feed_selection
from plan_hydration import render_hydration_selection
from plan_review import PlanTargets, render_delivery_review
from plan_sources import IntakeSources
from plan_supplements import render_modular_orders, render_ons_orders
from session_state import (
    scenario_key,
    seed_scenario_state,
)
from ui_common import (
    number,
    render_box_heading,
    render_report_table,
    uncounted_volume_note,
    undisclosed_note,
)


def render_en_scenario(
    scenario_id: str,
    label: str,
    candidate_frame: pd.DataFrame,
    saved_modulars: pd.DataFrame,
    saved_ons: pd.DataFrame | None,
    total_energy_target: float | None,
    protein_target: float | None,
    water_target: float | None,
    propofol_rate: float,
    propofol_hours: float = 24,
    *,
    propofol_conditions: list[dict[str, object]] | None = None,
    propofol_method: str | None = None,
    estimated_energy_requirement: float | None = None,
) -> dict[str, object] | None:
    """Render one schedule-first regimen and return its final calculation outputs.

    Returns None when the direction of work needs assessment goals that have
    not been entered, having said so on the page.
    """
    selected = render_feed_selection(
        scenario_id,
        candidate_frame,
        total_energy_target,
        protein_target,
        propofol_rate,
        propofol_hours,
        propofol_conditions=propofol_conditions,
        propofol_method=propofol_method,
        estimated_energy_requirement=estimated_energy_requirement,
    )
    if selected is None:
        return None
    formula = selected.formula
    feed_order = selected.order
    final_planned_delivery = selected.planned_delivery
    propofol = selected.propofol
    iv_fluids = selected.iv_fluids
    conditions = selected.conditions
    conditional_orders = selected.conditional_orders
    energy_requirement = selected.energy_requirement
    prescription_target_pct = selected.prescription_target_pct
    prescription_interruption_note = selected.prescription_interruption_note
    total_energy_target = selected.energy_target
    schedule_type, hours, feeds_per_day, order_form, hours_per_feed = selected.schedule
    ordered_amount = selected.entered_amount
    describe_as_trickle = selected.describe_as_trickle
    reviewing_regimen = selected.reviewing_regimen
    conditional_mode = feed_order.conditional_rates is not None

    formula_only_gap = (
        None
        if protein_target is None
        else protein_target - final_planned_delivery["protein_g"]
    )
    with st.container(border=True):
        render_box_heading(
            "Protein from formula"
            if propofol_method
            else "Protein from selected formula"
        )
        feed_label = "Formula" if propofol_method else "Selected EN feed"
        feed_protein = (
            f"{feed_label}: "
            f'<strong>{final_planned_delivery["protein_g"]:.0f} g/day</strong>'
        )
        # With no protein goal entered there is nothing to subtract from, so
        # the line states what the feed delivers and stops there rather than
        # naming a shortfall against a target nobody set.
        if formula_only_gap is None:
            st.markdown(
                f'<p class="summary-line">{feed_protein}</p>',
                unsafe_allow_html=True,
            )
        else:
            gap_label = (
                "Projected protein gap"
                if propofol_method and formula_only_gap >= 0
                else "Shortfall" if formula_only_gap >= 0 else "Exceeds goal by"
            )
            gap_class = " protein-shortfall" if formula_only_gap > 0 else ""
            st.markdown(
                '<p class="summary-line">'
                f"Goal: <strong>{protein_target:.0f} g/day</strong> &nbsp;|&nbsp; "
                f"{feed_protein} "
                f'&nbsp;|&nbsp; <span class="protein-gap{gap_class}">{gap_label}: '
                f"<strong>{abs(formula_only_gap):.0f} g/day</strong></span></p>",
                unsafe_allow_html=True,
            )

    modular_selection = render_modular_orders(scenario_id, saved_modulars)
    modular_totals = modular_selection.totals
    chart_modulars = modular_selection.chart_orders
    modular_note_parts = modular_selection.note_parts
    modular_undisclosed = modular_selection.undisclosed
    modular_protein_sources = modular_selection.protein_sources
    ons_selection = render_ons_orders(scenario_id, saved_ons)
    ons_totals = ons_selection.totals
    chart_ons = ons_selection.chart_orders

    if saved_ons is not None and chart_ons:
        en_provision = {
            "Energy (kcal/day)": (
                final_planned_delivery["energy_kcal"] + modular_totals["energy_kcal"]
            ),
            "Protein (g/day)": (
                final_planned_delivery["protein_g"] + modular_totals["protein_g"]
            ),
            "CHO (g/day)": (
                final_planned_delivery["carbohydrate_g"]
                + modular_totals["carbohydrate_g"]
            ),
            "Fat (g/day)": (final_planned_delivery["fat_g"] + modular_totals["fat_g"]),
            "Free water (mL/day)": (
                final_planned_delivery["free_water_ml"]
                + modular_totals["free_water_ml"]
            ),
        }
        ons_provision = {
            "Energy (kcal/day)": ons_totals["energy_kcal"],
            "Protein (g/day)": ons_totals["protein_g"],
            "CHO (g/day)": ons_totals["carbohydrate_g"],
            "Fat (g/day)": ons_totals["fat_g"],
            "Free water (mL/day)": ons_totals["free_water_ml"],
        }
        with st.container(border=True):
            render_box_heading("Planned EN and ONS provision")
            render_report_table(
                pd.DataFrame(
                    [
                        {"Source": "EN", **en_provision},
                        {"Source": "ONS", **ons_provision},
                        {
                            "Source": "Combined EN + ONS",
                            **{
                                key: en_provision[key] + ons_provision[key]
                                for key in en_provision
                            },
                        },
                    ]
                ),
                decimals=DAILY_INTAKE_DECIMALS,
            )
    if conditional_mode:
        schedule_description = (
            "; ".join(
                f'{order["formula_rate_ml_hr"]:.0f} mL/hour when Propofol is '
                f'{order["propofol_rate_ml_hr"]:g} mL/hour'
                for order in conditional_orders
            )
            + f"; projected over {hours:g} feeding hours daily"
        )
    # The one place downstream that reads the entry form, so the note says the
    # order the way the clinician wrote it rather than in a normalised form.
    elif order_form == ORDER_FORM_RATE_PER_FEED:
        schedule_description = (
            f"{ordered_amount:.0f} mL/hour over {hours_per_feed:g} hours per feed, "
            f"{feeds_per_day} feeds daily "
            f"({final_planned_delivery['ordered_volume_per_feed_ml']:.0f} mL per feed)"
        )
    else:
        schedule_description = (
            f"{final_planned_delivery['ordered_rate_ml_hr']:.0f} mL/hour for {hours:g} hours daily"
            if schedule_type == "Continuous / cyclic"
            else f"{final_planned_delivery['ordered_volume_per_feed_ml']:.0f} mL per feed, {feeds_per_day} feeds daily"
        )

    water = render_hydration_selection(
        scenario_id,
        water_target=water_target,
        final_planned_delivery=final_planned_delivery,
        modular_totals=modular_totals,
        chart_ons=chart_ons,
        schedule_type=schedule_type,
        feeds_per_day=feeds_per_day,
    )
    hydration = water.totals
    other_water_flushes = water.other_water_flushes
    modular_preparation_water = modular_totals["preparation_water_ml"]
    chart_water_only = water.chart_water_only
    hydration_chart_schedule_text = water.chart_schedule_text
    enter_flushes_as_ordered = water.entered_as_ordered
    medication, patency = water.medication, water.patency

    sources = IntakeSources(
        formula_name=str(formula["name"]),
        modular_totals=modular_totals,
        ons_totals=ons_totals,
        iv_fluids=iv_fluids,
        propofol=propofol,
        include_modulars=bool(chart_modulars),
        include_ons=bool(chart_ons),
        other_water_flushes=other_water_flushes,
    )

    review = render_delivery_review(
        scenario_id,
        formula=formula,
        feed_order=feed_order,
        final_planned_delivery=final_planned_delivery,
        schedule_description=schedule_description,
        sources=sources,
        targets=PlanTargets(
            total_energy_target,
            protein_target,
            water_target,
            energy_requirement,
            prescription_target_pct,
            chart_water_only,
        ),
        modular_protein_sources=modular_protein_sources,
    )
    displayed_delivery, view_percent, intake = (
        review.delivery,
        review.percentage,
        review.intake,
    )

    source_frame = pd.DataFrame(intake.displayed_rows)
    total: dict[str, object] = {"Source": "Total", **intake.displayed_total}
    modular_note = "; ".join(modular_note_parts) or "No modulars ordered"
    chart_total = intake.planned_total
    return {
        "propofol_rate": propofol_rate,
        "propofol_hours": propofol_hours,
        "propofol": propofol,
        "iv_fluids": iv_fluids,
        "propofol_method": propofol_method,
        "propofol_conditions": conditions,
        "conditional_orders": conditional_orders,
        "feeding_hours": hours,
        "estimated_energy_requirement": energy_requirement,
        "prescription_target_pct": prescription_target_pct,
        "prescription_interruption_note": prescription_interruption_note,
        "formula": formula,
        "schedule_description": schedule_description,
        "modulars": modular_note,
        "source_frame": source_frame,
        "total": total,
        "table_notes": [
            note
            for note in (
                # Each note explains something on the table that does not mean
                # what it looks like. They are conditional, so a plain plan
                # carries none.
                (
                    "Free water from ONS is shown as oral intake but does not "
                    "affect hydration flush calculations."
                    if ons_totals["free_water_ml"]
                    else ""
                ),
                (
                    "Modular water includes the product's own water and the "
                    "water used to prepare it."
                    if modular_totals["free_water_ml"] and modular_preparation_water
                    else ""
                ),
                uncounted_volume_note(
                    [
                        (iv_fluids["volume_ml"], "IV fluids"),
                        (propofol["volume_ml"], "propofol"),
                    ]
                ),
                undisclosed_note(
                    modular_undisclosed,
                    {
                        "sodium": "Na",
                        "potassium": "K",
                        "calcium": "Ca",
                        "phosphorus": "P",
                        "magnesium": "Mg",
                    },
                ),
            )
            if note
        ],
        "delivery": final_planned_delivery,
        "displayed_delivery": displayed_delivery,
        "chart_total": chart_total,
        "modular_totals": modular_totals,
        "chart_modulars": chart_modulars,
        "ons_totals": ons_totals,
        "chart_ons": chart_ons,
        "hydration": hydration,
        "hydration_chart_schedule_text": hydration_chart_schedule_text,
        # An ordered schedule states its own volumes, so the note must not
        # prefix it with a per-flush amount and say each volume twice.
        "hydration_entered_as_ordered": enter_flushes_as_ordered,
        "medication_flushes_ml": number(medication),
        "patency_flushes_ml": number(patency),
        "describe_as_trickle": bool(describe_as_trickle),
        "regimen_already_running": reviewing_regimen,
        "intake_heading": (
            "Planned daily intake"
            if view_percent == 100
            else f"Estimated daily intake at {view_percent}% formula delivery"
        ),
    }


def render_micronutrient_panel(result: dict) -> None:
    """Show what the ordered formula delivers, without judging the amounts.

    Micronutrients are rarely the question in acute care, so this stays shut
    until someone opens it. It reports amounts only. No amount is compared with
    a reference intake, because the intake that applies depends on the patient
    and because the reference groups the manufacturers publish against do not
    describe most inpatients.
    """
    formula = result.get("formula")
    if formula is None:
        return
    volume = number(result["displayed_delivery"]["delivered_volume_ml"])
    if volume <= 0:
        return
    amounts = micronutrient_delivery(formula, volume)
    with st.expander("Micronutrients from the formula", expanded=False):
        if any(value is None for value in amounts.values()):
            st.caption(
                "An em dash (—) means the micronutrient amount was not disclosed "
                "in the formula data. A declared zero remains zero."
            )
        st.caption(
            f"Delivered by {volume:,.0f} mL of {formula['name']} a day. "
            "ONS and modular products are not counted, because their labels do "
            "not declare micronutrients."
        )
        render_report_table(
            pd.DataFrame(
                [
                    {
                        "Micronutrient": MICRONUTRIENT_ROW_LABELS[column],
                        "Per day": value,
                    }
                    for column, value in amounts.items()
                ]
            ),
            row_decimals=MICRONUTRIENT_ROW_DECIMALS,
        )


def render_en_workflow_setup(
    key_prefix: str,
    candidates_key: str,
) -> (
    tuple[
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        list[str],
        float | None,
        float | None,
        float | None,
    ]
    | None
):
    """Render shared Assessment goals and feed candidates for a planning workflow.

    Any of the three goals may come back None. Whether a missing one stops the
    work depends on the direction of work, which is asked further down the
    page, so the scenario decides that rather than this.
    """
    saved_ons = st.session_state.my_ons
    saved_feeds = st.session_state.my_formulas
    saved_modulars = st.session_state.my_modulars
    if candidates_key in st.session_state:
        available_feed_names = set(saved_feeds["name"].tolist())
        st.session_state[candidates_key] = [
            name
            for name in st.session_state[candidates_key]
            if name in available_feed_names
        ]
    total_energy_target, protein_target, water_target = render_assessment_goals(
        key_prefix
    )
    if saved_feeds.empty:
        st.caption(
            "Add at least one feed to My Formulary before building an EN regimen."
        )
        return None

    with st.container(border=True):
        render_box_heading("Formulas to compare")
        candidates = st.multiselect(
            "Select formulas",
            saved_feeds["name"].tolist(),
            max_selections=9,
            key=candidates_key,
        )
        st.caption("Missing a feed? Add it to My Formulary on the Formulary tab.")
    if not candidates:
        st.caption("Select at least one formula.")
        return None
    candidate_frame = saved_feeds.loc[saved_feeds["name"].isin(candidates)]
    return (
        candidate_frame,
        saved_modulars,
        saved_ons,
        candidates,
        None if total_energy_target is None else float(total_energy_target),
        None if protein_target is None else float(protein_target),
        None if water_target is None else float(water_target),
    )


def show_en_plan() -> None:
    setup = render_en_workflow_setup("en", "feed_candidates")
    if setup is None:
        return
    (
        candidate_frame,
        saved_modulars,
        saved_ons,
        candidates,
        total_energy_target,
        protein_target,
        water_target,
    ) = setup
    standard_migration = (
        "lower"
        if any(key.startswith("scenario_lower_") for key in st.session_state)
        else (
            "primary"
            if any(key.startswith("scenario_primary_") for key in st.session_state)
            else None
        )
    )
    seed_scenario_state("standard", candidates, saved_modulars, standard_migration)
    st.session_state[scenario_key("standard", "propofol_rate")] = 0.0

    result = render_en_scenario(
        "standard",
        "EN plan",
        candidate_frame,
        saved_modulars,
        saved_ons,
        total_energy_target,
        protein_target,
        water_target,
        0.0,
    )
    if result is None:
        return
    with st.container(key="fullbleed_standard_daily_intake", border=True):
        render_box_heading(str(result["intake_heading"]))
        render_report_table(
            pd.concat(
                [result["source_frame"], pd.DataFrame([result["total"]])],
                ignore_index=True,
            ),
            decimals=DAILY_INTAKE_DECIMALS,
            wide=True,
        )
        # One caption rather than one per note: separate captions each carry
        # their own block spacing, which reads as a gap between unrelated
        # remarks when they belong together under the same table.
        if result["table_notes"]:
            st.caption("  \n".join(str(note) for note in result["table_notes"]))
        render_micronutrient_panel(result)
    with st.container(border=True):
        render_box_heading("Chart note")
        st.caption(
            "Edit as needed, then copy to the EMR. Downloading the record does not "
            "save the chart-note text."
        )
        render_chart_note_editor(
            build_chart_note_html(st.session_state, [result]),
            editor_id="en_plan",
            case_token=str(st.session_state["_chart_note_case_token"]),
        )
    render_save_record("en_plan")
