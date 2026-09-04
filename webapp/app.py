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

WORKSPACE_TABS = ("Formulary", "Assessment", "EN plan", "Propofol")


def _open_workspace_tab(tab_label: str) -> None:
    """Open a top-level calculator tab from a footer navigation strip."""
    st.session_state.workspace_tab = tab_label


def _tab_key(tab_label: str) -> str:
    return tab_label.lower().replace(" ", "_")


def render_workspace_navigation(active_tab: str) -> None:
    """Mirror the workspace tabs at the bottom of each tab panel."""
    active_key = _tab_key(active_tab)
    with st.container(key=f"workspace_navigation_{active_key}"):
        columns = st.columns(len(WORKSPACE_TABS))
        for position, tab_label in enumerate(WORKSPACE_TABS):
            if tab_label == active_tab:
                continue
            tab_key = _tab_key(tab_label)
            columns[position].button(
                tab_label,
                type="tertiary",
                key=f"workspace_nav_{active_key}_{tab_key}",
                on_click=_open_workspace_tab,
                args=(tab_label,),
            )


def main() -> None:
    initialise_state()
    apply_wireframe_theme()
    record_label = render_case_record_actions()
    render_record_title(record_label)
    with st.container(key="pagenote"):
        st.caption(
            "Adult Inpatient Enteral Nutrition Calculator, a [Feed. Form. Flow.]"
            "(https://feedformflow.substack.com/p/feed-form-flow) project. "
            "Uses Canadian formula, modular, and ONS product information.  \n"
            "Work left to right: set up "
            "My Formulary, complete the assessment, build an EN plan, and review the totals."
        )
    formulary_tab, assessment_tab, plan_tab, propofol_tab = st.tabs(
        ["Formulary", "Assessment", "EN plan", "Propofol"],
        default="Formulary",
        key="workspace_tab",
        on_change="rerun",
    )
    with formulary_tab:
        show_formulary()
        render_workspace_navigation("Formulary")
    with assessment_tab:
        show_assessment()
        render_workspace_navigation("Assessment")
    with plan_tab:
        show_en_plan()
        render_workspace_navigation("EN plan")
    with propofol_tab:
        show_icu_propofol()
        render_workspace_navigation("Propofol")
    render_footer()


if __name__ == "__main__":
    main()
