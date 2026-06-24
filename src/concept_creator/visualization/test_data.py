import pickle
from unittest.mock import MagicMock, patch

from visualization import data


def test_list_debug_sessions_query_and_shape():
    record = {"session_id": "7_1", "image_count": 33}
    mock_session = MagicMock()
    mock_session.run.return_value = [record]
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    with patch("neo4j.GraphDatabase.driver", return_value=mock_driver) as drv:
        rows = data.list_debug_sessions("bolt://x", "u", "p")

    drv.assert_called_once_with("bolt://x", auth=("u", "p"))
    query = mock_session.run.call_args.args[0]
    assert "concept_id IS NULL" in query
    assert "session_id" in query
    assert rows == [{"session_id": "7_1", "image_count": 33}]


def test_load_payload_roundtrip(tmp_path):
    p = tmp_path / "x.pkl"
    with p.open("wb") as fh:
        pickle.dump({"meta": {}}, fh)
    assert data.load_payload(p) == {"meta": {}}


def test_runner_cmd_shape(tmp_path):
    cmd, env, cwd = data.runner_invocation("7_1", steps=10,
                                           out_path=tmp_path / "o.pkl")
    assert cmd[1].endswith("visualization/formation_runner.py")
    assert "--session" in cmd and "7_1" in cmd
    assert "--steps" in cmd and "10" in cmd
    assert "--mismatch-threshold" not in cmd
    assert "PYTHONPATH" in env
    assert str(cwd).endswith("src/concept_creator")
