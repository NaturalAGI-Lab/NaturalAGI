import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import neo4j
import pandas as pd
from streamlit.testing.v1 import AppTest

DASHBOARD = os.path.join(os.path.dirname(__file__), "dashboard.py")


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def run(self, *a, **k):
        return []


class _FakeDriver:
    def session(self):
        return _FakeSession()

    def close(self):
        pass


def _make_run(tmp_path):
    run = tmp_path / "training_results" / "run_test"
    run.mkdir(parents=True)
    pd.DataFrame([{
        "image_id": "img1", "image_path": "/x/7.png",
        "expected": "7", "predicted": "3", "status": "success",
        "classification_results": '[{"concept_id": "3_1", "is_minor": true, "similarity": 0.74}, '
                                  '{"concept_id": "7_1", "is_minor": true, "similarity": 0.67}]',
    }]).to_csv(run / "incorrect_results.csv", index=False)
    return run


def test_dashboard_drilldown_renders(tmp_path, monkeypatch):
    _make_run(tmp_path)
    monkeypatch.chdir(tmp_path)
    # Patch the shared neo4j class object so every `from neo4j import GraphDatabase`
    # in the executed script resolves to the fake (no live Neo4j needed). Empty
    # query results → "No concept of class 7" branch renders deterministically.
    monkeypatch.setattr(neo4j.GraphDatabase, "driver", lambda *a, **k: _FakeDriver())

    at = AppTest.from_file(DASHBOARD, default_timeout=60).run()

    assert not at.exception
    assert any("No concept of class" in i.value for i in at.info)
