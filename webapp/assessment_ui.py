"""Assessment workflow and authoritative EN-plan goals."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from calculations import (
    adjusted_body_weight_kg,
    devine_ibw_kg,
    hamwi_ibw_kg,
    harris_benedict_kcal,
    height_to_cm,
    iv_fluid_delivery,
    mifflin_st_jeor_kcal,
    open_abdomen_protein_loss_g,
    penn_state_2003b_kcal,
    penn_state_2010_kcal,
    total_iv_fluid_delivery,
)
from constants import (
    IV_FLUIDS,
    KG_PER_LB,
    MAX_IV_FLUID_ORDERS,
    PLAN_GOALS,
    PROTEIN_WEIGHT_SAME_AS_ENERGY,
    WATER_MODES,
    WEIGHT_ACRONYMS,
)
from session_state import (
    sync_height_from_cm_entry,
    sync_height_from_feet_inches,
    sync_height_unit_fields,
    sync_weight_from_kg_entry,
    sync_weight_from_lb,
    sync_weight_unit_fields,
)
from ui_common import number, render_box_heading, render_report_table, render_worked_bounds

def show_assessment() -> None:
    st.caption("Blank means not entered; use 0 only when zero is intended.")
    with st.container(border=True):
        st.subheader("Measurements and weight history")
        measurement_left, measurement_right = st.columns(2)
        sex = measurement_left.selectbox("Sex used for equations", ["", "Female", "Male"], key="assessment_sex", format_func=lambda value: value or "Select…")
        age = measurement_left.number_input("Age (years)", min_value=18, max_value=120, value=None, step=1, key="assessment_age", placeholder="Enter age")
        height_unit = measurement_right.selectbox(
            "Height measurement unit", ["cm", "ft/in"], key="assessment_height_unit",
            format_func=lambda unit: "Centimetres (cm)" if unit == "cm" else "Feet and inches",
            on_change=sync_height_unit_fields,
        )
        if height_unit == "cm":
            if "assessment_height_cm_entry" not in st.session_state:
                st.session_state.assessment_height_cm_entry = st.session_state.get(
                    "assessment_height_cm"
                )
            height_cm = measurement_right.number_input(
                "Height (cm)", min_value=50, max_value=250, value=None, step=1,
                key="assessment_height_cm_entry", placeholder="Enter height",
                on_change=sync_height_from_cm_entry,
            )
        else:
            feet_column, inches_column = measurement_right.columns(2)
            height_feet = feet_column.number_input(
                "Height (ft)", min_value=3, max_value=8, value=None, step=1,
                key="assessment_height_feet", placeholder="Feet",
                on_change=sync_height_from_feet_inches,
            )
            height_inches = inches_column.number_input(
                "Height (in)", min_value=0.0, max_value=11.9, value=None, step=0.1,
                format="%.1f", key="assessment_height_inches", placeholder="Inches",
                on_change=sync_height_from_feet_inches,
            )
            height_cm = (
                height_to_cm("ft/in", feet=int(height_feet), inches=height_inches)
                if height_feet is not None and height_inches is not None else None
            )

        weight_unit = st.selectbox(
            "Weight measurement unit", ["kg", "lb"], key="assessment_weight_unit",
            format_func=lambda unit: "Kilograms (kg)" if unit == "kg" else "Pounds (lb)",
            on_change=sync_weight_unit_fields,
        )
        weights = st.columns(2)
        if weight_unit == "kg":
            if "assessment_current_weight_kg_entry" not in st.session_state:
                st.session_state.assessment_current_weight_kg_entry = st.session_state.get(
                    "assessment_current_weight"
                )
            if "assessment_usual_weight_kg_entry" not in st.session_state:
                st.session_state.assessment_usual_weight_kg_entry = st.session_state.get(
                    "assessment_usual_weight"
                )
            current_weight = weights[0].number_input(
                "Current body weight (kg)", min_value=1.0, value=None, step=0.1,
                format="%.1f", key="assessment_current_weight_kg_entry",
                placeholder="Enter weight", on_change=sync_weight_from_kg_entry,
                args=(
                    "assessment_current_weight_kg_entry",
                    "assessment_current_weight",
                    "assessment_current_weight_lb",
                ),
            )
            usual_weight = weights[1].number_input(
                "Usual body weight (kg)", min_value=1.0, value=None, step=0.1,
                format="%.1f", key="assessment_usual_weight_kg_entry",
                placeholder="Optional", on_change=sync_weight_from_kg_entry,
                args=(
                    "assessment_usual_weight_kg_entry",
                    "assessment_usual_weight",
                    "assessment_usual_weight_lb",
                ),
            )
        else:
            current_weight_lb = weights[0].number_input(
                "Current body weight (lb)", min_value=1.0, value=None, step=0.1,
                format="%.1f", key="assessment_current_weight_lb", placeholder="Enter weight",
                on_change=sync_weight_from_lb,
                args=("assessment_current_weight_lb", "assessment_current_weight"),
            )
            usual_weight_lb = weights[1].number_input(
                "Usual body weight (lb)", min_value=1.0, value=None, step=0.1,
                format="%.1f", key="assessment_usual_weight_lb", placeholder="Optional",
                on_change=sync_weight_from_lb,
                args=("assessment_usual_weight_lb", "assessment_usual_weight"),
            )
            current_weight = current_weight_lb * KG_PER_LB if current_weight_lb is not None else None
            usual_weight = usual_weight_lb * KG_PER_LB if usual_weight_lb is not None else None

        ready_for_weight = bool(sex and current_weight is not None and height_cm is not None)
        if ready_for_weight:
            bmi = current_weight / (height_cm / 100) ** 2
            stats = [f"BMI <strong>{bmi:.1f} kg/m²</strong>"]
            if usual_weight is None:
                stats.extend(["weight change not entered", "weight loss not entered"])
            else:
                change = current_weight - usual_weight
                stats.extend([
                    f"weight change <strong>{change:+.1f} kg</strong>",
                    f"weight loss <strong>{max((usual_weight - current_weight) / usual_weight * 100, 0):.1f}%</strong>",
                ])
            st.markdown(f'<p class="assessment-readout">{" · ".join(stats)}</p>', unsafe_allow_html=True)
            ibw = hamwi_ibw_kg(sex, height_cm)
            devine_ibw = devine_ibw_kg(sex, height_cm)
        else:
            ibw = None
            devine_ibw = None

        if st.session_state.get("assessment_adjusted_weight_factor") is None:
            st.session_state.assessment_adjusted_weight_factor = 0.25
        correction_factor = st.session_state.assessment_adjusted_weight_factor
        estimated_weight = st.session_state.get("assessment_estimated_weight")
        adjusted_weight = (adjusted_body_weight_kg(current_weight, ibw, correction_factor)
                           if ready_for_weight and correction_factor is not None else None)

        hamwi_work = (
            f"45.5 + 0.866 × ({height_cm:.1f} − 152.4)"
            if sex == "Female" and height_cm is not None
            else f"48.0 + 1.063 × ({height_cm:.1f} − 152.4)"
            if sex == "Male" and height_cm is not None
            else "—"
        )
        devine_work = (
            f"45.5 + 2.3 × (({height_cm:.1f} ÷ 2.54) − 60)"
            if sex == "Female" and height_cm is not None
            else f"50.0 + 2.3 × (({height_cm:.1f} ÷ 2.54) − 60)"
            if sex == "Male" and height_cm is not None
            else "—"
        )
        adjusted_work = (f"{ibw:.1f} + ({current_weight:.1f} − {ibw:.1f}) × [[{correction_factor:g}]]"
                         if adjusted_weight is not None else "—")
        weight_calculations = pd.DataFrame([
            {"Weight": "Current body weight (CBW)", "Values used": "Entered measurement", "Result (kg)": f"{current_weight:.1f}" if current_weight is not None else "—"},
            {"Weight": "Ideal body weight (IBW) — Hamwi, SI units", "Values used": hamwi_work, "Result (kg)": f"{ibw:.1f}" if ibw is not None else "—"},
            {"Weight": "Ideal body weight — Devine, medication-dosing reference", "Values used": devine_work, "Result (kg)": f"{devine_ibw:.1f}" if devine_ibw is not None else "—"},
            {"Weight": "Adjusted body weight (AdjBW) — from Hamwi IBW", "Values used": adjusted_work, "Result (kg)": f"{adjusted_weight:.1f}" if adjusted_weight is not None else "—"},
            {"Weight": "Estimated dry / clinician-selected weight", "Values used": "Entered weight", "Result (kg)": f"{estimated_weight:.1f}" if estimated_weight is not None else "—"},
        ])
        render_report_table(weight_calculations)
        adjustment, estimated = st.columns(2)
        correction_factor = adjustment.number_input(
            "Adjusted body-weight factor", min_value=0.0, max_value=1.0,
            value=None, step=0.05, format="%.2f", key="assessment_adjusted_weight_factor",
        )
        estimated_weight = estimated.number_input("Estimated dry / clinician-selected weight (kg)", min_value=1.0, value=None, step=0.1, format="%.1f", key="assessment_estimated_weight", placeholder="Optional")
        adjusted_weight = (adjusted_body_weight_kg(current_weight, ibw, correction_factor)
                           if ready_for_weight and correction_factor is not None else None)
        hamwi_label = "Ideal body weight (Hamwi — SI units)"
        if st.session_state.get("assessment_weight_choice") == "Hamwi IBW":
            st.session_state.assessment_weight_choice = hamwi_label
        adjusted_label = "Adjusted body weight (Hamwi IBW)"
        if st.session_state.get("assessment_weight_choice") in {
            "Adjusted body weight", "Adjusted body weight (Hamwi-based)"
        }:
            st.session_state.assessment_weight_choice = adjusted_label
        weight_options = {
            "Current body weight": current_weight,
            hamwi_label: ibw,
            adjusted_label: adjusted_weight,
            "Estimated dry / clinician-selected weight": estimated_weight,
        }
        available_choices = [name for name, value in weight_options.items() if value is not None]

    # Propofol affects the EN allocation rather than the energy-requirement
    # equations, so it is owned by the EN plan and not by Assessment.
    st.session_state.pop("assessment_propofol_rate", None)
    with st.container(border=True):
        st.subheader("Energy assessment")
        weight_choice = st.selectbox(
            "Weight used for energy and water calculations",
            [""] + available_choices,
            key="assessment_weight_choice",
            format_func=lambda value: (
                f"{value} ({weight_options[value]:.1f} kg)" if value else "Select…"
            ),
        )
        calculation_weight = weight_options.get(weight_choice)
        ready_for_equations = bool(ready_for_weight and calculation_weight is not None and age is not None)
        mifflin = mifflin_st_jeor_kcal(sex, calculation_weight, height_cm, age) if ready_for_equations else None
        harris = harris_benedict_kcal(sex, calculation_weight, height_cm, age) if ready_for_equations else None
        # Both Penn State equations were derived and validated with the Mifflin
        # term computed on actual body weight, including in obesity — the
        # modified 2010 form handles obesity through its own coefficients rather
        # than through a substituted weight. Feeding it an ideal or adjusted
        # weight applies the correction twice and understates the requirement.
        # An entered dry weight is an acceptable actual-weight proxy in fluid
        # overload; ideal and adjusted weights are not.
        # Penn State needs an actual weight, so it follows the weight selected
        # above only when that is the current or the clinician-selected weight.
        # An ideal or adjusted weight is not an actual weight, and substituting
        # a different one would contradict the clinician's selection, so the
        # rows are withheld instead.
        # Same abbreviations the chart note uses, so the two agree.
        penn_weight_labels = {
            "Current body weight": "CBW",
            "Estimated dry / clinician-selected weight": "clinician-selected weight",
        }
        penn_weight_label = penn_weight_labels.get(weight_choice, "")
        penn_weight = calculation_weight if penn_weight_label else None
        penn_mifflin = (
            mifflin_st_jeor_kcal(sex, penn_weight, height_cm, age)
            if sex and penn_weight is not None and height_cm is not None and age is not None
            else None
        )
        energy_low, energy_high, energy_measure = st.columns(3)
        low_kcal_kg = energy_low.number_input(
            "Energy range, from (kcal/kg)", min_value=0.0, value=None,
            step=1.0, format="%.0f", key="assessment_energy_low_kcal_kg",
            placeholder="Optional",
        )
        high_kcal_kg = energy_high.number_input(
            "Energy range, to (kcal/kg)", min_value=0.0, value=None,
            step=1.0, format="%.0f", key="assessment_energy_high_kcal_kg",
            placeholder="Optional",
        )
        measured = energy_measure.number_input(
            "Indirect calorimetry (kcal/day)", min_value=0.0, value=None,
            step=25.0, format="%.0f", key="assessment_indirect_calorimetry",
            placeholder="Optional",
        )
        st.session_state.setdefault("assessment_activity_factor", 1.0)
        st.session_state.setdefault("assessment_stress_factor", 1.0)
        factor_columns = st.columns(2)
        activity_factor = factor_columns[0].number_input(
            "Activity factor", min_value=0.0, max_value=5.0, step=0.05, format="%.2f",
            key="assessment_activity_factor",
        )
        stress_factor = factor_columns[1].number_input(
            "Stress factor", min_value=0.0, max_value=5.0, step=0.05, format="%.2f",
            key="assessment_stress_factor",
        )
        with st.expander(
            "Ventilation and temperature for Penn State equations", expanded=False
        ):
            st.caption(
                "The Penn State equations use only the current body weight or "
                "the clinician-selected weight. They are not shown when an ideal "
                "or adjusted weight is selected above."
            )
            temperature_input, minute_ventilation_input = st.columns(2)
            temperature = temperature_input.number_input(
                "Maximum temperature (°C)", min_value=30.0, max_value=45.0, value=None,
                step=0.1, format="%.1f", key="assessment_temperature", placeholder="Optional",
            )
            minute_ventilation = minute_ventilation_input.number_input(
                "Minute ventilation (L/min)", min_value=0.0, value=None, step=0.1,
                format="%.1f", key="assessment_minute_ventilation", placeholder="Optional",
            )
        st.markdown("**Energy requirement calculations**")
        energy_rows: list[dict[str, object]] = []
        if calculation_weight is not None and (
            low_kcal_kg is not None or high_kcal_kg is not None
        ):
            entered_bounds = [
                bound for bound in (low_kcal_kg, high_kcal_kg) if bound is not None
            ]
            bound_text = "–".join(f"{bound:g}" for bound in entered_bounds)
            energy_text = "–".join(
                f"{calculation_weight * bound:.0f}" for bound in entered_bounds
            )
            energy_rows.append({
                "Method": (
                    "Weight-based range" if len(entered_bounds) == 2
                    else "Weight-based estimate"
                ),
                "Calculation": (
                    f"{calculation_weight:.1f} kg × {bound_text} kcal/kg"
                ),
                "Energy (kcal/day)": energy_text,
                "Activity/stress-adjusted\nenergy (kcal/day)": "—",
            })
        if measured is not None:
            energy_rows.append({
                "Method": "Indirect calorimetry",
                "Calculation": "Measured value",
                "Energy (kcal/day)": f"{measured:.0f}",
                "Activity/stress-adjusted\nenergy (kcal/day)": "—",
            })
        if ready_for_equations:
            if sex == "Male":
                mifflin_calculation = (
                    f"10 × {calculation_weight:.1f} kg + 6.25 × {height_cm:.1f} cm "
                    f"− 5 × {age:.0f} y + 5"
                )
                harris_calculation = (
                    f"88.362 + 13.397 × {calculation_weight:.1f} kg + 4.799 × {height_cm:.1f} cm "
                    f"− 5.677 × {age:.0f} y"
                )
            else:
                mifflin_calculation = (
                    f"10 × {calculation_weight:.1f} kg + 6.25 × {height_cm:.1f} cm "
                    f"− 5 × {age:.0f} y − 161"
                )
                harris_calculation = (
                    f"447.593 + 9.247 × {calculation_weight:.1f} kg + 3.098 × {height_cm:.1f} cm "
                    f"− 4.330 × {age:.0f} y"
                )
            energy_rows.extend([
                {
                    "Method": "Mifflin–St Jeor", "Calculation": mifflin_calculation,
                    "Energy (kcal/day)": f"{mifflin:.0f}",
                    "Activity/stress-adjusted\nenergy (kcal/day)": (
                        f"{mifflin * activity_factor * stress_factor:.0f}"
                    ),
                },
                {
                    "Method": "Harris–Benedict", "Calculation": harris_calculation,
                    "Energy (kcal/day)": f"{harris:.0f}",
                    "Activity/stress-adjusted\nenergy (kcal/day)": (
                        f"{harris * activity_factor * stress_factor:.0f}"
                    ),
                },
            ])
            if (temperature is not None and minute_ventilation is not None
                    and penn_mifflin is not None):
                penn_basis = f"MSJ at {penn_weight_label} {penn_weight:.1f} kg"
                energy_rows.extend([
                    {
                        "Method": "Penn State 2003b — ventilated adults",
                        "Calculation": (
                            f"0.96 × {penn_mifflin:.0f} + 167 × {temperature:.1f} °C + "
                            f"31 × {minute_ventilation:.1f} L/min − 6212 "
                            f"({penn_basis})"
                        ),
                        "Energy (kcal/day)": f'{penn_state_2003b_kcal(
                            penn_mifflin, temperature, minute_ventilation
                        ):.0f}',
                        "Activity/stress-adjusted\nenergy (kcal/day)": "—",
                    },
                    {
                        "Method": "Modified Penn State 2010 — ventilated, age ≥60 and BMI ≥30",
                        "Calculation": (
                            f"0.71 × {penn_mifflin:.0f} + 85 × {temperature:.1f} °C + "
                            f"64 × {minute_ventilation:.1f} L/min − 3085 "
                            f"({penn_basis})"
                        ),
                        "Energy (kcal/day)": f'{penn_state_2010_kcal(
                            penn_mifflin, temperature, minute_ventilation
                        ):.0f}',
                        "Activity/stress-adjusted\nenergy (kcal/day)": "—",
                    },
                ])
        if energy_rows:
            with st.container(key="energy_calculations_table"):
                render_report_table(pd.DataFrame(energy_rows).round(0))
        target_energy = st.number_input(
            "Energy goal for EN plan (kcal/day)", min_value=0.0, value=None,
            step=25.0, format="%.0f", key="assessment_energy_target", placeholder="Enter goal",
        )

    iv_orders: list[dict[str, float]] = []
    with st.container(border=True, key="protein_target_box"):
        st.subheader("Protein assessment")
        # Protein gets its own weight because practice routinely
        # prescribes it on a different basis than energy -- commonly
        # IBW for protein against CBW or AdjBW for energy. The default
        # follows the energy weight, so a case that never touches this
        # behaves as it did when one selector drove every figure.
        def protein_weight_option(value: str) -> str:
            # The default names the energy weight rather than showing a
            # figure of its own, so resolve it here. Otherwise the one
            # option most cases sit on is the only one without a
            # kilogram value, and the weight driving the protein range
            # is stated only in a different section of the page.
            if value != PROTEIN_WEIGHT_SAME_AS_ENERGY:
                return f"{value} ({weight_options[value]:.1f} kg)"
            if calculation_weight is None:
                return value
            return f"{value} ({calculation_weight:.1f} kg)"

        protein_weight_choice = st.selectbox(
            "Weight used for protein calculations",
            [PROTEIN_WEIGHT_SAME_AS_ENERGY] + available_choices,
            key="assessment_protein_weight_choice",
            format_func=protein_weight_option,
        )
        protein_weight = (
            calculation_weight
            if protein_weight_choice == PROTEIN_WEIGHT_SAME_AS_ENERGY
            else weight_options.get(protein_weight_choice)
        )
        protein_low, protein_high = st.columns(2)
        low_gkg = protein_low.number_input("Lower (g/kg)", min_value=0.0, value=None, step=0.1, format="%.1f", key="assessment_protein_low_gkg", placeholder="Optional")
        high_gkg = protein_high.number_input("Upper (g/kg)", min_value=0.0, value=None, step=0.1, format="%.1f", key="assessment_protein_high_gkg", placeholder="Optional")
        render_worked_bounds("Calculated protein requirement range", protein_weight, low_gkg, high_gkg, "g/day")
        with st.expander("Additional protein losses", expanded=False):
            st.caption(
                "Open abdomen: exudate volume × protein factor. Suggested factor: "
                "**15–30 g/L**; use a measured or local value when available."
            )
            volume, factor = st.columns(2)
            exudate_ml = volume.number_input(
                "Exudate volume (mL/day)", min_value=0.0, value=None, step=25.0,
                format="%.0f", key="assessment_exudate_ml", placeholder="Optional",
            )
            loss_factor = factor.number_input(
                "Chosen protein factor (g/L)", min_value=0.0, value=None, step=1.0,
                format="%.0f", key="assessment_protein_loss_factor", placeholder="15–30",
            )
            exudate_loss = (
                open_abdomen_protein_loss_g(exudate_ml, loss_factor)
                if exudate_ml is not None and loss_factor is not None else None
            )
            exudate_result = f"{exudate_loss:.0f} g/day" if exudate_loss is not None else "—"
            st.markdown(
                '<p class="worked-bounds">Estimated additional protein loss: '
                f'<strong>{exudate_result}</strong></p>',
                unsafe_allow_html=True,
            )
            other_loss = st.number_input(
                "Other clinician-estimated protein loss (g/day)", min_value=0.0, value=None,
                step=1.0, format="%.0f", key="assessment_other_protein_loss", placeholder="Optional",
            )
            entered_losses = [
                loss for loss in (exudate_loss, other_loss) if loss is not None
            ]
            if entered_losses:
                st.markdown(
                    f'<p class="worked-bounds">Total additional protein loss: '
                    f'<strong>{sum(entered_losses):.0f} g/day</strong></p>',
                    unsafe_allow_html=True,
                )
        target_protein = st.number_input("Protein goal for EN plan (g/day)", min_value=0.0, value=None, step=1.0, format="%.0f", key="assessment_protein_target", placeholder="Enter goal")

    with st.container(border=True):
        st.subheader("Water and IV assessment")
        st.caption(
            "Enter any intravenous fluids, then choose whether hydration "
            "flushes are being prescribed and enter the water goal."
        )
        with st.expander("Intravenous fluids", expanded=False):
            st.caption(
                "Enter maintenance IVs here with their rate and hours per day. "
                "Dextrose from these counts toward energy and CHO, changing the "
                "suggested EN volume and rate. IV fluids here do not count "
                "toward daily water requirements — Clinician to lower the water "
                "goal below to avoid over-hydration."
            )
            for index in range(MAX_IV_FLUID_ORDERS):
                fluid_column, rate_column, hours_column, tkvo_column = st.columns(
                    [2, 1, 1, 1], vertical_alignment="bottom"
                )
                fluid_name = fluid_column.selectbox(
                    "IV" if index == 0 else f"IV {index + 1}",
                    [""] + list(IV_FLUIDS),
                    key=f"assessment_iv_fluid_{index}",
                    format_func=lambda value: value or "None",
                )
                # A line kept open supplies nothing and has no rate worth
                # entering, so TKVO replaces the rate rather than sitting
                # beside it. Read before the widget so the rate can be
                # disabled rather than silently ignored.
                tkvo = bool(st.session_state.get(f"assessment_iv_tkvo_{index}"))
                rate = rate_column.number_input(
                    "Rate (mL/hour)", min_value=0.0, step=5.0, format="%.0f",
                    value=None, key=f"assessment_iv_rate_{index}",
                    placeholder="TKVO" if tkvo else "Optional",
                    disabled=tkvo,
                )
                hours = hours_column.number_input(
                    "Hours", min_value=0.0, max_value=24.0, step=1.0,
                    format="%.0f", value=24.0,
                    key=f"assessment_iv_hours_{index}",
                    disabled=tkvo,
                )
                tkvo_column.checkbox("TKVO", key=f"assessment_iv_tkvo_{index}")
                if fluid_name and not tkvo and rate:
                    iv_orders.append(
                        iv_fluid_delivery(
                            IV_FLUIDS[fluid_name], number(rate), number(hours)
                        )
                    )
            if iv_orders:
                iv_totals = total_iv_fluid_delivery(iv_orders)
                st.markdown(
                    '<p class="summary-line">From IVs: Fluids '
                    f'<strong>{iv_totals["volume_ml"]:,.0f} mL/day</strong>, energy '
                    f'<strong>{iv_totals["energy_kcal"]:,.0f} kcal/day</strong>, CHO '
                    f'<strong>{iv_totals["carbohydrate_g"]:,.0f} g/day</strong>'
                    '</p>',
                    unsafe_allow_html=True,
                )

        with st.container(border=True, key="water_target_box"):
            st.markdown('<div class="target-box-heading"><strong>Water</strong></div>', unsafe_allow_html=True)
            # Charting the requirement and prescribing flushes are separate
            # decisions. With a line running the requirement is still
            # charted, as protein is, but no flush schedule follows from it.
            st.radio(
                "Water management", WATER_MODES,
                key="assessment_water_mode",
                label_visibility="collapsed",
            )
            water_low, water_high = st.columns(2)
            low_mlkg = water_low.number_input("Lower (mL/kg)", min_value=0.0, value=None, step=1.0, format="%.0f", key="assessment_water_low_mlkg", placeholder="Optional")
            high_mlkg = water_high.number_input("Upper (mL/kg)", min_value=0.0, value=None, step=1.0, format="%.0f", key="assessment_water_high_mlkg", placeholder="Optional")
            render_worked_bounds(
                "Calculated water requirement range", calculation_weight, low_mlkg,
                high_mlkg, "mL/day",
                weight_basis=WEIGHT_ACRONYMS.get(weight_choice, weight_choice) or None,
            )
            target_water = st.number_input("Water goal for EN plan (mL/day)", min_value=0.0, value=None, step=25.0, format="%.0f", key="assessment_water_target", placeholder="Enter goal")


    st.session_state.assessment_handoff = {
        "energy_target": target_energy, "protein_target": target_protein, "water_target": target_water,
        "calculation_weight": calculation_weight,
        "protein_weight": protein_weight,
    }


def update_assessment_goal(
    editor_key: str,
    assessment_key: str,
    en_key: str,
    icu_key: str,
    handoff_key: str,
) -> None:
    """Update the authoritative Assessment goal from a plan-page editor."""
    value = st.session_state.get(editor_key)
    st.session_state[assessment_key] = value
    st.session_state[en_key] = value
    st.session_state[icu_key] = value
    handoff = dict(st.session_state.get("assessment_handoff", {}))
    handoff[handoff_key] = value
    st.session_state.assessment_handoff = handoff


def render_assessment_goals(
    key_prefix: str,
) -> tuple[float | None, float | None, float | None]:
    """Show one shared set of goals with an optional in-place Assessment editor."""
    goal_values: list[float | None] = []
    editor_keys: list[str] = []
    for goal in PLAN_GOALS:
        assessment_key = str(goal["assessment_key"])
        value = st.session_state.get(assessment_key)
        goal_values.append(value)
        st.session_state[str(goal["en_key"])] = value
        st.session_state[str(goal["icu_key"])] = value
        editor_key = f"{key_prefix}_assessment_{goal['name']}_goal_editor"
        st.session_state[editor_key] = value
        editor_keys.append(editor_key)

    with st.container(border=True):
        render_box_heading("Goals from Assessment")
        summary_columns = st.columns([1, 1, 1, 0.8], vertical_alignment="bottom")
        for column, goal, value in zip(summary_columns[:3], PLAN_GOALS, goal_values):
            display = "—" if value is None else f"{number(value):.0f} {goal['unit']}"
            column.markdown(
                f'<p class="summary-line">{goal["label"]}<br><strong>{display}</strong></p>',
                unsafe_allow_html=True,
            )
        with summary_columns[3].popover("Adjust goals", width="stretch"):
            st.caption("Changes here also update Assessment.")
            for goal, editor_key in zip(PLAN_GOALS, editor_keys):
                st.number_input(
                    f"{goal['label']} goal ({goal['unit']})",
                    min_value=0.0,
                    value=None,
                    step=float(goal["step"]),
                    format="%.0f",
                    key=editor_key,
                    placeholder="Enter goal",
                    on_change=update_assessment_goal,
                    args=(
                        editor_key,
                        str(goal["assessment_key"]),
                        str(goal["en_key"]),
                        str(goal["icu_key"]),
                        str(goal["handoff_key"]),
                    ),
                )
    return goal_values[0], goal_values[1], goal_values[2]
