"""Session-state initialization, migration, and widget synchronization."""

from __future__ import annotations

from uuid import uuid4
from zipfile import BadZipFile

import pandas as pd
import streamlit as st

from calculations import height_to_cm
from case_io import CASE_DYNAMIC_PREFIXES, CASE_STATE_KEYS, import_case_record_workbook
from constants import KG_PER_LB, MEASUREMENT_ENTRY_KEYS, PLAN_GOALS
from data import load_master_formulas, load_master_modulars, load_master_ons
from ui_common import number

@st.cache_data
def master_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return load_master_formulas(), load_master_modulars(), load_master_ons()


def initialise_state() -> None:
    formulas, modulars, ons = master_data()
    if "my_formulas" not in st.session_state:
        st.session_state.my_formulas = formulas.iloc[0:0].copy()
    if "my_modulars" not in st.session_state:
        st.session_state.my_modulars = modulars.iloc[0:0].copy()
    if "my_ons" not in st.session_state:
        st.session_state.my_ons = ons.iloc[0:0].copy()
    st.session_state.setdefault("case_record_label", "My EN record")
    st.session_state.setdefault("_chart_note_case_token", uuid4().hex)
    for goal in PLAN_GOALS:
        assessment_key = str(goal["assessment_key"])
        if st.session_state.get(assessment_key) is None:
            for legacy_key in (str(goal["en_key"]), str(goal["icu_key"])):
                if st.session_state.get(legacy_key) is not None:
                    st.session_state[assessment_key] = st.session_state[legacy_key]
                    break


def sync_height_from_cm_entry() -> None:
    """Update canonical cm and the inactive imperial fields from the cm widget."""
    height_cm = st.session_state.get("assessment_height_cm_entry")
    st.session_state.assessment_height_cm = height_cm
    if height_cm is None:
        st.session_state.assessment_height_feet = None
        st.session_state.assessment_height_inches = None
        return
    total_inches = number(height_cm) / 2.54
    feet = int(total_inches // 12)
    inches = round(total_inches - feet * 12, 1)
    if inches >= 12:
        feet += 1
        inches = 0.0
    st.session_state.assessment_height_feet = feet
    st.session_state.assessment_height_inches = inches


def sync_height_from_feet_inches() -> None:
    """Update the canonical cm value when either imperial height field changes."""
    feet = st.session_state.get("assessment_height_feet")
    inches = st.session_state.get("assessment_height_inches")
    st.session_state.assessment_height_cm = (
        height_to_cm("ft/in", feet=int(feet), inches=number(inches))
        if feet is not None and inches is not None else None
    )


def sync_height_unit_fields() -> None:
    """Prepare the alternate height widgets before they are displayed."""
    if st.session_state.get("assessment_height_unit") == "ft/in":
        height_cm = st.session_state.get("assessment_height_cm")
        if height_cm is None:
            st.session_state.assessment_height_feet = None
            st.session_state.assessment_height_inches = None
        else:
            total_inches = number(height_cm) / 2.54
            feet = int(total_inches // 12)
            inches = round(total_inches - feet * 12, 1)
            if inches >= 12:
                feet += 1
                inches = 0.0
            st.session_state.assessment_height_feet = feet
            st.session_state.assessment_height_inches = inches
    else:
        st.session_state.assessment_height_cm_entry = st.session_state.get(
            "assessment_height_cm"
        )


def sync_weight_from_kg_entry(entry_key: str, kg_key: str, lb_key: str) -> None:
    """Update canonical kg and the inactive pound field from a kg widget."""
    kilograms = st.session_state.get(entry_key)
    st.session_state[kg_key] = kilograms
    st.session_state[lb_key] = (
        number(kilograms) / KG_PER_LB if kilograms is not None else None
    )


def sync_weight_from_lb(lb_key: str, kg_key: str) -> None:
    """Update one canonical kg field when its pound entry changes."""
    pounds = st.session_state.get(lb_key)
    st.session_state[kg_key] = (
        number(pounds) * KG_PER_LB if pounds is not None else None
    )


def sync_weight_unit_fields() -> None:
    """Prepare pound widgets from the canonical kg values when units change."""
    if st.session_state.get("assessment_weight_unit") == "lb":
        for kg_key, lb_key in (
            ("assessment_current_weight", "assessment_current_weight_lb"),
            ("assessment_usual_weight", "assessment_usual_weight_lb"),
        ):
            kilograms = st.session_state.get(kg_key)
            st.session_state[lb_key] = (
                number(kilograms) / KG_PER_LB if kilograms is not None else None
            )
    else:
        st.session_state.assessment_current_weight_kg_entry = st.session_state.get(
            "assessment_current_weight"
        )
        st.session_state.assessment_usual_weight_kg_entry = st.session_state.get(
            "assessment_usual_weight"
        )


def clear_case_record_state() -> None:
    """Remove the current case inputs before applying a complete saved record."""
    for key in list(st.session_state):
        if (
            key in CASE_STATE_KEYS
            or key in MEASUREMENT_ENTRY_KEYS
            or key.startswith(CASE_DYNAMIC_PREFIXES)
            or key.startswith("_propofol_widget_")
        ):
            del st.session_state[key]


def open_uploaded_case_record(uploaded_file) -> None:
    """Apply a saved record before its widgets are instantiated on the rerun."""
    try:
        state, formulas, modulars, ons = import_case_record_workbook(uploaded_file)
    except (BadZipFile, ValueError, OSError) as error:
        st.session_state["_case_record_notice"] = ("error", str(error))
        return

    clear_case_record_state()
    st.session_state.update(state)
    st.session_state.my_formulas = formulas
    st.session_state.my_modulars = modulars
    st.session_state.my_ons = ons
    st.session_state["_chart_note_case_token"] = uuid4().hex
    st.session_state["_case_record_notice"] = (
        "success", "The saved record is now open."
    )


def load_example_record() -> None:
    """Load a clearly-labelled demonstration without persisting any case data."""
    formulas, modulars, ons = master_data()
    example_feed = formulas.loc[
        formulas["name"].isin(["Isosource 1.5", "Peptamen 1.5"])
    ].copy()
    example_modular = modulars.loc[modulars["id"] == "nestle-beneprotein"].iloc[[0]].copy()

    clear_case_record_state()
    st.session_state.my_formulas = example_feed
    st.session_state.my_modulars = example_modular
    st.session_state.my_ons = ons.loc[
        ons["name"].isin(["BOOST Plus Calories — Vanilla"])
    ].copy()
    st.session_state["_chart_note_case_token"] = uuid4().hex
    st.session_state.update({
        "case_record_label": "Example — inpatient EN review",
        "assessment_sex": "Female",
        "assessment_age": 67,
        "assessment_current_weight": 64.0,
        "assessment_usual_weight": 68.0,
        "assessment_weight_unit": "kg",
        "assessment_height_unit": "cm",
        "assessment_height_cm": 165,
        "assessment_adjusted_weight_factor": 0.25,
        "assessment_estimated_weight": 62.0,
        "assessment_weight_choice": "Current body weight",
        "assessment_indirect_calorimetry": None,
        "assessment_activity_factor": 1.2,
        "assessment_stress_factor": 1.0,
        "assessment_energy_low_kcal_kg": 25.0,
        "assessment_energy_high_kcal_kg": 30.0,
        "assessment_energy_target": 1800.0,
        "assessment_protein_low_gkg": 1.2,
        "assessment_protein_high_gkg": 1.5,
        "assessment_protein_target": 85.0,
        "assessment_water_low_mlkg": 25.0,
        "assessment_water_high_mlkg": 30.0,
        "assessment_water_target": 1900.0,
        "en_energy_target": 1800.0,
        "en_total_energy_target": 1800.0,
        "en_protein_target": 85.0,
        "en_water_target": 1900.0,
        "feed_candidates": ["Isosource 1.5"],
        "icu_total_energy_target": 1800.0,
        "icu_protein_target": 85.0,
        "icu_water_target": 1900.0,
        "icu_feed_candidates": ["Peptamen 1.5"],
        "icu_planned_daily_intake_scenario": "lower",
        "en_selected_formula": "Isosource 1.5",
        "en_schedule_type": "Continuous / cyclic",
        "en_feeding_hours": 23.0,
        "en_achieved_delivery_pct": 100,
        "chosen_modulars": ["Beneprotein"],
        "modular_units_nestle-beneprotein": 1.0,
        "modular_doses_nestle-beneprotein": 2.0,
        "modular_water_nestle-beneprotein": 60.0,
        "en_medication_flushes": 120.0,
        "en_patency_flushes": 0.0,
        "en_hydration_flushes": 6,
        "en_hydration_schedule_format": "qXh",
        "en_hydration_interval_hours": 4,
        "scenario_standard_propofol_rate": 0.0,
        "scenario_standard_propofol_hours": 24.0,
        "scenario_standard_selected_formula": "Isosource 1.5",
        "scenario_standard_schedule_type": "Continuous / cyclic",
        "scenario_standard_feeding_hours": 23.0,
        "scenario_standard_achieved_delivery_pct": 100,
        "scenario_standard_chosen_modulars": ["Beneprotein"],
        "scenario_standard_modular_units_nestle-beneprotein": 1.0,
        "scenario_standard_modular_doses_nestle-beneprotein": 2.0,
        "scenario_standard_modular_water_nestle-beneprotein": 60.0,
        "scenario_standard_medication_flushes": 120.0,
        "scenario_standard_patency_flushes": 0.0,
        "scenario_standard_hydration_flushes": 6,
        "scenario_standard_hydration_schedule_format": "qXh",
        "scenario_standard_hydration_interval_hours": 4,
        "scenario_propofol_propofol_method": "Single Propofol rate",
        "scenario_propofol_prescription_target_pct": 100.0,
        "scenario_propofol_prescription_interruption_note": False,
        "scenario_propofol_propofol_rate": 20.0,
        "scenario_propofol_propofol_hours": 24.0,
        "scenario_propofol_lower_propofol_rate": 0.0,
        "scenario_propofol_higher_propofol_rate": 20.0,
        "scenario_propofol_higher_propofol_hours": 6.0,
        "scenario_propofol_selected_formula": "Peptamen 1.5",
        "scenario_propofol_schedule_type": "Continuous / cyclic",
        "scenario_propofol_feeding_hours": 23.0,
        "scenario_propofol_achieved_delivery_pct": 100,
        "scenario_propofol_chosen_modulars": ["Beneprotein"],
        "scenario_propofol_modular_units_nestle-beneprotein": 1.0,
        "scenario_propofol_modular_doses_nestle-beneprotein": 2.0,
        "scenario_propofol_modular_water_nestle-beneprotein": 60.0,
        "scenario_propofol_medication_flushes": 120.0,
        "scenario_propofol_patency_flushes": 0.0,
        "scenario_propofol_hydration_flushes": 6,
        "scenario_propofol_hydration_schedule_format": "qXh",
        "scenario_propofol_hydration_interval_hours": 4,
        "scenario_lower_propofol_rate": 0.0,
        "scenario_lower_propofol_hours": 24.0,
        "scenario_lower_selected_formula": "Peptamen 1.5",
        "scenario_lower_schedule_type": "Continuous / cyclic",
        "scenario_lower_feeding_hours": 23.0,
        "scenario_lower_achieved_delivery_pct": 100,
        "scenario_lower_chosen_modulars": ["Beneprotein"],
        "scenario_lower_modular_units_nestle-beneprotein": 1.0,
        "scenario_lower_modular_doses_nestle-beneprotein": 2.0,
        "scenario_lower_modular_water_nestle-beneprotein": 60.0,
        "scenario_lower_medication_flushes": 120.0,
        "scenario_lower_patency_flushes": 0.0,
        "scenario_lower_hydration_flushes": 6,
        "scenario_lower_hydration_schedule_format": "qXh",
        "scenario_lower_hydration_interval_hours": 4,
        "scenario_higher_propofol_rate": 20.0,
        "scenario_higher_propofol_hours": 24.0,
        "scenario_higher_selected_formula": "Peptamen 1.5",
        "scenario_higher_schedule_type": "Continuous / cyclic",
        "scenario_higher_feeding_hours": 23.0,
        "scenario_higher_achieved_delivery_pct": 100,
        "scenario_higher_chosen_modulars": ["Beneprotein"],
        "scenario_higher_modular_units_nestle-beneprotein": 1.0,
        "scenario_higher_modular_doses_nestle-beneprotein": 2.0,
        "scenario_higher_modular_water_nestle-beneprotein": 60.0,
        "scenario_higher_medication_flushes": 120.0,
        "scenario_higher_patency_flushes": 0.0,
        "scenario_higher_hydration_flushes": 6,
        "scenario_higher_hydration_schedule_format": "qXh",
        "scenario_higher_hydration_interval_hours": 4,
    })


def scenario_key(scenario_id: str, field: str) -> str:
    return f"scenario_{scenario_id}_{field}"


def mark_order_as_edited(flag_key: str) -> None:
    """Remember that the RD has replaced the calculated order suggestion."""
    st.session_state[flag_key] = True


def propofol_widget_key(state_key: str) -> str:
    """Return a temporary widget key for a saved Propofol-plan value."""
    return f"_propofol_widget_{state_key}"


def seed_propofol_widget(state_key: str) -> str:
    """Seed a temporary widget from its persistent saved-record value."""
    widget_key = propofol_widget_key(state_key)
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state.get(state_key)
    return widget_key


def sync_propofol_widget(
    widget_key: str,
    state_key: str,
    edited_key: str | None = None,
) -> None:
    """Copy a mounted Propofol widget value into persistent calculator state."""
    st.session_state[state_key] = st.session_state.get(widget_key)
    if edited_key is not None:
        st.session_state[edited_key] = True


def request_suggested_order(pending_key: str) -> None:
    """Queue a reset that can be applied before the order widget is rendered."""
    st.session_state[pending_key] = True


def show_partial_formula_delivery(scenario_id: str) -> None:
    """Show the newly entered partial-delivery estimate by default."""
    achieved_key = scenario_key(scenario_id, "achieved_delivery_pct")
    if number(st.session_state.get(achieved_key, 100)) < 100:
        st.session_state[scenario_key(scenario_id, "delivery_view")] = "Achieved delivery"


def reset_new_modular_orders(
    scenario_id: str,
    modular_ids_by_name: dict[str, str],
) -> None:
    """Clear implicit amounts when a modular is newly added to an order."""
    chosen_key = scenario_key(scenario_id, "chosen_modulars")
    previous_key = scenario_key(scenario_id, "chosen_modulars_previous")
    current = list(st.session_state.get(chosen_key, []))
    previous = set(st.session_state.get(previous_key, []))
    for modular_name in set(current) - previous:
        product_id = modular_ids_by_name.get(modular_name)
        if product_id is None:
            continue
        st.session_state[scenario_key(
            scenario_id, f"modular_units_{product_id}"
        )] = None
        st.session_state[scenario_key(
            scenario_id, f"modular_doses_{product_id}"
        )] = None
    st.session_state[previous_key] = current


def seed_scenario_state(
    scenario_id: str,
    candidates: list[str],
    saved_modulars: pd.DataFrame,
    migration_scenario_id: str | None = None,
) -> None:
    """Seed one propofol scenario while retaining compatibility with older records."""
    legacy_fields = {
        "selected_formula": "en_selected_formula",
        "schedule_type": "en_schedule_type",
        "feeding_hours": "en_feeding_hours",
        "feeds_per_day": "en_feeds_per_day",
        "achieved_delivery_pct": "en_achieved_delivery_pct",
        "delivery_view": "en_delivery_view",
        "chosen_modulars": "chosen_modulars",
        "ordered_rate_ml_hr": "en_ordered_rate_ml_hr",
        "ordered_volume_per_feed_ml": "en_ordered_volume_per_feed_ml",
        "ordered_formula_name": "en_ordered_formula_name",
        "medication_flushes": "en_medication_flushes",
        "patency_flushes": "en_patency_flushes",
        "hydration_flushes": "en_hydration_flushes",
        "hydration_schedule_format": "en_hydration_schedule_format",
        "hydration_interval_hours": "en_hydration_interval_hours",
        "describe_as_trickle": "en_describe_as_trickle",
        "prescription_target_pct": "en_prescription_target_pct",
        "prescription_interruption_note": "en_prescription_interruption_note",
    }
    defaults: dict[str, object] = {
        "selected_formula": candidates[0],
        "schedule_type": "Continuous / cyclic",
        "feeding_hours": 23.0,
        "feeds_per_day": 4,
        "achieved_delivery_pct": 100,
        "delivery_view": "Full planned EN",
        "chosen_modulars": [],
        "ordered_rate_ml_hr": None,
        "ordered_volume_per_feed_ml": None,
        "ordered_formula_name": None,
        "medication_flushes": 0.0,
        "patency_flushes": 0.0,
        "hydration_flushes": 6,
        "hydration_schedule_format": "times/day",
        "hydration_interval_hours": 4,
        "describe_as_trickle": False,
        "prescription_target_pct": 100.0,
        "prescription_interruption_note": False,
    }
    for field, legacy_key in legacy_fields.items():
        key = scenario_key(scenario_id, field)
        if key not in st.session_state:
            migrated_key = scenario_key(migration_scenario_id, field) if migration_scenario_id else None
            if migrated_key and migrated_key in st.session_state:
                st.session_state[key] = st.session_state[migrated_key]
            else:
                st.session_state[key] = st.session_state.get(legacy_key, defaults[field])
    edited_key = scenario_key(scenario_id, "order_user_edited")
    if edited_key not in st.session_state:
        migrated_edited_key = (
            scenario_key(migration_scenario_id, "order_user_edited")
            if migration_scenario_id else None
        )
        if migrated_edited_key and migrated_edited_key in st.session_state:
            st.session_state[edited_key] = st.session_state[migrated_edited_key]
        else:
            st.session_state[edited_key] = any(
                st.session_state.get(scenario_key(scenario_id, field)) is not None
                for field in ("ordered_rate_ml_hr", "ordered_volume_per_feed_ml")
            )
    ordered_schedule_key = scenario_key(scenario_id, "ordered_schedule_type")
    if ordered_schedule_key not in st.session_state:
        migrated_schedule_key = (
            scenario_key(migration_scenario_id, "ordered_schedule_type")
            if migration_scenario_id else None
        )
        st.session_state[ordered_schedule_key] = (
            st.session_state[migrated_schedule_key]
            if migrated_schedule_key and migrated_schedule_key in st.session_state
            else st.session_state[scenario_key(scenario_id, "schedule_type")]
        )
    propofol_key = scenario_key(scenario_id, "propofol_rate")
    if propofol_key not in st.session_state:
        migrated_propofol_key = scenario_key(migration_scenario_id, "propofol_rate") if migration_scenario_id else None
        if migrated_propofol_key and migrated_propofol_key in st.session_state:
            migrated_include_key = scenario_key(migration_scenario_id, "include_propofol")
            migrated_rate = st.session_state[migrated_propofol_key]
            st.session_state[propofol_key] = (
                migrated_rate if st.session_state.get(migrated_include_key, number(migrated_rate) > 0)
                else 0.0
            )
        elif scenario_id == "lower":
            st.session_state[propofol_key] = number(st.session_state.get("assessment_propofol_rate"))
        else:
            st.session_state[propofol_key] = None
    propofol_hours_key = scenario_key(scenario_id, "propofol_hours")
    if propofol_hours_key not in st.session_state:
        migrated_hours_key = (
            scenario_key(migration_scenario_id, "propofol_hours") if migration_scenario_id else None
        )
        st.session_state[propofol_hours_key] = (
            st.session_state[migrated_hours_key]
            if migrated_hours_key and migrated_hours_key in st.session_state else 24.0
        )

    selected_key = scenario_key(scenario_id, "selected_formula")
    if st.session_state[selected_key] not in candidates:
        st.session_state[selected_key] = candidates[0]
    schedule_key = scenario_key(scenario_id, "schedule_type")
    if st.session_state[schedule_key] == "Continuous":
        st.session_state[schedule_key] = "Continuous / cyclic"
    modular_names = set(saved_modulars["name"].tolist()) if not saved_modulars.empty else set()
    chosen_key = scenario_key(scenario_id, "chosen_modulars")
    st.session_state[chosen_key] = [
        name for name in st.session_state.get(chosen_key, []) if name in modular_names
    ]
    st.session_state.setdefault(
        scenario_key(scenario_id, "chosen_modulars_previous"),
        list(st.session_state[chosen_key]),
    )
    for _, product in saved_modulars.iterrows():
        product_id = str(product["id"])
        for field, legacy_prefix, default in (
            ("modular_units", "modular_units_", None),
            ("modular_doses", "modular_doses_", None),
            ("modular_water", "modular_water_", number(product.get("default_preparation_water_ml_per_dose", 0))),
        ):
            key = scenario_key(scenario_id, f"{field}_{product_id}")
            if key not in st.session_state:
                migrated_key = (
                    scenario_key(migration_scenario_id, f"{field}_{product_id}")
                    if migration_scenario_id else None
                )
                if migrated_key and migrated_key in st.session_state:
                    st.session_state[key] = st.session_state[migrated_key]
                else:
                    st.session_state[key] = st.session_state.get(f"{legacy_prefix}{product_id}", default)
