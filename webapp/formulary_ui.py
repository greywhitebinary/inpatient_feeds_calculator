"""Formulary and modular library interface."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from data import export_formulary_workbook, import_formulary_workbook
from session_state import master_data
from ui_common import number, render_formulary_table, render_report_table

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


def render_reference_list(options: pd.DataFrame, saved_names: set[str], kind: str) -> None:
    """Render a compact, browsable reference list without displacing saved cards."""
    with st.container(height=360, border=False):
        if options.empty:
            st.caption(f"No matching {kind} in the reference library.")
        for row_position, (_, item) in enumerate(options.iterrows()):
            description = (f"{item['brand']} · {formula_type(str(item['name']))}"
                           if kind == "feed" else f"{item['brand']} · {item['basis_description']}")
            with st.container(key=f"reference_row_{kind}_{row_position}"):
                description_column, button_column = st.columns([3, 2], vertical_alignment="center")
                description_column.markdown(
                    '<div class="reference-product-text">'
                    f'<strong>{escape(str(item["name"]))}</strong>'
                    f'<span>{escape(description)}</span></div>',
                    unsafe_allow_html=True,
                )
                if item["name"] in saved_names:
                    button_column.button(
                        "Saved", key=f"saved_{kind}_{item['name']}",
                        disabled=True, width="content",
                    )
                else:
                    button_column.button(
                        f"Add to My {'Formulary' if kind == 'feed' else 'Modulars'}",
                        key=f"add_{kind}_{item['name']}",
                        width="content",
                        on_click=add_reference_product,
                        args=(kind, item.to_dict()),
                    )


def add_unique(frame: pd.DataFrame, additions: pd.DataFrame, key: str) -> pd.DataFrame:
    combined = pd.concat([frame, additions], ignore_index=True)
    return combined.drop_duplicates(subset=[key], keep="last").reset_index(drop=True)


def add_reference_product(kind: str, item: dict[str, object]) -> None:
    """Add a product before Streamlit performs the full page render."""
    addition = pd.DataFrame([item])
    if kind == "feed":
        st.session_state.my_formulas = add_unique(
            st.session_state.my_formulas, addition, "name"
        )
    else:
        st.session_state.my_modulars = add_unique(
            st.session_state.my_modulars, addition, "id"
        )


def remove_selected_products(kind: str) -> None:
    """Remove products while retaining calculator state unrelated to them."""
    if kind == "feed":
        removed = set(st.session_state.get("remove_feeds", []))
        st.session_state.my_formulas = st.session_state.my_formulas.loc[
            ~st.session_state.my_formulas["name"].isin(removed)
        ].reset_index(drop=True)
        for candidates_key in ("feed_candidates", "icu_feed_candidates"):
            if candidates_key in st.session_state:
                st.session_state[candidates_key] = [
                    name for name in st.session_state[candidates_key]
                    if name not in removed
                ]
        st.session_state.remove_feeds = []
    else:
        removed = set(st.session_state.get("remove_modulars", []))
        st.session_state.my_modulars = st.session_state.my_modulars.loc[
            ~st.session_state.my_modulars["name"].isin(removed)
        ].reset_index(drop=True)
        st.session_state.remove_modulars = []


def show_formulary() -> None:
    master_formulas, master_modulars = master_data()
    st.caption("Verify product values against current local labels before use.")

    with st.expander("Import or export My Formulary", expanded=False):
        st.caption(
            "Uploading replaces My Formulary for this session. "
            "Calculations use the uploaded values."
        )
        upload = st.file_uploader("Import a .xlsx workbook", type="xlsx", key="formulary_upload")
        if upload is not None and st.button("Validate and import workbook"):
            try:
                formulas, modulars = import_formulary_workbook(upload)
                st.session_state.my_formulas = formulas
                st.session_state.my_modulars = modulars
                st.success("Imported the product worksheets. No patient information is imported or retained.")
            except ValueError as error:
                st.error(str(error))
        st.caption("To add or edit a product, update the downloaded workbook and upload it here.")
        st.download_button(
            "Download My Formulary (.xlsx)",
            data=export_formulary_workbook(st.session_state.my_formulas, st.session_state.my_modulars),
            file_name="my_enteral_formulary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    feed_heading, feed_actions = st.columns([4, 1], vertical_alignment="bottom")
    feed_heading.subheader("My Formulary")
    if not st.session_state.my_formulas.empty:
        with feed_actions.popover("Remove feeds", width="stretch"):
            remove = st.multiselect(
                "Feeds to remove",
                st.session_state.my_formulas["name"].tolist(),
                key="remove_feeds",
            )
            st.button(
                "Remove selected feeds",
                key="remove_selected_feeds",
                disabled=not remove,
                on_click=remove_selected_products,
                args=("feed",),
                use_container_width=True,
            )
    if not st.session_state.my_formulas.empty:
        # BTF uses readable report rows for dense nutrition information.  The
        # formulary therefore uses one full-width row per feed, rather than a
        # large card with decorative empty space.
        with st.container(key="fullbleed_my_formulary"):
            render_formulary_table(st.session_state.my_formulas)

    with st.expander("Find a feed", expanded=False):
        search = st.text_input("Search formula name", key="feed_search")
        manufacturer = st.radio("Supplied reference library", ["All supplied reference feeds", "Nestlé", "Abbott"], horizontal=True, key="feed_reference_brand_filter")
        options = master_formulas if manufacturer == "All supplied reference feeds" else master_formulas[
            master_formulas["brand"].str.contains(manufacturer, case=False, na=False)
        ]
        if search.strip():
            options = options.loc[options["name"].str.contains(search.strip(), case=False, na=False)]
        render_reference_list(options, set(st.session_state.my_formulas["name"]), "feed")

    st.divider()
    modular_heading, modular_actions = st.columns([4, 1], vertical_alignment="bottom")
    modular_heading.subheader("My Modulars")
    if not st.session_state.my_modulars.empty:
        with modular_actions.popover("Remove modulars", width="stretch"):
            remove = st.multiselect(
                "Modulars to remove",
                st.session_state.my_modulars["name"].tolist(),
                key="remove_modulars",
            )
            st.button(
                "Remove selected modulars",
                key="remove_selected_modulars",
                disabled=not remove,
                on_click=remove_selected_products,
                args=("modular",),
                use_container_width=True,
            )
    if not st.session_state.my_modulars.empty:
        render_report_table(
            st.session_state.my_modulars[["name", "basis_description"]].rename(columns={
                "name": "Product",
                "basis_description": "Description",
            }).assign(**{
                "Labelled serving": st.session_state.my_modulars.apply(
                    lambda item: f"{number(item['basis_amount']):g} {item['dose_unit']}", axis=1
                )
            })
        )
    with st.expander("Find a modular", expanded=False):
        search = st.text_input("Search modular name", key="modular_search")
        options = master_modulars
        if search.strip():
            options = options.loc[options["name"].str.contains(search.strip(), case=False, na=False)]
        render_reference_list(options, set(st.session_state.my_modulars["name"]), "modular")
