"""Shared EN planning workflow for projected Propofol exposure."""

from __future__ import annotations

from copy import deepcopy

import pandas as pd
import streamlit as st
from calculations import total_propofol_intake
from case_record_ui import render_save_record
from chart_note import build_chart_note_html, render_chart_note_editor
from constants import DAILY_INTAKE_DECIMALS
from plan_ui import render_en_scenario, render_en_workflow_setup
from session_state import (
    scenario_key,
    seed_propofol_widget,
    seed_scenario_state,
    sync_propofol_widget,
)
from ui_common import number, render_box_heading, render_report_table

PROPOFOL_METHODS = ("Single Propofol rate", "Changing Propofol rates")


def _seed_propofol_plan(candidates: list[str], saved_modulars: pd.DataFrame) -> None:
    """Create one shared plan while retaining values from older two-plan records."""
    legacy_plan = st.session_state.get("icu_planned_daily_intake_scenario", "higher")
    if legacy_plan not in {"lower", "higher"}:
        legacy_plan = "higher"
    seed_scenario_state("propofol", candidates, saved_modulars, legacy_plan)

    propofol_rate_key = scenario_key("propofol", "propofol_rate")
    if st.session_state.get(propofol_rate_key) is None:
        st.session_state[propofol_rate_key] = 0.0

    method_key = scenario_key("propofol", "propofol_method")
    st.session_state.setdefault(method_key, PROPOFOL_METHODS[0])
    method_migrations = {
        "Single daily EN rate": "Single Propofol rate",
        "Conditional EN rates": "Changing Propofol rates",
    }
    if st.session_state.get(method_key) in method_migrations:
        st.session_state[method_key] = method_migrations[
            str(st.session_state[method_key])
        ]
    st.session_state.setdefault(
        scenario_key("propofol", "lower_propofol_rate"),
        number(st.session_state.get(scenario_key("lower", "propofol_rate"))),
    )
    st.session_state.setdefault(
        scenario_key("propofol", "higher_propofol_rate"),
        number(st.session_state.get(scenario_key("higher", "propofol_rate"))),
    )
    st.session_state.setdefault(
        scenario_key("propofol", "higher_propofol_hours"),
        number(st.session_state.get(scenario_key("higher", "propofol_hours"), 6)),
    )


def _render_exposure_total(conditions: list[dict[str, object]]) -> dict[str, float]:
    total = total_propofol_intake(conditions)
    st.markdown(
        '<p class="propofol-exposure-summary"><strong>Projected daily Propofol: '
        f'{total["volume_ml"]:.0f} mL/day</strong>, providing '
        f'{total["kcal"]:.0f} kcal/day and {total["fat_g"]:.1f} g fat/day.</p>',
        unsafe_allow_html=True,
    )
    st.caption("Propofol provides 1.1 kcal and 0.1 g fat per mL.")
    return total


def _render_single_daily_exposure() -> tuple[list[dict[str, object]], float, float]:
    with st.container(border=True):
        render_box_heading("Projected Propofol exposure")
        columns = st.columns(2, vertical_alignment="bottom")
        rate_state_key = scenario_key("propofol", "propofol_rate")
        rate_widget_key = seed_propofol_widget(rate_state_key)
        rate = columns[0].number_input(
            "Propofol rate (mL/hour)", min_value=0.0, step=1.0, format="%.1f",
            key=rate_widget_key,
            on_change=sync_propofol_widget,
            args=(rate_widget_key, rate_state_key),
        )
        hours_state_key = scenario_key("propofol", "propofol_hours")
        hours_widget_key = seed_propofol_widget(hours_state_key)
        hours = columns[1].number_input(
            "Expected hours", min_value=0.0, max_value=24.0,
            step=1.0, format="%.1f",
            key=hours_widget_key,
            on_change=sync_propofol_widget,
            args=(hours_widget_key, hours_state_key),
        )
        conditions: list[dict[str, object]] = [{
            "id": "projected",
            "label": "Projected exposure",
            "rate_ml_hr": number(rate),
            "hours": number(hours),
        }]
        _render_exposure_total(conditions)
    return conditions, number(rate), number(hours)


def _render_conditional_exposure() -> list[dict[str, object]]:
    with st.container(border=True):
        render_box_heading("Propofol conditions")
        columns = st.columns(2, vertical_alignment="top")
        lower_state_key = scenario_key("propofol", "lower_propofol_rate")
        lower_widget_key = seed_propofol_widget(lower_state_key)
        higher_state_key = scenario_key("propofol", "higher_propofol_rate")
        higher_widget_key = seed_propofol_widget(higher_state_key)
        higher_hours_state_key = scenario_key("propofol", "higher_propofol_hours")
        higher_hours_widget_key = seed_propofol_widget(higher_hours_state_key)
        lower_hours = 24 - number(st.session_state.get(higher_hours_state_key))
        with columns[0].container(border=True):
            st.markdown("**Lower/no Propofol**")
            lower_rate = st.number_input(
                "Propofol rate (mL/hour)", min_value=0.0, step=1.0,
                format="%.1f", key=lower_widget_key,
                on_change=sync_propofol_widget,
                args=(lower_widget_key, lower_state_key),
            )
            st.markdown(
                '<p class="condition-duration">Projected duration: '
                f'<strong>{lower_hours:g} hours/day</strong></p>',
                unsafe_allow_html=True,
            )
        with columns[1].container(border=True):
            st.markdown("**Higher Propofol**")
            higher_rate = st.number_input(
                "Propofol rate (mL/hour)", min_value=0.0, step=1.0,
                format="%.1f", key=higher_widget_key,
                on_change=sync_propofol_widget,
                args=(higher_widget_key, higher_state_key),
            )
            higher_hours = st.number_input(
                "Expected duration (hours/day)", min_value=0.0, max_value=24.0,
                step=1.0, format="%.1f", key=higher_hours_widget_key,
                on_change=sync_propofol_widget,
                args=(higher_hours_widget_key, higher_hours_state_key),
            )
        lower_hours = 24 - number(higher_hours)
        conditions: list[dict[str, object]] = [
            {
                "id": "lower",
                "label": "Lower/no Propofol",
                "rate_ml_hr": number(lower_rate),
                "hours": lower_hours,
            },
            {
                "id": "higher",
                "label": "Higher Propofol",
                "rate_ml_hr": number(higher_rate),
                "hours": number(higher_hours),
            },
        ]
        _render_exposure_total(conditions)
    return conditions


def show_icu_propofol() -> None:
    if "icu_feed_candidates" not in st.session_state and st.session_state.get("feed_candidates"):
        st.session_state.icu_feed_candidates = deepcopy(st.session_state.feed_candidates)
    setup = render_en_workflow_setup("icu", "icu_feed_candidates")
    if setup is None:
        return
    (
        candidate_frame, saved_modulars, _saved_ons, candidates, estimated_energy_requirement,
        protein_target, water_target,
    ) = setup
    _seed_propofol_plan(candidates, saved_modulars)
    st.session_state.pop("assessment_propofol_rate", None)

    with st.container(border=True):
        render_box_heading("Propofol planning")
        method = st.radio(
            "Method", PROPOFOL_METHODS, horizontal=True,
            key=scenario_key("propofol", "propofol_method"),
        )
        with st.expander("How this calculation works"):
            st.markdown(
                '<div class="calculation-help-copy">'
                '<p><strong>Single Propofol rate</strong><br>'
                'Enter the expected Propofol rate and duration. The calculator subtracts '
                'projected Propofol energy from the EN energy target before calculating '
                'the formula rate.</p>'
                '<p><strong>Changing Propofol rates</strong><br>'
                'Enter the lower and higher Propofol rates and the expected hours at the '
                'higher rate. Remaining hours use the lower rate. The calculator provides '
                'two suggested EN rates. It uses the expected durations to calculate '
                'planned daily formula volume and protein provision. If feeding time is '
                'less than 24 hours/day, it is distributed proportionally according to '
                'the expected hours at each Propofol rate.</p>'
                '</div>',
                unsafe_allow_html=True,
            )

    if method == "Changing Propofol rates":
        conditions = _render_conditional_exposure()
        displayed_rate = 0.0
        displayed_hours = 24.0
    else:
        conditions, displayed_rate, displayed_hours = _render_single_daily_exposure()

    result = render_en_scenario(
        "propofol", "Propofol EN plan", candidate_frame, saved_modulars, None,
        estimated_energy_requirement, protein_target, water_target,
        displayed_rate, displayed_hours,
        propofol_conditions=conditions,
        propofol_method=method,
        estimated_energy_requirement=estimated_energy_requirement,
    )

    with st.container(key="fullbleed_icu_daily_intake", border=True):
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

    with st.container(border=True):
        render_box_heading("Chart note")
        st.caption(
            "Edit as needed, then copy to the EMR. Downloading the record does not "
            "save the chart-note text."
        )
        render_chart_note_editor(
            build_chart_note_html(st.session_state, [result]),
            editor_id="propofol",
            case_token=str(st.session_state["_chart_note_case_token"]),
            height=860,
        )
    render_save_record("icu_propofol")
