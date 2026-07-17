"""Section 7 (Tier C, DESTRUCTIVE): retrains for sample-count downstream (S3)
and augmentation (S4) studies.

Every driver here mutates Neo4j concepts. The backup gate (infra.BACKUP_PATH)
must exist; restore with restore_baseline("yes") between/after conditions.
"""
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from . import REPO
from .formation_lab import ALL_CONCEPTS
from .infra import BACKUP_PATH, driver, restore_neo4j, timer

SUBSETS_ROOT = REPO / "datasets" / "train_subsets"
TRAIN_ROOT = REPO / "datasets" / "train"
_AUG_RE = re.compile(r"_aug(\d+)\.png$")


def ensure_backup() -> None:
    if not BACKUP_PATH.exists():
        raise RuntimeError(
            f"Немає бекапа {BACKUP_PATH} — виконайте клітинку бекапа в Секції 0 "
            f"перед будь-якими ретренами."
        )


def _training_helpers():
    sys.path.insert(0, str(REPO / "src" / "training"))
    from infrastructure import (reload_concept_cache, verify_concept_created,
                                wait_for_kafka_idle)
    from pipeline import remove_concept
    return reload_concept_cache, verify_concept_created, wait_for_kafka_idle, remove_concept


def subset_n(n: int, seed: int):
    """Selector: n випадкових файлів на концепт."""
    def select(files: list[Path]) -> list[Path]:
        if len(files) <= n:
            return files
        return sorted(random.Random(seed).sample(files, n))
    return select


def aug_cap(max_aug: int):
    """Selector: лише файли з індексом аугментації ≤ max_aug (1 ≈ без аугментації)."""
    def select(files: list[Path]) -> list[Path]:
        keep = []
        for f in files:
            m = _AUG_RE.search(f.name)
            if m is None or int(m.group(1)) <= max_aug:
                keep.append(f)
        return keep
    return select


def build_condition_dirs(condition: str, selector,
                         source_root: Path = TRAIN_ROOT,
                         concepts: list[str] = ALL_CONCEPTS) -> Path:
    """Copy selected sample files into datasets/train_subsets/<condition>/<cid>/."""
    root = SUBSETS_ROOT / condition
    counts = {}
    for cid in concepts:
        src = source_root / cid
        dst = root / cid
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        files = selector(sorted(src.glob("*.png")))
        for f in files:
            shutil.copy2(f, dst / f.name)
        counts[cid] = len(files)
    print(f"{condition}: {sum(counts.values())} файлів — {counts}")
    return root


def _ingest_dir(container_path: str, session_id: str, concept_name: str) -> None:
    subprocess.run(
        ["make", "send_to_connector",
         "OPERATION=train",
         f"NUCLIO_STORAGE={container_path}",
         f"SESSION_ID={session_id}",
         f"CONCEPT_NAME={concept_name}",
         "SUBCLASS="],
        cwd=REPO, check=True, capture_output=True, text=True,
    )


def retrain_from(condition_root: Path, confirm: str = "",
                 concepts: list[str] = ALL_CONCEPTS) -> pd.DataFrame:
    """DESTRUCTIVE: replace each concept with one formed from condition_root/<cid>/.

    Formation crashes are recorded as results (crash rate is a first-class
    metric for the augmentation study), not raised.
    """
    if confirm != "yes":
        raise ValueError('Set confirm="yes" — ця операція замінює концепти в Neo4j.')
    ensure_backup()
    reload_cache, verify_created, wait_idle, remove_concept = _training_helpers()

    rel = condition_root.relative_to(REPO / "datasets")
    rows = []
    for cid in concepts:
        cls = cid.split("_")[0]
        with timer(f"retrain {cid}"):
            try:
                remove_concept(cid)
            except Exception as exc:
                print(f"  {cid}: remove_concept: {exc}")
            _ingest_dir(f"/opt/nuclio/shared_storage/{rel}/{cid}", cid, f"mnist_{cls}")
            wait_idle(topic="contour-analysis-output-topic", idle_timeout=10,
                      bootstrap_servers="localhost:29092")
            proc = subprocess.run(
                ["make", "create_concept", cid, f"mnist-{cls}"],
                cwd=REPO, capture_output=True, text=True,
            )
            created = proc.returncode == 0 and verify_created(cid)
            rows.append({
                "concept_id": cid,
                "created": created,
                "error": "" if created else (proc.stdout + proc.stderr)[-300:],
            })
    reload_cache()
    df = pd.DataFrame(rows)
    print(f"Створено {int(df.created.sum())}/{len(df)} концептів; кеш перезавантажено.")
    return df


def concept_node_counts() -> dict[str, int]:
    with driver().session() as s:
        result = s.run(
            "MATCH (n) WHERE n.concept_id IS NOT NULL AND (n:Point OR n:Vector) "
            "RETURN n.concept_id AS cid, count(n) AS nodes ORDER BY cid"
        )
        return {r["cid"]: r["nodes"] for r in result}


def restore_baseline(confirm: str = "") -> None:
    """DESTRUCTIVE: wipe Neo4j, restore the baseline backup, reload caches."""
    restore_neo4j(confirm)
    reload_cache, *_ = _training_helpers()
    reload_cache()
    print("Базлайн відновлено; кеш класифікації перезавантажено.")
