"""Adult Inpatient Enteral Nutrition Calculator — Streamlit entry point.

This application is a reviewable calculation workspace. It does not provide
autonomous clinical recommendations. It has no server-side patient-record
storage; clinicians can voluntarily download and later upload a local case file.
"""

from __future__ import annotations

from base64 import b64encode
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from calculations import (
    adjusted_body_weight_kg,
    feed_delivery,
    hamwi_ibw_kg,
    harris_benedict_kcal,
    height_to_cm,
    mg_to_mmol,
    mifflin_st_jeor_kcal,
    modular_delivery,
    open_abdomen_protein_loss_g,
    penn_state_2003b_kcal,
    propofol_intake,
    total_modular_delivery,
    water_plan,
)
from case_io import CASE_STATE_KEYS, export_case_record_workbook, import_case_record_workbook
from data import (
    export_formulary_workbook,
    import_formulary_workbook,
    load_master_formulas,
    load_master_modulars,
)


st.set_page_config(page_title="Adult Inpatient EN Calculator", layout="wide")


@st.cache_data
def master_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_master_formulas(), load_master_modulars()


def initialise_state() -> None:
    formulas, modulars = master_data()
    if "my_formulas" not in st.session_state:
        st.session_state.my_formulas = formulas.iloc[0:0].copy()
    if "my_modulars" not in st.session_state:
        st.session_state.my_modulars = modulars.iloc[0:0].copy()
    st.session_state.setdefault("case_record_label", "My EN record")


def number(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def compact_feed_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, item in frame.iterrows():
        rows.append({
            "Product": item["name"],
            "Manufacturer": item["brand"],
            "Energy (kcal/mL)": number(item["kcal_per_mL"]),
            "Protein (g/L)": number(item["protein_per_mL"]) * 1000,
            "Free water (mL/L)": number(item["free_water_per_mL"]) * 1000,
            "Na (mmol/L)": mg_to_mmol("sodium", number(item["sodium_per_mL"]) * 1000),
            "K (mmol/L)": mg_to_mmol("potassium", number(item["potassium_per_mL"]) * 1000),
            "Ca (mmol/L)": mg_to_mmol("calcium", number(item["calcium_per_mL"]) * 1000),
            "P (mmol/L)": mg_to_mmol("phosphorus", number(item["phosphorus_per_mL"]) * 1000),
            "Mg (mmol/L)": mg_to_mmol("magnesium", number(item["magnesium_per_mL"]) * 1000),
            "Fibre (g/L)": number(item["fibre_per_mL"]) * 1000,
        })
    return pd.DataFrame(rows)


def formula_type(name: str) -> str:
    """Return a plain-language working category for the saved-card display."""
    if any(term in name for term in ("NovaSource", "Nepro", "Suplena")):
        return "renal formula"
    if any(term in name for term in ("Peptamen", "Pivot", "Vital Peptide")):
        return "peptide-based"
    if any(term in name for term in ("Tolerex", "Vivonex")):
        return "elemental"
    if any(term in name for term in ("Diabetic", "Glucerna")):
        return "diabetes-specific"
    if "Compleat" in name:
        return "whole-food ingredients"
    if any(term in name for term in ("Fibre", "Jevity")):
        return "whole protein with fibre"
    if any(term in name for term in ("Intense", "Promote")):
        return "high protein"
    if any(term in name for term in ("2.0", "TwoCal", "Resource 2")):
        return "energy dense"
    return "standard whole protein"


def render_feed_card(item: pd.Series) -> None:
    """Render the saved-card structure established by the formulary wireframe."""
    with st.container(border=True):
        details, profile = st.columns([1, 1.8], gap="large")
        with details:
            st.markdown(f"#### {item['name']}")
            st.caption(f"{item['brand']} · {formula_type(str(item['name']))}")
            if st.button("Remove", key=f"remove_feed_{item['name']}"):
                st.session_state.my_formulas = st.session_state.my_formulas.loc[
                    st.session_state.my_formulas["name"] != item["name"]
                ].reset_index(drop=True)
                st.rerun()
        with profile:
            st.markdown('<div class="feed-profile">', unsafe_allow_html=True)
            metrics = [
                ("Energy", "kcal/mL", number(item["kcal_per_mL"])),
                ("Protein", "g/100 mL", number(item["protein_per_mL"]) * 100),
                ("Free water", "mL/L", number(item["free_water_per_mL"]) * 1000),
                ("Na", "mmol/100 mL", mg_to_mmol("sodium", number(item["sodium_per_mL"]) * 100)),
                ("K", "mmol/100 mL", mg_to_mmol("potassium", number(item["potassium_per_mL"]) * 100)),
                ("Ca", "mmol/100 mL", mg_to_mmol("calcium", number(item["calcium_per_mL"]) * 100)),
                ("P", "mmol/100 mL", mg_to_mmol("phosphorus", number(item["phosphorus_per_mL"]) * 100)),
                ("Mg", "mmol/100 mL", mg_to_mmol("magnesium", number(item["magnesium_per_mL"]) * 100)),
                ("Fibre", "g/100 mL", number(item["fibre_per_mL"]) * 100),
            ]
            for row in (metrics[:3], metrics[3:6], metrics[6:]):
                columns = st.columns(3)
                for column, (label, unit, value) in zip(columns, row):
                    column.caption(label)
                    column.markdown(f"<small>{unit}</small><br><b>{value:.1f}</b>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


def render_modular_card(item: pd.Series) -> None:
    with st.container(border=True):
        details, action = st.columns([4, 1])
        with details:
            st.markdown(f"#### {item['name']}")
            st.caption(f"{item['brand']} · {item['basis_description']}")
        with action:
            if st.button("Remove", key=f"remove_modular_{item['id']}"):
                st.session_state.my_modulars = st.session_state.my_modulars.loc[
                    st.session_state.my_modulars["id"] != item["id"]
                ].reset_index(drop=True)
                st.rerun()


def render_reference_list(options: pd.DataFrame, saved_names: set[str], kind: str) -> None:
    """Render a compact, browsable reference list without displacing saved cards."""
    with st.container(height=360, border=False):
        if options.empty:
            st.caption(f"No matching {kind} in the reference library.")
        for _, item in options.iterrows():
            description = (f"{item['brand']} · {formula_type(str(item['name']))}"
                           if kind == "feed" else f"{item['brand']} · {item['basis_description']}")
            description_column, button_column = st.columns([5, 1])
            description_column.markdown(f"**{item['name']}**  \n{description}")
            if item["name"] in saved_names:
                button_column.button("Saved", key=f"saved_{kind}_{item['name']}", disabled=True)
            elif button_column.button(f"Add to My {'Formulary' if kind == 'feed' else 'Modulars'}", key=f"add_{kind}_{item['name']}"):
                if kind == "feed":
                    st.session_state.my_formulas = add_unique(st.session_state.my_formulas, pd.DataFrame([item]), "name")
                else:
                    st.session_state.my_modulars = add_unique(st.session_state.my_modulars, pd.DataFrame([item]), "id")
                st.rerun()
            st.divider()


def apply_wireframe_theme() -> None:
    """Load the wireframe CSS that complements the Streamlit theme config."""
    stylesheet = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{stylesheet}</style>", unsafe_allow_html=True)


def render_record_title(record_label: str) -> None:
    """Show the shared food motif with an ENFit tubing line icon."""
    icon_path = Path(__file__).parent / "assets" / "enteral-enfit-tubing.svg"
    icon = b64encode(icon_path.read_bytes()).decode("ascii")
    title = escape(record_label or "EN record")
    st.markdown(
        f'<h1 class="record-title"><span class="record-title-food">🥕🥦</span><span>{title}</span><img src="data:image/svg+xml;base64,{icon}" '
        'alt="Enteral tubing with purple ENFit connectors"><span>💧</span></h1>',
        unsafe_allow_html=True,
    )


def add_unique(frame: pd.DataFrame, additions: pd.DataFrame, key: str) -> pd.DataFrame:
    combined = pd.concat([frame, additions], ignore_index=True)
    return combined.drop_duplicates(subset=[key], keep="last").reset_index(drop=True)


def frequency_text(doses: float) -> str:
    names = {1: "once daily", 2: "BID", 3: "TID", 4: "QID"}
    return names.get(doses, f"{doses:g} times daily")


def render_case_record_actions() -> str:
    """Use the BTF-style top bar for a label and returning-user action."""
    if st.button("📋 Load example record", key="load_example_record"):
        load_example_record()
        st.rerun()
    label_column, upload_column = st.columns([3, 1], vertical_alignment="bottom")
    with label_column:
        label = st.text_input(
            "Patient / record label",
            key="case_record_label",
            help=(
                "This label appears in the page title and downloaded workbook. It does not affect calculations. "
                "Use a label permitted by your local privacy policy."
            ),
        )
    with upload_column:
        with st.popover("📂 Open a saved record", width="stretch"):
            uploaded = st.file_uploader("Open a saved record", type="xlsx", key="case_record_upload", label_visibility="collapsed")
            st.caption("Loading replaces the inputs and My Formulary snapshot currently on screen.")
            if uploaded is not None and st.button("Open it", key="load_case_record", use_container_width=True):
                try:
                    state, formulas, modulars = import_case_record_workbook(uploaded)
                    for key in list(st.session_state):
                        if key.startswith(("modular_units_", "modular_doses_", "modular_water_")):
                            del st.session_state[key]
                    for key, value in state.items():
                        st.session_state[key] = value
                    st.session_state.my_formulas = formulas
                    st.session_state.my_modulars = modulars
                    st.success("The saved record is now open.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    return label


def load_example_record() -> None:
    """Load a clearly-labelled demonstration without persisting any case data."""
    formulas, modulars = master_data()
    example_feed = formulas.loc[formulas["name"] == "Isosource Fibre 1.5"].iloc[[0]].copy()
    example_modular = modulars.loc[modulars["id"] == "nestle-beneprotein"].iloc[[0]].copy()

    for key in list(st.session_state):
        if key in CASE_STATE_KEYS or key.startswith(("modular_units_", "modular_doses_", "modular_water_")):
            del st.session_state[key]
    st.session_state.my_formulas = example_feed
    st.session_state.my_modulars = example_modular
    st.session_state.update({
        "case_record_label": "Example — inpatient EN review",
        "assessment_sex": "Female",
        "assessment_age": 67.0,
        "assessment_current_weight": 64.0,
        "assessment_usual_weight": 68.0,
        "assessment_height_unit": "m",
        "assessment_height_m": 1.65,
        "assessment_adjusted_weight_factor": 0.25,
        "assessment_estimated_weight": 62.0,
        "assessment_weight_choice": "Current body weight",
        "assessment_indirect_calorimetry": None,
        "assessment_mechanical_ventilation": False,
        "assessment_propofol_rate": 0.0,
        "assessment_energy_target": 1800.0,
        "assessment_protein_low_gkg": 1.2,
        "assessment_protein_high_gkg": 1.5,
        "assessment_protein_target": 85.0,
        "assessment_additional_loss_mode": "No additional loss",
        "assessment_water_low_mlkg": 25.0,
        "assessment_water_high_mlkg": 30.0,
        "assessment_water_target": 1900.0,
        "en_energy_target": 1800.0,
        "en_protein_target": 85.0,
        "en_water_target": 1900.0,
        "feed_candidates": ["Isosource Fibre 1.5"],
        "en_selected_formula": "Isosource Fibre 1.5",
        "en_schedule_type": "Continuous",
        "en_feeding_hours": 20.0,
        "en_achieved_delivery_pct": 100,
        "chosen_modulars": ["Beneprotein"],
        "modular_units_nestle-beneprotein": 1.0,
        "modular_doses_nestle-beneprotein": 2.0,
        "en_medication_flushes": 120.0,
        "en_patency_flushes": 180.0,
        "en_hydration_flushes": 6,
    })


def render_save_record() -> None:
    """Present the BTF-style save action at the end of the EN workflow."""
    st.subheader("Save this record")
    st.download_button(
        "💾 Download this record",
        data=export_case_record_workbook(
            st.session_state, st.session_state.my_formulas, st.session_state.my_modulars
        ),
        file_name="inpatient_en_case_record.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="One spreadsheet that does both jobs: reopen it here later, or file it as it is.",
        use_container_width=True,
    )
    st.caption("Download this record to your computer as a spreadsheet. Reopen it later with “Open a saved record” at the top of the page, or file it as it is.")


def render_footer() -> None:
    """Use the shared BTF-style clinical-tool footer with EN-specific sources."""
    st.divider()
    with st.container(key="pagefooter"):
        st.caption(
            "- ⚠️ **Under development.** A calculator for dietitians and the teams supporting adult inpatient "
            "enteral nutrition, and anyone is welcome to use it. It is built to inform clinical judgment, not "
            "to replace it. Please use with caution and check numbers before acting on them.\n"
            "- Using this tool creates no dietitian–client or other professional relationship, and it is no "
            "substitute for professional medical advice, diagnosis, or treatment. For anything about a specific "
            "person's care, consult their physician, registered dietitian, or other qualified health professional. "
            "Do not delay seeking that advice because of anything calculated here.\n"
            "- Commercial formula and modular values come from each manufacturer's published product information. "
            "Verify values against the current local product label and institutional formulary before clinical use.\n"
            "- Issues or feedback? Please contact the project maintainer through the repository where this tool is hosted."
        )


def show_formulary() -> None:
    master_formulas, master_modulars = master_data()
    st.title("Formulary")
    st.caption("Maintain the local products used in this workspace. Product values should be verified against current local labels before clinical use.")

    with st.expander("Import or export My Formulary", expanded=False):
        st.info("The uploaded workbook becomes the active My Formulary for this browser session. Its product values, rather than the supplied reference library, are used in EN-plan calculations.")
        upload = st.file_uploader("Import a .xlsx workbook", type="xlsx", key="formulary_upload")
        if upload is not None and st.button("Validate and import workbook"):
            try:
                formulas, modulars = import_formulary_workbook(upload)
                st.session_state.my_formulas = formulas
                st.session_state.my_modulars = modulars
                st.success("Imported the product worksheets. No patient information is imported or retained.")
            except ValueError as error:
                st.error(str(error))
        st.caption("To add or revise a local product, download the workbook, complete its full product row with source and verification details, then upload the reviewed workbook.")
        st.download_button(
            "Download My Formulary (.xlsx)",
            data=export_formulary_workbook(st.session_state.my_formulas, st.session_state.my_modulars),
            file_name="my_enteral_formulary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    feeds_tab, modulars_tab = st.tabs(["Feeds", "Modulars"])
    with feeds_tab:
        st.subheader("My Formulary")
        if st.session_state.my_formulas.empty:
            st.caption("Browse the reference library and add the feeds you keep in My Formulary.")
        else:
            # Product values must remain readable.  Each feed therefore uses
            # the full working column instead of competing with a second card.
            for _, item in st.session_state.my_formulas.iterrows():
                render_feed_card(item)

        with st.expander("Find a feed", expanded=False):
            search = st.text_input("Search formula name", key="feed_search")
            manufacturer = st.radio("Supplied reference library", ["All supplied reference feeds", "Nestlé", "Abbott"], horizontal=True, key="feed_reference_brand_filter")
            options = master_formulas if manufacturer == "All supplied reference feeds" else master_formulas[
                master_formulas["brand"].str.contains(manufacturer, case=False, na=False)
            ]
            if search.strip():
                options = options.loc[options["name"].str.contains(search.strip(), case=False, na=False)]
            render_reference_list(options, set(st.session_state.my_formulas["name"]), "feed")

    with modulars_tab:
        st.subheader("My Modulars")
        if st.session_state.my_modulars.empty:
            st.caption("Browse the reference library and add the modulars you keep in My Modulars.")
        else:
            first_column, second_column = st.columns(2, gap="medium")
            for index, (_, item) in enumerate(st.session_state.my_modulars.iterrows()):
                with first_column if index % 2 == 0 else second_column:
                    render_modular_card(item)
        with st.expander("Find a modular", expanded=False):
            search = st.text_input("Search modular name", key="modular_search")
            manufacturer = st.radio("Supplied reference library", ["All supplied reference modulars", "Nestlé", "Abbott"], horizontal=True, key="modular_reference_brand_filter")
            options = master_modulars if manufacturer == "All supplied reference modulars" else master_modulars[
                master_modulars["brand"].str.contains(manufacturer, case=False, na=False)
            ]
            if search.strip():
                options = options.loc[options["name"].str.contains(search.strip(), case=False, na=False)]
            render_reference_list(options, set(st.session_state.my_modulars["name"]), "modular")


def show_assessment() -> None:
    st.title("Assessment")
    st.caption("Set the working targets that carry forward to the EN plan. A blank means the value has not been entered; enter 0 only when zero is the known clinical value.")
    with st.container(border=True):
        st.subheader("Measurements and weight history")
        st.caption("Enter current measurements first, then choose the calculation weight used throughout this assessment.")
        measure = st.columns(5)
        sex = measure[0].selectbox("Sex used by equations", ["", "Female", "Male"], key="assessment_sex", format_func=lambda value: value or "Select…")
        age = measure[1].number_input("Age (years)", min_value=18.0, max_value=120.0, value=None, key="assessment_age", placeholder="Enter age")
        current_weight = measure[2].number_input("Current body weight (kg)", min_value=1.0, value=None, key="assessment_current_weight", placeholder="Enter weight")
        usual_weight = measure[3].number_input("Usual body weight (kg)", min_value=1.0, value=None, key="assessment_usual_weight", placeholder="Optional")
        unit = measure[4].selectbox("Height entry", ["", "m", "ft/in"], key="assessment_height_unit", format_func=lambda value: value or "Select…")
        height_cm: float | None = None
        if unit == "m":
            height_m = measure[4].number_input("Height (m)", min_value=0.5, max_value=2.5, value=None, step=0.01, key="assessment_height_m", placeholder="Enter height")
            if height_m is not None:
                height_cm = height_to_cm("m", metres=height_m)
        else:
            if unit == "ft/in":
                feet, inches = measure[4].columns(2)
                height_feet = feet.number_input("Feet", min_value=2, max_value=8, value=None, key="assessment_height_feet", placeholder="Feet")
                height_inches = inches.number_input("Inches", min_value=0.0, max_value=11.9, value=None, key="assessment_height_inches", placeholder="Inches")
                if height_feet is not None and height_inches is not None:
                    height_cm = height_to_cm("ft_in", feet=int(height_feet), inches=height_inches)

        ready_for_weight = bool(sex and current_weight is not None and height_cm is not None)
        if ready_for_weight:
            bmi = current_weight / (height_cm / 100) ** 2
            stats = st.columns(3)
            stats[0].metric("Current BMI", f"{bmi:.1f} kg/m²")
            if usual_weight is None:
                stats[1].metric("Weight change", "Not entered")
                stats[2].metric("Weight loss", "Not entered")
            else:
                change = current_weight - usual_weight
                stats[1].metric("Weight change", f"{change:+.1f} kg")
                stats[2].metric("Weight loss", f"{max((usual_weight - current_weight) / usual_weight * 100, 0):.1f}%")
            ibw = hamwi_ibw_kg(sex, height_cm)
        else:
            st.info("Enter sex, current weight, and height before the weight-derived calculations are shown.")
            ibw = None

        correction, estimated = st.columns(2)
        correction_factor = correction.number_input("Adjusted-weight correction factor", min_value=0.0, max_value=1.0, value=None, step=0.05, key="assessment_adjusted_weight_factor", placeholder="Optional")
        estimated_weight = estimated.number_input("Estimated dry / clinician-selected weight (kg)", min_value=1.0, value=None, key="assessment_estimated_weight", placeholder="Optional")
        adjusted_weight = (adjusted_body_weight_kg(current_weight, ibw, correction_factor)
                           if ready_for_weight and correction_factor is not None else None)
        weight_options = {
            "Current body weight": current_weight,
            "Hamwi IBW": ibw,
            "Adjusted body weight": adjusted_weight,
            "Estimated dry / clinician-selected weight": estimated_weight,
        }
        available_choices = [name for name, value in weight_options.items() if value is not None]
        weight_choice = st.selectbox("Calculation weight", [""] + available_choices, key="assessment_weight_choice", format_func=lambda value: value or "Select…")
        calculation_weight = weight_options.get(weight_choice)
        if calculation_weight is not None:
            st.caption(f"Calculation weight used: {calculation_weight:.1f} kg")

    ready_for_equations = bool(ready_for_weight and calculation_weight is not None and age is not None)
    mifflin = mifflin_st_jeor_kcal(sex, calculation_weight, height_cm, age) if ready_for_equations else None
    harris = harris_benedict_kcal(sex, calculation_weight, height_cm, age) if ready_for_equations else None
    propofol = propofol_intake(0)
    with st.container(border=True):
        st.subheader("Energy assessment")
        st.caption("The selected calculation weight is used by every equation below. The RD chooses the final energy target.")
        energy_columns = st.columns([1, 1, 1.2])
        energy_columns[0].metric("Mifflin–St Jeor", f"{mifflin:.0f} kcal/day" if mifflin is not None else "Not calculated")
        energy_columns[1].metric("Harris–Benedict", f"{harris:.0f} kcal/day" if harris is not None else "Not calculated")
        measured = energy_columns[2].number_input("Indirect calorimetry (kcal/day)", min_value=0.0, value=None, key="assessment_indirect_calorimetry", placeholder="Optional")
        if ready_for_equations:
            with st.expander("Energy equations", expanded=False):
                st.dataframe(pd.DataFrame([
                    {"Equation": "Mifflin–St Jeor", "Values used": f"{sex}; {calculation_weight:.1f} kg; {height_cm:.1f} cm; {age:.0f} y", "Resting energy (kcal/day)": mifflin},
                    {"Equation": "Harris–Benedict", "Values used": f"{sex}; {calculation_weight:.1f} kg; {height_cm:.1f} cm; {age:.0f} y", "Resting energy (kcal/day)": harris},
                ]).round(0), hide_index=True, use_container_width=True)
        with st.expander("ICU additions", expanded=False):
            ventilation, propofol_column = st.columns(2)
            is_ventilated = ventilation.checkbox("Mechanical ventilation", key="assessment_mechanical_ventilation")
            if is_ventilated and ready_for_equations:
                temperature = ventilation.number_input("Maximum temperature (°C)", min_value=30.0, max_value=45.0, value=None, key="assessment_temperature", placeholder="Enter temperature")
                minute_ventilation = ventilation.number_input("Minute ventilation (L/min)", min_value=0.0, value=None, key="assessment_minute_ventilation", placeholder="Enter ventilation")
                if temperature is not None and minute_ventilation is not None:
                    ventilation.metric("Penn State 2003b", f"{penn_state_2003b_kcal(mifflin, temperature, minute_ventilation):.0f} kcal/day")
            elif is_ventilated:
                ventilation.caption("Enter the measurement fields before calculating Penn State 2003b.")
            propofol_rate = propofol_column.number_input("Active propofol rate (mL/hour; 0 if none)", min_value=0.0, value=None, step=1.0, key="assessment_propofol_rate", placeholder="Enter 0 if none")
            propofol = propofol_intake(number(propofol_rate))
            propofol_column.metric("Propofol energy", f"{propofol['kcal']:.0f} kcal/day" if propofol_rate is not None else "Not entered")
            if propofol_rate is not None:
                propofol_column.caption(f"Propofol fat: {propofol['fat_g']:.1f} g/day")
        target_energy = st.number_input("Energy target for EN plan (kcal/day)", min_value=0.0, value=None, key="assessment_energy_target", placeholder="Enter target")
        if measured is not None:
            st.caption(f"Recorded indirect calorimetry: {measured:.0f} kcal/day. It informs but does not override the target.")

    with st.container(border=True):
        st.subheader("Protein and water targets")
        st.caption("The worked ranges provide context. No automatic adjustment is applied to either entered target.")
        protein_panel, water_panel = st.columns(2, gap="large")
        with protein_panel:
            st.markdown("#### Protein target")
            protein_low, protein_high = st.columns(2)
            low_gkg = protein_low.number_input("Low range (g/kg)", min_value=0.0, value=None, step=0.1, key="assessment_protein_low_gkg", placeholder="Optional")
            high_gkg = protein_high.number_input("High range (g/kg)", min_value=0.0, value=None, step=0.1, key="assessment_protein_high_gkg", placeholder="Optional")
            if calculation_weight is not None and low_gkg is not None and high_gkg is not None:
                st.caption(f"Worked range: {low_gkg * calculation_weight:.0f}–{high_gkg * calculation_weight:.0f} g/day")
            target_protein = st.number_input("Protein target (g/day)", min_value=0.0, value=None, key="assessment_protein_target", placeholder="Enter target")
            with st.expander("Additional protein losses", expanded=True):
                mode = st.radio("Additional-loss detail", ["No additional loss", "Single manual addition", "Open-abdomen exudate", "Detailed surgical / critical-care addition"], key="assessment_additional_loss_mode")
                exudate_loss = other_loss = 0.0
                if mode in {"Open-abdomen exudate", "Detailed surgical / critical-care addition"}:
                    volume, factor = st.columns(2)
                    exudate_ml = volume.number_input("Exudate volume (mL/day)", min_value=0.0, value=None, key="assessment_exudate_ml", placeholder="Enter volume")
                    loss_factor = factor.number_input("Protein-loss factor (g/L), entered by RD", min_value=0.0, value=None, key="assessment_protein_loss_factor", placeholder="Enter factor")
                    exudate_loss = open_abdomen_protein_loss_g(number(exudate_ml), number(loss_factor))
                if mode in {"Single manual addition", "Detailed surgical / critical-care addition"}:
                    other_loss = st.number_input("Other quantified protein loss (g/day)", min_value=0.0, value=None, key="assessment_other_protein_loss", placeholder="Enter loss")
                st.caption(f"Calculated additional protein loss: {exudate_loss + number(other_loss):.1f} g/day. Consider it when setting the target; it does not change the target automatically.")
        with water_panel:
            st.markdown("#### Water target")
            water_low, water_high = st.columns(2)
            low_mlkg = water_low.number_input("Low range (mL/kg)", min_value=0.0, value=None, step=1.0, key="assessment_water_low_mlkg", placeholder="Optional")
            high_mlkg = water_high.number_input("High range (mL/kg)", min_value=0.0, value=None, step=1.0, key="assessment_water_high_mlkg", placeholder="Optional")
            if calculation_weight is not None and low_mlkg is not None and high_mlkg is not None:
                st.caption(f"Worked range: {low_mlkg * calculation_weight:.0f}–{high_mlkg * calculation_weight:.0f} mL/day")
            target_water = st.number_input("Water target (mL/day)", min_value=0.0, value=None, key="assessment_water_target", placeholder="Enter target")

    with st.container(border=True):
        st.subheader("Targets for EN plan")
        st.caption("They remain editable when the formula and delivery plan are chosen.")
        handoff_metrics = st.columns(4)
        handoff_metrics[0].metric("Energy target", f"{target_energy:.0f} kcal/day" if target_energy is not None else "Not entered")
        handoff_metrics[1].metric("Protein target", f"{target_protein:.0f} g/day" if target_protein is not None else "Not entered")
        handoff_metrics[2].metric("Water target", f"{target_water:.0f} mL/day" if target_water is not None else "Not entered")
        handoff_metrics[3].metric("Non-enteral energy", f"{propofol['kcal']:.0f} kcal/day" if st.session_state.get("assessment_propofol_rate") is not None else "Not entered")

    st.session_state.assessment_handoff = {
        "energy_target": target_energy, "protein_target": target_protein, "water_target": target_water,
        "propofol": propofol, "calculation_weight": calculation_weight,
    }


def mmol_from_delivery(delivery: dict[str, float], nutrient: str) -> float:
    return mg_to_mmol(nutrient, delivery.get(f"{nutrient}_mg", 0))


def show_en_plan() -> None:
    st.title("EN plan")
    saved_feeds = st.session_state.my_formulas
    saved_modulars = st.session_state.my_modulars
    handoff = st.session_state.get("assessment_handoff", {
        "energy_target": st.session_state.get("assessment_energy_target"),
        "protein_target": st.session_state.get("assessment_protein_target"),
        "water_target": st.session_state.get("assessment_water_target"),
        "propofol": propofol_intake(0),
    })
    if saved_feeds.empty:
        st.info("Add at least one product on the Formulary page before creating an EN plan.")
        return

    st.caption("Review the proposed arithmetic and choose the clinically appropriate formula and final order independently.")
    assessment_energy = handoff.get("energy_target")
    default_en_target = (max(0.0, number(assessment_energy) - number(handoff["propofol"].get("kcal", 0)))
                         if assessment_energy is not None else None)
    if "en_energy_target" not in st.session_state and default_en_target is not None:
        st.session_state.en_energy_target = default_en_target
    if "en_protein_target" not in st.session_state and handoff.get("protein_target") is not None:
        st.session_state.en_protein_target = handoff["protein_target"]
    if "en_water_target" not in st.session_state and handoff.get("water_target") is not None:
        st.session_state.en_water_target = handoff["water_target"]
    with st.container(border=True):
        st.subheader("Assessment reference and working targets")
        top = st.columns(3)
        en_energy_target = top[0].number_input("EN energy target (kcal/day)", min_value=0.0, value=None, key="en_energy_target", placeholder="Enter target")
        en_protein_target = top[1].number_input("Protein target (g/day)", min_value=0.0, value=None, key="en_protein_target", placeholder="Enter target")
        en_water_target = top[2].number_input("Water target (mL/day)", min_value=0.0, value=None, key="en_water_target", placeholder="Enter target")
        if number(handoff["propofol"].get("kcal", 0)):
            st.caption(f"The initial EN-energy value deducts {handoff['propofol']['kcal']:.0f} kcal/day from active propofol. It remains editable.")

    if en_energy_target is None or en_protein_target is None or en_water_target is None:
        st.info("Enter working energy, protein, and water targets before creating an EN delivery plan.")
        return

    with st.container(border=True):
        st.subheader("Feeds to compare")
        st.caption("Choose up to nine clinically plausible options from My Formulary.")
        candidates = st.multiselect("Formula candidates", saved_feeds["name"].tolist(), max_selections=9, key="feed_candidates")
    if not candidates:
        st.info("Select one or more saved feeds to compare their planned delivery.")
        return
    candidate_frame = saved_feeds.loc[saved_feeds["name"].isin(candidates)]
    with st.container(border=True):
        st.subheader("Selected formula and delivery")
        selected_name = st.selectbox("Formula selected for planned delivery", candidate_frame["name"].tolist(), key="en_selected_formula")
        schedule_a, schedule_b, schedule_c = st.columns(3)
        schedule_type = schedule_a.radio("Schedule", ["Continuous", "Intermittent"], horizontal=True, key="en_schedule_type")
        if "en_feeding_hours" not in st.session_state:
            st.session_state.en_feeding_hours = 20.0
        hours = schedule_b.number_input("Feeding hours/day", min_value=1.0, max_value=24.0, step=1.0, key="en_feeding_hours")
        feeds_per_day = 1
        if schedule_type == "Intermittent":
            if "en_feeds_per_day" not in st.session_state:
                st.session_state.en_feeds_per_day = 4
            feeds_per_day = int(schedule_c.number_input("Feeds/day", min_value=1, max_value=12, key="en_feeds_per_day"))
        if "en_achieved_delivery_pct" not in st.session_state:
            st.session_state.en_achieved_delivery_pct = 100
        achieved = st.slider("If delivery achieved (% planned EN)", min_value=0, max_value=100, step=5,
                             help="This is a reference view, not a second proposed order.", key="en_achieved_delivery_pct")
    formula = candidate_frame.loc[candidate_frame["name"] == selected_name].iloc[0].to_dict()
    planned_delivery = feed_delivery(formula, en_energy_target, hours, 100)
    displayed_delivery = feed_delivery(formula, en_energy_target, hours, achieved)

    comparison_rows = []
    for _, candidate in candidate_frame.iterrows():
        delivery = feed_delivery(candidate.to_dict(), en_energy_target, hours, 100)
        comparison_rows.append({"Feed": candidate["name"], "Volume (mL/day)": delivery["planned_volume_ml"],
                                "Rate (mL/hour)": delivery["rate_ml_hr"], "Energy (kcal/day)": delivery["energy_kcal"],
                                "Protein (g/day)": delivery["protein_g"], "Free water (mL/day)": delivery["free_water_ml"],
                                "Na (mmol/day)": mmol_from_delivery(delivery, "sodium"),
                                "K (mmol/day)": mmol_from_delivery(delivery, "potassium")})
    with st.container(key="fullbleed_formula_comparison", border=True):
        st.subheader("Formula comparison")
        st.caption("Selected feeds at full planned EN delivery.")
        st.dataframe(pd.DataFrame(comparison_rows).round(1), use_container_width=True, hide_index=True)

    schedule_description = (f"{planned_delivery['rate_ml_hr']:.0f} mL/hour for {hours:g} hours daily"
                            if schedule_type == "Continuous" else
                            f"{planned_delivery['planned_volume_ml'] / feeds_per_day:.0f} mL per feed, {feeds_per_day} feeds daily")
    selected_display = pd.DataFrame([
        {"Delivery view": "Full planned EN", "Volume (mL/day)": planned_delivery["delivered_volume_ml"],
         "Energy (kcal/day)": planned_delivery["energy_kcal"], "Protein (g/day)": planned_delivery["protein_g"],
         "Free water (mL/day)": planned_delivery["free_water_ml"]},
        {"Delivery view": f"Alternate achieved delivery ({achieved}%)", "Volume (mL/day)": displayed_delivery["delivered_volume_ml"],
         "Energy (kcal/day)": displayed_delivery["energy_kcal"], "Protein (g/day)": displayed_delivery["protein_g"],
         "Free water (mL/day)": displayed_delivery["free_water_ml"]},
    ])
    with st.container(border=True):
        st.subheader(f"Selected formula: {formula['name']}")
        st.caption(f"Full planned EN schedule: {schedule_description}.")
        st.dataframe(selected_display.round(1), hide_index=True, use_container_width=True)

    protein_gap = en_protein_target - displayed_delivery["protein_g"]
    with st.container(border=True):
        st.subheader("Protein check")
        check = st.columns(3)
        check[0].metric("Protein target", f"{en_protein_target:.1f} g/day")
        check[1].metric("Protein from selected EN", f"{displayed_delivery['protein_g']:.1f} g/day")
        check[2].metric("Still to cover", f"{max(protein_gap, 0):.1f} g/day")

    st.subheader("Modulars")
    modular_orders: list[dict[str, float]] = []
    if saved_modulars.empty:
        st.caption("No saved modulars. Add products on the Formulary page if needed.")
    else:
        chosen_modulars = st.multiselect("Modular orders (up to 6)", saved_modulars["name"].tolist(), max_selections=6, key="chosen_modulars")
        for index, modular_name in enumerate(chosen_modulars):
            product = saved_modulars.loc[saved_modulars["name"] == modular_name].iloc[0].to_dict()
            st.markdown(f"**{modular_name}** — {product['basis_description']}")
            a, b, c = st.columns(3)
            product_key = str(product["id"])
            units_key = f"modular_units_{product_key}"
            doses_key = f"modular_doses_{product_key}"
            if units_key not in st.session_state:
                st.session_state[units_key] = 1.0
            if doses_key not in st.session_state:
                st.session_state[doses_key] = 1.0
            units = a.number_input(f"{product['dose_unit']} per dose", min_value=0.0, step=0.5, key=units_key)
            doses = b.number_input("Doses per day", min_value=0.0, step=1.0, key=doses_key)
            preparation = 0.0
            rule = str(product.get("preparation_water_rule", "none"))
            if rule != "none":
                default = number(product.get("default_preparation_water_ml_per_dose", 0))
                preparation_key = f"modular_water_{product_key}"
                if preparation_key not in st.session_state:
                    st.session_state[preparation_key] = default
                preparation = c.number_input("Preparation water (mL/dose)", min_value=0.0, step=5.0, key=preparation_key)
            else:
                c.caption("No preparation water is added for this product.")
            modular_orders.append(modular_delivery(product, units, doses, preparation))
    modular_totals = total_modular_delivery(modular_orders)
    with st.container(border=True):
        st.subheader("Water target and hydration flushes")
        water_a, water_b, water_c = st.columns(3)
        if "en_medication_flushes" not in st.session_state:
            st.session_state.en_medication_flushes = 0.0
        if "en_patency_flushes" not in st.session_state:
            st.session_state.en_patency_flushes = 0.0
        if "en_hydration_flushes" not in st.session_state:
            st.session_state.en_hydration_flushes = 6
        medication = water_a.number_input("Medication flushes (mL/day)", min_value=0.0, step=10.0, key="en_medication_flushes")
        patency = water_b.number_input("Patency flushes (mL/day)", min_value=0.0, step=10.0,
                                       help="Reference: ASPEN minimum 30 mL q4h for continuous adult EN.", key="en_patency_flushes")
        flushes = int(water_c.number_input("Hydration flushes/day", min_value=1, max_value=24, key="en_hydration_flushes"))
        hydration = water_plan(en_water_target, displayed_delivery["free_water_ml"],
                               modular_totals["free_water_ml"], modular_totals["preparation_water_ml"],
                               medication, patency, flushes)
        st.info(f"Hydration flush proposal: {hydration['hydration_flush_each_ml']:.0f} mL, {flushes} times daily ({hydration['hydration_flush_total_ml']:.0f} mL/day).")

    propofol = handoff["propofol"]
    source_rows = [
        {"Source": formula["name"], "Energy (kcal)": displayed_delivery["energy_kcal"], "Protein (g)": displayed_delivery["protein_g"], "Carbohydrate (g)": displayed_delivery["carbohydrate_g"], "Fat (g)": displayed_delivery["fat_g"], "Free water (mL)": displayed_delivery["free_water_ml"], "Water flushes (mL)": 0},
        {"Source": "Modulars", "Energy (kcal)": modular_totals["energy_kcal"], "Protein (g)": modular_totals["protein_g"], "Carbohydrate (g)": modular_totals["carbohydrate_g"], "Fat (g)": modular_totals["fat_g"], "Free water (mL)": modular_totals["free_water_ml"], "Water flushes (mL)": 0},
        {"Source": "Propofol", "Energy (kcal)": propofol["kcal"], "Protein (g)": 0, "Carbohydrate (g)": 0, "Fat (g)": propofol["fat_g"], "Free water (mL)": 0, "Water flushes (mL)": 0},
        {"Source": "Water flushes", "Energy (kcal)": 0, "Protein (g)": 0, "Carbohydrate (g)": 0, "Fat (g)": 0, "Free water (mL)": 0, "Water flushes (mL)": hydration["water_flushes_total_ml"]},
    ]
    source_frame = pd.DataFrame(source_rows)
    total = {"Source": "Total"}
    for column in source_frame.columns[1:]:
        total[column] = source_frame[column].sum()
    with st.container(key="fullbleed_daily_intake", border=True):
        st.subheader("Planned daily intake")
        st.caption("A numeric source-and-total view. Select the alternate delivery percentage above to inspect the achieved-delivery reference view.")
        st.dataframe(pd.concat([source_frame, pd.DataFrame([total])], ignore_index=True).round(1), hide_index=True, use_container_width=True)

    modular_note_parts = []
    for name in st.session_state.get("chosen_modulars", []):
        product = saved_modulars.loc[saved_modulars["name"] == name].iloc[0]
        product_key = str(product["id"])
        units = st.session_state.get(f"modular_units_{product_key}", 1)
        doses = st.session_state.get(f"modular_doses_{product_key}", 1)
        modular_note_parts.append(
            f"{name}: {units:g} {product['dose_unit']} {frequency_text(doses)}"
        )
    modular_note = "; ".join(modular_note_parts) or "No modulars ordered"
    note = (
        f"EN: {formula['name']} at {schedule_description}.\n\n"
        f"Modulars: {modular_note}.\n\n"
        f"Hydration flushes: {hydration['hydration_flush_each_ml']:.0f} mL {flushes} times daily.\n\n"
        f"Planned daily intake ({'alternate delivery view' if achieved != 100 else 'full planned EN'}): "
        f"{total['Energy (kcal)']:.0f} kcal, {total['Protein (g)']:.1f} g protein "
        f"({displayed_delivery['protein_g']:.1f} g from EN and {modular_totals['protein_g']:.1f} g from modulars), "
        f"{total['Carbohydrate (g)']:.1f} g carbohydrate, {total['Fat (g)']:.1f} g fat, and "
        f"{total['Free water (mL)']:.0f} mL free water plus {total['Water flushes (mL)']:.0f} mL water flushes."
    )
    with st.container(border=True):
        st.subheader("Chart note")
        st.caption("Read-only review and copy aid; local documentation policy takes precedence.")
        st.code(note, language=None)
    render_save_record()


def main() -> None:
    initialise_state()
    apply_wireframe_theme()
    record_label = render_case_record_actions()
    render_record_title(record_label)
    st.caption("Adult Inpatient Enteral Nutrition Calculator")
    formulary_tab, assessment_tab, plan_tab = st.tabs(["Formulary", "Assessment", "EN plan"])
    with formulary_tab:
        show_formulary()
    with assessment_tab:
        show_assessment()
    with plan_tab:
        show_en_plan()
    render_footer()


if __name__ == "__main__":
    main()
