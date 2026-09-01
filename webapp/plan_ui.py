"""Shared enteral formula, modular, hydration, and plan-check workflow."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from assessment_ui import render_assessment_goals
from chart_note import build_chart_note_html, render_chart_note_editor
from calculations import (
    hydration_flushes_per_day,
    mg_to_mmol,
    modular_delivery,
    ordered_feed_delivery,
    practical_feed_delivery,
    propofol_intake,
    total_modular_delivery,
    water_plan,
)
from case_record_ui import render_save_record
from constants import DAILY_INTAKE_DECIMALS, FORMULA_COMPARISON_DECIMALS, PLAN_CHECK_DECIMALS
from session_state import (
    mark_order_as_edited,
    request_suggested_order,
    reset_new_modular_orders,
    scenario_key,
    seed_scenario_state,
    show_partial_formula_delivery,
)
from ui_common import (
    mmol_from_delivery,
    modular_chart_amount,
    modular_daily_amount,
    modular_unit,
    number,
    render_box_heading,
    render_report_table,
)

def render_en_scenario(
    scenario_id: str,
    label: str,
    candidate_frame: pd.DataFrame,
    saved_modulars: pd.DataFrame,
    total_energy_target: float,
    protein_target: float,
    water_target: float,
    propofol_rate: float,
    propofol_hours: float = 24,
) -> dict[str, object]:
    """Render one schedule-first regimen and return its final calculation outputs."""
    propofol = propofol_intake(propofol_rate, propofol_hours)

    with st.container(border=True):
        render_box_heading("Feeding schedule")
        schedule_a, schedule_b = st.columns([1.7, 1])
        schedule_type = schedule_a.radio(
            "Schedule", ["Continuous / cyclic", "Intermittent"], horizontal=True,
            key=scenario_key(scenario_id, "schedule_type"),
        )
        feeds_per_day = 1
        if schedule_type == "Continuous / cyclic":
            hours = schedule_b.number_input(
                "Feeding hours/day", min_value=1.0, max_value=24.0, step=1.0, format="%.0f",
                key=scenario_key(scenario_id, "feeding_hours"),
            )
        else:
            hours = 24.0
            feeds_per_day = int(schedule_b.number_input(
                "Feeds/day", min_value=1, max_value=12, step=1,
                key=scenario_key(scenario_id, "feeds_per_day"),
            ))

    comparison_energy_target = max(total_energy_target - propofol["kcal"], 0)
    comparison_rows = []
    for _, candidate in candidate_frame.iterrows():
        delivery = practical_feed_delivery(
            candidate.to_dict(), comparison_energy_target, hours, 100, schedule_type, feeds_per_day
        )
        delivery_column = "Rate (mL/hour)" if schedule_type == "Continuous / cyclic" else "Volume/feed (mL)"
        delivery_value = (
            delivery["ordered_rate_ml_hr"] if schedule_type == "Continuous / cyclic"
            else delivery["ordered_volume_per_feed_ml"]
        )
        comparison_rows.append({
            "Feed": candidate["name"], "Volume (mL/day)": delivery["planned_volume_ml"],
            delivery_column: delivery_value, "Energy (kcal/day)": delivery["energy_kcal"],
            "Protein (g/day)": delivery["protein_g"], "Free water (mL/day)": delivery["free_water_ml"],
            "Na (mmol/day)": mmol_from_delivery(delivery, "sodium"),
            "K (mmol/day)": mmol_from_delivery(delivery, "potassium"),
            "Ca (mmol/day)": mmol_from_delivery(delivery, "calcium"),
            "P (mmol/day)": mmol_from_delivery(delivery, "phosphorus"),
            "Mg (mmol/day)": mmol_from_delivery(delivery, "magnesium"),
        })
    with st.container(key=f"fullbleed_formula_comparison_{scenario_id}", border=True):
        render_box_heading("Formula comparison")
        comparison_note = (
            "Suggested rates are rounded to the nearest 5 mL/hour."
            if schedule_type == "Continuous / cyclic"
            else "Suggested volumes per feed are rounded to the nearest 5 mL."
        )
        st.caption(comparison_note)
        if propofol_rate > 0:
            st.markdown(
                '<p class="formula-energy-calculation">'
                f'<strong>{total_energy_target:,.0f} kcal goal − '
                f'{propofol["kcal"]:,.0f} kcal from propofol = '
                f'{comparison_energy_target:,.0f} kcal</strong> used to calculate '
                'suggested formula volumes and rates.</p>',
                unsafe_allow_html=True,
            )
        render_report_table(
            pd.DataFrame(comparison_rows), wide=True,
            decimals=FORMULA_COMPARISON_DECIMALS,
        )

    formula_container = st.container(border=True)
    with formula_container:
        render_box_heading("Select formula")
        selected_name = st.selectbox(
            "Formula", candidate_frame["name"].tolist(),
            key=scenario_key(scenario_id, "selected_formula"),
        )

    formula = candidate_frame.loc[candidate_frame["name"] == selected_name].iloc[0].to_dict()
    ordered_formula_key = scenario_key(scenario_id, "ordered_formula_name")
    ordered_rate_key = scenario_key(scenario_id, "ordered_rate_ml_hr")
    ordered_volume_key = scenario_key(scenario_id, "ordered_volume_per_feed_ml")
    order_edited_key = scenario_key(scenario_id, "order_user_edited")
    ordered_schedule_key = scenario_key(scenario_id, "ordered_schedule_type")
    if st.session_state.get(ordered_formula_key) != selected_name:
        st.session_state[ordered_formula_key] = selected_name
        st.session_state[ordered_rate_key] = None
        st.session_state[ordered_volume_key] = None
        st.session_state[order_edited_key] = False
    if st.session_state.get(ordered_schedule_key) != schedule_type:
        st.session_state[ordered_schedule_key] = schedule_type
        st.session_state[ordered_rate_key] = None
        st.session_state[ordered_volume_key] = None
        st.session_state[order_edited_key] = False

    suggested_final_delivery = practical_feed_delivery(
        formula, comparison_energy_target, hours, 100, schedule_type, feeds_per_day
    )
    if schedule_type == "Continuous / cyclic":
        order_key = ordered_rate_key
        suggestion = suggested_final_delivery["ordered_rate_ml_hr"]
        order_label = "Rate (mL/hour)"
        suggestion_label = "Suggested rate"
        use_suggestion_label = "Reset to suggested rate"
        adjustment_label = "Adjust selected formula rate"
    else:
        order_key = ordered_volume_key
        suggestion = suggested_final_delivery["ordered_volume_per_feed_ml"]
        order_label = "Volume per feed (mL)"
        suggestion_label = "Suggested volume per feed"
        use_suggestion_label = "Reset to suggested volume"
        adjustment_label = "Adjust selected formula volume"
    pending_reset_key = scenario_key(scenario_id, "order_reset_requested")
    if st.session_state.get(pending_reset_key):
        st.session_state[pending_reset_key] = False
        st.session_state[order_edited_key] = False
    order_was_edited = bool(st.session_state.get(order_edited_key))
    if not order_was_edited or st.session_state.get(order_key) is None:
        st.session_state[order_key] = suggestion
        st.session_state[order_edited_key] = False
    ordered_amount = number(st.session_state.get(order_key, suggestion))
    final_planned_delivery = ordered_feed_delivery(
        formula, ordered_amount, hours, 100, schedule_type, feeds_per_day
    )

    formula_only_gap = protein_target - final_planned_delivery["protein_g"]
    with st.container(border=True):
        render_box_heading("Protein from selected formula")
        gap_label = "Shortfall" if formula_only_gap >= 0 else "Exceeds goal by"
        gap_class = " protein-shortfall" if formula_only_gap > 0 else ""
        st.markdown(
            '<p class="summary-line">'
            f'Goal: <strong>{protein_target:.0f} g/day</strong> &nbsp;|&nbsp; '
            f'Selected EN feed: <strong>{final_planned_delivery["protein_g"]:.0f} g/day</strong> '
            f'&nbsp;|&nbsp; <span class="protein-gap{gap_class}">{gap_label}: '
            f'<strong>{abs(formula_only_gap):.0f} g/day</strong></span></p>',
            unsafe_allow_html=True,
        )

    modular_orders: list[dict[str, float]] = []
    modular_note_parts: list[str] = []
    modular_protein_sources: list[str] = []
    modular_fat_sources: list[str] = []
    chart_modulars: list[dict[str, object]] = []
    chosen_modulars: list[str] = []
    with st.container(border=True):
        render_box_heading("Add modulars")
        st.caption("Enter the modular order. This calculator does not recommend doses.")
        if saved_modulars.empty:
            st.caption("Add modulars in Formulary if needed.")
        else:
            modular_ids_by_name = {
                str(product["name"]): str(product["id"])
                for _, product in saved_modulars.iterrows()
            }
            chosen_modulars = st.multiselect(
                "Modular orders (up to 6)", saved_modulars["name"].tolist(),
                max_selections=6, key=scenario_key(scenario_id, "chosen_modulars"),
                on_change=reset_new_modular_orders,
                args=(scenario_id, modular_ids_by_name),
            )
            for modular_name in chosen_modulars:
                product = saved_modulars.loc[
                    saved_modulars["name"] == modular_name
                ].iloc[0].to_dict()
                st.markdown(f"**{modular_name}** — {product['basis_description']}")
                a, b, c = st.columns(3)
                product_id = str(product["id"])
                units_key = scenario_key(scenario_id, f"modular_units_{product_id}")
                doses_key = scenario_key(scenario_id, f"modular_doses_{product_id}")
                unit_label = (
                    "Packets each time" if modular_unit(product) == "packet"
                    else f"{product['dose_unit']} each time"
                )
                packet_order = modular_unit(product) == "packet"
                units = a.number_input(
                    unit_label, min_value=0.0,
                    step=1.0 if packet_order else 0.5,
                    format="%.0f" if packet_order else "%.1f",
                    key=units_key,
                )
                doses = b.number_input(
                    "Times per day", min_value=0.0, step=1.0, format="%.0f",
                    key=doses_key,
                )
                preparation = 0.0
                if str(product.get("preparation_water_rule", "none")) != "none":
                    preparation = c.number_input(
                        "Preparation water (mL each time)", min_value=0.0,
                        step=5.0, format="%.0f",
                        key=scenario_key(scenario_id, f"modular_water_{product_id}"),
                    )
                else:
                    c.caption("No preparation water.")
                order_is_complete = number(units) > 0 and number(doses) > 0
                order = modular_delivery(
                    product,
                    number(units) if order_is_complete else 0,
                    number(doses) if order_is_complete else 0,
                    number(preparation) if order_is_complete else 0,
                )
                modular_orders.append(order)
                if order_is_complete:
                    daily_amount = modular_daily_amount(
                        product, number(units), number(doses)
                    )
                    modular_note_parts.append(
                        f"{modular_name} {modular_chart_amount(product, number(units), number(doses))}"
                    )
                    if order["protein_g"]:
                        modular_protein_sources.append(
                            f"{order['protein_g']:.0f} g from {modular_name} ({daily_amount})"
                        )
                    if order["fat_g"]:
                        modular_fat_sources.append(
                            f"{order['fat_g']:.0f} g from {modular_name} ({daily_amount})"
                        )
                    chart_modulars.append({
                        "name": modular_name,
                        "order": modular_chart_amount(
                            product, number(units), number(doses)
                        ),
                        "daily_amount": daily_amount,
                        "energy_kcal": order["energy_kcal"],
                        "protein_g": order["protein_g"],
                        "carbohydrate_g": order["carbohydrate_g"],
                        "fat_g": order["fat_g"],
                        "free_water_ml": order["free_water_ml"],
                        "preparation_water_ml": order["preparation_water_ml"],
                        "preparation_water_per_dose_ml": number(preparation),
                    })
                else:
                    st.caption(
                        "Enter both the amount and frequency to include this modular."
                    )
    modular_totals = total_modular_delivery(modular_orders)
    # Protein modulars supplement the established EN order. Their energy is
    # shown in the final totals, but does not silently displace formula volume.
    # Propofol remains the intentional non-enteral energy deduction.
    final_formula_energy_target = comparison_energy_target
    with formula_container.popover(adjustment_label, width="stretch"):
        st.markdown(
            f'<p class="worked-bounds">{suggestion_label}:<br>'
            f'<strong>{suggestion:.0f} {"mL/hour" if schedule_type == "Continuous / cyclic" else "mL"}</strong></p>',
            unsafe_allow_html=True,
        )
        ordered_amount = st.number_input(
            order_label, min_value=0.0, step=5.0, format="%.0f", key=order_key,
            on_change=mark_order_as_edited, args=(order_edited_key,),
        )
        st.button(
            use_suggestion_label,
            key=scenario_key(scenario_id, "use_suggested_order"),
            use_container_width=True,
            disabled=not bool(st.session_state.get(order_edited_key)),
            on_click=request_suggested_order, args=(pending_reset_key,),
        )

        final_planned_delivery = ordered_feed_delivery(
            formula, ordered_amount, hours, 100, schedule_type, feeds_per_day
        )
        planned_energy_total = (
            final_planned_delivery["energy_kcal"]
            + modular_totals["energy_kcal"]
            + propofol["kcal"]
        )
        preview_difference = planned_energy_total - total_energy_target
        if preview_difference > 0:
            difference_value = f"+{preview_difference:.0f} kcal/day"
        elif preview_difference < 0:
            difference_value = f"−{abs(preview_difference):.0f} kcal/day"
        else:
            difference_value = None
        if schedule_type == "Continuous / cyclic":
            order_summary = (
                f'At <strong>{ordered_amount:.0f} mL/hour</strong> for '
                f'<strong>{hours:g} hours</strong>'
            )
        else:
            order_summary = (
                f'At <strong>{ordered_amount:.0f} mL per feed</strong>, '
                f'<strong>{feeds_per_day} feeds daily</strong>'
            )
        difference_summary = (
            f'(<strong>{difference_value}</strong> from goal)'
            if difference_value is not None else "(at goal)"
        )
        st.markdown(
            f'<p class="order-preview">{order_summary}: '
            f'<strong>{final_planned_delivery["planned_volume_ml"]:.0f} mL</strong> formula/day, '
            f'<strong>{final_planned_delivery["energy_kcal"]:.0f} kcal/day</strong> from formula, '
            f'and <strong>{planned_energy_total:.0f} kcal/day</strong> total '
            f'{difference_summary}.</p>',
            unsafe_allow_html=True,
        )

    schedule_description = (
        f"{final_planned_delivery['ordered_rate_ml_hr']:.0f} mL/hour for {hours:g} hours daily"
        if schedule_type == "Continuous / cyclic"
        else f"{final_planned_delivery['ordered_volume_per_feed_ml']:.0f} mL per feed, {feeds_per_day} feeds daily"
    )

    with st.container(border=True):
        render_box_heading("Water goal and hydration flushes")
        free_water_before_flushes = (
            final_planned_delivery["free_water_ml"]
            + modular_totals["free_water_ml"]
            + modular_totals["preparation_water_ml"]
        )
        remaining_before_flushes = max(water_target - free_water_before_flushes, 0)
        st.markdown(
            '<p class="summary-line">Water goal: '
            f'<strong>{water_target:.0f} mL/day</strong> &nbsp;|&nbsp; '
            'Water from formula and modulars: '
            f'<strong>{free_water_before_flushes:.0f} mL/day</strong> &nbsp;|&nbsp; '
            'Remaining before flushes: '
            f'<strong>{remaining_before_flushes:.0f} mL/day</strong></p>',
            unsafe_allow_html=True,
        )
        water_a, water_b = st.columns(2)
        medication = water_a.number_input(
            "Medication flushes (mL/day)", min_value=0.0, step=10.0, format="%.0f",
            key=scenario_key(scenario_id, "medication_flushes"),
        )
        patency = water_b.number_input(
            "Patency flushes (mL/day)", min_value=0.0, step=10.0, format="%.0f",
            help="Enter a separate patency-flush volume only when it is part of the plan.",
            key=scenario_key(scenario_id, "patency_flushes"),
        )
        schedule_a, schedule_b = st.columns(2)
        schedule_format = schedule_a.selectbox(
            "Hydration flush frequency",
            options=["times/day", "qXh"],
            format_func=lambda value: (
                "Times/day (e.g., 6 times per day)"
                if value == "times/day"
                else "Interval (e.g., q4h)"
            ),
            help="Every-X-hours schedules run over 24 hours, independently of feeding hours.",
            key=scenario_key(scenario_id, "hydration_schedule_format"),
        )
        if schedule_format == "qXh":
            schedule_value = int(schedule_b.selectbox(
                "Flush interval (hours)",
                options=[1, 2, 3, 4, 6, 8, 12, 24],
                format_func=lambda value: f"{value} hours",
                key=scenario_key(scenario_id, "hydration_interval_hours"),
            ))
            flushes = hydration_flushes_per_day(schedule_format, schedule_value)
            hydration_schedule_text = f"q{schedule_value}h"
            hydration_chart_schedule_text = f"q{schedule_value}h"
        else:
            schedule_value = int(schedule_b.number_input(
                "Hydration flushes (number/day)", min_value=1, max_value=24,
                key=scenario_key(scenario_id, "hydration_flushes"),
            ))
            flushes = hydration_flushes_per_day(schedule_format, schedule_value)
            hydration_schedule_text = f"{flushes} times daily"
            hydration_chart_schedule_text = f"{flushes} times daily"
        hydration = water_plan(
            water_target, final_planned_delivery["free_water_ml"], modular_totals["free_water_ml"],
            modular_totals["preparation_water_ml"], medication, patency, flushes,
        )
        modular_preparation_water = modular_totals["preparation_water_ml"]
        other_water_flushes = max(
            hydration["water_flushes_total_ml"] - modular_preparation_water, 0
        )
        st.markdown(
            '<p class="summary-line">Calculated hydration flush schedule: '
            f'<strong>{hydration["hydration_flush_each_ml"]:.0f} mL '
            f'{hydration_schedule_text}.</strong></p>',
            unsafe_allow_html=True,
        )

    achieved_key = scenario_key(scenario_id, "achieved_delivery_pct")
    delivery_view_key = scenario_key(scenario_id, "delivery_view")
    saved_achieved = int(number(st.session_state.get(achieved_key, 100)))
    saved_view = st.session_state.get(delivery_view_key, "Full planned EN")
    partial_active = saved_achieved < 100 and saved_view == "Achieved delivery"
    with st.expander("EN plan check", expanded=partial_active):
        order_summary, partial_action = st.columns(
            [3, 1], vertical_alignment="center"
        )
        order_summary.markdown(
            '<p class="summary-line">Full planned formula order (100%): '
            f'{escape(str(formula["name"]))} at '
            f'{escape(schedule_description)}.</p>',
            unsafe_allow_html=True,
        )
        popover_label = (
            f"Partial delivery: {saved_achieved}%"
            if partial_active else "Review partial delivery"
        )
        with partial_action.popover(popover_label, width="stretch"):
            achieved = int(st.number_input(
                "Formula delivered (% of planned)", min_value=0, max_value=100, step=1,
                key=achieved_key,
                on_change=show_partial_formula_delivery, args=(scenario_id,),
            ))
            if achieved == 100:
                view_percent = 100
            else:
                view_choice = st.selectbox(
                    "Show intake for", ["Full planned EN", "Achieved delivery"],
                    key=delivery_view_key,
                    format_func=lambda option: (
                        "Full planned formula (100%)"
                        if option == "Full planned EN"
                        else f"{achieved}% of planned formula"
                    ),
                )
                view_percent = 100 if view_choice == "Full planned EN" else achieved

        final_achieved_delivery = ordered_feed_delivery(
            formula, ordered_amount, hours, achieved, schedule_type, feeds_per_day
        )
        displayed_delivery = (
            final_planned_delivery if view_percent == 100 else final_achieved_delivery
        )
        final_protein = displayed_delivery["protein_g"] + modular_totals["protein_g"]
        final_energy = (
            displayed_delivery["energy_kcal"]
            + modular_totals["energy_kcal"]
            + propofol["kcal"]
        )
        if view_percent < 100:
            st.markdown(
                '<p class="summary-line">Showing estimated intake at '
                f'<strong>{view_percent}% formula delivery</strong>. Modulars and '
                'flushes remain unchanged.</p>',
                unsafe_allow_html=True,
            )
        modular_protein_text = (
            ", ".join(modular_protein_sources) if modular_protein_sources else "None"
        )
        displayed_total_water = (
            displayed_delivery["free_water_ml"]
            + modular_totals["free_water_ml"]
            + modular_preparation_water
            + other_water_flushes
        )
        water_difference = displayed_total_water - water_target
        protein_difference = final_protein - protein_target
        energy_difference = final_energy - total_energy_target
        water_source_parts = []
        if modular_totals["free_water_ml"]:
            water_source_parts.append(
                f"{modular_totals['free_water_ml']:.0f} mL from modulars"
            )
        if modular_preparation_water:
            water_source_parts.append(
                f"{modular_preparation_water:.0f} mL from modular preparation water"
            )
        if other_water_flushes:
            water_source_parts.append(
                f"{other_water_flushes:.0f} mL from water flushes"
            )
        water_sources_text = "; ".join(water_source_parts) or "None"

        def signed_difference(value: float) -> str:
            if value > 0:
                return f"+{value:.0f}"
            if value < 0:
                return f"−{abs(value):.0f}"
            return "0"

        total_column = "Planned total" if view_percent == 100 else "Estimated total"
        difference_column = (
            "Difference (planned − goal)"
            if view_percent == 100 else "Difference (estimated − goal)"
        )
        final_checks = pd.DataFrame([
            {
                "Component": "Energy (kcal/day)",
                "Goal": total_energy_target,
                "From feed": displayed_delivery["energy_kcal"],
                "From other sources": (
                    f"{modular_totals['energy_kcal']:.0f} kcal from modulars"
                    + (
                        f"; {propofol['kcal']:.0f} kcal from propofol"
                        if propofol["kcal"] else ""
                    )
                ),
                total_column: final_energy,
                difference_column: signed_difference(energy_difference),
            },
            {
                "Component": "Protein (g/day)",
                "Goal": protein_target,
                "From feed": displayed_delivery["protein_g"],
                "From other sources": modular_protein_text,
                total_column: final_protein,
                difference_column: signed_difference(protein_difference),
            },
            {
                "Component": "Water (mL/day)",
                "Goal": water_target,
                "From feed": displayed_delivery["free_water_ml"],
                "From other sources": water_sources_text,
                total_column: displayed_total_water,
                difference_column: signed_difference(water_difference),
            },
        ])
        render_report_table(final_checks, decimals=PLAN_CHECK_DECIMALS)

    source_rows = [
        {
            "Source": formula["name"], "Energy (kcal)": displayed_delivery["energy_kcal"],
            "Protein (g)": displayed_delivery["protein_g"],
            "Carbohydrate (g)": displayed_delivery["carbohydrate_g"],
            "Fat (g)": displayed_delivery["fat_g"],
            "Free water (mL)": displayed_delivery["free_water_ml"],
            "Water flushes (mL)": 0,
            "Na (mmol)": mmol_from_delivery(displayed_delivery, "sodium"),
            "K (mmol)": mmol_from_delivery(displayed_delivery, "potassium"),
            "Ca (mmol)": mmol_from_delivery(displayed_delivery, "calcium"),
            "P (mmol)": mmol_from_delivery(displayed_delivery, "phosphorus"),
            "Mg (mmol)": mmol_from_delivery(displayed_delivery, "magnesium"),
        },
        {
            "Source": "Modulars", "Energy (kcal)": modular_totals["energy_kcal"],
            "Protein (g)": modular_totals["protein_g"],
            "Carbohydrate (g)": modular_totals["carbohydrate_g"],
            "Fat (g)": modular_totals["fat_g"],
            "Free water (mL)": modular_totals["free_water_ml"],
            "Water flushes (mL)": modular_preparation_water,
            "Na (mmol)": mg_to_mmol("sodium", modular_totals["sodium_mg"]),
            "K (mmol)": mg_to_mmol("potassium", modular_totals["potassium_mg"]),
            "Ca (mmol)": mg_to_mmol("calcium", modular_totals["calcium_mg"]),
            "P (mmol)": mg_to_mmol("phosphorus", modular_totals["phosphorus_mg"]),
            "Mg (mmol)": mg_to_mmol("magnesium", modular_totals["magnesium_mg"]),
        },
        {
            "Source": "Water flushes", "Energy (kcal)": 0, "Protein (g)": 0,
            "Carbohydrate (g)": 0, "Fat (g)": 0, "Free water (mL)": 0,
            "Water flushes (mL)": other_water_flushes,
            "Na (mmol)": 0, "K (mmol)": 0, "Ca (mmol)": 0, "P (mmol)": 0,
            "Mg (mmol)": 0,
        },
    ]
    if propofol_rate > 0:
        source_rows.insert(2, {
            "Source": "Propofol", "Energy (kcal)": propofol["kcal"], "Protein (g)": 0,
            "Carbohydrate (g)": 0, "Fat (g)": propofol["fat_g"], "Free water (mL)": 0,
            "Water flushes (mL)": 0, "Na (mmol)": 0, "K (mmol)": 0,
            "Ca (mmol)": 0, "P (mmol)": 0, "Mg (mmol)": 0,
        })
    source_frame = pd.DataFrame(source_rows)
    total: dict[str, object] = {"Source": "Total"}
    for column in source_frame.columns[1:]:
        total[column] = source_frame[column].sum()
    modular_note = "; ".join(modular_note_parts) or "No modulars ordered"
    planned_total = {
        "Energy (kcal)": (
            final_planned_delivery["energy_kcal"]
            + modular_totals["energy_kcal"]
            + propofol["kcal"]
        ),
        "Protein (g)": (
            final_planned_delivery["protein_g"] + modular_totals["protein_g"]
        ),
        "Fat (g)": (
            final_planned_delivery["fat_g"]
            + modular_totals["fat_g"]
            + propofol["fat_g"]
        ),
    }
    chart_total = {
        "Energy (kcal)": (
            final_planned_delivery["energy_kcal"]
            + modular_totals["energy_kcal"]
            + propofol["kcal"]
        ),
        "Protein (g)": (
            final_planned_delivery["protein_g"] + modular_totals["protein_g"]
        ),
        "Carbohydrate (g)": (
            final_planned_delivery["carbohydrate_g"]
            + modular_totals["carbohydrate_g"]
        ),
        "Fat (g)": (
            final_planned_delivery["fat_g"]
            + modular_totals["fat_g"]
            + propofol["fat_g"]
        ),
        "Free water (mL)": (
            final_planned_delivery["free_water_ml"]
            + modular_totals["free_water_ml"]
        ),
        "Water flushes (mL)": modular_preparation_water + other_water_flushes,
    }
    return {
        "label": label,
        "propofol_rate": propofol_rate, "propofol_hours": propofol_hours,
        "propofol": propofol,
        "formula": formula, "formula_energy_target": final_formula_energy_target,
        "schedule_description": schedule_description, "modulars": modular_note,
        "source_frame": source_frame, "total": total,
        "planned_total": planned_total,
        "delivery": final_planned_delivery,
        "chart_total": chart_total,
        "modular_totals": modular_totals,
        "chart_modulars": chart_modulars,
        "hydration": hydration,
        "hydration_chart_schedule_text": hydration_chart_schedule_text,
        "medication_flushes_ml": number(medication),
        "patency_flushes_ml": number(patency),
        "view_percent": view_percent,
        "intake_heading": (
            "Planned daily intake"
            if view_percent == 100 else f"Estimated daily intake at {view_percent}% formula delivery"
        ),
    }


def render_en_workflow_setup(
    key_prefix: str,
    candidates_key: str,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], float, float, float] | None:
    """Render shared Assessment goals and feed candidates for a planning workflow."""
    saved_feeds = st.session_state.my_formulas
    saved_modulars = st.session_state.my_modulars
    if candidates_key in st.session_state:
        available_feed_names = set(saved_feeds["name"].tolist())
        st.session_state[candidates_key] = [
            name for name in st.session_state[candidates_key]
            if name in available_feed_names
        ]
    total_energy_target, protein_target, water_target = render_assessment_goals(
        key_prefix
    )
    if saved_feeds.empty:
        st.caption("Add at least one formula in Formulary to create an EN plan.")
        return None
    if total_energy_target is None or protein_target is None or water_target is None:
        st.caption("Enter energy, protein, and water goals in Assessment or Adjust goals.")
        return None

    with st.container(border=True):
        render_box_heading("Formulas to compare")
        candidates = st.multiselect(
            "Select formulas", saved_feeds["name"].tolist(), max_selections=9, key=candidates_key
        )
    if not candidates:
        st.caption("Select at least one formula.")
        return None
    candidate_frame = saved_feeds.loc[saved_feeds["name"].isin(candidates)]
    return (
        candidate_frame, saved_modulars, candidates,
        float(total_energy_target), float(protein_target), float(water_target),
    )


def show_en_plan() -> None:
    setup = render_en_workflow_setup("en", "feed_candidates")
    if setup is None:
        return
    candidate_frame, saved_modulars, candidates, total_energy_target, protein_target, water_target = setup
    standard_migration = "lower" if any(
        key.startswith("scenario_lower_") for key in st.session_state
    ) else "primary" if any(key.startswith("scenario_primary_") for key in st.session_state) else None
    seed_scenario_state("standard", candidates, saved_modulars, standard_migration)
    st.session_state[scenario_key("standard", "propofol_rate")] = 0.0

    result = render_en_scenario(
        "standard", "EN plan", candidate_frame, saved_modulars,
        total_energy_target, protein_target, water_target, 0.0,
    )
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
