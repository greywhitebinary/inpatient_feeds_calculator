"""End-to-end safeguards for connections between orders and calculated intake."""

import re
import sys
from html import unescape
from io import BytesIO
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calculations import micronutrient_delivery
from data import (
    FORMULA_OPTIONAL_NUMERIC_COLUMNS,
    export_formulary_workbook,
    import_formulary_workbook,
    load_master_formulas,
    load_master_modulars,
)

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def widget(app, kind, key):
    return next(item for item in getattr(app, kind) if item.key == key)


def set_value(app, kind, key, value):
    widget(app, kind, key).set_value(value).run(timeout=30)
    assert not app.exception


def example():
    app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
    next(
        item for item in app.button if item.label == "📋 Load example record"
    ).click().run(timeout=30)
    assert not app.exception
    return app


def table_rows(app, header):
    """Read the visible report, rather than reusing a production calculation."""
    rows = []
    for item in app.markdown:
        if "<table" not in item.value or f"<th>{header}</th>" not in item.value:
            continue
        body = item.value.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
        for row in re.findall(r"<tr>(.*?)</tr>", body):
            rows.append(
                [
                    unescape(re.sub(r"<[^>]+>", "", cell))
                    for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row)
                ]
            )
    return rows


@pytest.mark.parametrize("duration,full,partial", [(2.0, 800, 400), (0.5, 200, 100)])
def test_partial_rate_duration_delivery_keeps_the_full_order(duration, full, partial):
    app = example()
    set_value(
        app,
        "radio",
        "scenario_standard_running_shape",
        "Intermittent, each feed run at a rate for a set time",
    )
    set_value(app, "number_input", "scenario_standard_hours_per_feed", duration)
    set_value(app, "number_input", "scenario_standard_feeds_per_day", 4)
    set_value(app, "number_input", "scenario_standard_ordered_rate_ml_hr", 100)
    full_note = app.session_state["_chart_note_generated_en_plan"]
    full_row = next(
        row for row in table_rows(app, "Source") if row[0] == "Isosource 1.5"
    )
    assert float(full_row[1]) == full
    assert float(full_row[2]) == full * 1.5
    set_value(app, "number_input", "scenario_standard_achieved_delivery_pct", 50)
    partial_row = next(
        row for row in table_rows(app, "Source") if row[0] == "Isosource 1.5"
    )
    # Independently: rate × duration × four feeds × one half.
    assert float(partial_row[1]) == partial
    assert float(partial_row[2]) == partial * 1.5
    assert app.session_state["scenario_standard_ordered_rate_ml_hr"] == 100
    assert app.session_state["_chart_note_generated_en_plan"] == full_note
    set_value(app, "selectbox", "scenario_standard_delivery_view", "Full planned EN")
    restored = next(
        row for row in table_rows(app, "Source") if row[0] == "Isosource 1.5"
    )
    assert float(restored[1]) == full


def conditional_example():
    app = example()
    set_value(
        app, "radio", "scenario_propofol_propofol_method", "Changing Propofol rates"
    )
    set_value(app, "number_input", "scenario_propofol_feeding_hours", 24.0)
    return app


@pytest.mark.parametrize("scenario", ["standard", "propofol"])
@pytest.mark.parametrize("target", [100.0, 50.0, 110.0])
def test_regimen_target_survives_switch_to_review_and_back(scenario, target):
    app = example()
    target_key = f"scenario_{scenario}_prescription_target_pct"
    mode_key = f"scenario_{scenario}_regimen_source"
    if target != 100:
        set_value(app, "number_input", target_key, target)
    for _ in range(2):
        set_value(app, "radio", mode_key, "Reviewing a feed already running")
        assert app.session_state[target_key] == target
        app.run(timeout=30)
        assert not app.exception
        set_value(app, "radio", mode_key, "Starting a new feed")
        assert widget(app, "number_input", target_key).value == target
        # AppTest alone misses the browser remounting this hidden input at
        # its serialized default (formerly the minimum, 1), despite Python
        # still reporting 100. Check the value sent for a fresh browser input.
        assert widget(app, "number_input", target_key).proto.default == target
        assert app.session_state[target_key] == target


def test_shorter_feeding_day_keeps_manual_rate_and_updates_suggestion():
    app = example()
    set_value(app, "number_input", "scenario_standard_feeding_hours", 24.0)
    set_value(app, "number_input", "scenario_standard_ordered_rate_ml_hr", 40.0)
    set_value(app, "number_input", "scenario_standard_feeding_hours", 16.0)
    assert (
        widget(app, "number_input", "scenario_standard_ordered_rate_ml_hr").value == 40
    )
    row = next(row for row in table_rows(app, "Source") if row[0] == "Isosource 1.5")
    assert float(row[1]) == 640
    assert float(row[2]) == 960
    assert any("Suggested: <strong>75 mL/hour" in item.value for item in app.markdown)
    widget(app, "button", "scenario_standard_use_suggested_order").click().run(
        timeout=30
    )
    assert not app.exception
    assert app.session_state["scenario_standard_ordered_rate_ml_hr"] == 75


def test_conditional_suggestions_include_iv_energy_and_keep_manual_orders():
    app = conditional_example()
    lower = "scenario_propofol_conditional_lower_rate_ml_hr"
    higher = "scenario_propofol_conditional_higher_rate_ml_hr"
    assert (app.session_state[lower], app.session_state[higher]) == (50, 35)
    set_value(app, "selectbox", "assessment_iv_fluid_0", "D5W")
    set_value(app, "number_input", "assessment_iv_rate_0", 100)
    # 1800 - 408 kcal IV; the higher condition additionally deducts
    # 20 × 24 × 1.1 = 528 kcal. Divide each remainder by 24 × 1.5,
    # then round to the nearest 5 mL/hour: 40 and 25.
    assert (app.session_state[lower], app.session_state[higher]) == (40, 25)
    rows = table_rows(app, "Suggested EN rate with lower/no Propofol (mL/hour)")
    selected = next(row for row in rows if row[0] == "Peptamen 1.5")
    assert [float(selected[2]), float(selected[3])] == [40, 25]
    rendered = "\n".join(item.value for item in app.markdown)
    assert "408 kcal from IV fluids" in rendered
    set_value(app, "number_input", "_propofol_widget_" + lower, 70)
    set_value(app, "number_input", "assessment_iv_rate_0", 200)
    # The entered lower-condition order persists, while the untouched higher
    # suggestion follows the new 816 kcal IV contribution.
    assert (app.session_state[lower], app.session_state[higher]) == (70, 15)
    rows = table_rows(app, "Suggested EN rate with lower/no Propofol (mL/hour)")
    selected = next(row for row in rows if row[0] == "Peptamen 1.5")
    assert [float(selected[2]), float(selected[3])] == [25, 15]
    widget(
        app, "button", "scenario_propofol_conditional_lower_use_suggested"
    ).click().run(timeout=30)
    assert not app.exception
    assert app.session_state[lower] == 25


@pytest.mark.parametrize(
    "change,expected", [("goal", 65), ("iv", 25), ("propofol", 20)]
)
def test_changed_inputs_update_suggestion_without_replacing_manual_feed(
    change, expected
):
    app = example()
    scenario = "propofol" if change == "propofol" else "standard"
    order_key = f"scenario_{scenario}_ordered_rate_ml_hr"
    display_key = "_propofol_widget_" + order_key if change == "propofol" else order_key
    set_value(app, "number_input", f"scenario_{scenario}_feeding_hours", 24.0)
    set_value(app, "number_input", display_key, 40.0)
    if change == "goal":
        set_value(app, "number_input", "assessment_energy_target", 2400.0)
        # 2400 kcal / 1.5 kcal/mL / 24 hours, rounded to 5 mL/hour.
    elif change == "iv":
        set_value(app, "selectbox", "assessment_iv_fluid_0", "D5W")
        set_value(app, "number_input", "assessment_iv_rate_0", 200.0)
        # (1800 - 816 kcal IV) / 1.5 / 24, rounded to 5 mL/hour.
    else:
        set_value(
            app,
            "number_input",
            "_propofol_widget_scenario_propofol_propofol_hours",
            24.0,
        )
        set_value(
            app,
            "number_input",
            "_propofol_widget_scenario_propofol_propofol_rate",
            40.0,
        )
        # (1800 - 40 * 24 * 1.1 kcal propofol) / 1.5 / 24, rounded to 5.
    assert widget(app, "number_input", display_key).value == 40
    assert any(
        f"Suggested: <strong>{expected} mL/hour" in item.value for item in app.markdown
    )
    formula_name = "Peptamen 1.5" if change == "propofol" else "Isosource 1.5"
    row = next(row for row in table_rows(app, "Source") if row[0] == formula_name)
    assert float(row[1]) == 960
    assert float(row[2]) == 1440
    widget(app, "button", f"scenario_{scenario}_use_suggested_order").click().run(
        timeout=30
    )
    assert not app.exception
    assert widget(app, "number_input", display_key).value == expected
    assert app.session_state[order_key] == expected


def test_switching_to_intermittent_volume_uses_target_not_previous_manual_volume():
    app = example()
    set_value(app, "number_input", "scenario_standard_feeding_hours", 24.0)
    set_value(app, "number_input", "scenario_standard_ordered_rate_ml_hr", 40.0)
    set_value(
        app,
        "radio",
        "scenario_standard_running_shape",
        "Intermittent, each feed a set volume",
    )
    set_value(app, "number_input", "scenario_standard_feeds_per_day", 4)
    assert (
        widget(
            app, "number_input", "scenario_standard_ordered_volume_per_feed_ml"
        ).value
        == 300
    )
    row = next(row for row in table_rows(app, "Source") if row[0] == "Isosource 1.5")
    assert float(row[1]) == 1200
    assert float(row[2]) == 1800


@pytest.mark.parametrize(
    "mode,expected", [("standard", 50), ("single", 35), ("lower", 50), ("higher", 35)]
)
def test_explicit_suggestion_applies_to_reviewed_order_and_survives_reruns(
    mode, expected
):
    app = conditional_example() if mode in {"lower", "higher"} else example()
    scenario = "standard" if mode == "standard" else "propofol"
    set_value(
        app,
        "radio",
        f"scenario_{scenario}_regimen_source",
        "Reviewing a feed already running",
    )
    if mode in {"lower", "higher"}:
        state_key = f"scenario_propofol_conditional_{mode}_rate_ml_hr"
        display_key = "_propofol_widget_" + state_key
        button_key = f"scenario_propofol_conditional_{mode}_use_suggested"
    else:
        state_key = f"scenario_{scenario}_ordered_rate_ml_hr"
        display_key = (
            state_key if mode == "standard" else "_propofol_widget_" + state_key
        )
        button_key = f"scenario_{scenario}_use_suggested_order"
    set_value(app, "number_input", display_key, 20)
    set_value(app, "number_input", f"scenario_{scenario}_medication_flushes", 40)
    assert app.session_state[state_key] == 20
    widget(app, "button", button_key).click().run(timeout=30)
    assert not app.exception
    assert app.session_state[state_key] == expected
    assert widget(app, "number_input", display_key).value == expected
    set_value(app, "number_input", f"scenario_{scenario}_medication_flushes", 80)
    assert app.session_state[state_key] == expected


@pytest.mark.parametrize(
    "duration,feeds,expected_rate", [(0.5, 1, 2400), (0.5, 2, 1200), (1.0, 1, 1200)]
)
def test_suggested_rate_uses_actual_total_intermittent_hours(
    duration, feeds, expected_rate
):
    app = example()
    set_value(
        app,
        "radio",
        "scenario_standard_running_shape",
        "Intermittent, each feed run at a rate for a set time",
    )
    set_value(app, "number_input", "scenario_standard_hours_per_feed", duration)
    set_value(app, "number_input", "scenario_standard_feeds_per_day", feeds)
    # The example's 1,800 kcal goal needs 1,200 mL of its 1.5 kcal/mL
    # formula. Divide that volume by the actual total running time, including
    # a valid half-hour day. These assertions check arithmetic, not whether
    # such a schedule is clinically appropriate.
    assert app.session_state["scenario_standard_ordered_rate_ml_hr"] == expected_rate
    row = next(row for row in table_rows(app, "Source") if row[0] == "Isosource 1.5")
    assert float(row[1]) == 1200
    assert float(row[2]) == 1800


@pytest.mark.parametrize("unknown", [None, "", float("nan")])
def test_micronutrient_unknown_is_distinct_from_declared_zero(unknown):
    amounts = micronutrient_delivery(
        {"zinc_mg_per_mL": unknown, "iron_per_mL": 0.014, "copper_mg_per_mL": 0},
        1000,
    )
    assert amounts["zinc_mg_per_mL"] is None
    assert amounts["thiamine_mg_per_mL"] is None
    assert amounts["copper_mg_per_mL"] == 0
    assert amounts["iron_per_mL"] == 14


def test_imported_minimal_formula_displays_unknown_micronutrients_as_unknown():
    formulas = load_master_formulas()
    formulas = formulas.loc[formulas["name"] == "Isosource 1.5"].drop(
        columns=list(FORMULA_OPTIONAL_NUMERIC_COLUMNS - {"fibre_per_mL"})
    )
    formulas["zinc_mg_per_mL"] = 0.0
    payload = export_formulary_workbook(formulas, load_master_modulars().iloc[0:0])
    imported, _, _ = import_formulary_workbook(BytesIO(payload))
    app = example()
    app.session_state["my_formulas"] = imported
    app.run(timeout=30)
    assert not app.exception
    rows = dict(table_rows(app, "Micronutrient"))
    assert rows["Iron (mg)"] == "—"
    assert float(rows["Zinc (mg)"]) == 0
    assert any("not disclosed" in item.value for item in app.caption)


@pytest.mark.parametrize(
    "fluid,sodium,potassium,calcium",
    [
        ("NS", 369.6, 0, 0),
        ("LR", 312, 9.6, 3.36),
        ("D5 1/2 NS + 20 mmol/L KCl", 184.8, 48, 0),
    ],
)
def test_iv_electrolytes_reach_both_intake_totals_during_partial_feeding(
    fluid, sodium, potassium, calcium
):
    app = example()
    set_value(app, "selectbox", "assessment_iv_fluid_0", fluid)
    set_value(app, "number_input", "assessment_iv_rate_0", 100)
    # At 100 mL/hour for 24 hours, each concentration in mmol/L is
    # multiplied by 2.4 L. Formula-delivery percentage never scales an IV.
    for percentage in (100, 50):
        if percentage != 100:
            for scenario in ("standard", "propofol"):
                set_value(
                    app,
                    "number_input",
                    f"scenario_{scenario}_achieved_delivery_pct",
                    percentage,
                )
        iv_rows = [row for row in table_rows(app, "Source") if row[0] == "IV fluids"]
        assert len(iv_rows) == 2
        for row in iv_rows:
            assert float(row[1]) == 2400
            assert float(row[6]) == 0  # IV volume still does not fill the water goal.
            assert float(row[7]) == pytest.approx(sodium, abs=0.05)
            assert float(row[8]) == pytest.approx(potassium, abs=0.05)
            assert float(row[9]) == pytest.approx(calcium, abs=0.05)
            assert float(row[10]) == 0  # No phosphorus in these source records.
            assert float(row[11]) == 0
        current_rows = []
        totals_checked = 0
        for row in table_rows(app, "Source"):
            if row[0] != "Total":
                current_rows.append(row)
                continue
            for column, contribution in ((7, sodium), (8, potassium), (9, calcium)):
                other_sources = sum(
                    float(source[column])
                    for source in current_rows
                    if source[0] != "IV fluids" and source[column] != "—"
                )
                # Source rows and totals round independently to one decimal.
                assert float(row[column]) == pytest.approx(
                    other_sources + contribution, abs=0.15
                )
            totals_checked += 1
            current_rows = []
        assert totals_checked == 2
