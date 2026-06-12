import os
import pickle
import subprocess
import sys
from pathlib import Path

CC_DIR = Path(__file__).parent.parent
REPO = CC_DIR.parent.parent
FIXTURE = CC_DIR / "probes" / "repro" / "sample_data" / "seven_flipped"


def test_runner_cli_roundtrip(tmp_path):
    out = tmp_path / "run.pkl"
    proc = subprocess.run(
        [sys.executable, "visualization/formation_runner.py",
         "--samples-dir", str(FIXTURE), "--out", str(out)],
        cwd=CC_DIR,
        env={**os.environ, "PYTHONPATH": f".:{REPO}/common"},
        capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    assert "PROGRESS step=" in proc.stdout
    assert "DONE steps=3 verdict=SUSPECT" in proc.stdout
    # pickle is safe here: the payload comes from our own runner subprocess
    # launched two lines above, never from an untrusted source.
    with out.open("rb") as fh:
        payload = pickle.load(fh)
    assert len(payload["steps"]) == 3
