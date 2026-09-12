"""Ordinary search text must not be interpreted as a regular expression."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


@pytest.mark.parametrize("key", ["feed_search", "modular_search", "ons_search"])
def test_search_punctuation_is_literal(key):
    app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
    app.text_input(key=key).set_value("(").run(timeout=30)
    assert not app.exception
    # Clearing a search restores a usable reference list after punctuation.
    app.text_input(key=key).set_value("").run(timeout=30)
    assert not app.exception
