"""Read AppTest session state in a way that survives Streamlit upgrades."""


def session_state_dict(app):
    """Return the user-visible session state of an AppTest run as a dict.

    Streamlit 1.64 wraps AppTest.session_state in a proxy whose public
    to_dict() replaces the private filtered_state that 1.62 exposes. Using
    to_dict() when it exists keeps these tests green on the pinned version
    and in the dependency canary, which installs the latest release.
    """
    state = app.session_state
    to_dict = getattr(type(state), "to_dict", None)
    if to_dict is not None:
        return to_dict(state)
    return state.filtered_state
