"""Verify that connected clinical workflows survive saving and reopening."""

import re
import sys
from html import unescape
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from case_io import export_case_record_workbook

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def example():
    app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
    next(
        button for button in app.button if button.label == "📋 Load example record"
    ).click().run(timeout=30)
    assert not app.exception
    return app


def enter(app, kind, key, value):
    getattr(app, kind)(key=key).set_value(value).run(timeout=30)
    assert not app.exception


def intake_tables(app):
    tables = tuple(
        item.value
        for item in app.markdown
        if "<table" in item.value
        and "<th>Source</th>" in item.value
        and "<th>Volume (mL)</th>" in item.value
    )
    assert len(tables) == 2, "Expected standard and Propofol intake tables"
    return tables


def table_rows(table):
    return {
        cells[0]: cells[1:]
        for row in re.findall(r"<tr>(.*?)</tr>", table)
        if (
            cells := [
                unescape(re.sub(r"<[^>]+>", "", cell))
                for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row)
            ]
        )
    }


def visible_results(app):
    return (
        intake_tables(app),
        app.session_state["_chart_note_generated_en_plan"],
        app.session_state["_chart_note_generated_propofol"],
    )


def save_replace_and_reopen(app):
    before = visible_results(app)
    payload = export_case_record_workbook(
        app.session_state.filtered_state,
        app.session_state["my_formulas"],
        app.session_state["my_modulars"],
        app.session_state["my_ons"],
    )
    # Replace the active case so reopening must restore saved inputs rather
    # than accidentally retain the currently mounted widgets and product list.
    next(
        button for button in app.button if button.label == "📋 Load example record"
    ).click().run(timeout=30)
    enter(app, "number_input", "assessment_age", 80)
    changed = visible_results(app)
    assert changed[0] != before[0]
    assert changed[1:] != before[1:]
    app.file_uploader(key="case_record_upload").upload(
        "workflow.xlsx",
        payload,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ).run(timeout=30)
    app.button(key="load_case_record").click().run(timeout=30)
    assert not app.exception
    assert visible_results(app) == before
    assert app.session_state["assessment_age"] == 67
    # A further unrelated rerun must not revive obsolete defaults or mirrors.
    app.run(timeout=30)
    assert not app.exception
    assert visible_results(app) == before


def test_partial_intermittent_feed_with_pudding_modular_and_iv_round_trips():
    app = example()
    app.button(key="add_ons_BOOST Pudding — Vanilla").click().run(timeout=30)
    enter(
        app,
        "radio",
        "scenario_standard_running_shape",
        "Intermittent, each feed run at a rate for a set time",
    )
    enter(app, "number_input", "scenario_standard_hours_per_feed", 2.0)
    enter(app, "number_input", "scenario_standard_feeds_per_day", 4)
    enter(app, "number_input", "scenario_standard_ordered_rate_ml_hr", 100)
    enter(app, "selectbox", "assessment_iv_fluid_0", "D5W")
    enter(app, "number_input", "assessment_iv_rate_0", 100)
    enter(
        app,
        "multiselect",
        "scenario_standard_chosen_ons",
        ["BOOST Pudding — Vanilla"],
    )
    product = "nestle-boost-pudding-vanilla"
    enter(app, "number_input", f"scenario_standard_ons_servings_{product}", 0.5)
    enter(app, "number_input", f"scenario_standard_ons_times_{product}", 2)
    enter(app, "number_input", "scenario_standard_achieved_delivery_pct", 50)

    rows = table_rows(intake_tables(app)[0])
    # 100 mL/hour × 2 hours × four feeds × 50% = 400 mL, giving
    # 600 kcal from a 1.5 kcal/mL formula. Non-formula sources are unscaled.
    assert rows["Isosource 1.5"][:2] == ["400", "600"]
    assert rows["Modulars"][1] == "50"
    assert rows["IV fluids"][:2] == ["2400", "408"]
    assert rows["ONS"][1] == "230"  # Half a 230-kcal cup twice daily.
    assert rows["Total"][1] == "1288"
    note = app.session_state["_chart_note_generated_en_plan"]
    assert "BOOST Pudding — Vanilla, 0.5 cups BID" in note
    assert "provides energy 1,888 kcal" in note  # Full prescribed delivery.
    save_replace_and_reopen(app)
    assert app.session_state["scenario_standard_ordered_rate_ml_hr"] == 100
    assert app.session_state["scenario_standard_achieved_delivery_pct"] == 50
    assert app.session_state[f"scenario_standard_ons_servings_{product}"] == 0.5


def test_conditional_propofol_with_manual_orders_and_iv_round_trips():
    app = example()
    enter(app, "radio", "scenario_propofol_propofol_method", "Changing Propofol rates")
    enter(app, "number_input", "scenario_propofol_feeding_hours", 24.0)
    enter(app, "selectbox", "assessment_iv_fluid_0", "D5W")
    enter(app, "number_input", "assessment_iv_rate_0", 100)
    lower = "scenario_propofol_conditional_lower_rate_ml_hr"
    higher = "scenario_propofol_conditional_higher_rate_ml_hr"
    assert (app.session_state[lower], app.session_state[higher]) == (40, 25)
    enter(app, "number_input", "_propofol_widget_" + lower, 70)
    enter(app, "number_input", "_propofol_widget_" + higher, 30)

    rows = table_rows(intake_tables(app)[1])
    # The higher Propofol condition lasts six hours, leaving eighteen at
    # the lower condition: 70 × 18 + 30 × 6 = 1440 mL of 1.5 kcal/mL feed.
    assert rows["Peptamen 1.5"][:2] == ["1440", "2160"]
    assert rows["Propofol"][1] == "132"  # 20 mL/hour × 6 hours × 1.1 kcal/mL.
    assert rows["IV fluids"][:2] == ["2400", "408"]
    assert rows["Modulars"][1] == "50"
    assert rows["Total"][1] == "2750"
    note = app.session_state["_chart_note_generated_propofol"]
    assert "When Propofol is not running, provide feed at 70 mL/hr" in note
    assert "When Propofol is at 20 mL/hr, provide feed at 30 mL/hr" in note
    assert "provides energy 2,750 kcal" in note
    save_replace_and_reopen(app)
    assert (app.session_state[lower], app.session_state[higher]) == (70, 30)
    assert app.number_input(key="_propofol_widget_" + lower).value == 70
    assert app.number_input(key="_propofol_widget_" + higher).value == 30
