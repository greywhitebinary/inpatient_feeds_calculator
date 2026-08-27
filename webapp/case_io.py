"""Portable, local-only case-record workbook helpers.

The Streamlit application does not persist cases.  These helpers create and
read a workbook selected by the clinician so a browser session can be resumed
on the same or another approved local device.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
from typing import Any
from copy import copy

import pandas as pd

from data import validate_import


CASE_RECORD_TITLE = "Adult Inpatient Enteral Nutrition case record"
CASE_RECORD_VERSION = 1
CASE_RECORD_SHEET = "Case record"
CASE_INPUTS_SHEET = "Case inputs"

# These keys are deliberately limited to clinical calculator inputs. The label
# is part of the downloaded file and must follow the clinician's local policy.
CASE_STATE_KEYS = {
    "case_record_label",
    "assessment_sex",
    "assessment_age",
    "assessment_current_weight",
    "assessment_usual_weight",
    "assessment_height_unit",
    "assessment_height_m",
    "assessment_height_feet",
    "assessment_height_inches",
    "assessment_adjusted_weight_factor",
    "assessment_estimated_weight",
    "assessment_weight_choice",
    "assessment_indirect_calorimetry",
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
    "en_protein_target",
    "en_water_target",
    "feed_candidates",
    "en_selected_formula",
    "en_schedule_type",
    "en_feeding_hours",
    "en_feeds_per_day",
    "en_achieved_delivery_pct",
    "chosen_modulars",
    "en_medication_flushes",
    "en_patency_flushes",
    "en_hydration_flushes",
}


def _json_value(value: Any) -> str:
    """Serialize only simple Streamlit widget values."""
    if isinstance(value, (str, int, float, bool, list)) or value is None:
        return json.dumps(value, ensure_ascii=False)
    raise ValueError("Case record contains an unsupported input value.")


def case_state_snapshot(session_state: dict[str, Any]) -> dict[str, Any]:
    """Return just the explicitly supported inputs and modular order values."""
    state: dict[str, Any] = {}
    for key in CASE_STATE_KEYS:
        if key in session_state:
            state[key] = session_state[key]
    for key, value in session_state.items():
        if key.startswith(("modular_units_", "modular_doses_", "modular_water_")):
            state[key] = value
    return state


def export_case_record_workbook(
    session_state: dict[str, Any], formulas: pd.DataFrame, modulars: pd.DataFrame
) -> bytes:
    """Create a reviewable workbook containing a local case and product snapshot."""
    state = case_state_snapshot(session_state)
    inputs = pd.DataFrame(
        [{"Field key": key, "Saved value (JSON)": _json_value(value)} for key, value in sorted(state.items())]
    )
    label = str(state.get("case_record_label", "")).strip()
    metadata = pd.DataFrame([
        [CASE_RECORD_TITLE, None],
        ["This file is local to the clinician's chosen device or approved storage location.", None],
        ["The website does not store or transmit case records.", None],
        ["The record label is part of this downloaded file. Store and transfer the file according to local privacy policy.", None],
        ["Record version", CASE_RECORD_VERSION],
        ["Saved at UTC", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")],
        ["Patient / record label", label],
    ])
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        metadata.to_excel(writer, sheet_name=CASE_RECORD_SHEET, header=False, index=False)
        inputs.to_excel(writer, sheet_name=CASE_INPUTS_SHEET, index=False)
        formulas.to_excel(writer, sheet_name="My Formulary", index=False)
        modulars.to_excel(writer, sheet_name="My Modulars", index=False)

        for name in (CASE_RECORD_SHEET, CASE_INPUTS_SHEET, "My Formulary", "My Modulars"):
            worksheet = writer.sheets[name]
            worksheet.sheet_view.showGridLines = False
            worksheet.freeze_panes = "A2" if name != CASE_RECORD_SHEET else "A5"
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
                for cell in (worksheet["A2"], worksheet["A3"], worksheet["A4"]):
                    alignment = copy(cell.alignment)
                    alignment.wrap_text = True
                    cell.alignment = alignment
                worksheet.row_dimensions[2].height = 28
                worksheet.row_dimensions[3].height = 28
                worksheet.row_dimensions[4].height = 42
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


def import_case_record_workbook(uploaded_file) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
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
    state: dict[str, Any] = {}
    for _, row in inputs.iterrows():
        key = str(row["Field key"]).strip()
        if key not in CASE_STATE_KEYS and not key.startswith(("modular_units_", "modular_doses_", "modular_water_")):
            raise ValueError(f"Case record contains an unsupported field: {key}.")
        try:
            value = json.loads(str(row["Saved value (JSON)"]))
        except json.JSONDecodeError as error:
            raise ValueError(f"Case record has an unreadable value for {key}.") from error
        if not isinstance(value, (str, int, float, bool, list, type(None))):
            raise ValueError(f"Case record has an unsupported value for {key}.")
        state[key] = value
    formulas = pd.read_excel(workbook, sheet_name="My Formulary")
    modulars = pd.read_excel(workbook, sheet_name="My Modulars")
    formulas, modulars = validate_import(formulas, modulars)
    return state, formulas, modulars
