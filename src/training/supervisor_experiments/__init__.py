"""Supporting package for src/training/supervisor_experiments.ipynb.

Notebook cells stay thin; all logic lives here. Import order mirrors
.claude/skills/debug-classification/explain_misclassification.py so the
production classification modules resolve identically.
"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUN_ID = "run_20260630_235356"
RUN_DIR = REPO / "experiments" / RUN_ID

NEO4J_URI = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "111122223333")

for _p in ("common", "src/classification", "src/training"):
    _path = str(REPO / _p)
    if _path not in sys.path:
        sys.path.insert(0, _path)
