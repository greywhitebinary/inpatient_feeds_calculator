"""Shared enteral formula, modular, hydration, and plan-check workflow."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st
from assessment_ui import render_assessment_goals
from calculations import (
    combined_intake,
    conditional_feed_delivery,
    hydration_flushes_per_day,
    mg_to_mmol,
    micronutrient_delivery,
    modular_delivery,
    ons_delivery,
    ordered_feed_delivery,
    ordered_flush_schedule,
    practical_feed_delivery,
    propofol_intake,
    suggested_conditional_formula_rate,
    total_modular_delivery,
    total_ons_delivery,
    total_propofol_intake,
    water_plan,
)
from case_record_ui import render_save_record
from chart_note import build_chart_note_html, render_chart_note_editor
from constants import (
    DAILY_INTAKE_DECIMALS,
    FORMULA_COMPARISON_DECIMALS,
    HYDRATION_ENTRY_MODES,
    HYDRATION_ENTRY_ORDERED,
    MICRONUTRIENT_ROW_DECIMALS,
    MICRONUTRIENT_ROW_LABELS,
    ORDER_FORM_RATE_AND_HOURS,
    ORDER_FORM_RATE_PER_FEED,
    PERI_FEED_FLUSH_NONE,
    PERI_FEED_FLUSH_PATTERNS,
    PERI_FEED_FLUSHES_PER_FEED,
    PLAN_CHECK_DECIMALS,
    REGIMEN_SOURCE_EXISTING,
    REGIMEN_SOURCES,
    RUNNING_SHAPE_MEANINGS,
    RUNNING_SHAPES,
    WATER_MODE_CHART_ONLY,
)
from session_state import (
    iv_fluid_orders,
    iv_fluid_totals,
    mark_order_as_edited,
    propofol_widget_key,
    request_suggested_order,
    reset_new_modular_orders,
    scenario_key,
    seed_scenario_state,
    show_partial_formula_delivery,
    sync_propofol_widget,
)
from ui_common import (
    mmol_from_delivery,
    mmol_if_disclosed,
    modular_chart_amount,
    modular_daily_amount,
    modular_unit,
    number,
    render_alert,
    render_box_heading,
    render_report_table,
    uncounted_volume_note,
    undisclosed_note,
)

# Shared by the header row and every condition row, so the columns line up.
# The condition column is kept narrow so the Propofol rate sits close to the
# suggested formula rate it drives; a wide first column reads as two unrelated
# halves rather than as cause and effect.
CONDITION_ROW_WIDTHS = [0.8, 0.8, 1, 0.95]


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


def _render_en_prescription(
    scenario_id: str,
    conditional_mode: bool,
    estimated_energy_requirement: float,
) -> tuple[str, float, bool, float, tuple[str, float, int, str, float] | None]:
    """Render the direction of work and the energy prescription.

    The schedule is returned only when a feed is being started. When a running
    feed is being reviewed the schedule belongs beside the order instead, so the
    caller renders it there and this returns None for it.
    """
    # This decides what the whole page looks like, so it sits above every box
    # rather than inside one named for prescribing.
    regimen_source = st.radio(
        "Are you...",
        REGIMEN_SOURCES,
        horizontal=True,
        label_visibility="collapsed",
        key=scenario_key(scenario_id, "regimen_source"),
    )
    # Conditional sedation rates keep the prescription layout, so the
    # schedule is still rendered here for them.
    reviewing = regimen_source == REGIMEN_SOURCE_EXISTING and not conditional_mode
    if reviewing:
        # Reviewing sets no target: the goal is the assessed requirement and
        # the running order is measured against it. A prescription percentage
        # would be asking what the feed is meant to achieve, which is not the
        # question when the order already exists.
        st.session_state[scenario_key(scenario_id, "prescription_target_pct")] = 100.0
        return (
            str(regimen_source),
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
        str(regimen_source),
        target_pct,
        bool(include_interruption_note),
        prescription_energy_target,
        None if reviewing else schedule,
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


def _engine_order_amount(
    entered_amount_ml: float,
    order_form: str,
    hours_per_feed: float,
) -> float:
    """Convert an entered order into the quantity the calculation expects.

    Only one shape needs converting. A continuous order is entered as the rate
    the calculation wants, and an intermittent one by volume is entered as the
    volume per feed it wants. A rate run for a set time each feed is the single
    case where what is typed and what is calculated differ, so it multiplies
    out here and no calculation learns that the shape exists.
    """
    entered = max(float(entered_amount_ml), 0)
    if order_form == ORDER_FORM_RATE_PER_FEED:
        return entered * max(hours_per_feed, 0)
    return entered


def _render_ordered_flush_entry(
    scenario_id: str,
    schedule_type: str,
    feeds_per_day: int,
) -> tuple[int, dict[str, float], str, str]:
    """Record a flush regimen already running, as two lines of the written order.

    A peri-feed line counts against the feeds rather than the clock, so "150 mL
    before and after each feed" on three feeds is six flushes. A scheduled line
    covers everything written against the clock, such as an overnight flush.
    Returns the flush count, the schedule for `water_plan`, and the wording for
    the screen and the chart note.
    """
    intermittent = schedule_type != "Continuous / cyclic"
    described: list[str] = []
    lines: list[dict[str, float]] = []

    if intermittent:
        peri_a, peri_b = st.columns([1.4, 1])
        pattern = peri_a.selectbox(
            "Flushes with each feed",
            PERI_FEED_FLUSH_PATTERNS,
            key=scenario_key(scenario_id, "peri_feed_flush_pattern"),
        )
        peri_volume = number(
            peri_b.number_input(
                "Volume each (mL)",
                min_value=0.0,
                step=10.0,
                format="%.0f",
                key=scenario_key(scenario_id, "peri_feed_flush_volume_ml"),
                disabled=pattern == PERI_FEED_FLUSH_NONE,
            )
        )
        per_feed = PERI_FEED_FLUSHES_PER_FEED[pattern]
        peri_times = per_feed * max(int(feeds_per_day), 1)
        if peri_times and peri_volume > 0:
            lines.append({"volume_each_ml": peri_volume, "times_per_day": peri_times})
            described.append(f"{peri_volume:,.0f} mL {pattern.lower()}")

    scheduled_a, scheduled_b = st.columns([1.4, 1])
    # A separate key from the calculated mode's `hydration_flushes`, which has a
    # minimum of one. Sharing it would leave a zero in state that the calculated
    # widget rejects the moment the clinician switches back.
    scheduled_times = int(
        scheduled_a.number_input(
            "Other flushes (number/day)",
            min_value=0,
            max_value=24,
            step=1,
            help=(
                "Flushes written against the clock rather than against a feed, "
                "such as an overnight flush."
            ),
            key=scenario_key(scenario_id, "ordered_flush_times_per_day"),
        )
    )
    scheduled_volume = number(
        scheduled_b.number_input(
            "Volume each (mL) ",
            min_value=0.0,
            step=10.0,
            format="%.0f",
            key=scenario_key(scenario_id, "ordered_flush_volume_ml"),
            disabled=scheduled_times == 0,
        )
    )
    if scheduled_times and scheduled_volume > 0:
        lines.append(
            {
                "volume_each_ml": scheduled_volume,
                "times_per_day": scheduled_times,
            }
        )
        described.append(
            f"{scheduled_volume:,.0f} mL "
            + (
                "once daily"
                if scheduled_times == 1
                else f"{scheduled_times} times daily"
            )
        )

    schedule = ordered_flush_schedule(lines)
    wording = " and ".join(described)
    return int(schedule["hydration_flush_count"]), schedule, wording, wording


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
    (
        regimen_source,
        prescription_target_pct,
        prescription_interruption_note,
        total_energy_target,
        schedule,
    ) = _render_en_prescription(scenario_id, conditional_mode, energy_requirement)
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
    iv_orders = iv_fluid_orders()
    iv_fluids = iv_fluid_totals()
    comparison_energy_target = max(
        total_energy_target - propofol["kcal"] - iv_fluids["energy_kcal"], 0
    )
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
                    total_energy_target,
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
            if propofol["kcal"] > 0:
                st.markdown(
                    '<p class="formula-energy-calculation">'
                    f"<strong>{total_energy_target:,.0f} kcal EN energy target − "
                    f'{propofol["kcal"]:,.0f} kcal from propofol = '
                    f"{comparison_energy_target:,.0f} kcal</strong> used to calculate "
                    "suggested formula volumes and rates.</p>",
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
        suggested_final_delivery = practical_feed_delivery(
            formula, comparison_energy_target, hours, 100, schedule_type, feeds_per_day
        )
        # Each form names its own quantity, and the suggestion is rounded in
        # the same unit the clinician sets. A rate-based form rounds the rate,
        # so on an intermittent schedule the resulting volume per feed need not
        # land on a multiple of 5, which is right because the pump is set by
        # rate rather than by volume.
        if order_form == ORDER_FORM_RATE_PER_FEED:
            order_key = ordered_rate_key
            suggestion = practical_feed_delivery(
                formula,
                comparison_energy_target,
                max(hours, 1),
                100,
                "Continuous / cyclic",
                1,
            )["ordered_rate_ml_hr"]
            order_label = "Formula rate (mL/hour)"
            use_suggestion_label = "Use suggested rate"
            order_unit = "mL/hour"
        elif schedule_type == "Continuous / cyclic":
            order_key = ordered_rate_key
            suggestion = suggested_final_delivery["ordered_rate_ml_hr"]
            order_label = "Formula rate (mL/hour)"
            use_suggestion_label = "Use suggested rate"
            order_unit = "mL/hour"
        else:
            order_key = ordered_volume_key
            suggestion = suggested_final_delivery["ordered_volume_per_feed_ml"]
            order_label = "Formula volume per feed (mL)"
            use_suggestion_label = "Use suggested volume"
            order_unit = "mL/feed"
        pending_reset_key = scenario_key(scenario_id, "order_reset_requested")
        if st.session_state.get(pending_reset_key):
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
        if st.session_state.get(order_edited_key):
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
        engine_amount = _engine_order_amount(ordered_amount, order_form, hours_per_feed)
        final_planned_delivery = ordered_feed_delivery(
            formula, engine_amount, hours, 100, schedule_type, feeds_per_day
        )
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

    formula_only_gap = protein_target - final_planned_delivery["protein_g"]
    with st.container(border=True):
        render_box_heading(
            "Protein from formula"
            if propofol_method
            else "Protein from selected formula"
        )
        gap_label = (
            "Projected protein gap"
            if propofol_method and formula_only_gap >= 0
            else "Shortfall" if formula_only_gap >= 0 else "Exceeds goal by"
        )
        gap_class = " protein-shortfall" if formula_only_gap > 0 else ""
        st.markdown(
            '<p class="summary-line">'
            f"Goal: <strong>{protein_target:.0f} g/day</strong> &nbsp;|&nbsp; "
            f'{"Formula" if propofol_method else "Selected EN feed"}: '
            f'<strong>{final_planned_delivery["protein_g"]:.0f} g/day</strong> '
            f'&nbsp;|&nbsp; <span class="protein-gap{gap_class}">{gap_label}: '
            f"<strong>{abs(formula_only_gap):.0f} g/day</strong></span></p>",
            unsafe_allow_html=True,
        )

    modular_orders: list[dict[str, float]] = []
    modular_note_parts: list[str] = []
    # Products whose label does not publish a figure for each electrolyte, so
    # the intake table can say so instead of implying a measured zero.
    modular_undisclosed: dict[str, list[str]] = {
        "sodium": [],
        "potassium": [],
        "calcium": [],
        "phosphorus": [],
        "magnesium": [],
    }
    modular_protein_sources: list[str] = []
    modular_fat_sources: list[str] = []
    chart_modulars: list[dict[str, object]] = []
    chosen_modulars: list[str] = []
    with st.container(border=True):
        render_box_heading("Add modulars")
        if saved_modulars.empty:
            st.caption("Missing a modular? Add it to My Modulars on the Formulary tab.")
        else:
            modular_ids_by_name = {
                str(product["name"]): str(product["id"])
                for _, product in saved_modulars.iterrows()
            }
            chosen_modulars = st.multiselect(
                "Modulars",
                saved_modulars["name"].tolist(),
                max_selections=6,
                key=scenario_key(scenario_id, "chosen_modulars"),
                on_change=reset_new_modular_orders,
                args=(scenario_id, modular_ids_by_name),
            )
            st.caption("Missing a modular? Add it to My Modulars on the Formulary tab.")
            for modular_name in chosen_modulars:
                product = (
                    saved_modulars.loc[saved_modulars["name"] == modular_name]
                    .iloc[0]
                    .to_dict()
                )
                st.markdown(f"**{modular_name}** — {product['basis_description']}")
                a, b, c = st.columns(3)
                product_id = str(product["id"])
                units_key = scenario_key(scenario_id, f"modular_units_{product_id}")
                doses_key = scenario_key(scenario_id, f"modular_doses_{product_id}")
                unit_label = (
                    "Packets each time"
                    if modular_unit(product) == "packet"
                    else f"{product['dose_unit']} each time"
                )
                packet_order = modular_unit(product) == "packet"
                units = a.number_input(
                    unit_label,
                    min_value=0.0,
                    step=1.0 if packet_order else 0.5,
                    format="%.0f" if packet_order else "%.1f",
                    key=units_key,
                )
                doses = b.number_input(
                    "Times per day",
                    min_value=0.0,
                    step=1.0,
                    format="%.0f",
                    key=doses_key,
                )
                preparation = 0.0
                if str(product.get("preparation_water_rule", "none")) != "none":
                    preparation = c.number_input(
                        "Preparation water (mL each time)",
                        min_value=0.0,
                        step=5.0,
                        format="%.0f",
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
                    for nutrient in (
                        "sodium",
                        "potassium",
                        "calcium",
                        "phosphorus",
                        "magnesium",
                    ):
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
                    chart_modulars.append(
                        {
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
                        }
                    )
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
                name
                for name in st.session_state[chosen_key]
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
                    product = (
                        saved_ons.loc[saved_ons["name"] == ons_name].iloc[0].to_dict()
                    )
                    serving_based = (
                        str(product.get("calculation_basis", "container_ml"))
                        .strip()
                        .casefold()
                        == "serving"
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
                    st.markdown(f"**{escape(ons_name)}** — {basis_description}")
                    a, b = st.columns(2)
                    product_id = str(product["id"])
                    quantity_each_time = a.number_input(
                        quantity_label,
                        min_value=0.0,
                        step=0.5,
                        format="%.1f",
                        key=scenario_key(scenario_id, f"{quantity_prefix}{product_id}"),
                    )
                    times_per_day = b.number_input(
                        "Times per day",
                        min_value=0.0,
                        step=1.0,
                        format="%.0f",
                        key=scenario_key(scenario_id, f"ons_times_{product_id}"),
                    )
                    order_is_complete = (
                        number(quantity_each_time) > 0 and number(times_per_day) > 0
                    )
                    order = ons_delivery(
                        product,
                        number(quantity_each_time) if order_is_complete else 0,
                        number(times_per_day) if order_is_complete else 0,
                    )
                    ons_orders.append(order)
                    if order_is_complete:
                        chart_ons.append(
                            {
                                "name": ons_name,
                                "product_name": product["product_name"],
                                "flavour": product["flavour"],
                                "package_unit": product["package_unit"],
                                "quantity_each_time": number(quantity_each_time),
                                "quantity_unit": (
                                    product["serving_unit"]
                                    if serving_based
                                    else product["package_unit"]
                                ),
                                "calculation_basis": (
                                    "serving" if serving_based else "container_ml"
                                ),
                                "containers_each_time": (
                                    number(quantity_each_time)
                                    if not serving_based
                                    else 0
                                ),
                                "servings_each_time": (
                                    number(quantity_each_time) if serving_based else 0
                                ),
                                "times_per_day": number(times_per_day),
                                **order,
                            }
                        )
                    else:
                        st.caption(
                            f"Enter both the number of {quantity_caption} and frequency "
                            "to include this ONS."
                        )
    ons_totals = total_ons_delivery(ons_orders)

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

    with st.container(border=True):
        render_box_heading("Water goal and hydration flushes")
        free_water_before_flushes = (
            final_planned_delivery["free_water_ml"]
            + modular_totals["free_water_ml"]
            + modular_totals["preparation_water_ml"]
        )
        chart_water_only = (
            st.session_state.get("assessment_water_mode") == WATER_MODE_CHART_ONLY
        )
        # A water goal can exist without a flush schedule following from
        # it: with a line running the requirement is charted, not filled
        # enterally. Flushes need both a goal and the intention to give them.
        plan_hydration_flushes = water_target is not None and not chart_water_only
        if not plan_hydration_flushes:
            goal_text = (
                "not set"
                if water_target is None
                else f"{water_target:,.0f} mL/day, charted only"
            )
            st.markdown(
                f'<p class="summary-line">Water goal: <strong>{goal_text}</strong> '
                "&nbsp;|&nbsp; Water from formula and modulars: "
                f"<strong>{free_water_before_flushes:.0f} mL/day</strong></p>",
                unsafe_allow_html=True,
            )
            st.caption(
                "Fluid needs are charted; no hydration flushes are calculated. "
                "Change the water setting in Assessment if flushes are being "
                "prescribed."
                if chart_water_only
                else "No hydration flushes are calculated or charted without a water "
                "goal. Enter one in Assessment or Adjust goals if enteral water "
                "is being managed for this patient."
            )
        else:
            remaining_before_flushes = max(water_target - free_water_before_flushes, 0)
            st.markdown(
                '<p class="summary-line">Water goal: '
                f"<strong>{water_target:.0f} mL/day</strong> &nbsp;|&nbsp; "
                "Water from formula and modulars: "
                f"<strong>{free_water_before_flushes:.0f} mL/day</strong> &nbsp;|&nbsp; "
                "Remaining before flushes: "
                f"<strong>{remaining_before_flushes:.0f} mL/day</strong></p>",
                unsafe_allow_html=True,
            )
        if chart_ons:
            st.caption(
                "Free water from ONS is included in daily totals but excluded "
                "from water-flush calculations."
            )
        water_a, water_b = st.columns(2)
        medication = water_a.number_input(
            "Medication flushes (mL/day)",
            min_value=0.0,
            step=10.0,
            format="%.0f",
            key=scenario_key(scenario_id, "medication_flushes"),
        )
        patency = water_b.number_input(
            "Patency flushes (mL/day)",
            min_value=0.0,
            step=10.0,
            format="%.0f",
            help="Enter a separate patency-flush volume only when it is part of the plan.",
            key=scenario_key(scenario_id, "patency_flushes"),
        )
        # Entering flushes as ordered needs neither a water goal nor the
        # flush-prescribing water mode, because a running order is a fact rather
        # than something derived from a target. That is why this is a separate
        # question from `plan_hydration_flushes`, which governs only the
        # goal-driven calculation below.
        hydration_entry_mode = st.radio(
            "Hydration flushes",
            HYDRATION_ENTRY_MODES,
            horizontal=True,
            key=scenario_key(scenario_id, "hydration_entry_mode"),
        )
        enter_flushes_as_ordered = hydration_entry_mode == HYDRATION_ENTRY_ORDERED
        ordered_flushes = None
        if enter_flushes_as_ordered:
            (
                flushes,
                ordered_flushes,
                hydration_schedule_text,
                hydration_chart_schedule_text,
            ) = _render_ordered_flush_entry(scenario_id, schedule_type, feeds_per_day)
        # The hydration schedule exists only to distribute a goal-driven volume,
        # so it is hidden whenever flushes are not being prescribed. Medication
        # and patency flushes above are ordered independently and still apply.
        elif not plan_hydration_flushes:
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
                schedule_value = int(
                    schedule_b.selectbox(
                        "Flush interval (hours)",
                        options=[1, 2, 3, 4, 6, 8, 12, 24],
                        format_func=lambda value: f"{value} hours",
                        key=scenario_key(scenario_id, "hydration_interval_hours"),
                    )
                )
                flushes = hydration_flushes_per_day(schedule_format, schedule_value)
                hydration_schedule_text = f"q{schedule_value}h"
                hydration_chart_schedule_text = f"q{schedule_value}h"
            else:
                schedule_value = int(
                    schedule_b.number_input(
                        "Hydration flushes (number/day)",
                        min_value=1,
                        max_value=24,
                        key=scenario_key(scenario_id, "hydration_flushes"),
                    )
                )
                flushes = hydration_flushes_per_day(schedule_format, schedule_value)
                hydration_schedule_text = f"{flushes} times daily"
                hydration_chart_schedule_text = f"{flushes} times daily"
        hydration = water_plan(
            water_target if plan_hydration_flushes else None,
            final_planned_delivery["free_water_ml"],
            modular_totals["free_water_ml"],
            modular_totals["preparation_water_ml"],
            medication,
            patency,
            flushes,
            ordered_flushes,
        )
        modular_preparation_water = modular_totals["preparation_water_ml"]
        other_water_flushes = max(
            hydration["water_flushes_total_ml"] - modular_preparation_water, 0
        )
        if enter_flushes_as_ordered:
            ordered_total = hydration["hydration_flush_total_ml"]
            st.markdown(
                '<p class="summary-line">Ordered hydration flushes: '
                f'<strong>{hydration_schedule_text or "none entered"}</strong>'
                + (
                    f" &nbsp;|&nbsp; <strong>{ordered_total:,.0f} mL/day</strong>."
                    if ordered_total
                    else "."
                )
                + "</p>",
                unsafe_allow_html=True,
            )
        elif plan_hydration_flushes:
            st.markdown(
                '<p class="summary-line">Calculated hydration flush schedule: '
                f'<strong>{hydration["hydration_flush_each_ml"]:.0f} mL '
                f"{hydration_schedule_text}.</strong></p>",
                unsafe_allow_html=True,
            )

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
            + iv_fluids["energy_kcal"]
            + ons_totals["energy_kcal"]
        )
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
        displayed_total_water = (
            displayed_delivery["free_water_ml"]
            + modular_totals["free_water_ml"]
            + ons_totals["free_water_ml"]
            + modular_preparation_water
            + other_water_flushes
        )
        water_difference = (
            None if water_target is None else displayed_total_water - water_target
        )
        protein_difference = final_protein - protein_target
        energy_difference = final_energy - total_energy_target
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

        def signed_difference(value: float) -> str:
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

    def _intake_rows(delivery):
        """One row per contributing source, for a given feed delivery.

        Built twice: once from what is displayed, which follows the
        partial-delivery view and feeds the table, and once from the full
        planned order, which is what the chart note reports. Sharing the
        construction is what stops the two drifting apart.
        """
        rows = [
            {
                "Source": formula["name"],
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
                "Water (mL)": modular_totals["free_water_ml"]
                + modular_preparation_water,
                "Na (mmol)": mmol_if_disclosed(modular_totals, "sodium"),
                "K (mmol)": mmol_if_disclosed(modular_totals, "potassium"),
                "Ca (mmol)": mmol_if_disclosed(modular_totals, "calcium"),
                "P (mmol)": mmol_if_disclosed(modular_totals, "phosphorus"),
                "Mg (mmol)": mmol_if_disclosed(modular_totals, "magnesium"),
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
            },
        ]
        if chart_ons:
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
                    "Na (mmol)": 0,
                    "K (mmol)": 0,
                    "Ca (mmol)": 0,
                    "P (mmol)": 0,
                    "Mg (mmol)": 0,
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
                },
            )
        if not chart_modulars:
            rows = [row for row in rows if row["Source"] != "Modulars"]
        return rows

    source_rows = _intake_rows(displayed_delivery)
    planned_rows = _intake_rows(final_planned_delivery)
    source_frame = pd.DataFrame(source_rows)
    total: dict[str, object] = {"Source": "Total", **combined_intake(source_rows)}
    modular_note = "; ".join(modular_note_parts) or "No modulars ordered"
    # The note reports the full planned order, so it sums the planned
    # rows while the table sums the displayed ones. Same builder, same
    # adder, so the two cannot drift apart.
    chart_total = combined_intake(planned_rows)
    return {
        "label": label,
        "propofol_rate": propofol_rate,
        "propofol_hours": propofol_hours,
        "propofol": propofol,
        "iv_fluids": iv_fluids,
        "iv_orders": iv_orders,
        "propofol_method": propofol_method,
        "propofol_conditions": conditions,
        "conditional_orders": conditional_orders,
        "feeding_hours": hours,
        "estimated_energy_requirement": energy_requirement,
        "prescription_target_pct": prescription_target_pct,
        "prescription_energy_target": total_energy_target,
        "prescription_interruption_note": prescription_interruption_note,
        "formula": formula,
        "formula_energy_target": final_formula_energy_target,
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
        "view_percent": view_percent,
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
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str], float, float, float]
    | None
):
    """Render shared Assessment goals and feed candidates for a planning workflow."""
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
    if total_energy_target is None or protein_target is None:
        st.caption("Enter energy and protein goals in Assessment or Adjust goals.")
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
        float(total_energy_target),
        float(protein_target),
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
