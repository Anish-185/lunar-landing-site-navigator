"""Incremental `make derived`: a step is skipped only when its code, inputs and outputs are unchanged."""

import pytest

from pipeline import build_all as ba


def _helper():
    return 1


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(ba, "ROOT", tmp_path)
    monkeypatch.setattr(ba, "STATE", tmp_path / "state.json")
    (tmp_path / "in.txt").write_text("a")
    calls = []

    def run():
        calls.append(1)
        (tmp_path / "out.txt").write_text("done")

    step = ba.Step("demo", run, [_helper], ["in.txt"], ["out.txt"])
    monkeypatch.setattr(ba, "steps", lambda: [step])
    monkeypatch.delenv("FORCE", raising=False)
    return tmp_path, calls, step


def test_runs_then_skips_when_clean(sandbox):
    _, calls, _ = sandbox
    ba.main([])
    ba.main([])
    assert len(calls) == 1


def test_input_change_reruns(sandbox):
    root, calls, _ = sandbox
    ba.main([])
    (root / "in.txt").write_text("b")
    ba.main([])
    assert len(calls) == 2


def test_missing_output_reruns(sandbox):
    root, calls, _ = sandbox
    ba.main([])
    (root / "out.txt").unlink()
    ba.main([])
    assert len(calls) == 2


def test_force_env_and_flag(sandbox, monkeypatch):
    _, calls, _ = sandbox
    ba.main([])
    ba.main(["--force"])
    monkeypatch.setenv("FORCE", "1")
    ba.main([])
    assert len(calls) == 3


def test_code_change_changes_fingerprint(sandbox):
    _, _, step = sandbox
    before = ba.fingerprint(step)
    step.code.append(ba.fingerprint)
    assert ba.fingerprint(step) != before


def test_glob_inputs_and_new_file(sandbox):
    root, _, step = sandbox
    step.inputs = ["d/*.txt"]
    (root / "d").mkdir()
    (root / "d" / "1.txt").write_text("x")
    fp = ba.fingerprint(step)
    (root / "d" / "2.txt").write_text("y")
    assert ba.fingerprint(step) != fp


def test_real_steps_have_unique_names_and_outputs():
    names = [s.name for s in ba.steps()]
    assert len(names) == len(set(names))
    assert all(s.outputs for s in ba.steps())
