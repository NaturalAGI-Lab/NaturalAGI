"""
data.py — Neo4j session listing + runner subprocess plumbing for the viz app.
Must not import from src/ or probes/ (keeps the app decoupled from
concept_creator code; only the runner subprocess imports it).
"""
import os
import pickle
import subprocess
from pathlib import Path

_VIZ_DIR = Path(__file__).parent
CC_DIR = _VIZ_DIR.parent
REPO_DIR = CC_DIR.parent.parent
VENV_PYTHON = REPO_DIR / "natural-agi" / "bin" / "python"
OUTPUT_DIR = _VIZ_DIR / "output"

NEO4J_DSN = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "111122223333")

_SESSIONS_QUERY = (
    "MATCH (n) WHERE n.session_id IS NOT NULL AND n.concept_id IS NULL "
    "RETURN n.session_id AS session_id, "
    "count(DISTINCT n.image_id) AS image_count "
    "ORDER BY session_id"
)


def list_debug_sessions(uri: str = NEO4J_DSN, user: str = NEO4J_USER,
                        password: str = NEO4J_PASSWORD) -> list[dict]:
    import neo4j

    driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            return [
                {"session_id": r["session_id"], "image_count": r["image_count"]}
                for r in session.run(_SESSIONS_QUERY)
            ]
    finally:
        driver.close()


def runner_invocation(session_id: str, steps, mismatch_threshold: float,
                      out_path: Path):
    cmd = [
        str(VENV_PYTHON), "visualization/formation_runner.py",
        "--session", session_id,
        "--mismatch-threshold", str(mismatch_threshold),
        "--out", str(out_path),
    ]
    if steps:
        cmd += ["--steps", str(steps)]
    env = {
        **os.environ,
        "PYTHONPATH": f".:{REPO_DIR}/common",
    }
    return cmd, env, CC_DIR


def stderr_log_path(out_path: Path) -> Path:
    return Path(out_path).with_suffix(".stderr.log")


def launch_runner(session_id: str, steps, mismatch_threshold: float,
                  out_path: Path) -> subprocess.Popen:
    cmd, env, cwd = runner_invocation(session_id, steps, mismatch_threshold, out_path)
    # stderr goes to a file, NOT a pipe: the formation service logs verbosely
    # to stderr, and an unread PIPE buffer would deadlock the runner while the
    # app reads stdout line-by-line for PROGRESS events.
    err_fh = stderr_log_path(out_path).open("w")
    return subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=err_fh, text=True)


def load_payload(path: Path) -> dict:
    # pickle is safe here: payloads are produced exclusively by our own
    # formation_runner subprocess on this machine, never untrusted input.
    with Path(path).open("rb") as fh:
        return pickle.load(fh)
