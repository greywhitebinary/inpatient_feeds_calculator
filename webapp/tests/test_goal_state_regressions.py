"""Exercise deliberate blanks through goal widgets, reruns, and saved records."""

import sys
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from case_io import export_case_record_workbook
from constants import PLAN_GOALS
from data import load_master_formulas, load_master_modulars

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def open_record(app, payload):
    app.file_uploader(key="case_record_upload").upload(
        "goal-regression.xlsx",
        payload,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ).run(timeout=30)
    app.button(key="load_case_record").click().run(timeout=30)
    assert not app.exception


def assert_blank_goals(app):
    assert not app.exception
    for goal in PLAN_GOALS:
        for key in (goal["assessment_key"], goal["en_key"], goal["icu_key"]):
            assert app.session_state[key] is None, key
        assert app.number_input(key=goal["assessment_key"]).value is None
        assert app.session_state["assessment_handoff"][goal["handoff_key"]] is None
        for prefix in ("en", "icu"):
            editor_key = f"{prefix}_assessment_{goal['name']}_goal_editor"
            assert app.number_input(key=editor_key).value is None


@pytest.mark.parametrize("editor", ["assessment", "en", "icu"])
def test_cleared_goals_survive_rerun_and_save_reopen(editor):
    app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
    next(
        button for button in app.button if button.label == "📋 Load example record"
    ).click().run(timeout=30)
    for goal in PLAN_GOALS:
        key = (
            goal["assessment_key"]
            if editor == "assessment"
            else f"{editor}_assessment_{goal['name']}_goal_editor"
        )
        app.number_input(key=key).set_value(None)
    app.run(timeout=30)
    assert_blank_goals(app)

    app.number_input(key="assessment_age").set_value(68).run(timeout=30)
    assert_blank_goals(app)
    payload = export_case_record_workbook(
        app.session_state.filtered_state,
        app.session_state["my_formulas"],
        app.session_state["my_modulars"],
        app.session_state["my_ons"],
    )
    # Reopening must replace a subsequently entered goal with the saved blank.
    app.number_input(key="assessment_energy_target").set_value(2000).run(timeout=30)
    open_record(app, payload)
    assert_blank_goals(app)
    assert app.session_state["assessment_age"] == 68


@pytest.mark.parametrize("legacy_source", ["en_key", "icu_key"])
def test_old_record_migrates_only_absent_assessment_goals(legacy_source):
    payload = export_case_record_workbook(
        {"assessment_energy_target": None},
        load_master_formulas().head(1),
        load_master_modulars().head(0),
    )
    workbook = load_workbook(BytesIO(payload))
    for goal, value in zip(PLAN_GOALS, (1800, 85, 1900)):
        workbook["Case inputs"].append([goal[legacy_source], str(value)])
    buffer = BytesIO()
    workbook.save(buffer)

    app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
    open_record(app, buffer.getvalue())
    assert app.session_state["assessment_energy_target"] is None
    assert app.session_state["assessment_protein_target"] == 85
    assert app.session_state["assessment_water_target"] == 1900
