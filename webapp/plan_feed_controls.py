"""Feed selection and order controls; layout and session keys are preserved."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

import pandas as pd
import streamlit as st
from calculations import (
    conditional_feed_delivery,
    mmol_from_delivery,
    practical_feed_delivery,
    propofol_intake,
    suggested_conditional_formula_rate,
    total_propofol_intake,
)
from constants import (
    FORMULA_COMPARISON_DECIMALS,
    ORDER_FORM_RATE_AND_HOURS,
    ORDER_FORM_RATE_PER_FEED,
    REGIMEN_SOURCE_EXISTING,
    REGIMEN_SOURCES,
    RUNNING_SHAPE_MEANINGS,
    RUNNING_SHAPES,
)
from plan_order import FeedOrder, FormulaEnergy
from session_state import (
    iv_fluid_totals,
    mark_order_as_edited,
    propofol_widget_key,
    request_suggested_order,
    scenario_key,
    sync_propofol_widget,
)
from ui_common import (
    number,
    render_alert,
    render_box_heading,
    render_report_table,
)

CONDITION_ROW_WIDTHS = [0.8, 0.8, 1, 0.95]


def _warn_if_over_a_day(
    hours: float, hours_per_feed: float, feeds_per_day: int
) -> None:
    """Flag a feed schedule that does not fit in a day, without refusing it.

    Blocking the entry would be out of character: the arithmetic still
    describes the order as it was given, and the clinician may be part way
    through typing it.
    """
    if hours <= 24:
        return
    render_alert(
        "warning",
        f"{hours_per_feed:g} hours per feed across {feeds_per_day} feeds is "
        f"{hours:g} hours, which is more than a day. The volumes below still "
        "follow what was entered.",
    )


def _render_regimen_source(scenario_id: str) -> str:
    """Ask which direction of work the page is being used for.

    This decides what the whole page looks like, so it sits above every box
    rather than inside one named for prescribing. It is also asked before the
    assessment goals are required, because reviewing a running feed does not
    need them.
    """
    return str(
        st.radio(
            "Are you...",
            REGIMEN_SOURCES,
            horizontal=True,
            label_visibility="collapsed",
            key=scenario_key(scenario_id, "regimen_source"),
        )
    )


def _render_en_prescription(
    scenario_id: str,
    reviewing: bool,
    conditional_mode: bool,
    estimated_energy_requirement: float | None,
) -> tuple[float, bool, float | None, tuple[str, float, int, str, float] | None]:
    """Render the energy prescription for the chosen direction of work.

    The schedule is returned only when a feed is being started. When a running
    feed is being reviewed the schedule belongs beside the order instead, so the
    caller renders it there and this returns None for it.
    """
    if reviewing:
        # Reviewing sets no target: the goal is the assessed requirement and
        # the running order is measured against it. A prescription percentage
        # would be asking what the feed is meant to achieve, which is not the
        # question when the order already exists.
        st.session_state[scenario_key(scenario_id, "prescription_target_pct")] = 100.0
        return (
            100.0,
            False,
            estimated_energy_requirement,
            None,
        )

    with st.container(border=True):
        render_box_heading("EN regimen")
        schedule = _render_running_shape(scenario_id, conditional_mode)

        target_a, target_b = st.columns([1, 1.7], vertical_alignment="bottom")
        prescription_target_pct = target_a.number_input(
            "EN regimen target (%)",
            min_value=1.0,
            max_value=200.0,
            step=5.0,
            format="%.0f",
            key=scenario_key(scenario_id, "prescription_target_pct"),
            help=(
                "Values above 100% increase the EN regimen to account for "
                "expected interruptions. Protein and water goals are unchanged."
            ),
        )
        target_pct = number(prescription_target_pct)
        prescription_energy_target = estimated_energy_requirement * target_pct / 100
        with target_b.container(key=f"prescription_target_summary_{scenario_id}"):
            st.markdown(
                '<p class="formula-energy-calculation"><strong>EN energy target: '
                f"{prescription_energy_target:,.0f} kcal/day</strong> "
                f"({estimated_energy_requirement:,.0f} kcal/day × {target_pct:g}%).</p>",
                unsafe_allow_html=True,
            )
            interruption_key = scenario_key(
                scenario_id, "prescription_interruption_note"
            )
            if target_pct > 100:
                include_interruption_note = st.checkbox(
                    "Include “to account for anticipated interruptions” in the "
                    "**Chart note below**",
                    key=interruption_key,
                )
            else:
                st.session_state[interruption_key] = False
                include_interruption_note = False

    return (
        target_pct,
        bool(include_interruption_note),
        prescription_energy_target,
        schedule,
    )


def _render_running_shape(
    scenario_id: str,
    conditional_mode: bool = False,
    pair_amount: bool = False,
):
    """Ask how the feed runs, as one question rather than two nested ones.

    The three answers each settle both facts the calculation needs: whether
    the feed is continuous or intermittent, and whether the amount is a rate or
    a volume. Asking those separately made the second question look like a
    property of the feed when it is really a property of the order.

    Entering a daily total is deliberately absent. It is not a way a feed runs,
    and on either screen the number beside it is already shown, so it would be
    a fourth answer to a question it does not answer.

    With `pair_amount`, the amount shares a row with the number qualifying it,
    a rate with its hours and a volume with its feeds, and the column for it is
    returned. Where a feed comparison sits between the two that cannot hold, so
    the caller places the amount itself and this returns None.
    """
    if conditional_mode:
        # Sedation-conditional rates run continuously by construction, and
        # their per-condition rates are entered on their own rows below.
        st.session_state[scenario_key(scenario_id, "schedule_type")] = (
            "Continuous / cyclic"
        )
        st.session_state[scenario_key(scenario_id, "order_entry_form")] = (
            ORDER_FORM_RATE_AND_HOURS
        )
        hours = number(
            st.number_input(
                "Feeding hours/day",
                min_value=1.0,
                max_value=24.0,
                step=1.0,
                format="%.0f",
                key=scenario_key(scenario_id, "feeding_hours"),
            )
        )
        schedule = (
            "Continuous / cyclic",
            hours,
            1,
            ORDER_FORM_RATE_AND_HOURS,
            0.0,
        )
        return (schedule, None) if pair_amount else schedule

    running = st.radio(
        "How is EN running?" if pair_amount else "How will EN run?",
        RUNNING_SHAPES,
        key=scenario_key(scenario_id, "running_shape"),
    )
    schedule_type, order_form = RUNNING_SHAPE_MEANINGS[running]
    st.session_state[scenario_key(scenario_id, "schedule_type")] = schedule_type
    st.session_state[scenario_key(scenario_id, "order_entry_form")] = order_form

    feeds_per_day = 1
    hours_per_feed = 0.0
    amount_column = None
    if pair_amount:
        amount_column, qualifier = st.columns(2, vertical_alignment="top")
    else:
        qualifier = st.container()

    if order_form == ORDER_FORM_RATE_AND_HOURS:
        hours = number(
            qualifier.number_input(
                "Hours a day",
                min_value=1.0,
                max_value=24.0,
                step=1.0,
                format="%.0f",
                key=scenario_key(scenario_id, "feeding_hours"),
            )
        )
    elif order_form == ORDER_FORM_RATE_PER_FEED:
        # Running at a rate for a set time each feed is arithmetically the same
        # as that rate over the summed hours, which is why the calculation does
        # not have to know this shape exists.
        hours_per_feed = number(
            qualifier.number_input(
                "Hours each feed",
                min_value=0.5,
                max_value=24.0,
                step=0.5,
                format="%.1f",
                key=scenario_key(scenario_id, "hours_per_feed"),
            )
        )
        feeds_per_day = int(
            st.number_input(
                "Feeds a day",
                min_value=1,
                max_value=12,
                step=1,
                key=scenario_key(scenario_id, "feeds_per_day"),
            )
        )
        hours = hours_per_feed * feeds_per_day
        _warn_if_over_a_day(hours, hours_per_feed, feeds_per_day)
    else:
        hours = 24.0
        feeds_per_day = int(
            qualifier.number_input(
                "Feeds a day",
                min_value=1,
                max_value=12,
                step=1,
                key=scenario_key(scenario_id, "feeds_per_day"),
            )
        )

    schedule = (
        schedule_type,
        number(hours),
        feeds_per_day,
        order_form,
        hours_per_feed,
    )
    return (schedule, amount_column) if pair_amount else schedule


@dataclass(frozen=True)
class FeedSelection:
    formula: dict[str, object]
    order: FeedOrder
    planned_delivery: dict[str, float]
    propofol: dict[str, float]
    iv_fluids: dict[str, float]
    conditions: list[dict[str, object]]
    conditional_orders: list[dict[str, object]]
    energy_requirement: float | None
    prescription_target_pct: float
    prescription_interruption_note: str
    energy_target: float | None
    schedule: tuple[str, float, int, str, float]
    entered_amount: float
    describe_as_trickle: bool
    reviewing_regimen: bool


def render_feed_selection(
    scenario_id: str,
    candidate_frame: pd.DataFrame,
    total_energy_target: float | None,
    protein_target: float | None,
    propofol_rate: float,
    propofol_hours: float,
    *,
    propofol_conditions: list[dict[str, object]] | None,
    propofol_method: str | None,
    estimated_energy_requirement: float | None,
) -> FeedSelection | None:
    """Keep the starting/reviewing layouts and return the entered feed order."""
    conditions = propofol_conditions or [
        {
            "label": "Projected Propofol",
            "rate_ml_hr": propofol_rate,
            "hours": propofol_hours,
        }
    ]
    propofol = (
        total_propofol_intake(conditions)
        if propofol_conditions is not None
        else propofol_intake(propofol_rate, propofol_hours)
    )
    conditional_mode = propofol_method in {
        "Changing Propofol rates",
        "Conditional EN rates",
    }
    energy_requirement = (
        estimated_energy_requirement
        if estimated_energy_requirement is not None
        else total_energy_target
    )
    regimen_source = _render_regimen_source(scenario_id)
    # Starting a feed is a browsing job, so the schedule sits with the
    # prescription above a comparison of candidate feeds. Reviewing a running
    # feed is a transcription job: the schedule, the amount and the result
    # belong together beside the formula, and a comparison of suggested rates
    # is not wanted. The two need different arrangements, not one arrangement
    # with a flag.
    # Sedation-conditional rates are not a single order, so the review layout
    # does not apply to them. That path keeps its own per-condition entry.
    # Two separate questions. Whether the order is already running governs
    # behaviour: nothing may overwrite what was typed, and the note says
    # "Continue". Whether to use the review layout is narrower, because
    # conditional sedation rates are not a single order and keep their own
    # screen. Carrying both on one flag silently disabled the first for them.
    reviewing_regimen = regimen_source == REGIMEN_SOURCE_EXISTING
    regimen_already_running = reviewing_regimen and not conditional_mode
    # A running order is a fact to be transcribed, so it can be read out
    # against no goals at all: every figure below describes what the feed
    # delivers rather than how far it falls from a target. Every other
    # direction of work calculates an amount backwards from the energy goal
    # and cannot begin without one.
    if not regimen_already_running and (
        energy_requirement is None or protein_target is None
    ):
        # Reviewing has already been chosen on the one path that reaches here
        # with it set, which is changing Propofol rates, so pointing at it
        # again would read as an instruction the clinician has followed. What
        # is missing there is the goal the two conditional rates are worked
        # back from.
        st.caption(
            "Enter energy and protein goals in Assessment or Adjust goals. "
            "Rates for changing Propofol conditions are calculated from the "
            "energy goal, so they are suggested rather than transcribed."
            if reviewing_regimen
            else "Enter energy and protein goals in Assessment or Adjust goals to "
            "calculate a suggested rate, or select “Reviewing a feed already "
            "running” to enter an order that is running now."
        )
        return None
    (
        prescription_target_pct,
        prescription_interruption_note,
        total_energy_target,
        schedule,
    ) = _render_en_prescription(
        scenario_id, regimen_already_running, conditional_mode, energy_requirement
    )
    review_container = st.container(border=True) if regimen_already_running else None
    if regimen_already_running:
        with review_container:
            render_box_heading("EN regimen")
            # The formula is claimed first so it renders above the schedule,
            # matching how an order reads: the feed, then how it runs.
            formula_slot = st.container()
            schedule, amount_column = _render_running_shape(
                scenario_id, conditional_mode, pair_amount=True
            )
            reset_order_slot = st.empty()
            order_summary_slot = st.empty()
            trickle_note_slot = st.empty()
    schedule_type, hours, feeds_per_day, order_form, hours_per_feed = schedule

    # Intravenous dextrose supplies energy the feed no longer has to, so it
    # reduces the EN target the same way propofol does. Volume is not
    # subtracted anywhere: the goals are entered net of intravenous fluid.
    # Modular energy is deliberately not deducted here. It appears in the final
    # totals, but deducting it would silently displace formula volume, so
    # propofol and intravenous energy stay the only intentional deductions.
    iv_fluids = iv_fluid_totals()
    # Conditional suggestions subtract each condition's own 24-hour propofol
    # exposure below. Deduct IV energy here once, without subtracting the
    # duration-weighted propofol total a second time.
    energy = FormulaEnergy.from_target(
        total_energy_target, iv_fluids["energy_kcal"], propofol["kcal"]
    )
    energy_target_after_iv = energy.after_iv
    comparison_energy_target = energy.after_iv_and_propofol
    # Suggested rates for every candidate feed are the point of the screen when
    # choosing one, and noise when the order already exists.
    comparison_rows = []
    candidates_to_compare = (
        [] if regimen_already_running else list(candidate_frame.iterrows())
    )
    for _, candidate in candidates_to_compare:
        candidate_dict = candidate.to_dict()
        if conditional_mode:
            condition_rates = [
                suggested_conditional_formula_rate(
                    candidate_dict,
                    energy_target_after_iv,
                    hours,
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
                candidate_dict,
                comparison_energy_target,
                hours,
                100,
                schedule_type,
                feeds_per_day,
            )
            delivery_column = (
                "Rate (mL/hour)"
                if schedule_type == "Continuous / cyclic"
                else "Volume/feed (mL)"
            )
            delivery_values = {
                delivery_column: (
                    delivery["ordered_rate_ml_hr"]
                    if schedule_type == "Continuous / cyclic"
                    else delivery["ordered_volume_per_feed_ml"]
                )
            }
        volume_column = (
            "Projected EN volume (mL/day)" if conditional_mode else "Volume (mL/day)"
        )
        comparison_rows.append(
            {
                "Feed": candidate["name"],
                volume_column: delivery["planned_volume_ml"],
                **delivery_values,
                "Energy (kcal/day)": delivery["energy_kcal"],
                "Protein (g/day)": delivery["protein_g"],
                "Free water (mL/day)": delivery["free_water_ml"],
                "Na (mmol/day)": mmol_from_delivery(delivery, "sodium"),
                "K (mmol/day)": mmol_from_delivery(delivery, "potassium"),
                "Ca (mmol/day)": mmol_from_delivery(delivery, "calcium"),
                "P (mmol/day)": mmol_from_delivery(delivery, "phosphorus"),
                "Mg (mmol/day)": mmol_from_delivery(delivery, "magnesium"),
            }
        )
    if not regimen_already_running:
        with st.container(
            key=f"fullbleed_formula_comparison_{scenario_id}", border=True
        ):
            render_box_heading("Formula comparison")
            comparison_note = (
                "Suggested rates are rounded to the nearest 5 mL/hour."
                if schedule_type == "Continuous / cyclic"
                else "Suggested volumes per feed are rounded to the nearest 5 mL."
            )
            st.caption(comparison_note)
            if conditional_mode:
                st.markdown(
                    '<p class="formula-energy-calculation">'
                    f"<strong>{total_energy_target:,.0f} kcal EN energy target − "
                    f"{iv_fluids['energy_kcal']:,.0f} kcal from IV fluids = "
                    f"{energy_target_after_iv:,.0f} kcal</strong>. Each condition's "
                    "suggested formula rate then subtracts the energy from that "
                    "Propofol rate projected over 24 hours, with a minimum "
                    "formula-energy allocation of zero, and divides by the "
                    "feeding hours and formula energy per mL. Projected daily "
                    "intake uses the expected hours at each condition.</p>",
                    unsafe_allow_html=True,
                )
            elif propofol["kcal"] > 0 or iv_fluids["energy_kcal"] > 0:
                st.markdown(
                    '<p class="formula-energy-calculation">'
                    f"<strong>{total_energy_target:,.0f} kcal EN energy target − "
                    f"{propofol['kcal']:,.0f} kcal from propofol − "
                    f"{iv_fluids['energy_kcal']:,.0f} kcal from IV fluids = "
                    f"{comparison_energy_target:,.0f} kcal</strong> used to calculate "
                    "suggested formula volumes and rates (minimum zero).</p>",
                    unsafe_allow_html=True,
                )
            if propofol["kcal"] >= total_energy_target and propofol["kcal"] > 0:
                render_alert(
                    "warning",
                    "Projected Propofol energy meets or exceeds the EN "
                    "regimen energy target. A zero formula-energy "
                    "allocation does not meet protein or micronutrient needs.",
                )
            render_report_table(
                pd.DataFrame(comparison_rows),
                wide=True,
                decimals=FORMULA_COMPARISON_DECIMALS,
            )
            # Choosing from the comparison and setting the amount belong in the
            # box that shows the comparison, not in a separate card below it.
            # That also removes the caption that used to point down the page.
            formula_container = st.container()

    # Reviewing reads in the order the chart is written: the feed, then how it
    # runs, then the amount. Those three are separate slots so the schedule
    # question can sit between the formula and the number it governs.
    if regimen_already_running:
        with formula_slot:
            selected_name = st.selectbox(
                "Formula",
                candidate_frame["name"].tolist(),
                key=scenario_key(scenario_id, "selected_formula"),
            )
        # The suggested figure sits directly beneath the box it refers to, so
        # there is no doubt which entry it belongs to.
        with amount_column:
            entered_order_slot = st.container()
            calculated_order_slot = st.container()
    else:
        with formula_container:
            formula_columns = st.columns(
                [1] if conditional_mode else [2.2, 1.4],
                # Top-aligned for the same reason as the review layout: the
                # entry column is the taller one once the suggestion sits below.
                vertical_alignment="top",
            )
            selected_name = formula_columns[0].selectbox(
                "Formula",
                candidate_frame["name"].tolist(),
                key=scenario_key(scenario_id, "selected_formula"),
            )
            if not conditional_mode:
                # Entry first, suggested figure directly beneath it, so the two
                # read as a pair rather than as two neighbouring columns whose
                # labels and boxes sit at different heights.
                with formula_columns[1]:
                    entered_order_slot = st.container()
                    calculated_order_slot = st.container()
                reset_order_slot = st.empty()
                order_summary_slot = st.empty()
                trickle_note_slot = st.empty()

    formula = (
        candidate_frame.loc[candidate_frame["name"] == selected_name].iloc[0].to_dict()
    )
    ordered_formula_key = scenario_key(scenario_id, "ordered_formula_name")
    ordered_rate_key = scenario_key(scenario_id, "ordered_rate_ml_hr")
    ordered_volume_key = scenario_key(scenario_id, "ordered_volume_per_feed_ml")
    order_edited_key = scenario_key(scenario_id, "order_user_edited")
    ordered_schedule_key = scenario_key(scenario_id, "ordered_schedule_type")
    if st.session_state.get(ordered_formula_key) != selected_name:
        st.session_state[ordered_formula_key] = selected_name
        # Changing feed on a running regimen is comparing an alternative, not
        # abandoning the order. The entered rate keeps its meaning, because its
        # units have not changed, so it survives and drives the comparison.
        if not reviewing_regimen:
            st.session_state[ordered_rate_key] = None
            st.session_state[ordered_volume_key] = None
            st.session_state[order_edited_key] = False
            for condition in conditions:
                condition_id = str(condition.get("id", "condition"))
                st.session_state[
                    scenario_key(scenario_id, f"conditional_{condition_id}_rate_ml_hr")
                ] = None
                st.session_state[
                    scenario_key(
                        scenario_id, f"conditional_{condition_id}_rate_user_edited"
                    )
                ] = False
    # Changing schedule or entry form changes the units of the entered number,
    # from a rate to a volume per feed to a daily total, so a stale value would
    # be misread. This clears in both directions of work, unlike the feed
    # change above, because there the units are unaffected.
    # Tracked in two keys rather than one combined string, because
    # `ordered_schedule_type` is validated against the schedule names when a
    # saved record is reopened and would reject anything else.
    ordered_form_key = scenario_key(scenario_id, "ordered_entry_form")
    if (
        st.session_state.get(ordered_schedule_key) != schedule_type
        or st.session_state.get(ordered_form_key) != order_form
    ):
        st.session_state[ordered_schedule_key] = schedule_type
        st.session_state[ordered_form_key] = order_form
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
                "<br><span>(mL/hour)</span></p>",
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
                    formula, energy_target_after_iv, hours, condition_propofol_rate
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
                    # An explicit request replaces even a running order.
                    st.session_state[order_key] = suggestion
                    st.session_state[pending_key] = False
                    st.session_state[edited_key] = False
                # The conditional twin of the single-rate seeding below. On a
                # running regimen each condition's entered rate is seeded once
                # and then left alone, or the suggestion would overwrite it on
                # the next rerun exactly as it does on the plan tab.
                if st.session_state.get(order_key) is None:
                    st.session_state[order_key] = suggestion
                    st.session_state[edited_key] = False
                elif (
                    not bool(st.session_state.get(edited_key)) and not reviewing_regimen
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
                    f"<span>Propofol {condition_propofol_rate:g} mL/hour</span></p>",
                    unsafe_allow_html=True,
                )
                condition_columns[1].markdown(
                    f'<p class="worked-bounds"><strong>{suggestion:.0f}</strong></p>',
                    unsafe_allow_html=True,
                )
                ordered_condition_rate = condition_columns[2].number_input(
                    f"Formula rate for {condition_label} (mL/hour)",
                    min_value=0.0,
                    step=5.0,
                    format="%.0f",
                    key=widget_key,
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
                        on_click=request_suggested_order,
                        args=(pending_key,),
                    )
                conditional_rates.append(number(ordered_condition_rate))
                conditional_orders.append(
                    {
                        "id": condition_id,
                        "label": condition_label,
                        "propofol_rate_ml_hr": condition_propofol_rate,
                        "propofol_hours": number(condition.get("hours")),
                        "formula_rate_ml_hr": number(ordered_condition_rate),
                    }
                )
            order_summary_slot = st.empty()
            trickle_note_slot = st.empty()
        feed_order = FeedOrder.from_conditions(hours, conditions, conditional_rates)
        final_planned_delivery = feed_order.delivery(formula)
        ordered_amount = final_planned_delivery["ordered_rate_ml_hr"]
        total_condition_hours = sum(
            number(condition.get("hours")) for condition in conditions
        )
        equation_terms = []
        for condition, rate in zip(conditions, conditional_rates):
            allocated_hours = (
                hours * number(condition.get("hours")) / total_condition_hours
                if total_condition_hours > 0
                else 0
            )
            equation_terms.append(f"{rate:.0f} mL/hour × {allocated_hours:g} hours")
        order_summary = (
            "Projected formula delivery: ("
            + ") + (".join(escape(term) for term in equation_terms)
            + ") = "
            f'<strong>{final_planned_delivery["planned_volume_ml"]:,.0f} mL/day</strong>.'
        )
    else:
        # Without an energy goal there is no figure to suggest an amount from,
        # so the box below is left for the running order to be typed into and
        # no suggestion is offered.
        suggested_final_delivery = (
            None
            if comparison_energy_target is None
            else practical_feed_delivery(
                formula,
                comparison_energy_target,
                hours,
                100,
                schedule_type,
                feeds_per_day,
            )
        )
        # Each form names its own quantity, and the suggestion is rounded in
        # the same unit the clinician sets. A rate-based form rounds the rate,
        # so on an intermittent schedule the resulting volume per feed need not
        # land on a multiple of 5, which is right because the pump is set by
        # rate rather than by volume.
        if order_form == ORDER_FORM_RATE_PER_FEED:
            order_key = ordered_rate_key
            suggestion = (
                None
                if comparison_energy_target is None
                else practical_feed_delivery(
                    formula,
                    comparison_energy_target,
                    hours,
                    100,
                    "Continuous / cyclic",
                    1,
                )["ordered_rate_ml_hr"]
            )
            order_label = "Formula rate (mL/hour)"
            use_suggestion_label = "Use suggested rate"
            order_unit = "mL/hour"
        elif schedule_type == "Continuous / cyclic":
            order_key = ordered_rate_key
            suggestion = (
                None
                if suggested_final_delivery is None
                else suggested_final_delivery["ordered_rate_ml_hr"]
            )
            order_label = "Formula rate (mL/hour)"
            use_suggestion_label = "Use suggested rate"
            order_unit = "mL/hour"
        else:
            order_key = ordered_volume_key
            suggestion = (
                None
                if suggested_final_delivery is None
                else suggested_final_delivery["ordered_volume_per_feed_ml"]
            )
            order_label = "Formula volume per feed (mL)"
            use_suggestion_label = "Use suggested volume"
            order_unit = "mL/feed"
        pending_reset_key = scenario_key(scenario_id, "order_reset_requested")
        if st.session_state.get(pending_reset_key):
            # Apply the requested value before the widget is instantiated.
            st.session_state[order_key] = suggestion
            st.session_state[pending_reset_key] = False
            st.session_state[order_edited_key] = False
        order_was_edited = bool(st.session_state.get(order_edited_key))
        # On a running regimen the box is seeded once while empty and then left
        # alone, so what the clinician typed is never silently replaced by the
        # suggestion on the next rerun.
        if st.session_state.get(order_key) is None:
            st.session_state[order_key] = suggestion
            st.session_state[order_edited_key] = False
        elif not order_was_edited and not reviewing_regimen:
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
                display_order_key,
                order_key,
                order_edited_key,
            )
        if suggestion is not None:
            calculated_order_slot.markdown(
                f'<p class="worked-bounds">Suggested: '
                f"<strong>{suggestion:.0f} {order_unit}</strong></p>",
                unsafe_allow_html=True,
            )
        with entered_order_slot:
            ordered_amount = st.number_input(
                order_label,
                min_value=0.0,
                step=5.0,
                format="%.0f",
                key=display_order_key,
                on_change=order_change_callback,
                args=order_change_args,
            )
        # Nothing to return to when no suggestion was offered, so the button
        # that restores it is not shown either.
        if suggestion is not None and st.session_state.get(order_edited_key):
            reset_order_slot.button(
                use_suggestion_label,
                key=scenario_key(scenario_id, "use_suggested_order"),
                disabled=False,
                on_click=request_suggested_order,
                args=(pending_reset_key,),
            )
        else:
            reset_order_slot.empty()

        ordered_amount = number(ordered_amount)
        # The forms collapse here. Whatever was typed becomes the quantity the
        # existing calculation already expects for this schedule, so nothing
        # downstream of this point knows which form produced it.
        feed_order = FeedOrder.from_entry(
            entered_amount=ordered_amount,
            order_form=order_form,
            hours_per_feed=hours_per_feed,
            hours=hours,
            schedule_type=schedule_type,
            feeds_per_day=feeds_per_day,
        )
        engine_amount = feed_order.amount
        final_planned_delivery = feed_order.delivery(formula)
        daily_volume = final_planned_delivery["planned_volume_ml"]
        if order_form == ORDER_FORM_RATE_PER_FEED:
            order_summary = (
                f"At <strong>{ordered_amount:.0f} mL/hour</strong> for "
                f"<strong>{hours_per_feed:g} hours per feed</strong>, "
                f"<strong>{feeds_per_day} feeds daily</strong>: "
                f"<strong>{engine_amount:.0f} mL per feed</strong>, "
                f"<strong>{daily_volume:.0f} mL</strong> formula/day."
            )
        elif schedule_type == "Continuous / cyclic":
            order_summary = (
                f"At <strong>{ordered_amount:.0f} mL/hour</strong> for "
                f"<strong>{hours:g} hours</strong>: "
                f"<strong>{daily_volume:.0f} mL</strong> formula/day."
            )
        else:
            order_summary = (
                f"At <strong>{ordered_amount:.0f} mL per feed</strong>, "
                f"<strong>{feeds_per_day} feeds daily</strong>: "
                f"<strong>{daily_volume:.0f} mL</strong> formula/day."
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
            if conditional_mode
            else ordered_amount <= 30
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

    return FeedSelection(
        formula=formula,
        order=feed_order,
        planned_delivery=final_planned_delivery,
        propofol=propofol,
        iv_fluids=iv_fluids,
        conditions=conditions,
        conditional_orders=conditional_orders,
        energy_requirement=energy_requirement,
        prescription_target_pct=prescription_target_pct,
        prescription_interruption_note=prescription_interruption_note,
        energy_target=total_energy_target,
        schedule=schedule,
        entered_amount=ordered_amount,
        describe_as_trickle=describe_as_trickle,
        reviewing_regimen=reviewing_regimen,
    )
