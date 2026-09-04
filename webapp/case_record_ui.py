"""Saved-record actions and persistent page footer."""

from __future__ import annotations

import streamlit as st

from case_io import export_case_record_workbook
from session_state import load_example_record, open_uploaded_case_record
from ui_common import render_alert, render_box_heading

def render_case_record_actions() -> str:
    """Use the BTF-style top bar for a label and returning-user action."""
    if st.button("📋 Load example record", key="load_example_record"):
        load_example_record()
        st.rerun()
    label_column, upload_column = st.columns([3, 1], vertical_alignment="bottom")
    with label_column:
        compact_label_column, _label_spacer = st.columns([2, 1])
        with compact_label_column:
            label = st.text_input(
                "Record label",
                key="case_record_label",
                help=(
                    "Used in the page title and downloaded workbook. Avoid patient identifiers; "
                    "use a local record label that follows your privacy policy."
                ),
            )
    with upload_column:
        with st.popover("📂 Open a saved record", width="stretch"):
            uploaded = st.file_uploader("Open a saved record", type="xlsx", key="case_record_upload", label_visibility="collapsed")
            st.caption("Opening a file replaces the current record and product lists.")
            st.button(
                "Open it",
                key="load_case_record",
                use_container_width=True,
                disabled=uploaded is None,
                on_click=open_uploaded_case_record,
                args=(uploaded,),
            )
    notice = st.session_state.pop("_case_record_notice", None)
    if notice is not None:
        level, message = notice
        render_alert("success" if level == "success" else "error", message)
    return label


def render_save_record(key_suffix: str) -> None:
    """Present the BTF-style save action at the end of the EN workflow."""
    render_box_heading("Save this record")
    st.download_button(
        "💾 Download this record",
        data=export_case_record_workbook(
            st.session_state,
            st.session_state.my_formulas,
            st.session_state.my_modulars,
            st.session_state.my_ons,
        ),
        file_name="inpatient_en_case_record.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"download_case_record_{key_suffix}",
    )
    st.caption(
        "Download the calculator inputs and product snapshot as a spreadsheet. The editable "
        "chart-note draft is not included. Reopen the file later with “Open a saved record”."
    )


def render_footer() -> None:
    """Use the shared BTF-style clinical-tool footer with EN-specific sources."""
    st.divider()
    with st.container(key="pagefooter"):
        st.caption(
            "- ⚠️ **Review calculations before clinical use.**\n"
            "- **Related tool:** [BTFCalc](https://btfcalc.feedformflow.ca) — blenderized tube feeding calculator.\n"
            "- **Display tip:** Adjust Zoom in your browser menu, or use `Ctrl +/−` on Windows and "
            "`⌘ +/−` on Mac. You can also pinch on touchscreens and trackpads.\n"
            "- Issues or feedback? Please [open an issue at GitHub](https://github.com/greywhitebinary/inpatient_feeds_calculator/issues), "
            "or [find me on LinkedIn](https://www.linkedin.com/in/hui-jun-gail-chew/)."
        )
        with st.expander("About this calculator"):
            st.caption(
                "ENCalc is designed for dietitians and teams supporting adult inpatient enteral nutrition. "
                "It supports, but does not replace, clinical judgement.\n\n"
                "This tool does not create a dietitian–client or other professional relationship and is not a "
                "substitute for professional medical advice, diagnosis, or treatment. For advice about an "
                "individual's care, consult their physician, registered dietitian, or other qualified health "
                "professional. Do not delay seeking that advice because of a result from this calculator.\n\n"
                "Formula, modular, and ONS values come from manufacturers’ Canadian product information. Verify them "
                "against current local product labels and institutional formularies before clinical use."
            )
