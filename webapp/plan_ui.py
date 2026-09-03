"""Shared enteral formula, modular, hydration, and plan-check workflow."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from assessment_ui import render_assessment_goals
from chart_note import build_chart_note_html, render_chart_note_editor
from calculations import (
    conditional_feed_delivery,
    hydration_flushes_per_day,
    mg_to_mmol,
    modular_delivery,
    ons_delivery,
    ordered_feed_delivery,
    practical_feed_delivery,
    propofol_intake,
    suggested_conditional_formula_rate,
    total_propofol_intake,
    total_modular_delivery,
    total_ons_delivery,
    water_plan,
)
from case_record_ui import render_save_record
from constants import DAILY_INTAKE_DECIMALS, FORMULA_COMPARISON_DECIMALS, PLAN_CHECK_DECIMALS
from session_state import (
    mark_order_as_edited,
    propofol_widget_key,
    request_suggested_order,
    reset_new_modular_orders,
    scenario_key,
    seed_scenario_state,
    sync_propofol_widget,
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
    mmol_if_disclosed,
    undisclosed_note,
)


# Shared by the header row and every condition row, so the columns line up.
# The condition column is kept narrow so the Propofol rate sits close to the
# suggested formula rate it drives; a wide first column reads as two unrelated
# halves rather than as cause and effect.
CONDITION_ROW_WIDTHS = [0.8, 0.8, 1, 0.95]


def _render_en_prescription(
    scenario_id: str,
    conditional_mode: bool,
    estimated_energy_requirement: float,
) -> tuple[str, float, int, float, bool, float]:
    """Render schedule and energy-prescription controls shared by both plans."""
    with st.container(border=True):
        render_box_heading("EN prescription")
        schedule_a, schedule_b = st.columns([1.7, 1])
        schedule_key = scenario_key(scenario_id, "schedule_type")
        if conditional_mode:
            st.session_state[schedule_key] = "Continuous / cyclic"
            schedule_options = ["Continuous / cyclic"]
        else:
            schedule_options = ["Continuous / cyclic", "Intermittent"]
        schedule_type = schedule_a.radio(
            "Schedule", schedule_options, horizontal=True, key=schedule_key,
        )
        feeds_per_day = 1
        if schedule_type == "Continuous / cyclic":
            hours = schedule_b.number_input(
                "Feeding hours/day", min_value=1.0, max_value=24.0,
                step=1.0, format="%.0f",
                key=scenario_key(scenario_id, "feeding_hours"),
            )
        else:
            hours = 24.0
            feeds_per_day = int(schedule_b.number_input(
                "Feeds/day", min_value=1, max_value=12, step=1,
                key=scenario_key(scenario_id, "feeds_per_day"),
            ))

        target_a, target_b = st.columns([1, 1.7], vertical_alignment="bottom")
        prescription_target_pct = target_a.number_input(
            "EN prescription target (%)", min_value=1.0, max_value=200.0,
            step=5.0, format="%.0f",
            key=scenario_key(scenario_id, "prescription_target_pct"),
            help=(
                "Values above 100% increase the EN prescription to account for "
                "expected interruptions. Protein and water goals are unchanged."
            ),
        )
        target_pct = number(prescription_target_pct)
        prescription_energy_target = estimated_energy_requirement * target_pct / 100
        with target_b.container(key=f"prescription_target_summary_{scenario_id}"):
            st.markdown(
                '<p class="formula-energy-calculation"><strong>EN energy target: '
                f'{prescription_energy_target:,.0f} kcal/day</strong> '
                f'({estimated_energy_requirement:,.0f} kcal/day × {target_pct:g}%).</p>',
                unsafe_allow_html=True,
            )
            interruption_key = scenario_key(
                scenario_id, "prescription_interruption_note"
            )
            if target_pct > 100:
                include_interruption_note = st.checkbox(
                    'Include “to account for anticipated interruptions” in the '
                    '**Chart note below**',
                    key=interruption_key,
                )
            else:
                st.session_state[interruption_key] = False
                include_interruption_note = False

    return (
        schedule_type, number(hours), feeds_per_day, target_pct,
        bool(include_interruption_note), prescription_energy_target,
    )


def render_en_scenario(
    scenario_id: str,
    label: str,
    candidate_frame: pd.DataFrame,
    saved_modulars: pd.DataFrame,
    saved_ons: pd.DataFrame | None,
    total_energy_target: float,
    protein_target: float,
    water_target: float | None,
    propofol_rate: float,
    propofol_hours: float = 24,
    *,
    propofol_conditions: list[dict[str, object]] | None = None,
    propofol_method: str | None = None,
    estimated_energy_requirement: float | None = None,
) -> dict[str, object]:
    """Render one schedule-first regimen and return its final calculation outputs."""
    conditions = propofol_conditions or [{
        "label": "Projected Propofol",
        "rate_ml_hr": propofol_rate,
        "hours": propofol_hours,
    }]
    propofol = (
        total_propofol_intake(conditions)
        if propofol_conditions is not None
        else propofol_intake(propofol_rate, propofol_hours)
    )
    conditional_mode = propofol_method in {
        "Changing Propofol rates", "Conditional EN rates",
    }
    energy_requirement = (
        estimated_energy_requirement
        if estimated_energy_requirement is not None else total_energy_target
    )
    (
        schedule_type, hours, feeds_per_day, prescription_target_pct,
        prescription_interruption_note, total_energy_target,
    ) = _render_en_prescription(
        scenario_id, conditional_mode, energy_requirement
    )

    comparison_energy_target = max(total_energy_target - propofol["kcal"], 0)
    comparison_rows = []
    for _, candidate in candidate_frame.iterrows():
        candidate_dict = candidate.to_dict()
        if conditional_mode:
            condition_rates = [
                suggested_conditional_formula_rate(
                    candidate_dict, total_energy_target, hours,
                    number(condition.get("rate_ml_hr")),
                )
                for condition in conditions
            ]
            delivery = conditional_feed_delivery(
                candidate_dict, hours, conditions, condition_rates
            )
            delivery_values = {
                (
                    "Suggested EN rate with lower/no Propofol (mL/hour)"
                    if condition.get("id") == "lower"
                    else "Suggested EN rate with higher Propofol (mL/hour)"
                ): rate
                for condition, rate in zip(conditions, condition_rates)
            }
        else:
            delivery = practical_feed_delivery(
                candidate_dict, comparison_energy_target, hours, 100,
                schedule_type, feeds_per_day,
            )
            delivery_column = (
                "Rate (mL/hour)"
                if schedule_type == "Continuous / cyclic" else "Volume/feed (mL)"
            )
            delivery_values = {delivery_column: (
                delivery["ordered_rate_ml_hr"]
                if schedule_type == "Continuous / cyclic"
                else delivery["ordered_volume_per_feed_ml"]
            )}
        volume_column = (
            "Projected EN volume (mL/day)"
            if conditional_mode else "Volume (mL/day)"
        )
        comparison_rows.append({
            "Feed": candidate["name"], volume_column: delivery["planned_volume_ml"],
            **delivery_values, "Energy (kcal/day)": delivery["energy_kcal"],
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
        if propofol["kcal"] > 0:
            st.markdown(
                '<p class="formula-energy-calculation">'
                f'<strong>{total_energy_target:,.0f} kcal EN energy target − '
                f'{propofol["kcal"]:,.0f} kcal from propofol = '
                f'{comparison_energy_target:,.0f} kcal</strong> used to calculate '
                'suggested formula volumes and rates.</p>',
                unsafe_allow_html=True,
            )
        if propofol["kcal"] >= total_energy_target and propofol["kcal"] > 0:
            st.warning(
                "Projected Propofol energy meets or exceeds the EN prescription "
                "energy target. A zero formula-energy allocation does not meet "
                "protein or micronutrient needs."
            )
        render_report_table(
            pd.DataFrame(comparison_rows), wide=True,
            decimals=FORMULA_COMPARISON_DECIMALS,
        )

    formula_container = st.container(border=True)
    with formula_container:
        render_box_heading("Select formula")
        formula_columns = st.columns(
            [1] if conditional_mode else [2.2, 1, 1.15],
            vertical_alignment="bottom",
        )
        selected_name = formula_columns[0].selectbox(
            "Formula", candidate_frame["name"].tolist(),
            key=scenario_key(scenario_id, "selected_formula"),
        )
        if not conditional_mode:
            calculated_order_slot = formula_columns[1].container()
            entered_order_slot = formula_columns[2].container()
            reset_order_slot = st.empty()
            order_summary_slot = st.empty()
            trickle_note_slot = st.empty()

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
        for condition in conditions:
            condition_id = str(condition.get("id", "condition"))
            st.session_state[scenario_key(
                scenario_id, f"conditional_{condition_id}_rate_ml_hr"
            )] = None
            st.session_state[scenario_key(
                scenario_id, f"conditional_{condition_id}_rate_user_edited"
            )] = False
    if st.session_state.get(ordered_schedule_key) != schedule_type:
        st.session_state[ordered_schedule_key] = schedule_type
        st.session_state[ordered_rate_key] = None
        st.session_state[ordered_volume_key] = None
        st.session_state[order_edited_key] = False

    conditional_orders: list[dict[str, object]] = []
    conditional_rates: list[float] = []
    if conditional_mode:
        with formula_container:
            st.markdown("**Formula rates by Propofol condition**")
            # Each column names itself. A heading spanning the pair had to be
            # centred across two sub-columns that Streamlit separates with a
            # gap, so it never sat over both, and "Adjust as needed" is an
            # instruction that does not inherit a noun heading the way
            # "Suggested" does.
            header_columns = st.columns(
                CONDITION_ROW_WIDTHS, vertical_alignment="bottom"
            )
            header_columns[1].markdown(
                '<p class="inline-field-label">Suggested formula rate'
                '<br><span>(mL/hour)</span></p>',
                unsafe_allow_html=True,
            )
            header_columns[2].markdown(
                '<p class="inline-field-label"><span>Adjust as needed</span></p>',
                unsafe_allow_html=True,
            )
            for condition in conditions:
                condition_id = str(condition.get("id", "condition"))
                condition_label = str(condition.get("label", "Propofol condition"))
                condition_propofol_rate = number(condition.get("rate_ml_hr"))
                suggestion = suggested_conditional_formula_rate(
                    formula, total_energy_target, hours, condition_propofol_rate
                )
                order_key = scenario_key(
                    scenario_id, f"conditional_{condition_id}_rate_ml_hr"
                )
                edited_key = scenario_key(
                    scenario_id, f"conditional_{condition_id}_rate_user_edited"
                )
                pending_key = scenario_key(
                    scenario_id, f"conditional_{condition_id}_reset_requested"
                )
                if st.session_state.get(pending_key):
                    st.session_state[pending_key] = False
                    st.session_state[edited_key] = False
                if (
                    not bool(st.session_state.get(edited_key))
                    or st.session_state.get(order_key) is None
                ):
                    st.session_state[order_key] = suggestion
                    st.session_state[edited_key] = False
                widget_key = propofol_widget_key(order_key)
                if not bool(st.session_state.get(edited_key)):
                    st.session_state[widget_key] = st.session_state[order_key]
                elif widget_key not in st.session_state:
                    st.session_state[widget_key] = st.session_state[order_key]
                condition_columns = st.columns(
                    CONDITION_ROW_WIDTHS, vertical_alignment="center"
                )
                condition_columns[0].markdown(
                    f'<p class="inline-field-label">{escape(condition_label)}<br>'
                    f'<span>Propofol {condition_propofol_rate:g} mL/hour</span></p>',
                    unsafe_allow_html=True,
                )
                condition_columns[1].markdown(
                    f'<p class="worked-bounds"><strong>{suggestion:.0f}</strong></p>',
                    unsafe_allow_html=True,
                )
                ordered_condition_rate = condition_columns[2].number_input(
                    f"Formula rate for {condition_label} (mL/hour)",
                    min_value=0.0, step=5.0, format="%.0f", key=widget_key,
                    label_visibility="collapsed",
                    on_change=sync_propofol_widget,
                    args=(widget_key, order_key, edited_key),
                )
                if st.session_state.get(edited_key):
                    condition_columns[3].button(
                        "Use suggested rate",
                        key=scenario_key(
                            scenario_id, f"conditional_{condition_id}_use_suggested"
                        ),
                        on_click=request_suggested_order, args=(pending_key,),
                    )
                conditional_rates.append(number(ordered_condition_rate))
                conditional_orders.append({
                    "id": condition_id,
                    "label": condition_label,
                    "propofol_rate_ml_hr": condition_propofol_rate,
                    "propofol_hours": number(condition.get("hours")),
                    "formula_rate_ml_hr": number(ordered_condition_rate),
                })
            order_summary_slot = st.empty()
            trickle_note_slot = st.empty()
        final_planned_delivery = conditional_feed_delivery(
            formula, hours, conditions, conditional_rates
        )
        ordered_amount = final_planned_delivery["ordered_rate_ml_hr"]
        total_condition_hours = sum(
            number(condition.get("hours")) for condition in conditions
        )
        equation_terms = []
        for condition, rate in zip(conditions, conditional_rates):
            allocated_hours = (
                hours * number(condition.get("hours")) / total_condition_hours
                if total_condition_hours > 0 else 0
            )
            equation_terms.append(
                f"{rate:.0f} mL/hour × {allocated_hours:g} hours"
            )
        order_summary = (
            'Projected formula delivery: ('
            + ") + (".join(escape(term) for term in equation_terms)
            + ") = "
            f'<strong>{final_planned_delivery["planned_volume_ml"]:,.0f} mL/day</strong>.'
        )
    else:
        suggested_final_delivery = practical_feed_delivery(
            formula, comparison_energy_target, hours, 100, schedule_type, feeds_per_day
        )
        if schedule_type == "Continuous / cyclic":
            order_key = ordered_rate_key
            suggestion = suggested_final_delivery["ordered_rate_ml_hr"]
            order_label = "Formula rate (mL/hour)"
            suggestion_label = "Suggested rate"
            use_suggestion_label = "Use suggested rate"
        else:
            order_key = ordered_volume_key
            suggestion = suggested_final_delivery["ordered_volume_per_feed_ml"]
            order_label = "Formula volume per feed (mL)"
            suggestion_label = "Suggested volume per feed"
            use_suggestion_label = "Use suggested volume"
        pending_reset_key = scenario_key(scenario_id, "order_reset_requested")
        if st.session_state.get(pending_reset_key):
            st.session_state[pending_reset_key] = False
            st.session_state[order_edited_key] = False
        order_was_edited = bool(st.session_state.get(order_edited_key))
        if not order_was_edited or st.session_state.get(order_key) is None:
            st.session_state[order_key] = suggestion
            st.session_state[order_edited_key] = False
        display_order_key = order_key
        order_change_callback = mark_order_as_edited
        order_change_args: tuple[object, ...] = (order_edited_key,)
        if propofol_method:
            display_order_key = propofol_widget_key(order_key)
            if not bool(st.session_state.get(order_edited_key)):
                st.session_state[display_order_key] = st.session_state[order_key]
            elif display_order_key not in st.session_state:
                st.session_state[display_order_key] = st.session_state[order_key]
            order_change_callback = sync_propofol_widget
            order_change_args = (
                display_order_key, order_key, order_edited_key,
            )
        calculated_order_slot.markdown(
            f'<p class="worked-bounds">{suggestion_label}:<br>'
            f'<strong>{suggestion:.0f} {"mL/hour" if schedule_type == "Continuous / cyclic" else "mL"}</strong></p>',
            unsafe_allow_html=True,
        )
        with entered_order_slot:
            ordered_amount = st.number_input(
                order_label, min_value=0.0, step=5.0, format="%.0f",
                key=display_order_key,
                on_change=order_change_callback, args=order_change_args,
            )
        if st.session_state.get(order_edited_key):
            reset_order_slot.button(
                use_suggestion_label,
                key=scenario_key(scenario_id, "use_suggested_order"),
                disabled=False,
                on_click=request_suggested_order, args=(pending_reset_key,),
            )
        else:
            reset_order_slot.empty()

        ordered_amount = number(ordered_amount)
        final_planned_delivery = ordered_feed_delivery(
            formula, ordered_amount, hours, 100, schedule_type, feeds_per_day
        )
        if schedule_type == "Continuous / cyclic":
            order_summary = (
                f'At <strong>{ordered_amount:.0f} mL/hour</strong> for '
                f'<strong>{hours:g} hours</strong>: '
                f'<strong>{final_planned_delivery["planned_volume_ml"]:.0f} mL</strong> formula/day.'
            )
        else:
            order_summary = (
                f'At <strong>{ordered_amount:.0f} mL per feed</strong>, '
                f'<strong>{feeds_per_day} feeds daily</strong>: '
                f'<strong>{final_planned_delivery["planned_volume_ml"]:.0f} mL</strong> formula/day.'
            )
    order_summary_slot.markdown(
        f'<p class="order-preview">{order_summary}</p>',
        unsafe_allow_html=True,
    )

    trickle_key = scenario_key(scenario_id, "describe_as_trickle")
    trickle_eligible = (
        schedule_type == "Continuous / cyclic"
        and (
            max(conditional_rates, default=ordered_amount) <= 30
            if conditional_mode else ordered_amount <= 30
        )
        and 23 <= hours <= 24
    )
    if trickle_eligible:
        with trickle_note_slot:
            describe_as_trickle = st.checkbox(
                "Describe as trickle/trophic feeding in the chart note",
                key=trickle_key,
            )
    else:
        st.session_state[trickle_key] = False
        describe_as_trickle = False

    formula_only_gap = protein_target - final_planned_delivery["protein_g"]
    with st.container(border=True):
        render_box_heading("Protein from formula" if propofol_method else "Protein from selected formula")
        gap_label = (
            "Projected protein gap"
            if propofol_method and formula_only_gap >= 0
            else "Shortfall" if formula_only_gap >= 0
            else "Exceeds goal by"
        )
        gap_class = " protein-shortfall" if formula_only_gap > 0 else ""
        st.markdown(
            '<p class="summary-line">'
            f'Goal: <strong>{protein_target:.0f} g/day</strong> &nbsp;|&nbsp; '
            f'{"Formula" if propofol_method else "Selected EN feed"}: '
            f'<strong>{final_planned_delivery["protein_g"]:.0f} g/day</strong> '
            f'&nbsp;|&nbsp; <span class="protein-gap{gap_class}">{gap_label}: '
            f'<strong>{abs(formula_only_gap):.0f} g/day</strong></span></p>',
            unsafe_allow_html=True,
        )

    modular_orders: list[dict[str, float]] = []
    modular_note_parts: list[str] = []
    # Products whose label does not publish a figure for each electrolyte, so
    # the intake table can say so instead of implying a measured zero.
    modular_undisclosed: dict[str, list[str]] = {
        "sodium": [], "potassium": [], "calcium": [], "phosphorus": [], "magnesium": [],
    }
    modular_protein_sources: list[str] = []
    modular_fat_sources: list[str] = []
    chart_modulars: list[dict[str, object]] = []
    chosen_modulars: list[str] = []
    with st.container(border=True):
        render_box_heading("Add modulars")
        if saved_modulars.empty:
            st.caption(
                "Missing a modular? Add it to My Modulars on the Formulary tab."
            )
        else:
            modular_ids_by_name = {
                str(product["name"]): str(product["id"])
                for _, product in saved_modulars.iterrows()
            }
            chosen_modulars = st.multiselect(
                "Modulars", saved_modulars["name"].tolist(),
                max_selections=6, key=scenario_key(scenario_id, "chosen_modulars"),
                on_change=reset_new_modular_orders,
                args=(scenario_id, modular_ids_by_name),
            )
            st.caption(
                "Missing a modular? Add it to My Modulars on the Formulary tab."
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
                    for nutrient in ("sodium", "potassium", "calcium",
                                     "phosphorus", "magnesium"):
                        if not order["disclosed"][f"{nutrient}_mg"]:
                            modular_undisclosed[nutrient].append(modular_name)
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

    ons_orders: list[dict[str, float]] = []
    chart_ons: list[dict[str, object]] = []
    if saved_ons is not None:
        chosen_key = scenario_key(scenario_id, "chosen_ons")
        available_ons_names = set(saved_ons["name"].tolist())
        if chosen_key in st.session_state:
            st.session_state[chosen_key] = [
                name for name in st.session_state[chosen_key]
                if name in available_ons_names
            ]
        with st.container(border=True):
            render_box_heading("Add ONS")
            if saved_ons.empty:
                st.caption("Missing an ONS? Add it to My ONS on the Formulary tab.")
            else:
                chosen_ons = st.multiselect(
                    "ONS orders",
                    saved_ons["name"].tolist(),
                    max_selections=6,
                    key=chosen_key,
                )
                st.caption("Missing an ONS? Add it to My ONS on the Formulary tab.")
                for ons_name in chosen_ons:
                    product = saved_ons.loc[
                        saved_ons["name"] == ons_name
                    ].iloc[0].to_dict()
                    serving_based = (
                        str(product.get("calculation_basis", "container_ml"))
                        .strip().casefold() == "serving"
                    )
                    if serving_based:
                        basis_description = (
                            f"{number(product['serving_size_g']):g} g per "
                            f"{escape(str(product['serving_unit']))}"
                        )
                        quantity_label = "Servings each time"
                        quantity_prefix = "ons_servings_"
                        quantity_caption = "servings"
                    else:
                        basis_description = (
                            f"{number(product['container_size_ml']):g} mL "
                            f"{escape(str(product['package_unit']))}"
                        )
                        quantity_label = "Containers each time"
                        quantity_prefix = "ons_containers_"
                        quantity_caption = "containers"
                    st.markdown(
                        f"**{escape(ons_name)}** — "
                        f"{basis_description}"
                    )
                    a, b = st.columns(2)
                    product_id = str(product["id"])
                    quantity_each_time = a.number_input(
                        quantity_label,
                        min_value=0.0,
                        step=0.5,
                        format="%.1f",
                        key=scenario_key(
                            scenario_id, f"{quantity_prefix}{product_id}"
                        ),
                    )
                    times_per_day = b.number_input(
                        "Times per day",
                        min_value=0.0,
                        step=1.0,
                        format="%.0f",
                        key=scenario_key(scenario_id, f"ons_times_{product_id}"),
                    )
                    order_is_complete = (
                        number(quantity_each_time) > 0
                        and number(times_per_day) > 0
                    )
                    order = ons_delivery(
                        product,
                        number(quantity_each_time) if order_is_complete else 0,
                        number(times_per_day) if order_is_complete else 0,
                    )
                    ons_orders.append(order)
                    if order_is_complete:
                        chart_ons.append({
                            "name": ons_name,
                            "product_name": product["product_name"],
                            "flavour": product["flavour"],
                            "package_unit": product["package_unit"],
                            "quantity_each_time": number(quantity_each_time),
                            "quantity_unit": (
                                product["serving_unit"]
                                if serving_based else product["package_unit"]
                            ),
                            "calculation_basis": (
                                "serving" if serving_based else "container_ml"
                            ),
                            "containers_each_time": (
                                number(quantity_each_time) if not serving_based else 0
                            ),
                            "servings_each_time": (
                                number(quantity_each_time) if serving_based else 0
                            ),
                            "times_per_day": number(times_per_day),
                            **order,
                        })
                    else:
                        st.caption(
                            f"Enter both the number of {quantity_caption} and frequency "
                            "to include this ONS."
                        )
    ons_totals = total_ons_delivery(ons_orders)

    if saved_ons is not None and chart_ons:
        en_provision = {
            "Energy (kcal/day)": (
                final_planned_delivery["energy_kcal"]
                + modular_totals["energy_kcal"]
            ),
            "Protein (g/day)": (
                final_planned_delivery["protein_g"]
                + modular_totals["protein_g"]
            ),
            "CHO (g/day)": (
                final_planned_delivery["carbohydrate_g"]
                + modular_totals["carbohydrate_g"]
            ),
            "Fat (g/day)": (
                final_planned_delivery["fat_g"] + modular_totals["fat_g"]
            ),
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
            render_report_table(pd.DataFrame([
                {"Source": "EN", **en_provision},
                {"Source": "ONS", **ons_provision},
                {
                    "Source": "Combined EN + ONS",
                    **{
                        key: en_provision[key] + ons_provision[key]
                        for key in en_provision
                    },
                },
            ]), decimals=DAILY_INTAKE_DECIMALS)
    # Protein modulars supplement the established EN order. Their energy is
    # shown in the final totals, but does not silently displace formula volume.
    # Propofol remains the intentional non-enteral energy deduction.
    final_formula_energy_target = comparison_energy_target
    if conditional_mode:
        schedule_description = (
            "; ".join(
                f'{order["formula_rate_ml_hr"]:.0f} mL/hour when Propofol is '
                f'{order["propofol_rate_ml_hr"]:g} mL/hour'
                for order in conditional_orders
            )
            + f"; projected over {hours:g} feeding hours daily"
        )
    else:
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
        if water_target is None:
            st.markdown(
                '<p class="summary-line">Water goal: <strong>not set</strong> '
                '&nbsp;|&nbsp; Water from formula and modulars: '
                f'<strong>{free_water_before_flushes:.0f} mL/day</strong></p>',
                unsafe_allow_html=True,
            )
            st.caption(
                "No hydration flushes are calculated or charted without a water "
                "goal. Enter one in Assessment or Adjust goals if enteral water "
                "is being managed for this patient."
            )
        else:
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
        if chart_ons:
            st.caption(
                "Free water from ONS is included in daily totals but excluded "
                "from water-flush calculations."
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
        # The hydration schedule exists only to distribute a goal-driven volume,
        # so it is hidden when no water goal is set. Medication and patency
        # flushes above are ordered independently and still apply.
        if water_target is None:
            flushes = 0
            hydration_schedule_text = ""
            hydration_chart_schedule_text = ""
        else:
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
        if water_target is not None:
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

        final_achieved_delivery = (
            conditional_feed_delivery(
                formula, hours, conditions, conditional_rates, achieved
            )
            if conditional_mode
            else ordered_feed_delivery(
                formula, ordered_amount, hours, achieved, schedule_type, feeds_per_day
            )
        )
        displayed_delivery = (
            final_planned_delivery if view_percent == 100 else final_achieved_delivery
        )
        final_protein = (
            displayed_delivery["protein_g"]
            + modular_totals["protein_g"]
            + ons_totals["protein_g"]
        )
        final_energy = (
            displayed_delivery["energy_kcal"]
            + modular_totals["energy_kcal"]
            + propofol["kcal"]
            + ons_totals["energy_kcal"]
        )
        if view_percent < 100:
            st.markdown(
                '<p class="summary-line">Showing estimated intake at '
                f'<strong>{view_percent}% formula delivery</strong>. Modulars and '
                'flushes remain unchanged.</p>',
                unsafe_allow_html=True,
            )
        other_protein_sources = list(modular_protein_sources)
        if ons_totals["protein_g"]:
            other_protein_sources.append(
                f"{ons_totals['protein_g']:.0f} g from ONS"
            )
        other_protein_text = "; ".join(other_protein_sources) or "None"
        displayed_total_water = (
            displayed_delivery["free_water_ml"]
            + modular_totals["free_water_ml"]
            + ons_totals["free_water_ml"]
            + modular_preparation_water
            + other_water_flushes
        )
        water_difference = (
            None if water_target is None
            else displayed_total_water - water_target
        )
        protein_difference = final_protein - protein_target
        energy_difference = final_energy - total_energy_target
        water_source_parts = []
        if modular_totals["free_water_ml"]:
            water_source_parts.append(
                f"{modular_totals['free_water_ml']:.0f} mL from modulars"
            )
        if ons_totals["free_water_ml"]:
            water_source_parts.append(
                f"{ons_totals['free_water_ml']:.0f} mL from ONS"
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
        check_rows = [
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
                    + (
                        f"; {ons_totals['energy_kcal']:.0f} kcal from ONS"
                        if ons_totals["energy_kcal"] else ""
                    )
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
            check_rows.append({
                "Component": "Water (mL/day)",
                "Goal": water_target,
                "From feed": displayed_delivery["free_water_ml"],
                "From other sources": water_sources_text,
                total_column: displayed_total_water,
                difference_column: signed_difference(water_difference),
            })
        final_checks = pd.DataFrame(check_rows)
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
            "Na (mmol)": mmol_if_disclosed(modular_totals, "sodium"),
            "K (mmol)": mmol_if_disclosed(modular_totals, "potassium"),
            "Ca (mmol)": mmol_if_disclosed(modular_totals, "calcium"),
            "P (mmol)": mmol_if_disclosed(modular_totals, "phosphorus"),
            "Mg (mmol)": mmol_if_disclosed(modular_totals, "magnesium"),
        },
        {
            "Source": "Water flushes", "Energy (kcal)": 0, "Protein (g)": 0,
            "Carbohydrate (g)": 0, "Fat (g)": 0, "Free water (mL)": 0,
            "Water flushes (mL)": other_water_flushes,
            "Na (mmol)": 0, "K (mmol)": 0, "Ca (mmol)": 0, "P (mmol)": 0,
            "Mg (mmol)": 0,
        },
    ]
    if chart_ons:
        source_rows.insert(2, {
            "Source": "ONS", "Energy (kcal)": ons_totals["energy_kcal"],
            "Protein (g)": ons_totals["protein_g"],
            "Carbohydrate (g)": ons_totals["carbohydrate_g"],
            "Fat (g)": ons_totals["fat_g"],
            "Free water (mL)": ons_totals["free_water_ml"],
            "Water flushes (mL)": 0,
            "Na (mmol)": mg_to_mmol("sodium", ons_totals["sodium_mg"]),
            "K (mmol)": mg_to_mmol("potassium", ons_totals["potassium_mg"]),
            "Ca (mmol)": mg_to_mmol("calcium", ons_totals["calcium_mg"]),
            "P (mmol)": mg_to_mmol("phosphorus", ons_totals["phosphorus_mg"]),
            "Mg (mmol)": mg_to_mmol("magnesium", ons_totals["magnesium_mg"]),
        })
    if propofol["kcal"] > 0:
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
            + ons_totals["energy_kcal"]
        ),
        "Protein (g)": (
            final_planned_delivery["protein_g"]
            + modular_totals["protein_g"]
            + ons_totals["protein_g"]
        ),
        "Fat (g)": (
            final_planned_delivery["fat_g"]
            + modular_totals["fat_g"]
            + propofol["fat_g"]
            + ons_totals["fat_g"]
        ),
    }
    chart_total = {
        "Energy (kcal)": (
            final_planned_delivery["energy_kcal"]
            + modular_totals["energy_kcal"]
            + propofol["kcal"]
            + ons_totals["energy_kcal"]
        ),
        "Protein (g)": (
            final_planned_delivery["protein_g"]
            + modular_totals["protein_g"]
            + ons_totals["protein_g"]
        ),
        "Carbohydrate (g)": (
            final_planned_delivery["carbohydrate_g"]
            + modular_totals["carbohydrate_g"]
            + ons_totals["carbohydrate_g"]
        ),
        "Fat (g)": (
            final_planned_delivery["fat_g"]
            + modular_totals["fat_g"]
            + propofol["fat_g"]
            + ons_totals["fat_g"]
        ),
        "Free water (mL)": (
            final_planned_delivery["free_water_ml"]
            + modular_totals["free_water_ml"]
            + ons_totals["free_water_ml"]
        ),
        "Water flushes (mL)": modular_preparation_water + other_water_flushes,
    }
    return {
        "label": label,
        "propofol_rate": propofol_rate, "propofol_hours": propofol_hours,
        "propofol": propofol,
        "propofol_method": propofol_method,
        "propofol_conditions": conditions,
        "conditional_orders": conditional_orders,
        "feeding_hours": hours,
        "estimated_energy_requirement": energy_requirement,
        "prescription_target_pct": prescription_target_pct,
        "prescription_energy_target": total_energy_target,
        "prescription_interruption_note": prescription_interruption_note,
        "formula": formula, "formula_energy_target": final_formula_energy_target,
        "schedule_description": schedule_description, "modulars": modular_note,
        "source_frame": source_frame, "total": total,
        "table_notes": [
            note for note in (
                # Each note explains one cell that does not mean what it looks
                # like. They are conditional so a plain plan carries none.
                (
                    "Free water from ONS is shown as oral intake but does not "
                    "affect hydration flush calculations."
                    if ons_totals["free_water_ml"] else ""
                ),
                (
                    f"{propofol['volume_ml']:.0f} mL/day from propofol is not "
                    "counted as free water."
                    if propofol["volume_ml"] else ""
                ),
                undisclosed_note(
                    modular_undisclosed,
                    {"sodium": "Na", "potassium": "K", "calcium": "Ca",
                     "phosphorus": "P", "magnesium": "Mg"},
                ),
            ) if note
        ],
        "planned_total": planned_total,
        "delivery": final_planned_delivery,
        "chart_total": chart_total,
        "modular_totals": modular_totals,
        "chart_modulars": chart_modulars,
        "ons_totals": ons_totals,
        "chart_ons": chart_ons,
        "hydration": hydration,
        "hydration_chart_schedule_text": hydration_chart_schedule_text,
        "medication_flushes_ml": number(medication),
        "patency_flushes_ml": number(patency),
        "describe_as_trickle": bool(describe_as_trickle),
        "view_percent": view_percent,
        "intake_heading": (
            "Planned daily intake"
            if view_percent == 100 else f"Estimated daily intake at {view_percent}% formula delivery"
        ),
    }


def render_en_workflow_setup(
    key_prefix: str,
    candidates_key: str,
) -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str], float, float, float
] | None:
    """Render shared Assessment goals and feed candidates for a planning workflow."""
    saved_ons = st.session_state.my_ons
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
        st.caption("Add at least one product to My Formulary to create an EN plan.")
        return None
    if total_energy_target is None or protein_target is None:
        st.caption("Enter energy and protein goals in Assessment or Adjust goals.")
        return None

    with st.container(border=True):
        render_box_heading("Formulas to compare")
        candidates = st.multiselect(
            "Select formulas", saved_feeds["name"].tolist(), max_selections=9, key=candidates_key
        )
        st.caption(
            "Missing a feed? Add it to My Formulary on the Formulary tab."
        )
    if not candidates:
        st.caption("Select at least one formula.")
        return None
    candidate_frame = saved_feeds.loc[saved_feeds["name"].isin(candidates)]
    return (
        candidate_frame, saved_modulars, saved_ons, candidates,
        float(total_energy_target), float(protein_target),
        None if water_target is None else float(water_target),
    )


def show_en_plan() -> None:
    setup = render_en_workflow_setup("en", "feed_candidates")
    if setup is None:
        return
    (
        candidate_frame, saved_modulars, saved_ons, candidates,
        total_energy_target, protein_target, water_target,
    ) = setup
    standard_migration = "lower" if any(
        key.startswith("scenario_lower_") for key in st.session_state
    ) else "primary" if any(key.startswith("scenario_primary_") for key in st.session_state) else None
    seed_scenario_state("standard", candidates, saved_modulars, standard_migration)
    st.session_state[scenario_key("standard", "propofol_rate")] = 0.0

    result = render_en_scenario(
        "standard", "EN plan", candidate_frame, saved_modulars, saved_ons,
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
        for note in result["table_notes"]:
            st.caption(str(note))
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
