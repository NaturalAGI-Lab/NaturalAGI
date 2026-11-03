"""Pure-python unit tests (no Docker, Kafka or Neo4j).

Every Nuclio function directory has its own `nuclio_handler.py`, `src/`, `models/`…,
so modules are loaded by file path instead of by package name.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def load_module(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def direction_map():
    return load_module("direction_map", "src/contour_analysis/logic/direction_map.py")


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


def _on_path(relpath: str) -> None:
    path = str(REPO / relpath)
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture(scope="session")
def band_math():
    _on_path("src/concept_creator/src")
    import band_concepts.band_math as module
    return module


@pytest.fixture(scope="session")
def band():
    _on_path("src/classification")
    import band.band_model as model
    import band.band_scorer as scorer
    return model, scorer


@pytest.fixture(scope="session")
def selection():
    _on_path("src/training")
    import fewshot_selection as module
    return module
