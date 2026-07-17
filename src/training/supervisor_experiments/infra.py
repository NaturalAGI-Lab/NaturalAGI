"""Infrastructure helpers: Neo4j driver, health checks, volume backup/restore."""
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

from neo4j import GraphDatabase

from . import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, REPO

EXPECTED_CONCEPTS = 13
EXPECTED_IMAGES = 8685
BACKUP_PATH = REPO / "backups" / "neo4j_baseline_2026-07-17.tar.gz"
NEO4J_CONTAINER = "naturalagi-neo4j-1"

_driver = None


def driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def _single_value(session, query: str):
    record = session.run(query).single()
    if record is None:
        raise RuntimeError(f"Query returned no rows: {query}")
    return record["c"]


def neo4j_counts() -> dict:
    with driver().session() as session:
        concepts = _single_value(
            session,
            "MATCH (n) WHERE n.concept_id IS NOT NULL "
            "RETURN count(DISTINCT n.concept_id) AS c",
        )
        images = _single_value(
            session,
            "MATCH (n) WHERE n.image_id IS NOT NULL "
            "RETURN count(DISTINCT n.image_id) AS c",
        )
    return {"concepts": concepts, "images": images}


def docker_status(name_filter: str = "") -> list[str]:
    out = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
        capture_output=True, text=True,
    ).stdout
    return [line for line in out.splitlines() if name_filter in line]


def health_check() -> dict:
    running = docker_status()
    counts = neo4j_counts()
    report = {
        "neo4j_container_up": any(NEO4J_CONTAINER in line for line in running),
        "kafka_up": any("kafka" in line for line in running),
        "nuclio_functions_up": sum(1 for line in running if "nuclio-nuclio-" in line),
        **counts,
        "baseline_state_intact": (
            counts["concepts"] == EXPECTED_CONCEPTS
            and counts["images"] == EXPECTED_IMAGES
        ),
        "backup_exists": BACKUP_PATH.exists(),
    }
    return report


def neo4j_volume_name() -> str:
    out = subprocess.run(
        ["docker", "inspect", NEO4J_CONTAINER, "--format",
         "{{range .Mounts}}{{.Name}} {{.Destination}}\n{{end}}"],
        capture_output=True, text=True, check=True,
    ).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == "/data":
            return parts[0]
    raise RuntimeError(f"No /data volume mount found on {NEO4J_CONTAINER}: {out!r}")


def _compose(*args: str) -> None:
    subprocess.run(["docker", "compose", *args], cwd=REPO, check=True)


def _wait_for_neo4j(timeout_s: int = 120) -> None:
    close_driver()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            neo4j_counts()
            return
        except Exception:
            time.sleep(3)
    raise TimeoutError("Neo4j did not come back up in time")


def backup_neo4j(confirm: str = "") -> Path:
    """Cold backup of the Neo4j data volume. Pass confirm="yes" to run."""
    if confirm != "yes":
        raise ValueError('Set confirm="yes" to run the backup (stops Neo4j briefly).')
    volume = neo4j_volume_name()
    BACKUP_PATH.parent.mkdir(exist_ok=True)
    _compose("stop", "neo4j")
    try:
        subprocess.run(
            ["docker", "run", "--rm",
             "-v", f"{volume}:/data",
             "-v", f"{BACKUP_PATH.parent}:/backup",
             "alpine", "tar", "czf", f"/backup/{BACKUP_PATH.name}", "-C", "/", "data"],
            check=True,
        )
    finally:
        _compose("start", "neo4j")
    _wait_for_neo4j()
    size_mb = BACKUP_PATH.stat().st_size / 1e6
    print(f"Backup OK: {BACKUP_PATH} ({size_mb:.0f} MB); counts={neo4j_counts()}")
    return BACKUP_PATH


def restore_neo4j(confirm: str = "") -> None:
    """DESTRUCTIVE: wipe the Neo4j volume and restore the baseline backup."""
    if confirm != "yes":
        raise ValueError('Set confirm="yes" to restore (WIPES current Neo4j data).')
    if not BACKUP_PATH.exists():
        raise FileNotFoundError(f"No backup at {BACKUP_PATH} — refusing to wipe.")
    volume = neo4j_volume_name()
    _compose("stop", "neo4j")
    try:
        subprocess.run(
            ["docker", "run", "--rm",
             "-v", f"{volume}:/data",
             "-v", f"{BACKUP_PATH.parent}:/backup",
             "alpine", "sh", "-c",
             f"rm -rf /data/* /data/..?* /data/.[!.]* ; "
             f"tar xzf /backup/{BACKUP_PATH.name} -C /"],
            check=True,
        )
    finally:
        _compose("start", "neo4j")
    _wait_for_neo4j()
    counts = neo4j_counts()
    ok = counts == {"concepts": EXPECTED_CONCEPTS, "images": EXPECTED_IMAGES}
    print(f"Restore {'OK' if ok else 'MISMATCH'}: counts={counts}")


@contextmanager
def timer(label: str):
    start = time.monotonic()
    yield
    print(f"[{label}] elapsed {time.monotonic() - start:.1f}s")
