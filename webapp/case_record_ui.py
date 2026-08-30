"""Saved-record actions and persistent page footer."""

from __future__ import annotations

import streamlit as st

from case_io import export_case_record_workbook
from session_state import load_example_record, open_uploaded_case_record
from ui_common import render_box_heading

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
                "Used in the page title and downloaded workbook. "
                "Follow local privacy policy."
            ),
        )
    with upload_column:
        with st.popover("📂 Open a saved record", width="stretch"):
            uploaded = st.file_uploader("Open a saved record", type="xlsx", key="case_record_upload", label_visibility="collapsed")
            st.caption("Opening a file replaces the current record and My Formulary.")
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
        if level == "success":
            st.success(message)
        else:
            st.error(message)
    return label


def render_save_record(key_suffix: str) -> None:
    """Present the BTF-style save action at the end of the EN workflow."""
    render_box_heading("Save this record")
    st.download_button(
        "💾 Download this record",
        data=export_case_record_workbook(
            st.session_state, st.session_state.my_formulas, st.session_state.my_modulars
        ),
        file_name="inpatient_en_case_record.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"download_case_record_{key_suffix}",
    )
    st.caption("Download this record as a spreadsheet. Reopen it later with “Open a saved record”.")


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
            "- **Display tip:** Adjust Zoom in your browser menu, or use `Ctrl +/−` on Windows and "
            "`⌘ +/−` on Mac. You can also pinch on touchscreens and trackpads.\n"
            "- Issues or feedback? Please [open an issue at GitHub](https://github.com/greywhitebinary/inpatient_feeds_calculator/issues), "
            "or [find me on LinkedIn](https://www.linkedin.com/in/hui-jun-gail-chew/)."
        )
