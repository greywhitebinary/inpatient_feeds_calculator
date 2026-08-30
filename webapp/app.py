"""Adult Inpatient Enteral Nutrition Calculator — Streamlit entry point.

This application is a reviewable calculation workspace. It does not provide
autonomous clinical recommendations. It has no server-side patient-record
storage; clinicians can voluntarily download and later upload a local case file.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Adult Inpatient EN Calculator", layout="wide")

from assessment_ui import show_assessment
from case_record_ui import render_case_record_actions, render_footer
from formulary_ui import show_formulary
from plan_ui import show_en_plan
from propofol_ui import show_icu_propofol
from session_state import initialise_state
from ui_common import apply_wireframe_theme, render_record_title


def main() -> None:
    initialise_state()
    apply_wireframe_theme()
    record_label = render_case_record_actions()
    render_record_title(record_label)
    with st.container(key="pagenote"):
        st.caption(
            "Adult Inpatient Enteral Nutrition Calculator: a [Feed. Form. Flow.]"
            "(https://feedformflow.substack.com/p/feed-form-flow) project. "
            "First time here? Load the example record. Work left to right: set up "
            "My Formulary, complete the assessment, build an EN plan, and review the totals."
        )
    formulary_tab, assessment_tab, plan_tab, propofol_tab = st.tabs(
        ["Formulary", "Assessment", "EN plan", "Propofol"]
    )
    with formulary_tab:
        show_formulary()
    with assessment_tab:
        show_assessment()
    with plan_tab:
        show_en_plan()
    with propofol_tab:
        show_icu_propofol()
    render_footer()


if __name__ == "__main__":
    main()
