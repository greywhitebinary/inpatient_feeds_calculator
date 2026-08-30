"""Lower- and higher-propofol EN scenario workflow."""

from __future__ import annotations

from copy import deepcopy

import pandas as pd
import streamlit as st

from calculations import propofol_intake
from case_record_ui import render_save_record
from constants import DAILY_INTAKE_DECIMALS, PROPOFOL_COMPARISON_ROW_DECIMALS, PROPOFOL_SCENARIOS
from plan_ui import render_en_scenario, render_en_workflow_setup
from session_state import scenario_key, seed_scenario_state
from ui_common import number, render_box_heading, render_report_table

def render_propofol_exposure(
    scenario_id: str,
    *,
    allow_blank_rate: bool = False,
) -> tuple[float | None, float]:
    """Render scenario-specific propofol inputs beside their calculated contributions."""
    with st.container(border=True):
        render_box_heading("Propofol rate and duration")
        exposure_columns = st.columns([1, 1, 1.35], vertical_alignment="bottom")
        rate_arguments: dict[str, object] = {
            "label": "Propofol rate (mL/hour)",
            "min_value": 0.0,
            "step": 1.0,
            "format": "%.1f",
            "key": scenario_key(scenario_id, "propofol_rate"),
        }
        if allow_blank_rate:
            rate_arguments.update({"value": None, "placeholder": "Optional"})
        rate = exposure_columns[0].number_input(**rate_arguments)
        hours = exposure_columns[1].number_input(
            "Hours at this rate",
            min_value=0.0,
            max_value=24.0,
            step=1.0,
            format="%.1f",
            key=scenario_key(scenario_id, "propofol_hours"),
            disabled=rate is None,
        )
        contribution = propofol_intake(number(rate), number(hours)) if rate is not None else None
        energy_display = f"{contribution['kcal']:.0f} kcal/day" if contribution else "—"
        fat_amount = (
            f"{contribution['fat_g']:.1f}".rstrip("0").rstrip(".")
            if contribution else None
        )
        fat_display = f"{fat_amount} g/day" if fat_amount is not None else "—"
        exposure_columns[2].markdown(
            '<div class="propofol-readouts">'
            '<p><span>Energy from propofol:</span> '
            f'<strong>{energy_display}</strong></p>'
            '<p><span>Fat from propofol:</span> '
            f'<strong>{fat_display}</strong></p>'
            '</div>',
            unsafe_allow_html=True,
        )
    return rate, number(hours)


def show_icu_propofol() -> None:
    if "icu_feed_candidates" not in st.session_state and st.session_state.get("feed_candidates"):
        st.session_state.icu_feed_candidates = deepcopy(st.session_state.feed_candidates)
    setup = render_en_workflow_setup("icu", "icu_feed_candidates")
    if setup is None:
        return
    candidate_frame, saved_modulars, candidates, total_energy_target, protein_target, water_target = setup
    lower_migration = "primary" if any(
        key.startswith("scenario_primary_") for key in st.session_state
    ) else None
    higher_migration = "alternate" if any(
        key.startswith("scenario_alternate_") for key in st.session_state
    ) else None
    seed_scenario_state("lower", candidates, saved_modulars, lower_migration)
    seed_scenario_state("higher", candidates, saved_modulars, higher_migration)
    st.session_state.pop("assessment_propofol_rate", None)

    results: dict[str, dict[str, object]] = {}
    with st.container(key="propofol_scenario_tabs"):
        scenario_tabs = st.tabs([label for _, label in PROPOFOL_SCENARIOS])
    with scenario_tabs[0]:
        lower_rate, lower_hours = render_propofol_exposure("lower")
        results["lower"] = render_en_scenario(
            "lower", "Lower/no propofol", candidate_frame, saved_modulars,
            total_energy_target, protein_target, water_target,
            number(lower_rate), number(lower_hours),
        )
    with scenario_tabs[1]:
        higher_rate, higher_hours = render_propofol_exposure(
            "higher", allow_blank_rate=True
        )
        copy_lower = st.button(
            "Copy lower-propofol EN plan",
            type="secondary",
            help="Copies the EN regimen and water plan. Propofol settings are unchanged.",
        )
        if copy_lower:
            for key, value in list(st.session_state.items()):
                if key.startswith("scenario_lower_") and key not in {
                    scenario_key("lower", "propofol_rate"),
                    scenario_key("lower", "propofol_hours"),
                } and not key.endswith(("_use_suggested_order", "_order_reset_requested")):
                    higher_key = key.replace("scenario_lower_", "scenario_higher_", 1)
                    st.session_state[higher_key] = deepcopy(value)
            st.session_state.icu_planned_daily_intake_scenario = "higher"
            st.rerun()
        if higher_rate is None:
            st.caption("Enter a higher propofol rate to calculate this plan.")
        else:
            results["higher"] = render_en_scenario(
                "higher", "Higher propofol", candidate_frame, saved_modulars,
                total_energy_target, protein_target, water_target,
                number(higher_rate), number(higher_hours),
            )

    if "higher" in results:
        comparison_rows = []
        for row_label, getter in (
            ("Propofol rate (mL/hour)", lambda item: item["propofol_rate"]),
            ("Hours at this rate", lambda item: item["propofol_hours"]),
            ("Propofol volume (mL/day)", lambda item: item["propofol"]["volume_ml"]),
            ("Propofol energy (kcal/day)", lambda item: item["propofol"]["kcal"]),
            ("Formula energy allocation (kcal/day)", lambda item: item["formula_energy_target"]),
            ("Formula", lambda item: item["formula"]["name"]),
            ("EN order", lambda item: item["schedule_description"]),
            ("Modulars", lambda item: item["modulars"]),
            ("Total energy (kcal/day)", lambda item: item["planned_total"]["Energy (kcal)"]),
            ("Total protein (g/day)", lambda item: item["planned_total"]["Protein (g)"]),
            ("Total fat (g/day)", lambda item: item["planned_total"]["Fat (g)"]),
        ):
            comparison_rows.append({
                "Plan element": row_label,
                "Lower/no propofol": getter(results["lower"]),
                "Higher propofol": getter(results["higher"]),
            })
        with st.container(border=True):
            render_box_heading("Plan comparison")
            render_report_table(
                pd.DataFrame(comparison_rows),
                row_decimals=PROPOFOL_COMPARISON_ROW_DECIMALS,
            )

    valid_scenarios = list(results)
    if len(valid_scenarios) > 1:
        if st.session_state.get("icu_planned_daily_intake_scenario") not in valid_scenarios:
            legacy_selection = st.session_state.get("planned_daily_intake_scenario")
            st.session_state.icu_planned_daily_intake_scenario = (
                legacy_selection if legacy_selection in valid_scenarios else "lower"
            )
    else:
        st.session_state.icu_planned_daily_intake_scenario = "lower"
    initial_selected_scenario = st.session_state.icu_planned_daily_intake_scenario
    with st.container(key="fullbleed_icu_daily_intake", border=True):
        render_box_heading(str(results[initial_selected_scenario]["intake_heading"]))
        if len(valid_scenarios) > 1:
            selector_label, selector_control = st.columns(
                [1.15, 2.2], vertical_alignment="center"
            )
            selector_label.markdown(
                '<p class="inline-field-label">Show planned daily intake for</p>',
                unsafe_allow_html=True,
            )
            selected_scenario = selector_control.radio(
                "Show planned daily intake for", valid_scenarios, horizontal=True,
                key="icu_planned_daily_intake_scenario",
                format_func=lambda scenario_id: dict(PROPOFOL_SCENARIOS)[scenario_id],
                label_visibility="collapsed",
            )
        else:
            selected_scenario = "lower"
        selected_result = results[selected_scenario]
        source_frame = selected_result["source_frame"]
        total = selected_result["total"]
        render_report_table(
            pd.concat([source_frame, pd.DataFrame([total])], ignore_index=True),
            decimals=DAILY_INTAKE_DECIMALS,
            wide=True,
        )

    with st.container(border=True):
        render_box_heading("Chart note")
        st.caption("Copy and paste into your chart. No patient-identifying fields are included.")
        if "higher" in results:
            note = f"{results['lower']['note']}\n\n{results['higher']['note']}"
        else:
            note = str(results["lower"]["note"])
        st.code(note, language=None)
    render_save_record("icu_propofol")
