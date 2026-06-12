from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).parent / "formation_viz_app.py"


def test_app_renders_without_exception():
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.run()
    assert not at.exception
