"""Water and flush controls for an entered feed; preserves existing policy."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st
from calculations import (
    hydration_flushes_per_day,
    ordered_flush_schedule,
    water_plan,
)
from constants import (
    HYDRATION_ENTRY_MODES,
    HYDRATION_ENTRY_ORDERED,
    PERI_FEED_FLUSH_NONE,
    PERI_FEED_FLUSH_PATTERNS,
    PERI_FEED_FLUSHES_PER_FEED,
    WATER_MODE_CHART_ONLY,
)
from session_state import (
    scenario_key,
)
from ui_common import (
    number,
    render_box_heading,
)


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


@dataclass(frozen=True)
class HydrationSelection:
    totals: dict[str, float]
    other_water_flushes: float
    chart_water_only: bool
    chart_schedule_text: str
    entered_as_ordered: bool
    medication: float | None
    patency: float | None


def render_hydration_selection(
    scenario_id: str,
    *,
    water_target: float | None,
    final_planned_delivery: dict[str, float],
    modular_totals: dict[str, object],
    chart_ons: list[dict[str, object]],
    schedule_type: str,
    feeds_per_day: int,
) -> HydrationSelection:
    """Read water controls and calculate the full-order flush plan."""
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

    return HydrationSelection(
        totals=hydration,
        other_water_flushes=other_water_flushes,
        chart_water_only=chart_water_only,
        chart_schedule_text=hydration_chart_schedule_text,
        entered_as_ordered=enter_flushes_as_ordered,
        medication=medication,
        patency=patency,
    )
