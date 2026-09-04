"""Portable, local-only case-record workbook helpers.

The Streamlit application does not persist cases.  These helpers create and
read a workbook selected by the clinician so a browser session can be resumed
on the same or another approved local device.
"""

from __future__ import annotations

import json
import os
import re
from copy import copy
from datetime import datetime, timezone
from io import BytesIO
from math import isfinite
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from constants import (
    HYDRATION_ENTRY_MODES,
    IV_FLUIDS,
    ORDER_FORMS,
    PERI_FEED_FLUSH_PATTERNS,
    REGIMEN_SOURCES,
    RUNNING_SHAPES,
    WATER_MODES,
)
from data import load_master_ons, validate_import

CASE_RECORD_TITLE = "Adult Inpatient Enteral Nutrition case record"
CASE_RECORD_VERSION = 1
CASE_RECORD_SHEET = "Case record"
CASE_INPUTS_SHEET = "Case inputs"
CALCULATOR_WEBSITE_URL = os.getenv("CALCULATOR_WEBSITE_URL", "To be added after deployment")

# These keys are deliberately limited to clinical calculator inputs. The label
# is part of the downloaded file and must follow the clinician's local policy.
CASE_STATE_KEYS = {
    "case_record_label",
    "assessment_sex",
    "assessment_age",
    "assessment_current_weight",
    "assessment_usual_weight",
    "assessment_weight_unit",
    "assessment_current_weight_lb",
    "assessment_usual_weight_lb",
    "assessment_height_cm",
    # Kept only so records downloaded before centimetres became the sole
    # height entry can be opened and migrated on import.
    "assessment_height_unit",
    "assessment_height_m",
    "assessment_height_feet",
    "assessment_height_inches",
    "assessment_adjusted_weight_factor",
    "assessment_estimated_weight",
    "assessment_weight_choice",
    "assessment_protein_weight_choice",
    "assessment_water_mode",
    "assessment_energy_low_kcal_kg",
    "assessment_energy_high_kcal_kg",
    "assessment_indirect_calorimetry",
    "assessment_activity_factor",
    "assessment_stress_factor",
    "assessment_mechanical_ventilation",
    "assessment_temperature",
    "assessment_minute_ventilation",
    "assessment_propofol_rate",
    "assessment_energy_target",
    "assessment_protein_low_gkg",
    "assessment_protein_high_gkg",
    "assessment_protein_target",
    "assessment_additional_loss_mode",
    "assessment_exudate_ml",
    "assessment_protein_loss_factor",
    "assessment_other_protein_loss",
    "assessment_water_low_mlkg",
    "assessment_water_high_mlkg",
    "assessment_water_target",
    "en_energy_target",
    "en_total_energy_target",
    "en_has_alternate_plan",
    "en_protein_target",
    "en_water_target",
    "feed_candidates",
    "icu_total_energy_target",
    "icu_protein_target",
    "icu_water_target",
    "icu_feed_candidates",
    "icu_planned_daily_intake_scenario",
    "en_selected_formula",
    "en_schedule_type",
    "en_feeding_hours",
    "en_feeds_per_day",
    "en_achieved_delivery_pct",
    "en_delivery_view",
    "chosen_modulars",
    "en_medication_flushes",
    "en_patency_flushes",
    "en_hydration_flushes",
    "en_hydration_schedule_format",
    "en_hydration_interval_hours",
    "planned_daily_intake_scenario",
}

CASE_DYNAMIC_PREFIXES = (
    "assessment_iv_fluid_",
    "assessment_iv_rate_",
    "assessment_iv_hours_",
    "assessment_iv_tkvo_",
    "modular_units_",
    "modular_doses_",
    "modular_water_",
    "scenario_",
)

CASE_TRANSIENT_SUFFIXES = (
    "_use_suggested_order",
    "_order_reset_requested",
    "_use_suggested",
    "_reset_requested",
    "_chosen_modulars_previous",
)

# These plan-level keys are retained only so older records remain importable.
# New records store the authoritative Assessment goals once.
CASE_EXPORT_OMIT_KEYS = {
    "en_energy_target",
    "en_total_energy_target",
    "en_protein_target",
    "en_water_target",
    "icu_total_energy_target",
    "icu_protein_target",
    "icu_water_target",
}

CASE_LIST_KEYS = {"feed_candidates", "icu_feed_candidates", "chosen_modulars"}
CASE_BOOL_KEYS = {"assessment_mechanical_ventilation", "en_has_alternate_plan"}
CASE_STRING_KEYS = {
    "case_record_label", "assessment_sex", "assessment_weight_unit",
    "assessment_height_unit", "assessment_weight_choice",
    "assessment_protein_weight_choice", "assessment_water_mode",
    "assessment_additional_loss_mode", "icu_planned_daily_intake_scenario",
    "en_selected_formula", "en_schedule_type", "en_delivery_view",
    "en_hydration_schedule_format", "planned_daily_intake_scenario",
}
CASE_ENUM_VALUES = {
    "assessment_sex": {"", "Female", "Male"},
    "assessment_weight_unit": {"kg", "lb"},
    "assessment_height_unit": {"cm", "ft/in", "m"},
    "icu_planned_daily_intake_scenario": {"lower", "higher"},
    "planned_daily_intake_scenario": {"lower", "higher", "primary", "alternate"},
    "en_schedule_type": {"Continuous", "Continuous / cyclic", "Intermittent"},
    "en_delivery_view": {"Full planned EN", "Achieved delivery"},
    "en_hydration_schedule_format": {"times/day", "qXh"},
    "assessment_water_mode": set(WATER_MODES),
}
CASE_NUMERIC_RANGES: dict[str, tuple[float | None, float | None, bool]] = {
    "assessment_age": (18, 120, True),
    "assessment_current_weight": (1, None, False),
    "assessment_usual_weight": (1, None, False),
    "assessment_current_weight_lb": (1, None, False),
    "assessment_usual_weight_lb": (1, None, False),
    "assessment_height_cm": (50, 250, False),
    "assessment_height_m": (0.5, 2.5, False),
    "assessment_height_feet": (3, 8, True),
    "assessment_height_inches": (0, 11.9, False),
    "assessment_adjusted_weight_factor": (0, 1, False),
    "assessment_estimated_weight": (1, None, False),
    "assessment_activity_factor": (0, 5, False),
    "assessment_stress_factor": (0, 5, False),
    "assessment_temperature": (30, 45, False),
    "assessment_minute_ventilation": (0, None, False),
    "en_feeds_per_day": (1, 12, True),
    "en_achieved_delivery_pct": (0, 100, False),
    "en_hydration_flushes": (1, 24, True),
    "en_hydration_interval_hours": (1, 24, True),
}
SCENARIO_ID_PATTERN = r"(?:standard|propofol|lower|higher|primary|alternate)"
SCENARIO_FIELD_PATTERN = re.compile(
    rf"^scenario_(?P<scenario>{SCENARIO_ID_PATTERN})_(?P<field>.+)$"
)
SCENARIO_STRING_FIELDS = {
    "selected_formula", "ordered_formula_name", "schedule_type",
    "ordered_schedule_type", "delivery_view", "hydration_schedule_format",
    "propofol_method", "regimen_source", "hydration_entry_mode",
    "peri_feed_flush_pattern", "order_entry_form", "ordered_entry_form",
    "running_shape",
}
SCENARIO_LIST_FIELDS = {"chosen_modulars", "chosen_ons"}
SCENARIO_BOOL_FIELDS = {
    "order_user_edited", "include_propofol", "describe_as_trickle",
    "conditional_lower_rate_user_edited", "conditional_higher_rate_user_edited",
    "prescription_interruption_note",
}
SCENARIO_NUMERIC_RANGES: dict[str, tuple[float | None, float | None, bool]] = {
    "feeding_hours": (1, 24, False),
    "feeds_per_day": (1, 12, True),
    "achieved_delivery_pct": (0, 100, False),
    "ordered_rate_ml_hr": (0, None, False),
    "ordered_volume_per_feed_ml": (0, None, False),
    "medication_flushes": (0, None, False),
    "patency_flushes": (0, None, False),
    "hydration_flushes": (1, 24, True),
    "hydration_interval_hours": (1, 24, True),
    # The ordered-flush count allows zero, unlike the calculated schedule above,
    # because an order may have no clock-scheduled line at all.
    "ordered_flush_times_per_day": (0, 24, True),
    "ordered_flush_volume_ml": (0, None, False),
    "peri_feed_flush_volume_ml": (0, None, False),
    "hours_per_feed": (0.5, 24, False),
    # No screen writes this any more: entering a daily total was dropped
    # because it is not a way a feed runs. Kept so a record saved while that
    # form existed still opens.
    "ordered_daily_volume_ml": (0, None, False),
    "propofol_rate": (0, None, False),
    "propofol_hours": (0, 24, False),
    "lower_propofol_rate": (0, None, False),
    "higher_propofol_rate": (0, None, False),
    "higher_propofol_hours": (0, 24, False),
    "prescription_target_pct": (1, 200, False),
    "conditional_lower_rate_ml_hr": (0, None, False),
    "conditional_higher_rate_ml_hr": (0, None, False),
}


def _validate_number(
    key: str,
    value: Any,
    minimum: float | None = 0,
    maximum: float | None = None,
    integer: bool = False,
) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Case record has a non-numeric value for {key}.")
    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError(f"Case record has a non-finite value for {key}.")
    if minimum is not None and numeric < minimum:
        raise ValueError(f"Case record has a value below {minimum:g} for {key}.")
    if maximum is not None and numeric > maximum:
        raise ValueError(f"Case record has a value above {maximum:g} for {key}.")
    if integer and not numeric.is_integer():
        raise ValueError(f"Case record requires a whole number for {key}.")


def _validate_string(key: str, value: Any, *, allow_none: bool = True) -> None:
    if value is None and allow_none:
        return
    if not isinstance(value, str):
        raise ValueError(f"Case record has a non-text value for {key}.")


def _validate_string_list(key: str, value: Any) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"Case record requires a list of product names for {key}.")


def _validate_case_state_value(key: str, value: Any) -> None:
    """Validate one restored input before it can reach widget-backed state."""
    if key in CASE_LIST_KEYS:
        _validate_string_list(key, value)
        return
    if key in CASE_BOOL_KEYS:
        if not isinstance(value, bool):
            raise ValueError(f"Case record requires true or false for {key}.")
        return
    if key in CASE_STRING_KEYS:
        _validate_string(key, value)
        if value is not None and key in CASE_ENUM_VALUES and value not in CASE_ENUM_VALUES[key]:
            raise ValueError(f"Case record has an unsupported value for {key}.")
        return
    if key in CASE_STATE_KEYS:
        minimum, maximum, integer = CASE_NUMERIC_RANGES.get(key, (0, None, False))
        _validate_number(key, value, minimum, maximum, integer)
        return

    for prefix in ("modular_units_", "modular_doses_", "modular_water_"):
        if key.startswith(prefix):
            _validate_number(key, value, 0)
            return

    if key.startswith("assessment_iv_rate_"):
        _validate_number(key, value, 0)
        return
    if key.startswith("assessment_iv_hours_"):
        _validate_number(key, value, 0, 24)
        return
    if key.startswith("assessment_iv_tkvo_"):
        if not isinstance(value, bool):
            raise ValueError(f"Case record requires true or false for {key}.")
        return
    if key.startswith("assessment_iv_fluid_"):
        # An empty string is the selectbox's "no fluid" state. Anything else
        # must name a fluid this build knows, so a record written by a later
        # version cannot restore a composition this one cannot cost.
        _validate_string(key, value)
        if value not in (None, "") and value not in IV_FLUIDS:
            raise ValueError(f"Case record names an unknown intravenous fluid: {value}.")
        return

    match = SCENARIO_FIELD_PATTERN.fullmatch(key)
    if match is None:
        raise ValueError(f"Case record contains an unsupported field: {key}.")
    field = match.group("field")
    if field in SCENARIO_LIST_FIELDS:
        _validate_string_list(key, value)
    elif field in SCENARIO_BOOL_FIELDS:
        if not isinstance(value, bool):
            raise ValueError(f"Case record requires true or false for {key}.")
    elif field in SCENARIO_STRING_FIELDS:
        _validate_string(key, value)
        if field in {"schedule_type", "ordered_schedule_type"} and value not in {
            "Continuous", "Continuous / cyclic", "Intermittent", None,
        }:
            raise ValueError(f"Case record has an unsupported schedule for {key}.")
        if field == "delivery_view" and value not in {
            "Full planned EN", "Achieved delivery", None,
        }:
            raise ValueError(f"Case record has an unsupported delivery view for {key}.")
        if field == "hydration_schedule_format" and value not in {
            "times/day", "qXh", None,
        }:
            raise ValueError(f"Case record has an unsupported hydration schedule for {key}.")
        if field == "propofol_method" and value not in {
            "Single Propofol rate", "Changing Propofol rates",
            "Single daily EN rate", "Conditional EN rates", None,
        }:
            raise ValueError(f"Case record has an unsupported Propofol method for {key}.")
        if field == "regimen_source" and value not in set(REGIMEN_SOURCES) | {None}:
            raise ValueError(f"Case record has an unsupported regimen source for {key}.")
        if field == "hydration_entry_mode" and value not in (
            set(HYDRATION_ENTRY_MODES) | {None}
        ):
            raise ValueError(
                f"Case record has an unsupported hydration entry mode for {key}."
            )
        if field == "peri_feed_flush_pattern" and value not in (
            set(PERI_FEED_FLUSH_PATTERNS) | {None}
        ):
            raise ValueError(
                f"Case record has an unsupported peri-feed flush pattern for {key}."
            )
        if field == "running_shape" and value not in set(RUNNING_SHAPES) | {None}:
            raise ValueError(
                f"Case record has an unsupported running shape for {key}."
            )
        if field in {"order_entry_form", "ordered_entry_form"} and value not in (
            set(ORDER_FORMS) | {None}
        ):
            raise ValueError(
                f"Case record has an unsupported order entry form for {key}."
            )
    elif field in SCENARIO_NUMERIC_RANGES:
        minimum, maximum, integer = SCENARIO_NUMERIC_RANGES[field]
        _validate_number(key, value, minimum, maximum, integer)
    elif field.startswith((
        "modular_units_", "modular_doses_", "modular_water_",
        "ons_containers_", "ons_times_",
    )):
        _validate_number(key, value, 0)
    else:
        raise ValueError(f"Case record contains an unsupported scenario field: {key}.")


def _json_value(value: Any) -> str:
    """Serialize only simple Streamlit widget values."""
    if isinstance(value, (str, int, float, bool, list)) or value is None:
        return json.dumps(value, ensure_ascii=False)
    raise ValueError("Case record contains an unsupported input value.")


def case_state_snapshot(session_state: dict[str, Any]) -> dict[str, Any]:
    """Return just the explicitly supported inputs and modular order values."""
    state: dict[str, Any] = {}
    has_shared_propofol_plan = any(
        key.startswith("scenario_propofol_") for key in session_state
    )
    for key in CASE_STATE_KEYS:
        if key in session_state and key not in CASE_EXPORT_OMIT_KEYS:
            if has_shared_propofol_plan and key in {
                "icu_planned_daily_intake_scenario", "planned_daily_intake_scenario",
            }:
                continue
            state[key] = session_state[key]
    for key, value in session_state.items():
        if key.startswith(CASE_DYNAMIC_PREFIXES) and not key.endswith(CASE_TRANSIENT_SUFFIXES):
            if has_shared_propofol_plan and key.startswith(
                ("scenario_lower_", "scenario_higher_", "scenario_primary_", "scenario_alternate_")
            ):
                continue
            state[key] = value
    return state


def _configured_calculator_website() -> str:
    """Return the configured public URL, or the deployment placeholder."""
    configured = os.getenv("CALCULATOR_WEBSITE_URL", CALCULATOR_WEBSITE_URL).strip()
    parsed = urlparse(configured)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return "To be added after deployment"
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or hostname.endswith(".localhost"):
        return "To be added after deployment"
    return configured


def export_case_record_workbook(
    session_state: dict[str, Any],
    formulas: pd.DataFrame,
    modulars: pd.DataFrame,
    ons: pd.DataFrame | None = None,
) -> bytes:
    """Create a reviewable workbook containing a local case and product snapshot."""
    state = case_state_snapshot(session_state)
    inputs = pd.DataFrame(
        [{"Field key": key, "Saved value (JSON)": _json_value(value)} for key, value in sorted(state.items())]
    )
    label = str(state.get("case_record_label", "")).strip()
    if ons is None:
        ons = load_master_ons().iloc[0:0].copy()
    metadata = pd.DataFrame([
        [CASE_RECORD_TITLE, None],
        ["Calculator website", _configured_calculator_website()],
        ["This file is local to the clinician's chosen device or approved storage location.", None],
        ["The application does not retain case records; a hosted session processes entered values while it is active.", None],
        ["The record label is part of this downloaded file. Store and transfer the file according to local privacy policy.", None],
        ["Record version", CASE_RECORD_VERSION],
        ["Saved at UTC", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")],
        ["Record label", label],
    ])
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        metadata.to_excel(writer, sheet_name=CASE_RECORD_SHEET, header=False, index=False)
        inputs.to_excel(writer, sheet_name=CASE_INPUTS_SHEET, index=False)
        formulas.to_excel(writer, sheet_name="My Formulary", index=False)
        modulars.to_excel(writer, sheet_name="My Modulars", index=False)
        ons.to_excel(writer, sheet_name="My ONS", index=False)

        for name in (
            CASE_RECORD_SHEET, CASE_INPUTS_SHEET, "My Formulary", "My Modulars", "My ONS",
        ):
            worksheet = writer.sheets[name]
            worksheet.sheet_view.showGridLines = False
            worksheet.freeze_panes = "A2" if name != CASE_RECORD_SHEET else "A6"
            worksheet.column_dimensions["A"].width = 34
            worksheet.column_dimensions["B"].width = 80 if name == CASE_RECORD_SHEET else 30
            for cell in worksheet[1]:
                font = copy(cell.font)
                font.bold = True
                font.color = "FFFFFF"
                cell.font = font
                fill = copy(cell.fill)
                fill.fgColor.rgb = "00A4243A"
                fill.fill_type = "solid"
                cell.fill = fill
            if name == CASE_RECORD_SHEET:
                worksheet.merge_cells("A1:B1")
                title_font = copy(worksheet["A1"].font)
                title_font.bold = True
                title_font.color = "FFFFFF"
                title_font.size = 14
                worksheet["A1"].font = title_font
                website_cell = worksheet["B2"]
                website = str(website_cell.value or "")
                if website.startswith(("http://", "https://")):
                    website_cell.hyperlink = website
                    website_cell.style = "Hyperlink"
                for cell in (worksheet["A3"], worksheet["A4"], worksheet["A5"]):
                    alignment = copy(cell.alignment)
                    alignment.wrap_text = True
                    cell.alignment = alignment
                worksheet.row_dimensions[3].height = 28
                worksheet.row_dimensions[4].height = 42
                worksheet.row_dimensions[5].height = 42
            else:
                worksheet.auto_filter.ref = worksheet.dimensions
    return buffer.getvalue()


def _read_metadata(workbook: pd.ExcelFile) -> dict[str, str]:
    metadata = pd.read_excel(workbook, sheet_name=CASE_RECORD_SHEET, header=None, usecols="A:B")
    if metadata.empty or str(metadata.iloc[0, 0]).strip() != CASE_RECORD_TITLE:
        raise ValueError("This is not an Adult Inpatient EN case-record workbook.")
    values = {
        str(row.iloc[0]).strip(): "" if len(row) < 2 or pd.isna(row.iloc[1]) else str(row.iloc[1]).strip()
        for _, row in metadata.iterrows() if not pd.isna(row.iloc[0])
    }
    if values.get("Record version") != str(CASE_RECORD_VERSION):
        raise ValueError("This case record uses an unsupported version.")
    return values


def import_case_record_workbook(
    uploaded_file,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read and validate a previously downloaded local case record."""
    workbook = pd.ExcelFile(uploaded_file)
    required = {CASE_RECORD_SHEET, CASE_INPUTS_SHEET, "My Formulary", "My Modulars"}
    missing = required - set(workbook.sheet_names)
    if missing:
        raise ValueError("Case record is missing worksheets: " + ", ".join(sorted(missing)))
    _read_metadata(workbook)
    # Preserve the JSON token `null`.  Pandas otherwise treats it as a
    # missing spreadsheet cell, which would silently collapse a deliberate
    # blank input into an unreadable record on reopening.
    inputs = pd.read_excel(workbook, sheet_name=CASE_INPUTS_SHEET, keep_default_na=False)
    if set(inputs.columns) != {"Field key", "Saved value (JSON)"}:
        raise ValueError("Case inputs worksheet has an unexpected layout.")
    normalized_keys = inputs["Field key"].astype(str).str.strip()
    if normalized_keys.eq("").any():
        raise ValueError("Case inputs worksheet contains a blank field key.")
    if normalized_keys.duplicated().any():
        raise ValueError("Case inputs worksheet contains duplicate field keys.")
    state: dict[str, Any] = {}
    for _, row in inputs.iterrows():
        key = str(row["Field key"]).strip()
        if key.endswith(CASE_TRANSIENT_SUFFIXES):
            continue
        if key not in CASE_STATE_KEYS and not key.startswith(CASE_DYNAMIC_PREFIXES):
            raise ValueError(f"Case record contains an unsupported field: {key}.")
        try:
            value = json.loads(str(row["Saved value (JSON)"]))
        except json.JSONDecodeError as error:
            raise ValueError(f"Case record has an unreadable value for {key}.") from error
        if not isinstance(value, (str, int, float, bool, list, type(None))):
            raise ValueError(f"Case record has an unsupported value for {key}.")
        _validate_case_state_value(key, value)
        state[key] = value

    method_key = "scenario_propofol_propofol_method"
    method_migrations = {
        "Single daily EN rate": "Single Propofol rate",
        "Conditional EN rates": "Changing Propofol rates",
    }
    if state.get(method_key) in method_migrations:
        state[method_key] = method_migrations[str(state[method_key])]

    if "assessment_height_cm" not in state:
        unit = state.get("assessment_height_unit")
        if unit == "m" and state.get("assessment_height_m") is not None:
            state["assessment_height_cm"] = float(state["assessment_height_m"]) * 100
        elif (unit == "ft/in" and state.get("assessment_height_feet") is not None
              and state.get("assessment_height_inches") is not None):
            state["assessment_height_cm"] = (
                float(state["assessment_height_feet"]) * 12 + float(state["assessment_height_inches"])
            ) * 2.54
    # Metres are no longer offered in the interface. Preserve feet/inches so
    # a saved record reopens in the same entry mode, while retaining the
    # centimetre value used by all calculations.
    if state.get("assessment_height_unit") == "m":
        for key in ("assessment_height_unit", "assessment_height_m"):
            state.pop(key, None)
    formulas = pd.read_excel(workbook, sheet_name="My Formulary")
    modulars = pd.read_excel(workbook, sheet_name="My Modulars")
    ons = (
        pd.read_excel(workbook, sheet_name="My ONS")
        if "My ONS" in workbook.sheet_names
        else load_master_ons().iloc[0:0].copy()
    )
    formulas, modulars, ons = validate_import(formulas, modulars, ons)
    return state, formulas, modulars, ons
